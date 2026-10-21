"""Commissioned center-white peak output with conservative flash safeguards."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from .fixtures import FixtureConfig


WHITE_OUTPUT_CEILING = 0.10
MAX_WHITE_OUTPUT_CEILING = 1.0
DEFAULT_WHITE_OUTPUT_LEVEL = 0.05
MAX_WHITE_FLASH_HZ = 4.0
WHITE_PULSE_SECONDS = 0.08


@dataclass(slots=True)
class WhitePeakLimiter:
    """Turn onset threshold crossings into short, rate-limited peak accents."""

    maximum_flash_hz: float = MAX_WHITE_FLASH_HZ
    pulse_seconds: float = WHITE_PULSE_SECONDS
    _armed: bool = field(default=True, init=False)
    _last_trigger: float = field(default=-math.inf, init=False)
    _active_until: float = field(default=-math.inf, init=False)
    _strength: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.maximum_flash_hz) or not 0 < self.maximum_flash_hz <= 4:
            raise ValueError("white flash rate must be above zero and at most 4 Hz")
        if not math.isfinite(self.pulse_seconds) or not 0 < self.pulse_seconds <= 0.10:
            raise ValueError("white pulse duration must be above zero and at most 0.10 seconds")

    def reset(self) -> None:
        self._armed = True
        self._active_until = -math.inf
        self._strength = 0.0

    def update(
        self,
        now: float,
        onset: float,
        *,
        enabled: bool,
        threshold: float,
    ) -> float:
        for name, value in (("time", now), ("onset", onset), ("threshold", threshold)):
            if not math.isfinite(value):
                raise ValueError(f"white {name} must be finite")
        if not 0.0 <= onset <= 1.0 or not 0.1 <= threshold <= 1.0:
            raise ValueError("white onset and threshold must be normalized")
        if not enabled:
            self.reset()
            return 0.0
        if onset < threshold:
            self._armed = True
        interval = 1.0 / self.maximum_flash_hz
        if (
            self._armed
            and onset >= threshold
            and now - self._last_trigger >= interval
        ):
            peak = (onset - threshold) / max(0.001, 1.0 - threshold)
            self._strength = min(1.0, 0.35 + peak * 0.65)
            self._last_trigger = now
            self._active_until = now + self.pulse_seconds
            self._armed = False
        if now < self._active_until:
            return self._strength
        return 0.0


def commissioned_white_levels(
    fixtures: tuple[FixtureConfig, ...], level: float, *,
    maximum: float = WHITE_OUTPUT_CEILING,
) -> dict[str, tuple[float, ...]]:
    """Create equal output for all eight commissioned parts on both fixtures."""

    if (
        isinstance(maximum, bool)
        or not isinstance(maximum, (int, float))
        or not math.isfinite(maximum)
        or not 0.0 < maximum <= MAX_WHITE_OUTPUT_CEILING
    ):
        raise ValueError("white output ceiling must be above 0.0 and at most 1.0")
    if (
        isinstance(level, bool)
        or not isinstance(level, (int, float))
        or not math.isfinite(level)
        or not 0.0 <= level <= maximum
    ):
        raise ValueError(
            f"white output level must be between 0.0 and {maximum:.2f}"
        )
    result: dict[str, tuple[float, ...]] = {}
    for fixture in fixtures:
        if not fixture.white_commissioned:
            raise RuntimeError(f"white zones are not commissioned for {fixture.name}")
        if not fixture.white_rows_together:
            raise RuntimeError(f"white-row behavior is not confirmed for {fixture.name}")
        result[fixture.name] = (float(level),) * fixture.white_zone_count
    return result
