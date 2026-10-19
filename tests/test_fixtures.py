import unittest

from phreqed_dmx.fixtures import FixtureConfig, validate_fixture_set


class FixtureMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = FixtureConfig(name="Cube A", start_address=1)

    def test_zone_one_is_bottom_right(self) -> None:
        self.assertEqual(self.fixture.zone_number(7, 5), 1)
        self.assertEqual(self.fixture.rgb_offsets(7, 5), (0, 1, 2))

    def test_zones_progress_right_to_left_then_bottom_to_top(self) -> None:
        self.assertEqual(self.fixture.zone_number(0, 5), 8)
        self.assertEqual(self.fixture.zone_number(7, 4), 9)
        self.assertEqual(self.fixture.zone_number(0, 0), 48)

    def test_second_fixture_offsets_start_at_channel_153(self) -> None:
        fixture = FixtureConfig(name="Cube B", start_address=153)
        self.assertEqual(fixture.rgb_offsets(7, 5), (152, 153, 154))

    def test_rejects_fixture_outside_universe(self) -> None:
        with self.assertRaises(ValueError):
            FixtureConfig(name="Overflow", start_address=400)

    def test_rejects_overlapping_fixture_footprints(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlaps"):
            validate_fixture_set(
                (
                    FixtureConfig(name="One", start_address=1),
                    FixtureConfig(name="Two", start_address=152),
                )
            )


if __name__ == "__main__":
    unittest.main()
