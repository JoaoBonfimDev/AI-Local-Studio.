"""TTY-friendly progress/ETA for long media operations, without dependencies."""

from __future__ import annotations

import math
import time


def format_seconds(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        return "--:--:--"
    total = int(max(0, round(seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class Progress:
    def __init__(self, label: str, total: float, *, interval: float = 2.0) -> None:
        self.label = label
        self.total = max(float(total), .001)
        self.interval = interval
        self.started = time.monotonic()
        self.last_print = -1.0
        self.last_value = 0.0

    def update(self, processed: float, *, finished: bool = False) -> None:
        now = time.monotonic()
        self.last_value = max(self.last_value, min(self.total, processed))
        if not finished and self.last_print >= 0 and now - self.last_print < self.interval:
            return
        elapsed = max(.0001, now - self.started)
        fraction = self.last_value / self.total
        percentage = 100 * fraction
        speed = self.last_value / elapsed
        eta = (self.total - self.last_value) / speed if speed > .001 and elapsed >= 2 else math.nan
        filled = round(24 * fraction)
        bar = "#" * filled + "-" * (24 - filled)
        end = "\n" if finished else "\r"
        print(
            f"[{self.label}] [{bar}] {percentage:5.1f}%"
            f" | {format_seconds(self.last_value)}/{format_seconds(self.total)}"
            f" | decorrido {format_seconds(elapsed)}"
            f" | ETA {format_seconds(eta)}" + " " * 4,
            end=end, flush=True,
        )
        self.last_print = now

    def done(self) -> None:
        self.update(self.total, finished=True)
