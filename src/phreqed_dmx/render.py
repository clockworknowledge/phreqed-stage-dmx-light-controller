"""Composition of logical fixture grids into a DMX universe."""

from __future__ import annotations

from collections.abc import Mapping

from .color import NormalizedGrid
from .fixtures import FixtureConfig, UNIVERSE_CHANNELS, validate_fixture_set
from .frame import PixelGrid


def create_grids(fixtures: tuple[FixtureConfig, ...]) -> dict[str, PixelGrid]:
    return {fixture.name: PixelGrid(fixture.width, fixture.height) for fixture in fixtures}


def compose_dmx(
    fixtures: tuple[FixtureConfig, ...],
    grids: Mapping[str, PixelGrid | NormalizedGrid],
) -> bytes:
    """Quantize at the output boundary and leave every unmapped channel at zero."""
    validate_fixture_set(fixtures)
    universe = bytearray(UNIVERSE_CHANNELS)
    for fixture in fixtures:
        try:
            grid = grids[fixture.name]
        except KeyError as exc:
            raise ValueError(f"missing grid for fixture {fixture.name}") from exc
        if (grid.width, grid.height) != (fixture.width, fixture.height):
            raise ValueError(f"grid dimensions do not match fixture {fixture.name}")
        for y in range(grid.height):
            for x in range(grid.width):
                red_offset, green_offset, blue_offset = fixture.rgb_offsets(x, y)
                color = grid[x, y]
                if isinstance(grid, NormalizedGrid):
                    universe[red_offset] = round(color.red * 255)
                    universe[green_offset] = round(color.green * 255)
                    universe[blue_offset] = round(color.blue * 255)
                else:
                    universe[red_offset] = color.red
                    universe[green_offset] = color.green
                    universe[blue_offset] = color.blue
    return bytes(universe)
