"""Composition of logical fixture grids into a DMX universe."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math

from .color import NormalizedGrid
from .fixtures import FixtureConfig, UNIVERSE_CHANNELS, validate_fixture_set
from .frame import PixelGrid


def create_grids(fixtures: tuple[FixtureConfig, ...]) -> dict[str, PixelGrid]:
    return {fixture.name: PixelGrid(fixture.width, fixture.height) for fixture in fixtures}


def compose_dmx(
    fixtures: tuple[FixtureConfig, ...],
    grids: Mapping[str, PixelGrid | NormalizedGrid],
    white_zones: Mapping[str, Sequence[float]] | None = None,
) -> bytes:
    """Quantize RGB and optional white zones at the output boundary."""
    validate_fixture_set(fixtures)
    known_names = {fixture.name for fixture in fixtures}
    if white_zones is not None:
        unknown = set(white_zones).difference(known_names)
        if unknown:
            raise ValueError(f"white zones supplied for unknown fixture {min(unknown)}")
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
        if white_zones is None or fixture.name not in white_zones:
            continue
        levels = white_zones[fixture.name]
        if len(levels) != fixture.white_zone_count:
            raise ValueError(
                f"white zone count does not match fixture {fixture.name}"
            )
        for zone_number, level in enumerate(levels, start=1):
            if (
                isinstance(level, bool)
                or not isinstance(level, (int, float))
                or not math.isfinite(level)
                or not 0.0 <= level <= 1.0
            ):
                raise ValueError("white zone levels must be finite values from 0.0 to 1.0")
            universe[fixture.white_offset(zone_number)] = round(level * 255)
    return bytes(universe)
