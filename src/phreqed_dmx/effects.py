"""Address-independent effects reconstructed from the working v2 baseline."""

from __future__ import annotations

import colorsys
import math
from collections.abc import Sequence
from typing import Protocol

from .frame import PixelGrid, RGB

EFFECT_NAMES = ("plasma", "tunnel", "pulse", "chase", "cross-cube")
CUBE_MODES = ("mirror", "complementary", "independent")
STANDARD_EFFECTS = EFFECT_NAMES[:4]
FloatRGB = tuple[float, float, float]


class Effect(Protocol):
    def render(self, elapsed: float, grids: Sequence[PixelGrid]) -> None: ...


def _hsv(hue: float, saturation: float = 1.0, value: float = 1.0) -> FloatRGB:
    return colorsys.hsv_to_rgb(hue % 1.0, saturation, value)


def _plasma(x: int, y: int, elapsed: float, width: int, height: int) -> FloatRGB:
    del width, height
    a = math.sin(x * 0.85 + elapsed)
    b = math.sin(y * 1.1 - elapsed * 0.8)
    c = math.sin((x + y) * 0.65 + elapsed * 0.5)
    return _hsv((a + b + c) / 6 + 0.5)


def _tunnel(x: int, y: int, elapsed: float, width: int, height: int) -> FloatRGB:
    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    distance = math.hypot(x - center_x, y - center_y)
    wave = math.sin(distance * 2.5 - elapsed * 4)
    hue = (distance * 0.12 - elapsed * 0.12) % 1
    intensity = 0.15 + 0.85 * ((wave + 1) / 2)
    return _hsv(hue, 1.0, intensity)


def _pulse(x: int, y: int, elapsed: float, width: int, height: int) -> FloatRGB:
    del x, y, width, height
    intensity = ((math.sin(elapsed * 3) + 1) / 2) ** 3
    hue = (elapsed * 0.035) % 1
    return _hsv(hue, 1.0, intensity)


def _chase(x: int, y: int, elapsed: float, width: int, height: int) -> FloatRGB:
    position = y * width + x
    total = width * height
    head = int(elapsed * 10) % total
    distance = (head - position) % total
    if distance < 7:
        intensity = (1 - distance / 7) ** 2
        hue = (elapsed * 0.05 + position / total) % 1
        return _hsv(hue, 1.0, intensity)
    return 0.0, 0.0, 0.0


_EFFECT_FUNCTIONS = {
    "plasma": _plasma,
    "tunnel": _tunnel,
    "pulse": _pulse,
    "chase": _chase,
}


def _cross_cube(
    x: int,
    y: int,
    elapsed: float,
    *,
    cube_index: int,
    width: int,
    height: int,
) -> FloatRGB:
    global_x = x + cube_index * width
    combined_width = width * 2
    position = y * combined_width + global_x
    total = combined_width * height
    head = int(elapsed * 15) % total
    distance = (head - position) % total
    if distance < 10:
        intensity = (1 - distance / 10) ** 2
        hue = (elapsed * 0.06 + position / total) % 1
        return _hsv(hue, 1.0, intensity)
    return 0.0, 0.0, 0.0


def _hue_shift(color: FloatRGB, offset: float) -> FloatRGB:
    hue, saturation, value = colorsys.rgb_to_hsv(*color)
    return _hsv(hue + offset, saturation, value)


def _to_rgb(color: FloatRGB, brightness: float) -> RGB:
    channels = (max(0, min(255, int(channel * brightness * 255))) for channel in color)
    return RGB(*channels)


class VisualEngine:
    """Render the four v2 effects and cross-cube chase onto two logical grids."""

    def __init__(
        self,
        effect: str = "plasma",
        *,
        mode: str = "mirror",
        second_effect: str = "tunnel",
        brightness: float = 0.35,
    ) -> None:
        if effect not in EFFECT_NAMES:
            raise ValueError(f"unknown effect: {effect}")
        if second_effect not in STANDARD_EFFECTS:
            raise ValueError(f"unknown second effect: {second_effect}")
        if mode not in CUBE_MODES:
            raise ValueError(f"unknown cube mode: {mode}")
        if not 0.0 <= brightness <= 1.0:
            raise ValueError("brightness must be between 0.0 and 1.0")
        self.effect = effect
        self.mode = mode
        self.second_effect = second_effect
        self.brightness = brightness

    def render(self, elapsed: float, grids: Sequence[PixelGrid]) -> None:
        if len(grids) != 2:
            raise ValueError("the visual engine requires exactly two fixture grids")
        first, second = grids
        if (first.width, first.height) != (second.width, second.height):
            raise ValueError("cross-fixture effects require matching grid dimensions")

        if self.effect == "cross-cube":
            self._render_cross_cube(first, elapsed, cube_index=0)
            self._render_cross_cube(second, elapsed, cube_index=1)
            return

        self._render_standard(first, self.effect, elapsed)
        if self.mode == "mirror":
            self._render_standard(second, self.effect, elapsed)
        elif self.mode == "complementary":
            self._render_standard(second, self.effect, elapsed + 1.5, hue_offset=0.5)
        else:
            self._render_standard(second, self.second_effect, elapsed)

    def _render_standard(
        self,
        grid: PixelGrid,
        effect: str,
        elapsed: float,
        *,
        hue_offset: float = 0.0,
    ) -> None:
        effect_function = _EFFECT_FUNCTIONS[effect]
        for y in range(grid.height):
            for x in range(grid.width):
                color = effect_function(x, y, elapsed, grid.width, grid.height)
                if hue_offset:
                    color = _hue_shift(color, hue_offset)
                grid[x, y] = _to_rgb(color, self.brightness)

    def _render_cross_cube(
        self, grid: PixelGrid, elapsed: float, *, cube_index: int
    ) -> None:
        for y in range(grid.height):
            for x in range(grid.width):
                color = _cross_cube(
                    x,
                    y,
                    elapsed,
                    cube_index=cube_index,
                    width=grid.width,
                    height=grid.height,
                )
                grid[x, y] = _to_rgb(color, self.brightness)
