"""Private localhost rendering dashboard with live progress and ETA.

No framework, CDN, accounts or network APIs. The server binds to 127.0.0.1
only. It starts one render job, serves its current status, and exposes no
remote-control or arbitrary command execution endpoint.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import webbrowser

from .render import QUALITY_PRESETS, render_timeline


class RenderState:
    def __init__(self, timeline: dict, output: str | Path, quality: str) -> None:
        self.lock = threading.Lock()
        source = timeline["source"]
        self.data = {
            "stage": "preparing",
            "percent": 0.0,
            "message": "Preparando seu vídeo",
            "input": Path(source["path"]).name,
            "output": str(Path(output).expanduser().resolve()),
            "clip_total": len(timeline["clips"]),
            "clip_index": 0,
            "video_total": round(sum(float(c["end"]) - float(c["start"]) for c in timeline["clips"]), 1),
            "video_done": 0,
            "quality": quality,
            "quality_label": QUALITY_PRESETS[quality]["label"],
            "resolution": f"{source['width']} × {source['height']}",
            "encoder": "Detectando codificador",
            "elapsed": 0,
            "eta": None,
        }

    def update(self, changes: dict) -> None:
        with self.lock:
            if "percent" in changes:
                changes = dict(changes)
                changes["percent"] = max(float(self.data.get("percent", 0)), float(changes["percent"]))
            self.data.update(changes)

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.data)


class RenderServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, state: RenderState) -> None:
        self.render_state = state
        self.document = (Path(__file__).parent / "assets" / "studio.html").read_bytes()
        super().__init__(("127.0.0.1", 0), DashboardHandler)


class DashboardHandler(BaseHTTPRequestHandler):
    server: RenderServer

    def log_message(self, format, *args) -> None:  # noqa: A002
        # Do not spam the user's terminal for each progress poll.
        return

    def _reply(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:",
        )
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._reply(self.server.document, "text/html; charset=utf-8")
        elif self.path == "/api/status":
            data = json.dumps(self.server.render_state.snapshot(), ensure_ascii=False).encode("utf-8")
            self._reply(data, "application/json; charset=utf-8")
        else:
            self._reply(b"Not found", "text/plain; charset=utf-8", 404)

    def do_POST(self) -> None:
        if self.path != "/api/close":
            self._reply(b"Not found", "text/plain; charset=utf-8", 404)
            return
        if self.server.render_state.snapshot()["stage"] not in ("completed", "error"):
            self._reply("Renderização em andamento".encode("utf-8"), "text/plain; charset=utf-8", 409)
            return
        self._reply(b'{"ok":true}', "application/json; charset=utf-8")
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def render_with_dashboard(
    timeline: dict, output: str | Path, *, encoder: str = "auto",
    quality: str = "high", force: bool = False, open_browser: bool = True,
) -> RenderState:
    """Run a render in the background while serving a live localhost dashboard.

    The dashboard remains available after completion until the user presses
    'Encerrar painel' in the browser or Ctrl+C in the terminal.
    """
    state = RenderState(timeline, output, quality)
    server = RenderServer(state)
    url = f"http://127.0.0.1:{server.server_address[1]}/"

    def job() -> None:
        try:
            result = render_timeline(
                timeline, output, encoder=encoder, quality=quality,
                force=force, on_event=state.update, console_progress=False,
            )
            state.update({"stage": "completed", "percent": 100, "message": "Renderização concluída!", "output": str(result), "eta": 0})
            print(f"[pronto] {result}", flush=True)
        except Exception as exc:
            state.update({"stage": "error", "message": str(exc), "eta": None})
            print(f"[erro] {exc}", flush=True)

    threading.Thread(target=job, name="render-job", daemon=True).start()
    print(f"[painel] Acompanhe a renderização em: {url}", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            print("[painel] Não foi possível abrir a aba automaticamente. Cole o endereço acima no navegador.")
    try:
        server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:
        print("\n[painel] Encerrando. Se ainda estiver renderizando, aguarde antes de fechar o terminal.")
    finally:
        server.server_close()
    return state
