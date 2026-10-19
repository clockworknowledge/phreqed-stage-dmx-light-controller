"""Monochrome sprite definitions and address-independent drawing."""

from __future__ import annotations

from dataclasses import dataclass

from .frame import PixelGrid, RGB


@dataclass(frozen=True, slots=True)
class Sprite:
    rows: tuple[str, ...]
    on_character: str = "#"

    def __post_init__(self) -> None:
        if not self.rows or not self.rows[0]:
            raise ValueError("sprite cannot be empty")
        width = len(self.rows[0])
        if any(len(row) != width for row in self.rows):
            raise ValueError("all sprite rows must have the same width")

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)


def draw_sprite(
    grid: PixelGrid,
    sprite: Sprite,
    color: RGB,
    *,
    x_offset: int = 0,
    y_offset: int = 0,
    background: RGB | None = None,
) -> None:
    if background is not None:
        grid.fill(background)
    for sprite_y, row in enumerate(sprite.rows):
        for sprite_x, value in enumerate(row):
            x = x_offset + sprite_x
            y = y_offset + sprite_y
            if value == sprite.on_character and 0 <= x < grid.width and 0 <= y < grid.height:
                grid[x, y] = color


SMILEY = Sprite(
    (
        ".####.",
        "#....#",
        "#.#..#",
        "#....#",
        "#.##.#",
        ".####.",
    )
)
