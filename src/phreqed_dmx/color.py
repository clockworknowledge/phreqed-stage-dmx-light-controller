"""Normalized RGB colors and grids used before DMX quantization."""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class NormalizedRGB:
    red: float
    green: float
    blue: float

    def __post_init__(self) -> None:
        for name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
        ):
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and between 0.0 and 1.0")

    @classmethod
    def clamped(cls, red: float, green: float, blue: float) -> NormalizedRGB:
        return cls(*(_clamp(channel) for channel in (red, green, blue)))

    @classmethod
    def from_hsv(
        cls, hue: float, saturation: float = 1.0, value: float = 1.0
    ) -> NormalizedRGB:
        return cls(*colorsys.hsv_to_rgb(hue % 1.0, _clamp(saturation), _clamp(value)))

    def scaled(self, factor: float) -> NormalizedRGB:
        return NormalizedRGB.clamped(
            self.red * factor, self.green * factor, self.blue * factor
        )

    def lerp(self, other: NormalizedRGB, amount: float) -> NormalizedRGB:
        amount = _clamp(amount)
        return NormalizedRGB.clamped(
            self.red + (other.red - self.red) * amount,
            self.green + (other.green - self.green) * amount,
            self.blue + (other.blue - self.blue) * amount,
        )


BLACK_NORMALIZED = NormalizedRGB(0.0, 0.0, 0.0)


class Palette(str, Enum):
    SPECTRUM = "spectrum"
    MAGMA = "magma"
    OCEAN = "ocean"
    NEON = "neon"
    EMBER = "ember"
    MONOCHROME = "monochrome"


_PALETTE_STOPS: dict[Palette, tuple[tuple[float, NormalizedRGB], ...]] = {
    Palette.MAGMA: (
        (0.0, NormalizedRGB(0.03, 0.0, 0.08)),
        (0.35, NormalizedRGB(0.45, 0.0, 0.2)),
        (0.7, NormalizedRGB(1.0, 0.22, 0.02)),
        (1.0, NormalizedRGB(1.0, 0.9, 0.25)),
    ),
    Palette.OCEAN: (
        (0.0, NormalizedRGB(0.0, 0.02, 0.12)),
        (0.45, NormalizedRGB(0.0, 0.28, 0.65)),
        (0.75, NormalizedRGB(0.0, 0.85, 0.78)),
        (1.0, NormalizedRGB(0.7, 1.0, 0.95)),
    ),
    Palette.NEON: (
        (0.0, NormalizedRGB(1.0, 0.0, 0.6)),
        (0.33, NormalizedRGB(0.1, 0.1, 1.0)),
        (0.66, NormalizedRGB(0.0, 1.0, 0.55)),
        (1.0, NormalizedRGB(1.0, 0.0, 0.6)),
    ),
    Palette.EMBER: (
        (0.0, NormalizedRGB(0.02, 0.0, 0.0)),
        (0.4, NormalizedRGB(0.55, 0.02, 0.0)),
        (0.75, NormalizedRGB(1.0, 0.25, 0.0)),
        (1.0, NormalizedRGB(1.0, 0.9, 0.45)),
    ),
    Palette.MONOCHROME: (
        (0.0, BLACK_NORMALIZED),
        (1.0, NormalizedRGB(1.0, 1.0, 1.0)),
    ),
}


def palette_color(palette: Palette | str, position: float) -> NormalizedRGB:
    palette = Palette(palette)
    position = position % 1.0
    if palette is Palette.SPECTRUM:
        return NormalizedRGB.from_hsv(position)
    stops = _PALETTE_STOPS[palette]
    for (left_at, left), (right_at, right) in zip(stops, stops[1:]):
        if position <= right_at:
            span = right_at - left_at
            amount = 0.0 if span == 0 else (position - left_at) / span
            return left.lerp(right, amount)
    return stops[-1][1]


class NormalizedGrid:
    """A top-left-origin grid of normalized RGB values."""

    def __init__(
        self, width: int, height: int, fill: NormalizedRGB = BLACK_NORMALIZED
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("grid dimensions must be positive")
        self.width = width
        self.height = height
        self._pixels = [fill] * (width * height)

    def _index(self, x: int, y: int) -> int:
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise IndexError(f"pixel ({x}, {y}) is outside {self.width}x{self.height}")
        return y * self.width + x

    def __getitem__(self, coordinate: tuple[int, int]) -> NormalizedRGB:
        return self._pixels[self._index(*coordinate)]

    def __setitem__(self, coordinate: tuple[int, int], color: NormalizedRGB) -> None:
        if not isinstance(color, NormalizedRGB):
            raise TypeError("grid values must be NormalizedRGB instances")
        self._pixels[self._index(*coordinate)] = color

    def fill(self, color: NormalizedRGB) -> None:
        if not isinstance(color, NormalizedRGB):
            raise TypeError("fill color must be NormalizedRGB")
        self._pixels[:] = [color] * len(self._pixels)

    def copy(self) -> NormalizedGrid:
        copied = NormalizedGrid(self.width, self.height)
        copied._pixels[:] = self._pixels
        return copied

    def rows(self) -> tuple[tuple[NormalizedRGB, ...], ...]:
        return tuple(
            tuple(self._pixels[y * self.width : (y + 1) * self.width])
            for y in range(self.height)
        )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
