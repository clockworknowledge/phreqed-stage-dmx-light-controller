"""Deterministic procedural effect catalog for the two-cube stage display."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable

from .color import BLACK_NORMALIZED, NormalizedRGB, palette_color
from .effect_api import (
    COMMON_PARAMETER_SPECS,
    EffectMetadata,
    EffectParameters,
    EffectRegistry,
    FixtureIdentity,
    ParameterSpec,
    PerformanceContext,
)

Sampler = Callable[
    [int, int, int, int, float, FixtureIdentity, EffectParameters, PerformanceContext | None],
    NormalizedRGB,
]
TAU = math.tau


@dataclass(frozen=True, slots=True)
class ProceduralEffect:
    metadata: EffectMetadata
    sampler: Sampler

    def sample(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        animation_time: float,
        fixture: FixtureIdentity,
        parameters: EffectParameters,
        context: PerformanceContext | None = None,
    ) -> NormalizedRGB:
        if not 0 <= x < width or not 0 <= y < height:
            raise IndexError("effect coordinate is outside the frame")
        return self.sampler(
            x, y, width, height, animation_time, fixture, parameters, context
        )


def _number(
    key: str,
    label: str,
    default: float,
    minimum: float,
    maximum: float,
    step: float,
    description: str,
) -> ParameterSpec:
    return ParameterSpec(key, label, default, description, minimum, maximum, step)


def _metadata(
    effect_id: str,
    name: str,
    description: str,
    category: str,
    specific: tuple[ParameterSpec, ...],
    *,
    brightness: float = 0.55,
) -> EffectMetadata:
    common = tuple(
        replace(spec, default=brightness) if spec.key == "brightness" else spec
        for spec in COMMON_PARAMETER_SPECS
    )
    return EffectMetadata(effect_id, name, description, category, common + specific)


def _time(animation_time: float, parameters: EffectParameters) -> float:
    return animation_time * parameters.number("speed")


def _paint(
    phase: float, intensity: float, parameters: EffectParameters
) -> NormalizedRGB:
    level = _clamp(intensity) * parameters.number("brightness")
    return palette_color(parameters.choice("palette"), phase).scaled(level)


def _uv(x: int, y: int, width: int, height: int) -> tuple[float, float]:
    return (
        0.0 if width <= 1 else x / (width - 1),
        0.0 if height <= 1 else y / (height - 1),
    )


def _centered(x: int, y: int, width: int, height: int) -> tuple[float, float]:
    u, v = _uv(x, y, width, height)
    return u * 2.0 - 1.0, v * 2.0 - 1.0


def _hash01(x: int, y: int, seed: int = 0) -> float:
    value = (x * 0x1F123BB5) ^ (y * 0x5F356495) ^ (seed * 0x6C8E9CF5)
    value = (value ^ (value >> 16)) * 0x45D9F3B
    value = (value ^ (value >> 16)) * 0x45D9F3B
    value ^= value >> 16
    return (value & 0xFFFFFFFF) / 0xFFFFFFFF


def _smooth(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def _value_noise(x: float, y: float, seed: int) -> float:
    left = math.floor(x)
    top = math.floor(y)
    fx = _smooth(x - left)
    fy = _smooth(y - top)
    top_value = _lerp(_hash01(left, top, seed), _hash01(left + 1, top, seed), fx)
    bottom_value = _lerp(
        _hash01(left, top + 1, seed), _hash01(left + 1, top + 1, seed), fx
    )
    return _lerp(top_value, bottom_value, fy)


def _fbm(x: float, y: float, seed: int) -> float:
    value = 0.0
    amplitude = 0.58
    total = 0.0
    for octave in range(3):
        value += _value_noise(x, y, seed + octave * 101) * amplitude
        total += amplitude
        x *= 2.03
        y *= 2.03
        amplitude *= 0.5
    return value / total


def _plasma(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del width, height, fixture, context
    t = _time(animation_time, parameters)
    a = math.sin(x * parameters.number("x_scale") + t)
    b = math.sin(y * parameters.number("y_scale") - t * 0.8)
    c = math.sin((x + y) * parameters.number("diagonal_scale") + t * 0.5)
    return _paint((a + b + c) / 6.0 + 0.5, 1.0, parameters)


def _noise(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    u, v = _uv(x, y, width, height)
    t = _time(animation_time, parameters)
    scale = parameters.number("scale")
    drift = parameters.number("drift")
    seed = (context.seed if context else 0) + fixture.index * 997
    value = _fbm(u * scale + t * drift, v * scale - t * drift * 0.61, seed)
    return _paint(value + t * 0.025, 0.25 + value * 0.75, parameters)


def _lava(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del context
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    blob_size = parameters.number("blob_size")
    wobble = parameters.number("wobble")
    total = 0.0
    for index in range(3):
        phase = index * 2.1 + fixture.index * 0.35
        center_x = math.sin(t * (0.31 + index * 0.06) + phase) * wobble
        center_y = math.cos(t * (0.24 + index * 0.05) - phase) * 0.7
        distance_sq = (u - center_x) ** 2 + (v - center_y) ** 2
        total += math.exp(-distance_sq / max(0.02, blob_size**2))
    intensity = _clamp(total / 1.45)
    return _paint(0.03 + intensity * 0.18 + t * 0.008, intensity, parameters)


def _vortex(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    radius = math.hypot(u, v)
    angle = math.atan2(v, u) / TAU
    phase = angle * parameters.number("arms") + radius * parameters.number("twist") - t
    intensity = 0.25 + 0.75 * ((math.sin(phase * TAU) + 1.0) / 2.0)
    return _paint(phase + radius * 0.12, intensity, parameters)


def _kaleidoscope(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    segments = max(2, round(parameters.number("segments")))
    radius = math.hypot(u, v)
    angle = (math.atan2(v, u) + t * 0.35) % (TAU / segments)
    folded = abs(angle - TAU / segments / 2.0)
    value = (math.sin(radius * parameters.number("zoom") * 5.0 + folded * 18.0 - t) + 1) / 2
    return _paint(value + folded, 0.2 + value * 0.8, parameters)


def _rings(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    radius = math.hypot(u, v)
    phase = radius * parameters.number("spacing") - t * 1.8
    wave = (math.sin(phase * TAU) + 1.0) / 2.0
    exponent = 1.0 + (1.0 - parameters.number("thickness")) * 9.0
    intensity = wave**exponent
    return _paint(radius * 0.35 - t * 0.04, intensity, parameters)


def _interference(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    frequency = parameters.number("frequency")
    source_count = max(2, round(parameters.number("sources")))
    total = 0.0
    for index in range(source_count):
        angle = index / source_count * TAU + t * 0.2
        source_x = math.cos(angle) * 0.72
        source_y = math.sin(angle) * 0.72
        total += math.sin(math.hypot(u - source_x, v - source_y) * frequency - t * 2.0)
    value = total / source_count * 0.5 + 0.5
    return _paint(value + t * 0.02, 0.15 + abs(total / source_count) * 0.85, parameters)


def _bars(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    angle = math.radians(parameters.number("angle"))
    projected = u * math.cos(angle) + v * math.sin(angle) - t
    phase = projected % 1.0
    width_value = parameters.number("bar_width")
    distance = abs(phase - 0.5)
    intensity = _clamp((width_value - distance) / max(0.02, width_value))
    return _paint(projected * 0.22 + t * 0.04, intensity, parameters)


def _checkerboard(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del width, height, fixture, context
    t = _time(animation_time, parameters)
    size = max(1, round(parameters.number("size")))
    shift = math.floor(t * parameters.number("motion"))
    cell = ((x + shift) // size + (y + shift) // size) % 2
    contrast = parameters.number("contrast")
    intensity = 1.0 if cell else 1.0 - contrast
    return _paint(cell * 0.5 + t * 0.03, intensity, parameters)


def _fire(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    u, v = _uv(x, y, width, height)
    t = _time(animation_time, parameters)
    seed = (context.seed if context else 0) + fixture.index * 313
    turbulence = parameters.number("turbulence")
    cooling = parameters.number("cooling")
    # Logical y=0 is the visible top. Heat is anchored at the bottom and the
    # noise coordinate advances so features travel upward as time increases.
    noise = _fbm(u * turbulence, v * turbulence + t * 1.7, seed)
    intensity = _clamp(v * 1.15 + noise * 0.7 - cooling)
    return _paint(intensity * 0.24, intensity, parameters)


def _digital_rain(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del width
    t = _time(animation_time, parameters)
    seed = (context.seed if context else 0) + fixture.index * 211
    density = parameters.number("density")
    column_activity = _hash01(x * 17 + 5, seed * 3 + 7, 193)
    if column_activity > density:
        return BLACK_NORMALIZED
    speed = 0.85 + _hash01(x, 2, seed) * 1.35
    gap = 2.0 + _hash01(x, 4, seed) * 3.0
    cycle = height + gap
    offset = _hash01(x, 1, seed) * cycle
    # Logical y=0 is the top. Each head advances toward larger y, spends a
    # randomized interval below the fixture, then restarts above the top.
    head = (t * speed + offset) % cycle - 0.75
    distance = head - y
    trail = parameters.number("trail")
    if distance < -0.55 or distance > trail:
        return BLACK_NORMALIZED
    head_glow = math.exp(-((distance / 0.34) ** 2))
    tail_glow = math.exp(-max(0.0, distance) / max(0.15, trail)) * 0.58
    intensity = max(head_glow, tail_glow)
    tail_fraction = _clamp(max(0.0, distance) / max(0.15, trail))
    color_phase = 0.96 - tail_fraction * 0.58 + _hash01(x, 3, seed) * 0.03
    return _paint(color_phase, intensity, parameters)


def _glitch(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del width, height
    t = _time(animation_time, parameters)
    block = max(1, round(parameters.number("block_size")))
    frame = math.floor(t * parameters.number("jitter"))
    seed = (context.seed if context else 0) + fixture.index * 401
    displacement = round((_hash01(y // block, frame, seed) - 0.5) * 6)
    value = _hash01((x + displacement) // block, y // block, seed + frame)
    stripe = 1.0 if _hash01(y, frame, seed + 9) > 0.82 else 0.35
    return _paint(value + frame * 0.07, stripe, parameters)


def _sparks(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    t = _time(animation_time, parameters)
    count = max(1, round(parameters.number("count")))
    decay = parameters.number("decay")
    seed = (context.seed if context else 0) + fixture.index * 557
    intensity = 0.0
    hue = 0.0
    for index in range(count):
        phase = _hash01(index, 0, seed)
        age = (t * (0.22 + _hash01(index, 1, seed) * 0.25) + phase) % 1.0
        start_x = _hash01(index, 2, seed) * (width - 1)
        velocity_x = (_hash01(index, 3, seed) - 0.5) * width * 0.7
        spark_x = start_x + velocity_x * age
        spark_y = (height - 1) - age * (height + 1)
        distance = math.hypot(x - spark_x, y - spark_y)
        contribution = math.exp(-distance / max(0.05, decay)) * (1.0 - age)
        if contribution > intensity:
            intensity = contribution
            hue = _hash01(index, 4, seed)
    return _paint(hue + t * 0.015, intensity, parameters)


def _energy_transfer(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del height, context
    t = _time(animation_time, parameters)
    total_width = width * fixture.count
    global_x = x + fixture.index * width
    head = (t * parameters.number("rate")) % total_width
    distance = (head - global_x) % total_width
    trail = parameters.number("trail")
    horizontal = math.exp(-distance / max(0.1, trail))
    vertical = 0.45 + 0.55 * ((math.sin(y * 1.8 - t * 2.0) + 1.0) / 2.0)
    return _paint(global_x / total_width + t * 0.04, horizontal * vertical, parameters)


def _cross_blaster(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    t = _time(animation_time, parameters)
    total_width = width * fixture.count
    global_x = x + fixture.index * width
    trail = parameters.number("trail")
    core_width = parameters.number("core_width")
    rate = parameters.number("rate")
    direction = parameters.choice("direction")
    if direction == "left-right":
        path_position = global_x
        path_length = total_width - 1
    elif direction == "right-left":
        path_position = total_width - 1 - global_x
        path_length = total_width - 1
    else:
        path_position = max(0.0, abs(global_x - (total_width - 1) / 2) - 0.5)
        path_length = max(1.0, total_width / 2 - 1)

    cycle_length = path_length + trail + core_width + 2.0
    head = (t * rate) % cycle_length
    behind = head - path_position
    horizontal = 0.0
    if -core_width <= behind <= trail:
        if behind < 0.0:
            horizontal = 1.0 - abs(behind) / max(0.1, core_width)
        else:
            horizontal = math.exp(-behind / max(0.1, trail * 0.42))

    seed = context.seed if context else 0
    flicker = 0.72 + _value_noise(path_position * 0.7 - t * 5.0, y * 1.3, seed) * 0.28
    center = (height - 1) / 2 + math.sin(path_position * 0.65 - t * 2.3) * 0.24
    spread = parameters.number("spread")
    vertical = math.exp(-((abs(y - center) / max(0.2, spread * 1.45)) ** 2))
    blast = horizontal * vertical * flicker

    # A compact source flare makes each cycle read as a gun firing rather than
    # a generic travelling bar. Center-out uses the shared middle as its source.
    firing = _clamp(1.0 - head / max(0.5, core_width * 1.8))
    muzzle = (
        math.exp(-path_position / max(0.2, core_width * 0.7))
        * math.exp(-((abs(y - (height - 1) / 2) / max(0.2, spread * 1.45)) ** 2))
        * firing
    )
    intensity = max(blast, muzzle)
    progress = path_position / max(1.0, path_length)
    return _paint(0.98 - progress * 0.22 + t * 0.01, intensity, parameters)


def _flame_jet(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    """Render an anchored muzzle and turbulent strands across all fixtures."""
    t = _time(animation_time, parameters)
    total_width = width * fixture.count
    global_x = x + fixture.index * width
    u = global_x / max(1, total_width - 1)
    center = (height - 1) / 2
    turbulence = parameters.number("turbulence")
    strand_width = parameters.number("strand_width")

    dynamics = context.energy if context is not None else 0.5
    if context is not None and context.audio is not None:
        audio = context.audio
        dynamics = _clamp(
            audio.loudness * 0.5
            + audio.bands.bass * 0.25
            + audio.bands.mid * 0.15
            + audio.onset * 0.1
        )

    # Length is a fraction of the complete multi-fixture surface. Dynamics can
    # make the tips breathe, but the default remains long enough to cross the
    # fixture boundary even in a quiet room.
    reach = parameters.number("length") * (0.9 + dynamics * 0.1)
    tip_fade = _clamp((reach - u) * total_width / 3.0)

    seed = context.seed if context is not None else 0
    flow_noise = _value_noise(
        global_x * (0.32 + turbulence * 0.08) - t * (3.8 + turbulence),
        y * 1.7 + math.sin(t * 0.7),
        seed + 911,
    )
    flow = 0.58 + flow_noise * 0.42
    downstream_width = strand_width * (0.78 + u * 0.52)

    # Three coherent filaments share one origin and diverge into distinct,
    # continuously moving flame strands. Their phases are deliberately
    # different so the four-row fixture still shows gaps and forked tips.
    strands = 0.0
    strand_shapes = (
        (0.0, 0.42, 0.58, 1.0, 0.0),
        (-0.48, 0.34, 0.83, 0.72, 1.9),
        (0.48, 0.31, 0.71, 0.68, 4.2),
    )
    for offset, amplitude, frequency, weight, phase in strand_shapes:
        divergence = offset * (0.18 + u * 1.55)
        wave = math.sin(
            global_x * frequency * turbulence
            - t * (2.8 + frequency)
            + phase
        )
        ripple = math.sin(global_x * 1.31 + t * 1.9 + phase * 0.7) * 0.12
        line = center + divergence + (wave * amplitude + ripple) * (0.2 + u)
        distance = abs(y - line)
        filament = math.exp(-((distance / max(0.08, downstream_width)) ** 2))
        strands = max(strands, filament * weight)

    horizontal = (0.42 + 0.58 * math.exp(-u * 1.35)) * tip_fade
    jet = strands * horizontal * flow

    muzzle_size = parameters.number("muzzle_size")
    muzzle_distance = math.hypot(
        global_x / max(0.1, muzzle_size),
        (y - center) / max(0.1, strand_width * 2.4),
    )
    muzzle_pulse = 0.94 + 0.06 * math.sin(t * 5.3)
    muzzle = math.exp(-(muzzle_distance ** 2)) * muzzle_pulse
    intensity = max(jet, muzzle)

    # Ember is white-yellow at the muzzle, orange through the body, and red at
    # the tips. Clamp below 1.0 to avoid wrapping the cyclic palette to black.
    source_heat = math.exp(-global_x / max(0.1, muzzle_size)) * 0.12
    heat = min(0.99, 0.94 - u * 0.31 + (flow - 0.58) * 0.08 + source_heat)
    return _paint(heat, intensity, parameters)


def _dynamic_wave(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    t = _time(animation_time, parameters)
    total_width = width * fixture.count
    global_x = x + fixture.index * width
    u = global_x / max(1, total_width - 1)
    onset = 0.0
    treble = 0.0
    if context and context.audio is not None:
        onset = context.audio.onset
        treble = context.audio.bands.treble

    # The controller's shared animation clock already integrates tap tempo and
    # smoothed music energy into t. Onset adds a local spatial contraction so a
    # drum hit visibly increases frequency without replacing the tempo baseline.
    cycles = parameters.number("cycles") * (
        1.0 + onset * parameters.number("pulse_frequency")
    )
    amplitude = parameters.number("amplitude")
    spatial_phase = u * cycles * TAU
    sine_shape = math.sin(spatial_phase - t * 2.1)
    cosine_shape = math.cos(spatial_phase * 1.18 + t * 1.65)
    morph = _clamp(onset * parameters.number("cosine_morph"))
    carrier = _lerp(sine_shape, cosine_shape, morph)
    secondary = 0.16 + treble * 0.26
    line = (
        (height - 1) / 2
        + carrier * amplitude
        + math.cos(u * (cycles * 0.5 + 0.35) * TAU + t * 1.3) * secondary
    )
    thickness = parameters.number("thickness")
    distance = abs(y - line)
    intensity = math.exp(-((distance / max(0.05, thickness)) ** 2))
    return _paint(u * 0.65 - t * 0.035, intensity, parameters)


def _blinking_eye(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    t = _time(animation_time, parameters)
    u, v = _centered(x, y, width, height)
    phase = (t * parameters.number("blink_rate")) % 1.0
    blink_duration = parameters.number("blink_duration")
    blink_center = 0.84
    phase_distance = abs(phase - blink_center)
    phase_distance = min(phase_distance, 1.0 - phase_distance)
    half_blink = blink_duration / 2
    if phase_distance >= half_blink:
        closure = 0.0
    else:
        closure = 0.5 + 0.5 * math.cos(math.pi * phase_distance / half_blink)
    openness = 1.0 - closure

    almond = math.sqrt(max(0.0, 1.0 - u * u))
    half_height = almond * openness
    edge_softness = 0.22
    inside = _clamp((half_height + edge_softness - abs(v)) / edge_softness)
    brightness = parameters.number("brightness")

    if inside <= 0.0:
        # At full closure, leave a restrained coloured lid line rather than a
        # full-frame flash or abrupt white bar.
        lid = closure * almond * math.exp(-((abs(v) / 0.28) ** 2))
        return palette_color(parameters.choice("palette"), 0.62).scaled(
            brightness * lid * 0.32
        )

    gaze = parameters.number("gaze") + math.sin(t * 0.32) * 0.08
    iris_size = parameters.number("iris_size")
    iris_distance = abs(u - gaze)
    vertical_iris = abs(v) / max(0.15, openness)
    iris_radius = math.hypot(iris_distance, vertical_iris * 0.72)

    if iris_radius <= iris_size * 0.42:
        return BLACK_NORMALIZED
    if iris_radius <= iris_size:
        iris = palette_color(parameters.choice("palette"), 0.58 + t * 0.015)
        iris_level = _clamp(1.15 - iris_radius / max(0.05, iris_size))
        return iris.scaled(brightness * (0.62 + iris_level * 0.38) * inside)

    edge = _clamp((abs(v) - max(0.0, half_height - 0.22)) / 0.22)
    sclera = NormalizedRGB(0.92, 0.88, 0.72).scaled(
        brightness * inside * (1.0 - edge * 0.35)
    )
    return sclera


def _inside_out_vu(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    t = _time(animation_time, parameters)
    if context and context.audio is not None:
        audio = context.audio
        level = (
            audio.loudness * 0.58
            + audio.bands.bass * 0.24
            + audio.bands.mid * 0.12
            + audio.bands.treble * 0.06
            + audio.onset * 0.18
        ) * parameters.number("sensitivity")
    else:
        level = 0.5 + math.sin(t * 1.7) * 0.38
    level = _clamp(level)
    distance = (width - 1 - x) if fixture.index == 0 else x
    normalized = distance / max(1, width - 1)
    peak_width = parameters.number("peak_width")
    if normalized <= level:
        fill = 0.35 + (1.0 - normalized) * 0.65
    else:
        fill = 0.0
    peak = math.exp(-((normalized - level) / max(0.015, peak_width)) ** 2)
    row_shape = 0.72 + 0.28 * math.cos((y - (height - 1) / 2) * 1.7)
    intensity = max(fill * row_shape, peak)
    return _paint(normalized * 0.38 + t * 0.015, intensity, parameters)


def _radial_pulse(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture
    u, v = _centered(x, y, width, height)
    t = _time(animation_time, parameters)
    frequency = parameters.number("frequency")
    sharpness = parameters.number("sharpness")
    phase = math.hypot(u, v) * frequency - t
    intensity = ((math.sin(phase * TAU) + 1.0) / 2.0) ** sharpness
    hue = phase * 0.18 + t * 0.02
    if context and context.audio is not None:
        audio = context.audio
        measured_energy = (
            audio.loudness * 0.5
            + audio.bands.bass * 0.25
            + audio.bands.mid * 0.15
            + audio.bands.treble * 0.1
        )
        intensity = min(
            1.0,
            intensity
            * (0.45 + measured_energy * 0.55)
            * (1.0 + audio.onset * 0.25),
        )
        hue += (audio.bands.treble - audio.bands.bass) * 0.05
    return _paint(hue, intensity, parameters)


def _tunnel(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    t = _time(animation_time, parameters)
    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    distance = math.hypot(x - center_x, y - center_y)
    wave = math.sin(distance * parameters.number("ring_frequency") - t * 4)
    intensity = parameters.number("floor") + (1 - parameters.number("floor")) * ((wave + 1) / 2)
    return _paint(distance * 0.12 - t * 0.12, intensity, parameters)


def _pulse(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del x, y, width, height, fixture, context
    t = _time(animation_time, parameters)
    base = (math.sin(t * parameters.number("rate")) + 1) / 2
    intensity = base ** parameters.number("sharpness")
    return _paint(t * 0.035, intensity, parameters)


def _chase(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del fixture, context
    t = _time(animation_time, parameters)
    position = y * width + x
    total = width * height
    head = int(t * parameters.number("rate")) % total
    distance = (head - position) % total
    trail = parameters.number("trail")
    if distance >= trail:
        return BLACK_NORMALIZED
    intensity = (1 - distance / trail) ** 2
    return _paint(t * 0.05 + position / total, intensity, parameters)


def _cross_chase(
    x: int, y: int, width: int, height: int, animation_time: float,
    fixture: FixtureIdentity, parameters: EffectParameters,
    context: PerformanceContext | None,
) -> NormalizedRGB:
    del context
    t = _time(animation_time, parameters)
    combined_width = width * fixture.count
    global_x = x + fixture.index * width
    position = y * combined_width + global_x
    total = combined_width * height
    head = int(t * parameters.number("rate")) % total
    distance = (head - position) % total
    trail = parameters.number("trail")
    if distance >= trail:
        return BLACK_NORMALIZED
    intensity = (1 - distance / trail) ** 2
    return _paint(t * 0.06 + position / total, intensity, parameters)


def _build_effects() -> tuple[ProceduralEffect, ...]:
    number = _number
    return (
        ProceduralEffect(_metadata("plasma", "Advanced Plasma", "Layered sinusoidal psychedelic plasma.", "psychedelic", (
            number("x_scale", "Horizontal scale", 0.85, 0.1, 2.5, 0.05, "Horizontal wave scale"),
            number("y_scale", "Vertical scale", 1.1, 0.1, 2.5, 0.05, "Vertical wave scale"),
            number("diagonal_scale", "Diagonal scale", 0.65, 0.1, 2.5, 0.05, "Diagonal wave scale"),
        ), brightness=0.35), _plasma),
        ProceduralEffect(_metadata("flow-noise", "Flowing Noise", "Smooth deterministic fractal noise flow.", "organic", (
            number("scale", "Noise scale", 3.2, 1.0, 9.0, 0.1, "Spatial noise scale"),
            number("drift", "Drift", 0.32, 0.05, 1.5, 0.05, "Noise advection rate"),
        )), _noise),
        ProceduralEffect(_metadata("lava-lamp", "Lava Lamp", "Soft moving metaball-like blobs.", "organic", (
            number("blob_size", "Blob size", 0.62, 0.2, 1.2, 0.02, "Radius of each lava blob"),
            number("wobble", "Wobble", 0.55, 0.1, 1.0, 0.02, "Horizontal blob travel"),
        )), _lava),
        ProceduralEffect(_metadata("vortex", "Colour Vortex", "Rotating multi-arm colour spiral.", "psychedelic", (
            number("arms", "Arms", 3.0, 1.0, 8.0, 1.0, "Number of spiral arms"),
            number("twist", "Twist", 2.4, 0.2, 6.0, 0.1, "Radial spiral twist"),
        )), _vortex),
        ProceduralEffect(_metadata("kaleidoscope", "Kaleidoscope", "Mirrored rotating angular geometry.", "geometric", (
            number("segments", "Segments", 6.0, 2.0, 12.0, 1.0, "Mirror segment count"),
            number("zoom", "Zoom", 1.5, 0.4, 4.0, 0.1, "Radial pattern density"),
        )), _kaleidoscope),
        ProceduralEffect(_metadata("rings", "Concentric Rings", "Expanding rings radiating from the centre.", "geometric", (
            number("spacing", "Spacing", 1.8, 0.5, 4.0, 0.1, "Ring spacing"),
            number("thickness", "Thickness", 0.42, 0.1, 1.0, 0.02, "Ring thickness"),
        )), _rings),
        ProceduralEffect(_metadata("interference", "Wave Interference", "Oscillating waves from moving sources.", "psychedelic", (
            number("frequency", "Frequency", 7.0, 2.0, 15.0, 0.25, "Wave spatial frequency"),
            number("sources", "Sources", 3.0, 2.0, 6.0, 1.0, "Interference source count"),
        )), _interference),
        ProceduralEffect(_metadata("bars", "Sweeping Bars", "Angled luminous bars sweep across each fixture.", "geometric", (
            number("bar_width", "Bar width", 0.24, 0.05, 0.48, 0.01, "Width of each light bar"),
            number("angle", "Angle", 28.0, -90.0, 90.0, 1.0, "Sweep angle in degrees"),
        )), _bars),
        ProceduralEffect(_metadata("checkerboard", "Animated Checkerboard", "Colour-shifting checkerboard motion.", "geometric", (
            number("size", "Cell size", 2.0, 1.0, 4.0, 1.0, "Checker cell size"),
            number("contrast", "Contrast", 0.9, 0.0, 1.0, 0.05, "Difference between alternating cells"),
            number("motion", "Motion", 1.0, 0.1, 4.0, 0.1, "Grid movement rate"),
        )), _checkerboard),
        ProceduralEffect(_metadata("fire", "Fire", "Rising deterministic turbulent flame field.", "organic", (
            number("turbulence", "Turbulence", 3.5, 1.0, 8.0, 0.1, "Flame noise complexity"),
            number("cooling", "Cooling", 0.28, 0.0, 0.8, 0.02, "Vertical flame cooling"),
        )), _fire),
        ProceduralEffect(_metadata("digital-rain", "Digital Rain", "Falling column trails with deterministic timing.", "digital", (
            number("density", "Density", 0.72, 0.1, 1.0, 0.02, "Active column density"),
            number("trail", "Trail", 1.7, 0.3, 5.0, 0.1, "Trail persistence"),
        )), _digital_rain),
        ProceduralEffect(_metadata("glitch", "Glitch Distortion", "Block displacement and scan-line distortion.", "digital", (
            number("block_size", "Block size", 2.0, 1.0, 4.0, 1.0, "Glitch block size"),
            number("jitter", "Jitter", 5.0, 0.5, 12.0, 0.5, "Distortion update rate"),
        ), brightness=0.42), _glitch),
        ProceduralEffect(_metadata("sparks", "Spark Trail", "Deterministic rising particle sparks.", "particle", (
            number("count", "Spark count", 12.0, 3.0, 24.0, 1.0, "Simulated particle count"),
            number("decay", "Decay", 0.55, 0.15, 1.5, 0.05, "Particle glow radius"),
        )), _sparks),
        ProceduralEffect(_metadata("energy-transfer", "Cross-Cube Energy", "Energy packet travels continuously between cubes.", "cross-fixture", (
            number("rate", "Transfer rate", 5.0, 0.5, 16.0, 0.5, "Horizontal travel rate"),
            number("trail", "Trail", 2.8, 0.5, 8.0, 0.1, "Energy trail length"),
        )), _energy_transfer),
        ProceduralEffect(_metadata("cross-blaster", "Cross-Cube Blaster", "A hot energy or flame bolt sweeps left-to-right across both fixtures.", "cross-fixture", (
            ParameterSpec("direction", "Direction", "left-right", "Blast travel direction", choices=("left-right", "right-left", "center-out")),
            number("rate", "Travel rate", 7.0, 1.0, 24.0, 0.5, "Horizontal cells per animation second"),
            number("trail", "Trail length", 7.0, 1.0, 18.0, 0.5, "Length of the trailing plume"),
            number("core_width", "Core width", 1.4, 0.25, 4.0, 0.05, "Width of the leading blast core"),
            number("spread", "Vertical spread", 1.0, 0.2, 3.0, 0.05, "Vertical plume spread"),
        ), brightness=0.62), _cross_blaster),
        ProceduralEffect(_metadata("flame-jet", "Anchored Flame Jet", "A fixed left-side muzzle fires turbulent flame strands across both fixtures.", "cross-fixture", (
            number("length", "Jet length", 1.08, 0.45, 1.25, 0.01, "Fraction of the combined display reached by the flame"),
            number("turbulence", "Turbulence", 1.0, 0.25, 2.0, 0.05, "Motion and curl of the flame strands"),
            number("strand_width", "Strand width", 0.5, 0.18, 1.2, 0.02, "Soft width of each flame filament"),
            number("muzzle_size", "Muzzle size", 1.15, 0.4, 3.0, 0.05, "Size of the hot source at the far left"),
        ), brightness=0.68), _flame_jet),
        ProceduralEffect(_metadata("dynamic-wave", "Dynamic Sine Wave", "A continuous sine/cosine light ribbon drifts across both fixtures.", "musical", (
            number("cycles", "Wave cycles", 2.2, 0.5, 6.0, 0.1, "Cycles across the combined display"),
            number("amplitude", "Amplitude", 1.15, 0.1, 1.8, 0.05, "Vertical wave travel"),
            number("thickness", "Line thickness", 0.52, 0.12, 1.5, 0.02, "Soft line width"),
            number("pulse_frequency", "Pulse frequency boost", 0.75, 0.0, 1.5, 0.05, "Extra wave cycles at maximum onset"),
            number("cosine_morph", "Cosine hit morph", 0.9, 0.0, 1.0, 0.05, "Sine-to-cosine morph strength on onset"),
        ), brightness=0.64), _dynamic_wave),
        ProceduralEffect(_metadata("blinking-eye", "Blinking Eye", "A stylized eye opens, watches, and blinks on each fixture.", "sprite", (
            number("blink_rate", "Blink rate", 0.32, 0.08, 1.5, 0.02, "Complete blink cycles per animation second"),
            number("blink_duration", "Blink duration", 0.22, 0.08, 0.5, 0.01, "Fraction of the cycle spent closing and reopening"),
            number("iris_size", "Iris size", 0.34, 0.16, 0.65, 0.01, "Iris radius within the eye"),
            number("gaze", "Gaze", 0.0, -0.5, 0.5, 0.05, "Horizontal iris position"),
        ), brightness=0.58), _blinking_eye),
        ProceduralEffect(_metadata("inside-out-vu", "Inside-Out VU", "Audio level expands from the shared centre toward both outer edges.", "musical", (
            number("sensitivity", "VU sensitivity", 1.15, 0.25, 2.5, 0.05, "Audio level gain"),
            number("peak_width", "Peak width", 0.055, 0.015, 0.25, 0.005, "Width of the bright level marker"),
        ), brightness=0.72), _inside_out_vu),
        ProceduralEffect(_metadata("radial-pulse", "Radial Pulse", "Tempo-aware radial waves without hard flashes.", "musical", (
            number("frequency", "Frequency", 2.2, 0.5, 6.0, 0.1, "Radial pulse spacing"),
            number("sharpness", "Sharpness", 2.0, 1.0, 6.0, 0.1, "Pulse edge sharpness"),
        )), _radial_pulse),
        ProceduralEffect(_metadata("tunnel", "Legacy Tunnel", "Hardware-tested v2 tunnel formula.", "legacy", (
            number("ring_frequency", "Ring frequency", 2.5, 0.5, 6.0, 0.1, "Tunnel ring frequency"),
            number("floor", "Dark floor", 0.15, 0.0, 0.5, 0.01, "Minimum tunnel intensity"),
        ), brightness=0.35), _tunnel),
        ProceduralEffect(_metadata("pulse", "Legacy Pulse", "Smooth full-grid colour pulse.", "legacy", (
            number("rate", "Pulse rate", 3.0, 0.2, 6.0, 0.1, "Pulse oscillation rate"),
            number("sharpness", "Sharpness", 3.0, 1.0, 6.0, 0.1, "Pulse curve exponent"),
        ), brightness=0.35), _pulse),
        ProceduralEffect(_metadata("chase", "Legacy Chase", "Single-fixture v2 pixel chase.", "legacy", (
            number("rate", "Chase rate", 10.0, 1.0, 24.0, 0.5, "Pixels per second"),
            number("trail", "Trail", 7.0, 2.0, 16.0, 1.0, "Tail length"),
        ), brightness=0.35), _chase),
        ProceduralEffect(_metadata("cross-cube", "Legacy Cross-Cube Chase", "v2 chase across a virtual combined display.", "legacy", (
            number("rate", "Chase rate", 15.0, 1.0, 30.0, 0.5, "Pixels per second"),
            number("trail", "Trail", 10.0, 2.0, 24.0, 1.0, "Tail length"),
        ), brightness=0.35), _cross_chase),
    )


EFFECT_REGISTRY = EffectRegistry(_build_effects())


def _lerp(left: float, right: float, amount: float) -> float:
    return left + (right - left) * amount


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
