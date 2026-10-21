"""Fixture geometry and logical-to-physical pixel mapping."""

from __future__ import annotations

from dataclasses import dataclass

UNIVERSE_CHANNELS = 512
HORIZONTAL_ORDERS = {"left_to_right", "right_to_left"}
VERTICAL_ORDERS = {"top_to_bottom", "bottom_to_top"}


@dataclass(frozen=True, slots=True)
class FixtureConfig:
    name: str
    start_address: int
    channel_count: int = 152
    width: int = 12
    height: int = 4
    channels_per_pixel: int = 3
    white_zone_count: int = 8
    white_horizontal_order: str | None = None
    white_rows_together: bool = False
    white_commissioned: bool = False
    horizontal_order: str = "right_to_left"
    vertical_order: str = "bottom_to_top"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("fixture name cannot be empty")
        if self.start_address < 1:
            raise ValueError("DMX start_address is one-based and must be at least 1")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("fixture dimensions must be positive")
        if self.channels_per_pixel != 3:
            raise ValueError("only RGB fixtures with three channels per pixel are supported")
        if self.channel_count < self.pixel_channel_count:
            raise ValueError("fixture channel_count is smaller than its RGB pixel footprint")
        if (
            isinstance(self.white_zone_count, bool)
            or not isinstance(self.white_zone_count, int)
            or self.white_zone_count < 0
        ):
            raise ValueError("white_zone_count must be a nonnegative integer")
        if self.pixel_channel_count + self.white_zone_count > self.channel_count:
            raise ValueError("fixture channel_count is smaller than its RGB and white footprint")
        if self.white_horizontal_order not in HORIZONTAL_ORDERS | {None}:
            raise ValueError(
                f"unsupported white_horizontal_order: {self.white_horizontal_order}"
            )
        if not isinstance(self.white_rows_together, bool):
            raise TypeError("white_rows_together must be boolean")
        if not isinstance(self.white_commissioned, bool):
            raise TypeError("white_commissioned must be boolean")
        if self.white_commissioned and self.white_horizontal_order is None:
            raise ValueError(
                "commissioned white zones require a horizontal orientation"
            )
        if self.end_address > UNIVERSE_CHANNELS:
            raise ValueError("fixture extends beyond the 512-channel DMX universe")
        if self.horizontal_order not in HORIZONTAL_ORDERS:
            raise ValueError(f"unsupported horizontal_order: {self.horizontal_order}")
        if self.vertical_order not in VERTICAL_ORDERS:
            raise ValueError(f"unsupported vertical_order: {self.vertical_order}")

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    @property
    def pixel_channel_count(self) -> int:
        return self.pixel_count * self.channels_per_pixel

    @property
    def end_address(self) -> int:
        return self.start_address + self.channel_count - 1

    def zone_number(self, x: int, y: int) -> int:
        """Return the one-based physical zone for a top-left-origin coordinate."""
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise IndexError(f"pixel ({x}, {y}) is outside {self.width}x{self.height}")
        column = x if self.horizontal_order == "left_to_right" else self.width - 1 - x
        row = y if self.vertical_order == "top_to_bottom" else self.height - 1 - y
        return row * self.width + column + 1

    def rgb_offsets(self, x: int, y: int) -> tuple[int, int, int]:
        """Return zero-based universe offsets for the pixel's R, G, and B channels."""
        first = (self.start_address - 1) + (self.zone_number(x, y) - 1) * 3
        return first, first + 1, first + 2

    def white_offset(self, zone_number: int) -> int:
        """Return the zero-based universe offset for white zone 1 through 8.

        The LF4808 manual calls these white ``Part 1`` through ``Part 8``.
        This method deliberately preserves that numbering until the physical
        front-view order has been recorded on both fixtures.
        """
        if isinstance(zone_number, bool) or not isinstance(zone_number, int):
            raise TypeError("white zone number must be an integer")
        if not 1 <= zone_number <= self.white_zone_count:
            raise IndexError(
                f"white zone {zone_number} is outside 1 through {self.white_zone_count}"
            )
        return self.start_address - 1 + self.pixel_channel_count + zone_number - 1

    def white_part_number(self, x: int) -> int:
        """Map a left-to-right logical white coordinate to Part 1 through 8."""

        if not self.white_commissioned or self.white_horizontal_order is None:
            raise RuntimeError("white-zone orientation has not been commissioned")
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError("white part coordinate must be an integer")
        if not 0 <= x < self.white_zone_count:
            raise IndexError(
                f"white part coordinate {x} is outside 0 through {self.white_zone_count - 1}"
            )
        if self.white_horizontal_order == "left_to_right":
            return x + 1
        return self.white_zone_count - x


def validate_fixture_set(fixtures: tuple[FixtureConfig, ...]) -> None:
    if not fixtures:
        raise ValueError("at least one fixture is required")
    names: set[str] = set()
    occupied: set[int] = set()
    for fixture in fixtures:
        if fixture.name in names:
            raise ValueError(f"duplicate fixture name: {fixture.name}")
        names.add(fixture.name)
        fixture_channels = set(range(fixture.start_address, fixture.end_address + 1))
        overlap = occupied.intersection(fixture_channels)
        if overlap:
            raise ValueError(f"fixture {fixture.name} overlaps DMX address {min(overlap)}")
        occupied.update(fixture_channels)
