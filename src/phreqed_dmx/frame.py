"""Address-independent RGB frame primitives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RGB:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        for name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if not 0 <= value <= 255:
                raise ValueError(f"{name} must be between 0 and 255")

    def as_tuple(self) -> tuple[int, int, int]:
        return self.red, self.green, self.blue


BLACK = RGB(0, 0, 0)


class PixelGrid:
    """A front-view grid whose origin is the visible top-left."""

    def __init__(self, width: int, height: int, fill: RGB = BLACK) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("grid dimensions must be positive")
        self.width = width
        self.height = height
        self._pixels = [fill] * (width * height)

    def _index(self, x: int, y: int) -> int:
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise IndexError(f"pixel ({x}, {y}) is outside {self.width}x{self.height}")
        return y * self.width + x

    def __getitem__(self, coordinate: tuple[int, int]) -> RGB:
        return self._pixels[self._index(*coordinate)]

    def __setitem__(self, coordinate: tuple[int, int], color: RGB) -> None:
        if not isinstance(color, RGB):
            raise TypeError("grid values must be RGB instances")
        self._pixels[self._index(*coordinate)] = color

    def fill(self, color: RGB) -> None:
        if not isinstance(color, RGB):
            raise TypeError("fill color must be an RGB instance")
        self._pixels[:] = [color] * len(self._pixels)

    def rows(self) -> tuple[tuple[RGB, ...], ...]:
        return tuple(
            tuple(self._pixels[y * self.width : (y + 1) * self.width])
            for y in range(self.height)
        )
