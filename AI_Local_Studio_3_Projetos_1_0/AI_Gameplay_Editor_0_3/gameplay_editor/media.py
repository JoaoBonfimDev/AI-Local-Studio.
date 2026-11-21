"""Video metadata and bounded-memory audio/visual analysis using FFmpeg.

Only Python's standard library and locally installed FFmpeg are required.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from .progress import Progress


class MediaError(RuntimeError):
    """Input video or media processing failure."""


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration: float
    width: int
    height: int
    fps: str
    has_audio: bool
    size: int
    mtime_ns: int

    def source_record(self) -> dict:
        return {
            "path": str(self.path),
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "has_audio": self.has_audio,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
        }


def require_tools() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise MediaError("FFmpeg e FFprobe não encontrados no PATH. Consulte o README.")


def probe(path: str | Path) -> MediaInfo:
    require_tools()
    video = Path(path).expanduser().resolve()
    if not video.is_file():
        raise MediaError(f"Vídeo não encontrado: {video}")
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(video),
    ]
    p = subprocess.run(command, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise MediaError(f"Não foi possível analisar o arquivo: {p.stderr.strip()}")
    info = json.loads(p.stdout)
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise MediaError("O arquivo não contém uma faixa de vídeo.")
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration <= 0:
        duration = float(video_stream.get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise MediaError("Não foi possível determinar a duração do vídeo.")
    stat = video.stat()
    fps = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "30/1"
    if fps in ("0/0", "0/1", "N/A"):
        fps = "30/1"
    return MediaInfo(
        path=video,
        duration=duration,
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        fps=fps,
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
    )


def _read_exact(stream, amount: int) -> bytes:
    blocks = []
    remaining = amount
    while remaining > 0:
        part = stream.read(remaining)
        if not part:
            break
        blocks.append(part)
        remaining -= len(part)
    return b"".join(blocks)


def _complete(process: subprocess.Popen, context: str) -> None:
    assert process.stderr is not None
    message = process.stderr.read().decode("utf-8", errors="replace")
    result = process.wait()
    if result:
        raise MediaError(f"Erro durante {context}: {message.strip()[-1000:]}")


def scan_audio(info: MediaInfo) -> list[float]:
    """Read 8kHz mono PCM one second at a time; return normalized RMS per second."""
    total = max(1, math.ceil(info.duration))
    if not info.has_audio:
        print("[scan/audio] Sem faixa de áudio; continuando apenas com imagem.")
        return [0.0] * total
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-i", str(info.path), "-map", "0:a:0", "-vn", "-ac", "1",
        "-ar", "8000", "-acodec", "pcm_s16le", "-f", "s16le", "pipe:1",
    ]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    values: list[float] = []
    progress = Progress("scan/audio", info.duration)
    try:
        while True:
            chunk = _read_exact(proc.stdout, 16000)
            if not chunk:
                break
            samples = array("h")
            samples.frombytes(chunk[: len(chunk) - (len(chunk) % 2)])
            if sys.byteorder != "little":
                samples.byteswap()
            rms = math.sqrt(sum(int(x) * int(x) for x in samples) / len(samples)) / 32768 if samples else 0.0
            values.append(round(rms, 6))
            progress.update(min(info.duration, len(values)))
    finally:
        proc.stdout.close()
    _complete(proc, "análise de áudio")
    progress.done()
    return (values + [0.0] * max(total - len(values), 0))[:total]


def _cuda_decodes(info: MediaInfo) -> bool:
    """Attempt a one-frame decode: compiled CUDA support alone is insufficient."""
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
        "-hwaccel", "cuda", "-i", str(info.path), "-t", "1",
        "-vf", "fps=1,scale=96:54,format=gray", "-an",
        "-frames:v", "1", "-f", "null", "-",
    ]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    return result.returncode == 0


def _scan_motion_once(info: MediaInfo, every_seconds: int, *, gpu: bool) -> list[float]:
    total = max(1, math.ceil(info.duration))
    result = [0.0] * total
    w, h = 96, 54
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
    ]
    if gpu:
        command.extend(["-hwaccel", "cuda"])
    command.extend([
        "-i", str(info.path), "-vf", f"fps=1/{every_seconds},scale={w}:{h},format=gray",
        "-an", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ])
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    previous: bytes | None = None
    index = 0
    last_score = 0.0
    progress = Progress("scan/frames GPU" if gpu else "scan/frames CPU", info.duration)
    try:
        while True:
            frame = _read_exact(proc.stdout, w * h)
            if not frame:
                break
            if len(frame) != w * h:
                raise MediaError("Frame parcial durante análise visual.")
            if previous is not None:
                # Normalize against 48 gray levels: small camera shifts do not dominate.
                difference = sum(abs(a - b) for a, b in zip(previous[::3], frame[::3]))
                sample_count = len(frame[::3])
                last_score = min(1.0, difference / (sample_count * 48.0))
                start = min(total, (index - 1) * every_seconds)
                stop = min(total, index * every_seconds)
                for second in range(start, stop):
                    result[second] = round(last_score, 5)
            previous = frame
            index += 1
            progress.update(min(info.duration, index * every_seconds))
    finally:
        proc.stdout.close()
    _complete(proc, "análise visual")
    progress.done()
    if index > 1:
        for second in range(min(total, (index - 1) * every_seconds), total):
            result[second] = round(last_score, 5)
    return result


def scan_motion(info: MediaInfo, every_seconds: int = 3, decode: str = "auto") -> list[float]:
    """Sample gray frames, optionally decoding via RTX/NVDEC. CPU fallback is safe."""
    if every_seconds < 1:
        raise ValueError("every_seconds deve ser >= 1")
    if decode not in {"auto", "cpu", "gpu"}:
        raise ValueError("decode deve ser auto, cpu ou gpu")
    if decode == "cpu":
        print("[scan/frames] Decodificação na CPU.")
        return _scan_motion_once(info, every_seconds, gpu=False)

    available = _cuda_decodes(info)
    if not available:
        if decode == "gpu":
            raise MediaError("NVDEC/CUDA indisponível para este vídeo, driver ou FFmpeg. Tente --decode cpu.")
        print("[scan/frames] NVDEC indisponível; usando decodificação na CPU.")
        return _scan_motion_once(info, every_seconds, gpu=False)

    print("[scan/frames] Decodificação NVDEC/CUDA ativada (comparação de imagens ainda na CPU).")
    try:
        return _scan_motion_once(info, every_seconds, gpu=True)
    except MediaError:
        if decode == "gpu":
            raise
        print("\n[scan/frames] Falha no NVDEC; reiniciando a varredura visual pela CPU.")
        return _scan_motion_once(info, every_seconds, gpu=False)


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0.0, quantile) * (len(ordered) - 1))
    lo = math.floor(position)
    hi = math.ceil(position)
    weight = position - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


def build_activity(audio: list[float], motion: list[float]) -> list[float]:
    """Rank relative acoustic activity, movement and acoustic surprise [0..1]."""
    n = min(len(audio), len(motion))
    a20, a90 = percentile(audio, .20), percentile(audio, .90)
    m20, m90 = percentile(motion, .20), percentile(motion, .90)
    values = []
    for i in range(n):
        a = max(0.0, (audio[i] - a20) / max(.008, a90 - a20))
        m = max(0.0, (motion[i] - m20) / max(.08, m90 - m20))
        # Constant sustained motion (e.g. a long fight) should still be salient.
        m = max(m, motion[i] / .26)
        neighborhood = audio[max(0, i - 4): min(n, i + 5)]
        mean = sum(neighborhood) / len(neighborhood)
        peak = max(0.0, (audio[i] - mean) / max(.02, a90))
        score = .37 * min(1.0, a) + .48 * min(1.0, m) + .15 * min(1.0, peak)
        values.append(round(score, 4))
    return values
