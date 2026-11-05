"""Commissioned center-white animation with conservative flash safeguards."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping, Sequence

from .fixtures import FixtureConfig


WHITE_OUTPUT_CEILING = 0.10
MAX_WHITE_OUTPUT_CEILING = 1.0
DEFAULT_WHITE_OUTPUT_LEVEL = 0.05
MAX_WHITE_FLASH_HZ = 4.0
WHITE_PULSE_SECONDS = 0.08

WHITE_PATTERN_LABELS = {
    "dark": "Dark by design",
    "bloom": "Expanding bloom",
    "lava": "Slow molten highlights",
    "rain": "Sparse falling accents",
    "energy": "Travelling energy burst",
    "current": "Slow current crest",
    "mirrors": "Mirrored highlights",
    "collision": "Inward phase collision",
    "blades": "Sweeping white blades",
    "embers": "Scattered ember peaks",
    "tunnel": "Expanding tunnel bands",
    "blaster": "Directional blaster core",
    "flame": "Flame muzzle and hot front",
    "wave": "Flowing wave crest",
    "vu": "Inside-out level peak",
    "glint": "Sprite glint",
}

_EFFECT_PATTERNS = {
    "plasma": "bloom",
    "rings": "bloom",
    "lava-lamp": "lava",
    "digital-rain": "rain",
    "glitch": "rain",
    "energy-transfer": "energy",
    "flow-noise": "current",
    "vortex": "mirrors",
    "kaleidoscope": "mirrors",
    "interference": "collision",
    "checkerboard": "blades",
    "bars": "blades",
    "fire": "embers",
    "sparks": "embers",
    "tunnel": "tunnel",
    "radial-pulse": "bloom",
    "pulse": "bloom",
    "chase": "energy",
    "cross-cube": "energy",
    "cross-blaster": "blaster",
    "flame-jet": "flame",
    "dynamic-wave": "wave",
    "inside-out-vu": "vu",
    "blinking-eye": "glint",
    "sprite-parade": "glint",
    "pacman": "glint",
}

_PATTERN_PRIORITY = {
    "blaster": 0,
    "flame": 0,
    "wave": 0,
    "vu": 0,
    "glint": 1,
    "energy": 2,
    "collision": 3,
    "blades": 3,
    "tunnel": 3,
    "mirrors": 4,
    "embers": 4,
    "rain": 4,
    "bloom": 5,
    "lava": 5,
    "current": 6,
}


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


def select_white_pattern(effect_ids: Sequence[str]) -> str:
    """Select a deterministic accent from a preset's transport-free effects."""

    if isinstance(effect_ids, (str, bytes)):
        raise TypeError("white effect IDs must be a sequence of strings")
    selected = "dark"
    for effect_id in effect_ids:
        if not isinstance(effect_id, str):
            raise TypeError("white effect IDs must be strings")
        pattern_id = _EFFECT_PATTERNS.get(effect_id)
        if pattern_id is not None and (
            selected == "dark"
            or _PATTERN_PRIORITY[pattern_id] < _PATTERN_PRIORITY[selected]
        ):
            selected = pattern_id
    return selected


def _smooth_peak(position: float, center: float, width: float) -> float:
    return math.exp(-((position - center) / width) ** 2)


def _global_pattern(
    pattern_id: str,
    part_count: int,
    animation_time: float,
    loudness: float,
    onset: float,
) -> tuple[float, ...]:
    if pattern_id == "dark":
        return (0.0,) * part_count
    center = (part_count - 1) / 2.0
    if pattern_id == "bloom":
        radius = (animation_time * 2.2) % (center + 2.0)
        return tuple(min(0.68, 0.62 * _smooth_peak(abs(x - center), radius, 0.75)
                         + 0.16 * _smooth_peak(x, center, 1.4))
                     for x in range(part_count))
    if pattern_id == "lava":
        first = (center + center * math.sin(animation_time * 0.47))
        second = (center + center * math.sin(animation_time * 0.31 + 2.2))
        return tuple(min(0.55, 0.46 * _smooth_peak(x, first, 1.55)
                         + 0.34 * _smooth_peak(x, second, 2.1))
                     for x in range(part_count))
    if pattern_id == "rain":
        # Three soft, staggered heads keep the white row sparse.
        heads = (
            (animation_time * 1.1) % part_count,
            (animation_time * 0.73 + part_count * 0.37) % part_count,
            (animation_time * 0.51 + part_count * 0.71) % part_count,
        )
        return tuple(min(0.48, sum(
            gain * _smooth_peak(x, head, 0.48)
            for gain, head in zip((0.48, 0.34, 0.26), heads)
        )) for x in range(part_count))
    if pattern_id == "energy":
        # Follow the packet, then widen into symmetric wings on a strong onset.
        packet = (animation_time * 3.2) % (part_count + 4.0) - 2.0
        spread = 0.8 + onset * 3.2
        wing_gain = 0.16 + onset * 0.34
        return tuple(min(1.0, 0.82 * _smooth_peak(x, packet, 0.7)
                         + wing_gain * _smooth_peak(x, packet - spread, 0.8)
                         + wing_gain * _smooth_peak(x, packet + spread, 0.8))
                     for x in range(part_count))
    if pattern_id == "current":
        crest = (animation_time * 0.72) % (part_count + 6.0) - 3.0
        return tuple(min(0.38, 0.34 * _smooth_peak(x, crest, 2.3)
                         + 0.16 * _smooth_peak(x, crest - 5.0, 2.8))
                     for x in range(part_count))
    if pattern_id == "mirrors":
        offset = (0.5 + 0.5 * math.sin(animation_time * 1.25)) * center
        return tuple(min(0.58, 0.52 * _smooth_peak(abs(x - center), offset, 0.72))
                     for x in range(part_count))
    if pattern_id == "collision":
        phase = (animation_time * 1.55) % 2.0
        distance = center * abs(1.0 - phase)
        impact = max(0.0, 1.0 - distance / 1.8)
        return tuple(min(0.78, 0.62 * _smooth_peak(abs(x - center), distance, 0.68)
                         + 0.32 * impact * _smooth_peak(x, center, 1.25))
                     for x in range(part_count))
    if pattern_id == "blades":
        first = (animation_time * 2.6) % part_count
        second = (first + part_count * 0.48) % part_count
        return tuple(min(0.62, 0.58 * _smooth_peak(x, first, 0.5)
                         + 0.38 * _smooth_peak(x, second, 0.62))
                     for x in range(part_count))
    if pattern_id == "embers":
        values = []
        for x in range(part_count):
            flicker = 0.5 + 0.5 * math.sin(x * 4.13 + animation_time * 3.7)
            envelope = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(
                x * 1.71 - animation_time * 0.83
            ))
            values.append(0.48 * flicker ** 5 * envelope)
        return tuple(values)
    if pattern_id == "tunnel":
        radius = (animation_time * 2.8) % (center + 1.0)
        return tuple(min(0.64, 0.58 * _smooth_peak(abs(x - center), radius, 0.55)
                         + 0.18 * _smooth_peak(abs(x - center), radius - 2.6, 0.8))
                     for x in range(part_count))
    if pattern_id == "blaster":
        # A soft core crosses the joined fixture canvas with a decaying wake.
        travel = (animation_time * 4.0) % (part_count + 8.0) - 4.0
        return tuple(min(1.0, _smooth_peak(x, travel, 0.75)
                         + 0.42 * _smooth_peak(x, travel - 2.0, 1.8))
                     for x in range(part_count))
    if pattern_id == "flame":
        # The left muzzle stays identifiable while a turbulent hot front travels.
        front = 3.0 + (0.5 + 0.5 * math.sin(animation_time * 1.15)) * (
            part_count - 4.0
        )
        values = []
        for x in range(part_count):
            muzzle = 0.8 * _smooth_peak(x, 0.3, 0.9)
            front_heat = _smooth_peak(x, front, 1.45)
            strand = (0.5 + 0.5 * math.sin(x * 2.17 + animation_time * 5.3))
            body = (0.16 + 0.42 * strand) if x <= front else 0.0
            values.append(min(1.0, max(muzzle, front_heat, body)))
        return tuple(values)
    if pattern_id == "wave":
        return tuple(
            (0.5 + 0.5 * math.sin(x * 0.92 - animation_time * 2.0)) ** 4
            for x in range(part_count)
        )
    if pattern_id == "vu":
        reach = 0.65 + loudness * (center + 0.35)
        # A soft edge avoids hard multi-section switching at level boundaries.
        return tuple(
            max(0.0, min(1.0, reach - abs(x - center) + 0.35))
            for x in range(part_count)
        )
    if pattern_id == "glint":
        center = (animation_time * 1.7) % part_count
        return tuple(_smooth_peak(x, center, 0.72) for x in range(part_count))
    raise ValueError(f"unknown white animation pattern: {pattern_id}")


def animated_white_pattern(
    fixtures: tuple[FixtureConfig, ...],
    pattern_id: str,
    animation_time: float,
    *,
    loudness: float = 0.0,
    onset: float = 0.0,
) -> dict[str, tuple[float, ...]]:
    """Render normalized white parts in physical DMX Part 1-through-8 order.

    The visual canvas runs left-to-right across the ordered fixtures. Conversion
    to the LF4808's commissioned right-to-left part order happens here, outside
    effect and browser code.
    """

    if pattern_id not in WHITE_PATTERN_LABELS:
        raise ValueError(f"unknown white animation pattern: {pattern_id}")
    for name, value in (
        ("animation time", animation_time),
        ("loudness", loudness),
        ("onset", onset),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"white {name} must be finite")
    if animation_time < 0.0:
        raise ValueError("white animation time must be nonnegative")
    if not 0.0 <= loudness <= 1.0:
        raise ValueError("white loudness must be normalized")
    if not 0.0 <= onset <= 1.0:
        raise ValueError("white onset must be normalized")
    if not fixtures:
        return {}
    for fixture in fixtures:
        if not fixture.white_commissioned or not fixture.white_rows_together:
            raise RuntimeError(f"white zones are not commissioned for {fixture.name}")
    total = sum(fixture.white_zone_count for fixture in fixtures)
    global_levels = _global_pattern(
        pattern_id, total, animation_time, loudness, onset
    )
    result: dict[str, tuple[float, ...]] = {}
    offset = 0
    for fixture in fixtures:
        logical = global_levels[offset:offset + fixture.white_zone_count]
        physical = [0.0] * fixture.white_zone_count
        for x, value in enumerate(logical):
            physical[fixture.white_part_number(x) - 1] = value
        result[fixture.name] = tuple(physical)
        offset += fixture.white_zone_count
    return result


def scale_white_pattern(
    fixtures: tuple[FixtureConfig, ...],
    pattern: Mapping[str, Sequence[float]],
    level: float,
    *,
    maximum: float = WHITE_OUTPUT_CEILING,
) -> dict[str, tuple[float, ...]]:
    """Apply an operator level while enforcing per-part and aggregate bounds."""

    # Reuse the established scalar validation and commissioning checks.
    commissioned_white_levels(fixtures, level, maximum=maximum)
    known = {fixture.name for fixture in fixtures}
    if set(pattern) != known:
        raise ValueError("white animation pattern must contain every fixture exactly once")
    result: dict[str, tuple[float, ...]] = {}
    aggregate = 0.0
    aggregate_limit = level * sum(f.white_zone_count for f in fixtures)
    for fixture in fixtures:
        values = pattern[fixture.name]
        if len(values) != fixture.white_zone_count:
            raise ValueError(f"white animation part count does not match {fixture.name}")
        scaled = []
        for value in values:
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0.0 <= value <= 1.0):
                raise ValueError("white animation values must be normalized")
            output = min(maximum, float(value) * level)
            scaled.append(output)
            aggregate += output
        result[fixture.name] = tuple(scaled)
    if aggregate > aggregate_limit + 1e-12:
        # Defensive guard: normalized patterns should never reach this branch.
        factor = aggregate_limit / aggregate
        result = {
            name: tuple(value * factor for value in values)
            for name, values in result.items()
        }
    return result


def logical_white_levels(
    fixtures: tuple[FixtureConfig, ...],
    levels: Mapping[str, Sequence[float]],
) -> dict[str, tuple[float, ...]]:
    """Convert physical Part order back to browser left-to-right order."""

    result: dict[str, tuple[float, ...]] = {}
    for fixture in fixtures:
        physical = levels[fixture.name]
        result[fixture.name] = tuple(
            physical[fixture.white_part_number(x) - 1]
            for x in range(fixture.white_zone_count)
        )
    return result
