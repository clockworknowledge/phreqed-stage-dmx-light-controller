"""Composition of logical fixture grids into a DMX universe."""

from __future__ import annotations

from collections.abc import Mapping

from .fixtures import FixtureConfig, UNIVERSE_CHANNELS, validate_fixture_set
from .frame import PixelGrid


def create_grids(fixtures: tuple[FixtureConfig, ...]) -> dict[str, PixelGrid]:
    return {fixture.name: PixelGrid(fixture.width, fixture.height) for fixture in fixtures}


def compose_dmx(
    fixtures: tuple[FixtureConfig, ...],
    grids: Mapping[str, PixelGrid],
) -> bytes:
    """Build a full universe, leaving every unmapped channel at zero."""
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
                universe[red_offset] = color.red
                universe[green_offset] = color.green
                universe[blue_offset] = color.blue
    return bytes(universe)
