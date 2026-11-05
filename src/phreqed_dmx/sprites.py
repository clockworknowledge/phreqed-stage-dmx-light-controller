"""Deterministic address-independent sprite drawing and animation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from .color import BLACK_NORMALIZED, NormalizedGrid, NormalizedRGB
from .frame import PixelGrid, RGB


def _validate_scale(scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int) or scale <= 0:
        raise ValueError("sprite scale must be a positive integer")


@dataclass(frozen=True, slots=True)
class Sprite:
    rows: tuple[str, ...]
    on_character: str = "#"

    def __post_init__(self) -> None:
        if not self.rows or not self.rows[0]:
            raise ValueError("sprite cannot be empty")
        if len(self.on_character) != 1:
            raise ValueError("sprite on-character must be exactly one character")
        width = len(self.rows[0])
        if any(len(row) != width for row in self.rows):
            raise ValueError("all sprite rows must have the same width")

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    def is_on(
        self,
        x: int,
        y: int,
        *,
        scale: int = 1,
        flip_x: bool = False,
        flip_y: bool = False,
    ) -> bool:
        """Return whether a transformed local coordinate belongs to the sprite."""
        _validate_scale(scale)
        source_x = x // scale
        source_y = y // scale
        if not 0 <= source_x < self.width or not 0 <= source_y < self.height:
            return False
        if flip_x:
            source_x = self.width - 1 - source_x
        if flip_y:
            source_y = self.height - 1 - source_y
        return self.rows[source_y][source_x] == self.on_character


@dataclass(frozen=True, slots=True)
class SpriteAnimation:
    """A loop of equal-sized sprite frames selected by supplied time."""

    frames: tuple[Sprite, ...]
    frame_seconds: float = 0.2

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("sprite animation requires at least one frame")
        if not math.isfinite(self.frame_seconds) or self.frame_seconds <= 0.0:
            raise ValueError("sprite frame duration must be finite and positive")
        size = (self.frames[0].width, self.frames[0].height)
        if any((frame.width, frame.height) != size for frame in self.frames):
            raise ValueError("sprite animation frames must have matching dimensions")

    @property
    def width(self) -> int:
        return self.frames[0].width

    @property
    def height(self) -> int:
        return self.frames[0].height

    def frame_at(self, animation_time: float) -> Sprite:
        if not math.isfinite(animation_time):
            raise ValueError("sprite animation time must be finite")
        index = math.floor(animation_time / self.frame_seconds) % len(self.frames)
        return self.frames[index]


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


def draw_normalized_sprite(
    grid: NormalizedGrid,
    sprite: Sprite,
    color: NormalizedRGB,
    *,
    x_offset: int = 0,
    y_offset: int = 0,
    scale: int = 1,
    flip_x: bool = False,
    flip_y: bool = False,
    background: NormalizedRGB | None = None,
) -> None:
    """Draw a transformed sprite into normalized render space with clipping."""
    _validate_scale(scale)
    if background is not None:
        grid.fill(background)
    for y in range(sprite.height * scale):
        for x in range(sprite.width * scale):
            target_x = x_offset + x
            target_y = y_offset + y
            if (
                0 <= target_x < grid.width
                and 0 <= target_y < grid.height
                and sprite.is_on(
                    x, y, scale=scale, flip_x=flip_x, flip_y=flip_y
                )
            ):
                grid[target_x, target_y] = color


def render_cross_fixture_sprite(
    geometry: Mapping[str, tuple[int, int]],
    sprite: Sprite,
    color: NormalizedRGB,
    *,
    x_offset: int = 0,
    y_offset: int = 0,
    scale: int = 1,
    flip_x: bool = False,
    flip_y: bool = False,
    background: NormalizedRGB = BLACK_NORMALIZED,
) -> dict[str, NormalizedGrid]:
    """Render fixtures as one left-to-right canvas, then split them by name."""
    if not geometry:
        raise ValueError("sprite scene geometry cannot be empty")
    scene: dict[str, NormalizedGrid] = {}
    fixture_left = 0
    for name, (width, height) in geometry.items():
        grid = NormalizedGrid(width, height, background)
        draw_normalized_sprite(
            grid,
            sprite,
            color,
            x_offset=x_offset - fixture_left,
            y_offset=y_offset,
            scale=scale,
            flip_x=flip_x,
            flip_y=flip_y,
        )
        scene[name] = grid
        fixture_left += width
    return scene


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

BIRD_UP = Sprite(("#...#", ".###.", "..#..", "....."))
BIRD_DOWN = Sprite((".....", "..#..", ".###.", "#...#"))
STICKMAN_LEFT = Sprite((".#.", "###", ".#.", "#.."))
STICKMAN_RIGHT = Sprite((".#.", "###", ".#.", "..#"))
TRIANGLE = Sprite(("..#..", ".#.#.", "#...#", "#####"))
CIRCLE = Sprite((".###.", "#...#", "#...#", ".###."))
DIAMOND = Sprite(("..#..", ".#.#.", "#...#", ".###."))

SPRITE_ANIMATIONS: Mapping[str, SpriteAnimation] = {
    "bird": SpriteAnimation((BIRD_UP, BIRD_DOWN), 0.16),
    "stickman": SpriteAnimation((STICKMAN_LEFT, STICKMAN_RIGHT), 0.22),
    "triangle": SpriteAnimation((TRIANGLE,), 1.0),
    "circle": SpriteAnimation((CIRCLE,), 1.0),
    "diamond": SpriteAnimation((DIAMOND,), 1.0),
}
