"""CLI for local game-play editing; Windows-compatible, no paid services."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from gameplay_editor import __version__
from gameplay_editor.media import MediaError, build_activity, probe, require_tools, scan_audio, scan_motion
from gameplay_editor.planner import make_timeline
from gameplay_editor.render import read_timeline, render_timeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Gameplay Editor — gameplay completo ou melhores momentos, 100% local."
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Confere Python, FFmpeg e FFprobe")
    for command in ("analyze", "run"):
        cmd = sub.add_parser(command, help="Analisa e planeja" + ("; depois renderiza" if command == "run" else ""))
        cmd.add_argument("--input", required=True, help="Arquivo gravado pelo OBS (MP4, MKV etc.)")
        cmd.add_argument("--output-dir", required=True, help="Pasta para análise, timeline e resultado")
        cmd.add_argument("--mode", choices=("full", "highlights", "completo", "melhores"), required=True)
        cmd.add_argument("--sensitivity", type=int, default=50, help="0–100; apenas melhores momentos (padrão: 50)")
        cmd.add_argument("--min-idle", type=float, default=20.0, help="Segundos de inatividade a remover (padrão: 20)")
        cmd.add_argument("--audio-floor", type=float, default=.008, help="Limite de silêncio RMS, 0..1 (padrão conservador: 0.008)")
        cmd.add_argument("--motion-floor", type=float, default=.065, help="Limite de pouca movimentação, 0..1 (padrão: 0.065)")
        cmd.add_argument("--sample-seconds", type=int, default=3, help="Intervalo entre amostras visuais (padrão: 3)")
        cmd.add_argument("--decode", choices=("auto", "cpu", "gpu"), default="auto", help="Leitura de frames: GPU NVDEC se disponível (padrão: auto)")
        cmd.add_argument("--rescan", action="store_true", help="Ignora o cache e analisa o vídeo novamente")
        cmd.add_argument("--force", action="store_true", help="Permite substituir arquivos de saída existentes")
        if command == "run":
            cmd.add_argument("--encoder", choices=("auto", "cpu", "nvenc"), default="auto")
            cmd.add_argument("--quality", choices=("balanced", "high", "ultra"), default="high")
            ui = cmd.add_mutually_exclusive_group()
            ui.add_argument("--ui", action="store_true", help="Abre painel visual de renderização")
            ui.add_argument("--terminal", action="store_true", help="Força a barra de progresso apenas no terminal")
    render = sub.add_parser("render", help="Renderiza uma timeline JSON, inclusive após edição manual")
    render.add_argument("--timeline", required=True, help="Caminho do timeline_*.json")
    render.add_argument("--output", required=True, help="Arquivo final .mp4")
    render.add_argument("--encoder", choices=("auto", "cpu", "nvenc"), default="auto")
    render.add_argument("--quality", choices=("balanced", "high", "ultra"), default="high", help="Qualidade do MP4: balanced, high ou ultra")
    ui = render.add_mutually_exclusive_group()
    ui.add_argument("--ui", action="store_true", help="Abre uma aba do navegador com progresso visual")
    ui.add_argument("--terminal", action="store_true", help="Usa apenas o PowerShell")
    render.add_argument("--force", action="store_true")
    return parser


def _doctor() -> None:
    print(f"AI Gameplay Editor {__version__} | Python {sys.version.split()[0]}")
    for tool in ("ffmpeg", "ffprobe"):
        binary = shutil.which(tool)
        if not binary:
            print(f"[FALTA] {tool}: instale FFmpeg e adicione-o ao PATH")
        else:
            result = subprocess.run([binary, "-version"], capture_output=True, text=True)
            print(f"[OK] {tool}: {result.stdout.splitlines()[0] if result.stdout else binary}")
    require_tools()
    hw = subprocess.run(["ffmpeg", "-hide_banner", "-hwaccels"], capture_output=True, text=True)
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    print(f"[GPU] FFmpeg com suporte CUDA: {'sim' if 'cuda' in hw.stdout.splitlines() else 'não'}")
    print(f"[GPU] FFmpeg com encoder NVENC: {'sim' if 'h264_nvenc' in enc.stdout else 'não'}")
    print("[GPU] A compatibilidade real será testada com o vídeo no comando analyze/run.")
    print("[OK] Pronto para processamento local; nenhum login ou API necessários.")


def _write_json(path: Path, value: dict, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"O arquivo já existe: {path}. Use outra pasta ou --force.")
    # Write atomically; no partially overwritten JSON if interrupted.
    temporary = path.with_name(path.name + ".writing")
    try:
        with temporary.open("w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _analyze(args: argparse.Namespace) -> tuple[dict, Path]:
    if not 0 <= args.sensitivity <= 100:
        raise ValueError("--sensitivity deve estar entre 0 e 100")
    if args.min_idle < 1 or args.sample_seconds < 1:
        raise ValueError("--min-idle e --sample-seconds precisam ser >= 1")
    if not 0 <= args.audio_floor <= 1 or not 0 <= args.motion_floor <= 1:
        raise ValueError("--audio-floor e --motion-floor precisam estar entre 0 e 1")
    mode = {"completo": "full", "melhores": "highlights"}.get(args.mode, args.mode)
    info = probe(args.input)
    directory = Path(args.output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    timeline_path = directory / f"timeline_{mode}.json"
    analysis_path = directory / "analise.json"
    if timeline_path.exists() and not args.force:
        raise FileExistsError(f"Timeline já existe: {timeline_path}. Use outra pasta ou --force.")

    analysis = None
    if analysis_path.is_file() and not args.rescan:
        try:
            old = json.loads(analysis_path.read_text(encoding="utf-8"))
            if (old.get("source") == info.source_record()
                    and old.get("sample_seconds") == args.sample_seconds):
                analysis = old
                print("[cache] Reutilizando a análise audiovisual existente.")
        except (ValueError, OSError):
            pass
    if analysis is None:
        print(f"[scan] Vídeo: {info.duration / 60:.1f} min | {info.width}x{info.height} | áudio: {info.has_audio}")
        print("[scan] Analisando áudio localmente...", flush=True)
        audio = scan_audio(info)
        print("[scan] Analisando movimento (frames amostrados)...", flush=True)
        motion = scan_motion(info, every_seconds=args.sample_seconds, decode=args.decode)
        scores = build_activity(audio, motion)
        analysis = {
            "schema_version": 1,
            "source": info.source_record(),
            "sample_seconds": args.sample_seconds,
            "decode_requested": args.decode,
            "audio_rms": audio,
            "motion": motion,
            "activity": scores,
        }
        _write_json(analysis_path, analysis, overwrite=args.force or analysis_path.exists())

    timeline = make_timeline(
        source=info.source_record(), mode=mode,
        audio=analysis["audio_rms"], motion=analysis["motion"],
        activity=analysis["activity"], sensitivity=args.sensitivity, min_idle=args.min_idle,
        audio_floor=args.audio_floor, motion_floor=args.motion_floor,
    )
    _write_json(timeline_path, timeline, overwrite=args.force)
    print(f"[timeline] {timeline_path}")
    summary = timeline["summary"]
    print(f"[plano] {summary['clip_count']} trechos | {summary['selected_seconds']/60:.1f} min selecionados de {info.duration/60:.1f} min.")
    if not timeline["clips"]:
        print("[aviso] Nenhum destaque acima do limiar. Ajuste --sensitivity ou revise a gravação.")
    return timeline, timeline_path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            _doctor()
        elif args.command == "render":
            timeline = read_timeline(args.timeline)
            if args.ui or (sys.platform == "win32" and not args.terminal):
                from gameplay_editor.studio import render_with_dashboard
                job = render_with_dashboard(timeline, args.output, encoder=args.encoder, quality=args.quality, force=args.force)
                if job.snapshot()["stage"] == "error":
                    return 1
            else:
                result = render_timeline(timeline, args.output, encoder=args.encoder, quality=args.quality, force=args.force)
                print(f"[pronto] {result}")
        else:
            timeline, timeline_path = _analyze(args)
            if args.command == "run":
                mode = timeline["mode"]
                # Don't spend hours re-encoding a video when the cleaner made no cuts.
                if (mode == "full" and len(timeline["clips"]) == 1
                        and abs(timeline["clips"][0]["start"]) < .01
                        and abs(timeline["clips"][0]["end"] - float(timeline["source"]["duration"])) < .1):
                    print("[sem cortes] Nenhum período seguro para remoção foi encontrado.")
                    print("[sem cortes] O vídeo original já é o resultado; renderização integral evitada para economizar horas e espaço.")
                    return 0
                target = timeline_path.parent / f"gameplay_{mode}.mp4"
                if args.ui or (sys.platform == "win32" and not args.terminal):
                    from gameplay_editor.studio import render_with_dashboard
                    job = render_with_dashboard(timeline, target, encoder=args.encoder, quality=args.quality, force=args.force)
                    if job.snapshot()["stage"] == "error":
                        return 1
                else:
                    result = render_timeline(timeline, target, encoder=args.encoder, quality=args.quality, force=args.force)
                    print(f"[pronto] {result}")
        return 0
    except KeyboardInterrupt:
        print("\n[cancelado] Operação interrompida; vídeo original preservado.", file=sys.stderr)
        return 130
    except (MediaError, ValueError, FileNotFoundError, FileExistsError, OSError) as exc:
        print(f"[erro] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
