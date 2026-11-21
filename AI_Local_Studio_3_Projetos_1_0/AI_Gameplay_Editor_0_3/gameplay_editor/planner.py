"""Two conservative timeline planners; neither enforces a final duration limit."""

from __future__ import annotations

import math
from typing import Iterable

from .media import percentile


def _true_runs(flags: Iterable[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    started: int | None = None
    count = 0
    for count, selected in enumerate(flags, start=1):
        if selected and started is None:
            started = count - 1
        elif not selected and started is not None:
            runs.append((started, count - 1))
            started = None
    if started is not None:
        runs.append((started, count))
    return runs


def merge_intervals(intervals: list[tuple[float, float]], gap: float = 0) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def full_gameplay(
    audio: list[float], motion: list[float], duration: float,
    min_idle: float = 20, context: float = 4, audio_floor: float = .008,
    motion_floor: float = .065,
) -> list[tuple[float, float]]:
    """Discard only long near-silent, low-motion sections; preserve context."""
    if duration <= 0:
        raise ValueError("duration deve ser positivo")
    if min_idle < 1 or context < 0 or audio_floor < 0 or motion_floor < 0:
        raise ValueError("Parâmetros de limpeza inválidos")
    n = min(len(audio), len(motion), math.ceil(duration))
    flags = [audio[i] <= audio_floor and motion[i] <= motion_floor for i in range(n)]
    if n == 0 or all(flags):
        # Without any confirmed activity, preserve rather than destroy a video.
        return [(0.0, duration)]
    idle = _true_runs(flags)
    cuts = merge_intervals([
        (start + context, min(duration, end - context))
        for start, end in idle if end - start >= min_idle
    ])
    kept = []
    cursor = 0.0
    for start, end in cuts:
        if start > cursor:
            kept.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        kept.append((cursor, duration))
    # Never throw away a complete source video on a heuristic false positive.
    return merge_intervals(kept) or [(0.0, duration)]


def best_moments(
    activity: list[float], duration: float, *,
    sensitivity: int = 50, before: float = 5, after: float = 8,
    gap: float = 8,
) -> list[tuple[float, float]]:
    """Select dynamically scored moments, with lead-in and follow-through."""
    if duration <= 0:
        raise ValueError("duration deve ser positivo")
    if not 0 <= sensitivity <= 100 or min(before, after, gap) < 0:
        raise ValueError("Sensibilidade/contexto inválidos")
    if not activity:
        return []
    # Higher sensitivity selects more moments; no maximum quantity or minutes.
    rank = .82 - .37 * sensitivity / 100
    minimum = .48 - .23 * sensitivity / 100
    threshold = max(minimum, percentile(activity, rank))
    flags = [score >= threshold and score >= minimum for score in activity]
    runs = _true_runs(flags)
    # Reject isolated weak spikes, but retain one-second strong reactions.
    significant = [
        (start, end) for start, end in runs
        if end - start >= 2 or max(activity[start:end]) >= .72
    ]
    expanded = [
        (max(0.0, start - before), min(duration, end + after))
        for start, end in significant
    ]
    return merge_intervals(expanded, gap=gap)


def make_timeline(
    *, source: dict, mode: str, audio: list[float],
    motion: list[float], activity: list[float],
    sensitivity: int = 50, min_idle: float = 20,
    audio_floor: float = .008, motion_floor: float = .065,
) -> dict:
    duration = float(source["duration"])
    if mode == "full":
        spans = full_gameplay(audio, motion, duration, min_idle=min_idle,
                              audio_floor=audio_floor, motion_floor=motion_floor)
    elif mode == "highlights":
        spans = best_moments(activity, duration, sensitivity=sensitivity)
    else:
        raise ValueError("mode deve ser 'full' ou 'highlights'")
    clips = []
    for index, (start, end) in enumerate(spans, start=1):
        local_scores = activity[max(0, math.floor(start)):min(len(activity), math.ceil(end))]
        clips.append({
            "name": f"{'Parte' if mode == 'full' else 'Destaque'} {index:03d}",
            "start": round(start, 3),
            "end": round(end, 3),
            "score": round(max(local_scores, default=0), 3),
        })
    return {
        "schema_version": 1,
        "project": "AI Gameplay Editor",
        "mode": mode,
        "source": source,
        "settings": {"sensitivity": sensitivity, "min_idle_seconds": min_idle,
                     "audio_floor": audio_floor, "motion_floor": motion_floor},
        "clips": clips,
        "summary": {
            "original_seconds": round(duration, 3),
            "selected_seconds": round(sum(c["end"] - c["start"] for c in clips), 3),
            "clip_count": len(clips),
        },
        "note": "Edite 'clips' (start/end/name), se desejar, antes de renderizar.",
    }


def validate_timeline(timeline: dict) -> None:
    if timeline.get("schema_version") != 1:
        raise ValueError("Versão da timeline não suportada")
    source = timeline.get("source")
    if not isinstance(source, dict) or not source.get("path"):
        raise ValueError("Timeline sem caminho do vídeo original")
    duration = float(source.get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Duração inválida na timeline")
    clips = timeline.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("A timeline não possui trechos selecionados")
    for i, clip in enumerate(clips, start=1):
        try:
            start, end = float(clip["start"]), float(clip["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Trecho {i}: início/fim inválidos") from exc
        if not all(map(math.isfinite, (start, end))) or start < 0 or end <= start or end > duration + .05:
            raise ValueError(f"Trecho {i}: tempo fora dos limites do vídeo")
