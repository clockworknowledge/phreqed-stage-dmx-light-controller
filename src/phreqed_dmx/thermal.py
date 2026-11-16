"""Read-only Raspberry Pi CPU-temperature telemetry."""

from __future__ import annotations

import math
from pathlib import Path


DEFAULT_THERMAL_PATH = Path("/sys/class/thermal/thermal_zone0/temp")
CPU_WARM_C = 70.0
CPU_HOT_C = 80.0
MIN_CPU_MILLIDEGREES = 0.0
MAX_CPU_MILLIDEGREES = 150_000.0


def read_cpu_temperature_c(
    path: str | Path = DEFAULT_THERMAL_PATH,
) -> float | None:
    """Return validated degrees Celsius, or ``None`` when unavailable."""

    try:
        raw = float(Path(path).read_text(encoding="ascii").strip())
    except (OSError, UnicodeError, ValueError):
        return None
    if (
        not math.isfinite(raw)
        or raw < MIN_CPU_MILLIDEGREES
        or raw > MAX_CPU_MILLIDEGREES
    ):
        return None
    return raw / 1000.0


def cpu_temperature_band(value_c: float | None) -> str:
    """Classify a reading using informational Pi operating bands."""

    if value_c is None:
        return "unknown"
    if (
        isinstance(value_c, bool)
        or not isinstance(value_c, (int, float))
        or not math.isfinite(value_c)
        or value_c < 0.0
        or value_c > MAX_CPU_MILLIDEGREES / 1000.0
    ):
        raise ValueError("CPU temperature must be finite and between 0 and 150 C")
    if value_c >= CPU_HOT_C:
        return "hot"
    if value_c >= CPU_WARM_C:
        return "warm"
    return "normal"
