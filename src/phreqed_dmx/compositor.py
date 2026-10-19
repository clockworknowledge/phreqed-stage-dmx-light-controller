"""Normalized RGB layer compositing, masks, transitions, and safety limiting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

from .color import BLACK_NORMALIZED, NormalizedGrid, NormalizedRGB

Scene = dict[str, NormalizedGrid]
Geometry = Mapping[str, tuple[int, int]]


class BlendMode(str, Enum):
    ALPHA = "alpha"
    ADDITIVE = "additive"
    LIGHTEN = "lighten"


class SpatialMask(Protocol):
    def opacity(self, x: int, y: int, width: int, height: int) -> float: ...


@dataclass(frozen=True, slots=True)
class RadialMask:
    center_x: float = 0.5
    center_y: float = 0.5
    radius: float = 0.75
    feather: float = 0.25
    invert: bool = False

    def opacity(self, x: int, y: int, width: int, height: int) -> float:
        u = 0.5 if width <= 1 else x / (width - 1)
        v = 0.5 if height <= 1 else y / (height - 1)
        distance = ((u - self.center_x) ** 2 + (v - self.center_y) ** 2) ** 0.5
        edge_start = max(0.0, self.radius - self.feather)
        if distance <= edge_start:
            value = 1.0
        elif distance >= self.radius:
            value = 0.0
        else:
            value = 1.0 - (distance - edge_start) / max(0.0001, self.feather)
        return 1.0 - value if self.invert else value


@dataclass(frozen=True, slots=True)
class Layer:
    frames: Mapping[str, NormalizedGrid]
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.ALPHA
    mask: SpatialMask | None = None
    fixtures: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("layer opacity must be between 0.0 and 1.0")


class Compositor:
    def __init__(
        self, *, global_brightness: float = 0.5, maximum_brightness: float = 0.65
    ) -> None:
        if not 0.0 <= maximum_brightness <= 1.0:
            raise ValueError("maximum_brightness must be between 0.0 and 1.0")
        self.maximum_brightness = maximum_brightness
        self.set_global_brightness(global_brightness)

    def set_global_brightness(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("global brightness must be between 0.0 and 1.0")
        self.global_brightness = value

    def compose(self, geometry: Geometry, layers: tuple[Layer, ...]) -> Scene:
        output = {
            name: NormalizedGrid(width, height)
            for name, (width, height) in geometry.items()
        }
        for layer in layers:
            self._apply_layer(output, geometry, layer)
        level = min(self.global_brightness, self.maximum_brightness)
        for grid in output.values():
            for y in range(grid.height):
                for x in range(grid.width):
                    grid[x, y] = grid[x, y].scaled(level)
        return output

    def transition(
        self, first: Mapping[str, NormalizedGrid], second: Mapping[str, NormalizedGrid], progress: float
    ) -> Scene:
        progress = _clamp(progress)
        if first.keys() != second.keys():
            raise ValueError("transition scenes must contain the same fixtures")
        output: Scene = {}
        for name in first:
            left = first[name]
            right = second[name]
            if (left.width, left.height) != (right.width, right.height):
                raise ValueError("transition frame geometry must match")
            grid = NormalizedGrid(left.width, left.height)
            for y in range(grid.height):
                for x in range(grid.width):
                    grid[x, y] = left[x, y].lerp(right[x, y], progress)
            output[name] = grid
        return output

    def _apply_layer(self, output: Scene, geometry: Geometry, layer: Layer) -> None:
        for fixture_name, source in layer.frames.items():
            if fixture_name not in output:
                raise ValueError(f"layer contains unknown fixture: {fixture_name}")
            if layer.fixtures is not None and fixture_name not in layer.fixtures:
                continue
            width, height = geometry[fixture_name]
            if (source.width, source.height) != (width, height):
                raise ValueError(f"layer geometry does not match fixture {fixture_name}")
            target = output[fixture_name]
            for y in range(height):
                for x in range(width):
                    mask_opacity = (
                        1.0 if layer.mask is None else layer.mask.opacity(x, y, width, height)
                    )
                    opacity = _clamp(layer.opacity * mask_opacity)
                    target[x, y] = _blend(
                        target[x, y], source[x, y], opacity, layer.blend_mode
                    )


class FrameSafetyLimiter:
    """Limits brightness and repeated large full-frame luminance rises."""

    def __init__(
        self,
        *,
        maximum_brightness: float = 0.65,
        maximum_luminance_jump: float = 0.22,
        minimum_flash_interval: float = 0.125,
    ) -> None:
        if not 0.0 < maximum_brightness <= 1.0:
            raise ValueError("maximum_brightness must be in (0.0, 1.0]")
        if not 0.0 < maximum_luminance_jump <= 1.0:
            raise ValueError("maximum_luminance_jump must be in (0.0, 1.0]")
        if minimum_flash_interval <= 0.0:
            raise ValueError("minimum_flash_interval must be positive")
        self.maximum_brightness = maximum_brightness
        self.maximum_luminance_jump = maximum_luminance_jump
        self.minimum_flash_interval = minimum_flash_interval
        self._previous_luminance = 0.0
        self._last_brightening = float("-inf")

    def apply(self, scene: Mapping[str, NormalizedGrid], timestamp: float) -> Scene:
        limited = _copy_scene(scene)
        luminance = _mean_luminance(limited)
        jump = luminance - self._previous_luminance
        allowed = self.maximum_luminance_jump
        if timestamp - self._last_brightening < self.minimum_flash_interval:
            allowed *= 0.25
        if jump > allowed and luminance > 0.0:
            target = self._previous_luminance + allowed
            scale = target / luminance
            _scale_scene(limited, scale)
            luminance = target
            self._last_brightening = timestamp
        elif jump > self.maximum_luminance_jump * 0.25:
            self._last_brightening = timestamp
        _cap_scene(limited, self.maximum_brightness)
        self._previous_luminance = min(luminance, self.maximum_brightness)
        return limited


def black_scene(geometry: Geometry) -> Scene:
    return {name: NormalizedGrid(width, height) for name, (width, height) in geometry.items()}


def _blend(
    base: NormalizedRGB,
    source: NormalizedRGB,
    opacity: float,
    mode: BlendMode,
) -> NormalizedRGB:
    if mode is BlendMode.ALPHA:
        return base.lerp(source, opacity)
    scaled = source.scaled(opacity)
    if mode is BlendMode.ADDITIVE:
        return NormalizedRGB.clamped(
            base.red + scaled.red, base.green + scaled.green, base.blue + scaled.blue
        )
    return NormalizedRGB(
        max(base.red, scaled.red),
        max(base.green, scaled.green),
        max(base.blue, scaled.blue),
    )


def _copy_scene(scene: Mapping[str, NormalizedGrid]) -> Scene:
    return {name: grid.copy() for name, grid in scene.items()}


def _scale_scene(scene: Scene, factor: float) -> None:
    for grid in scene.values():
        for y in range(grid.height):
            for x in range(grid.width):
                grid[x, y] = grid[x, y].scaled(factor)


def _cap_scene(scene: Scene, maximum: float) -> None:
    for grid in scene.values():
        for y in range(grid.height):
            for x in range(grid.width):
                color = grid[x, y]
                grid[x, y] = NormalizedRGB(
                    min(color.red, maximum),
                    min(color.green, maximum),
                    min(color.blue, maximum),
                )


def _mean_luminance(scene: Mapping[str, NormalizedGrid]) -> float:
    values: list[float] = []
    for grid in scene.values():
        for row in grid.rows():
            for color in row:
                values.append(color.red * 0.2126 + color.green * 0.7152 + color.blue * 0.0722)
    return sum(values) / len(values) if values else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
