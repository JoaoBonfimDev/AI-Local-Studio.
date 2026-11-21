"""Frame-accurate local cuts and MP4 assembly with FFmpeg.

Intermediate clips are produced sequentially to keep RAM/VRAM bounded.
Original media is strictly read-only; final output is atomic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
from collections import deque
from typing import Callable
import time

from .media import MediaError, MediaInfo, probe, require_tools
from .planner import validate_timeline
from .progress import Progress


# Same resolution/FPS as the source; stronger settings reduce generational loss.
# "ultra" is deliberately generous with bitrate and temporary disk usage.
QUALITY_PRESETS = {
    "balanced": {"label": "Equilibrada", "nvenc_preset": "p4", "cq": 21, "cpu_preset": "faster", "crf": 20, "audio": "192k"},
    "high": {"label": "Alta qualidade", "nvenc_preset": "p6", "cq": 17, "cpu_preset": "slow", "crf": 17, "audio": "256k"},
    "ultra": {"label": "Qualidade máxima", "nvenc_preset": "p7", "cq": 14, "cpu_preset": "slow", "crf": 14, "audio": "320k"},
}


def _ffmpeg(
    command: list[str], label: str, *, cwd: Path | None = None,
    progress_total: float | None = None,
    on_progress: Callable[[float], None] | None = None,
    console_progress: bool = True,
) -> None:
    if progress_total is None:
        completed = subprocess.run(command, text=True, capture_output=True, cwd=cwd, check=False)
        if completed.returncode:
            raise MediaError(f"{label}: {completed.stderr.strip()[-1800:]}")
        return

    # Parse FFmpeg's structured progress; do not wait silently for long clips.
    command = command[:1] + ["-progress", "pipe:2", "-stats_period", "1"] + command[1:]
    process = subprocess.Popen(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        cwd=cwd, text=True, encoding="utf-8", errors="replace",
    )
    assert process.stderr is not None
    reporter = Progress(label, progress_total) if console_progress else None
    messages: deque[str] = deque(maxlen=30)
    with process.stderr:
        for raw in process.stderr:
            line = raw.strip()
            messages.append(line)
            if line.startswith("out_time_us="):
                try:
                    position = int(line.split("=", 1)[1]) / 1_000_000
                    if reporter:
                        reporter.update(position)
                    if on_progress:
                        on_progress(min(progress_total, max(0.0, position)))
                except ValueError:
                    pass
    result = process.wait()
    if result:
        if console_progress:
            print()  # End any partial progress line before reporting failure.
        raise MediaError(f"{label}: {' '.join(messages)[-1800:]}")
    if reporter:
        reporter.done()
    if on_progress:
        on_progress(progress_total)


def _nvenc_available() -> bool:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return p.returncode == 0 and "h264_nvenc" in p.stdout


def _source_matches(info: MediaInfo, source: dict) -> bool:
    return (
        str(info.path) == str(Path(source["path"]).expanduser().resolve())
        and info.size == int(source.get("size", -1))
        and info.mtime_ns == int(source.get("mtime_ns", -1))
        and abs(info.duration - float(source["duration"])) < .2
    )


def render_timeline(
    timeline: dict, output: str | Path, *, encoder: str = "auto",
    quality: str = "balanced", force: bool = False,
    on_event: Callable[[dict], None] | None = None,
    console_progress: bool = True,
) -> Path:
    """Render a reviewed timeline into H.264/AAC MP4; no external APIs used."""
    validate_timeline(timeline)
    require_tools()
    if encoder not in {"auto", "cpu", "nvenc"}:
        raise ValueError("Encoder deve ser auto, cpu ou nvenc")
    if quality not in QUALITY_PRESETS:
        raise ValueError(f"Qualidade inválida. Opções: {', '.join(QUALITY_PRESETS)}")
    profile = QUALITY_PRESETS[quality]
    info = probe(timeline["source"]["path"])
    if not _source_matches(info, timeline["source"]):
        raise MediaError("O vídeo original mudou após a análise. Gere uma nova timeline.")
    destination = Path(output).expanduser().resolve()
    if destination.suffix.lower() != ".mp4":
        raise MediaError("A saída precisa ter extensão .mp4")
    if destination == info.path:
        raise MediaError("Não é permitido sobrescrever o vídeo original.")
    if destination.exists() and not force:
        raise FileExistsError(f"Arquivo já existe: {destination}. Use outro nome ou --force.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    use_nvenc = encoder in {"auto", "nvenc"} and _nvenc_available()
    if encoder == "nvenc" and not use_nvenc:
        raise MediaError("Este FFmpeg não oferece h264_nvenc; tente --encoder cpu")

    total_seconds = sum(float(c["end"]) - float(c["start"]) for c in timeline["clips"])
    started = time.monotonic()

    def report(stage: str, percent: float, message: str, **extra) -> None:
        if on_event:
            on_event({
                "stage": stage, "percent": round(min(100.0, max(0.0, percent)), 2),
                "message": message, "elapsed": round(time.monotonic() - started, 2),
                "encoder": "NVENC / GPU" if use_nvenc else "H.264 / CPU",
                "quality": quality, **extra,
            })

    report("preparing", 0, "Preparando renderização em alta fidelidade")

    with tempfile.TemporaryDirectory(prefix="age-render-", dir=destination.parent) as tmp_name:
        temp = Path(tmp_name)
        generated: list[Path] = []
        rendered_seconds = 0.0
        for i, clip in enumerate(timeline["clips"], start=1):
            path = temp / f"clip_{i:05d}.mp4"
            start, duration = float(clip["start"]), float(clip["end"]) - float(clip["start"])
            if console_progress:
                print(f"[render] trecho {i}/{len(timeline['clips'])}: {start:.1f}s → {start + duration:.1f}s", flush=True)

            def encode(nvenc: bool) -> None:
                options = ([
                    "-c:v", "h264_nvenc", "-preset", profile["nvenc_preset"],
                    "-tune", "hq", "-rc", "vbr", "-cq", str(profile["cq"]), "-b:v", "0",
                ] if nvenc else [
                    "-c:v", "libx264", "-preset", profile["cpu_preset"],
                    "-crf", str(profile["crf"]), "-threads", "4",
                ])
                command = [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-ss", f"{start:.6f}", "-i", str(info.path),
                    "-t", f"{duration:.6f}", "-map", "0:v:0",
                ]
                if info.has_audio:
                    command.extend(["-map", "0:a:0"])
                command.extend([
                    "-vf", "scale=ceil(iw/2)*2:ceil(ih/2)*2",
                    *options, "-pix_fmt", "yuv420p", "-r", info.fps,
                    "-fps_mode", "cfr",
                ])
                if info.has_audio:
                    command.extend(["-c:a", "aac", "-b:a", profile["audio"], "-ar", "48000", "-ac", "2"])
                else:
                    command.append("-an")
                command.append(str(path))
                def progress(seconds: float) -> None:
                    elapsed = time.monotonic() - started
                    completed = rendered_seconds + seconds
                    remaining = max(0, total_seconds - completed)
                    speed = completed / elapsed if elapsed > 1 else 0
                    report(
                        "rendering", 88 * completed / max(.01, total_seconds),
                        f"Renderizando trecho {i} de {len(timeline['clips'])}",
                        clip_index=i, clip_total=len(timeline["clips"]),
                        clip_percent=round(100 * seconds / max(.01, duration), 1),
                        video_done=round(completed, 1), video_total=round(total_seconds, 1),
                        eta=round(remaining / speed, 1) if speed > .01 else None,
                    )

                _ffmpeg(command, f"render {i}/{len(timeline['clips'])}", progress_total=duration, on_progress=progress, console_progress=console_progress)

            try:
                encode(use_nvenc)
            except MediaError:
                if encoder != "auto" or not use_nvenc:
                    raise
                if console_progress:
                    print("[render] NVENC indisponível nesta máquina; usando CPU para este e os demais trechos.", flush=True)
                use_nvenc = False
                report("rendering", 88 * rendered_seconds / max(.01, total_seconds), "GPU indisponível; renderização pela CPU")
                encode(False)
            generated.append(path)
            rendered_seconds += duration

        # Reference only files created by this run, with safe relative filenames.
        concat = temp / "lista.txt"
        concat.write_text("".join(f"file '{path.name}'\n" for path in generated), encoding="utf-8")
        complete = temp / "final.mp4"
        if console_progress:
            print("[render] Unindo os trechos e finalizando o MP4...", flush=True)
        join_started = time.monotonic()

        def joining_progress(seconds: float) -> None:
            elapsed = max(.001, time.monotonic() - join_started)
            speed = seconds / elapsed
            report(
                "joining", 88 + 10 * seconds / max(.01, total_seconds),
                "Unindo cortes e preparando o arquivo final",
                video_done=round(seconds, 1), video_total=round(total_seconds, 1),
                eta=round((total_seconds - seconds) / speed, 1) if speed > .01 else None,
                clip_index=len(timeline["clips"]), clip_total=len(timeline["clips"]),
            )

        report("joining", 88, "Iniciando montagem final")
        _ffmpeg([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "concat", "-safe", "0", "-i", "lista.txt",
            "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy",
            "-movflags", "+faststart", str(complete),
        ], "junção", cwd=temp, progress_total=total_seconds, on_progress=joining_progress, console_progress=console_progress)
        report("verifying", 99, "Validando integridade do arquivo final")
        if complete.stat().st_size == 0 or probe(complete).duration <= 0:
            raise MediaError("O arquivo renderizado não passou na validação.")
        os.replace(complete, destination)
        report("completed", 100, "Vídeo finalizado com sucesso")
        return destination


def read_timeline(path: str | Path) -> dict:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        result = json.load(handle)
    validate_timeline(result)
    return result
