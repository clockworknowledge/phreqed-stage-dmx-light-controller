import unittest

from phreqed_dmx.fixtures import FixtureConfig, validate_fixture_set


class FixtureMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = FixtureConfig(name="Cube A", start_address=1)

    def test_zone_one_is_bottom_right(self) -> None:
        self.assertEqual(self.fixture.zone_number(11, 3), 1)
        self.assertEqual(self.fixture.rgb_offsets(11, 3), (0, 1, 2))

    def test_zones_progress_right_to_left_then_bottom_to_top(self) -> None:
        self.assertEqual(self.fixture.zone_number(0, 3), 12)
        self.assertEqual(self.fixture.zone_number(11, 2), 13)
        self.assertEqual(self.fixture.zone_number(0, 2), 24)
        self.assertEqual(self.fixture.zone_number(11, 1), 25)
        self.assertEqual(self.fixture.zone_number(11, 0), 37)
        self.assertEqual(self.fixture.zone_number(0, 0), 48)
        self.assertEqual(self.fixture.rgb_offsets(0, 3), (33, 34, 35))
        self.assertEqual(self.fixture.rgb_offsets(11, 2), (36, 37, 38))
        self.assertEqual(self.fixture.rgb_offsets(0, 2), (69, 70, 71))
        self.assertEqual(self.fixture.rgb_offsets(11, 1), (72, 73, 74))
        self.assertEqual(self.fixture.rgb_offsets(0, 1), (105, 106, 107))
        self.assertEqual(self.fixture.rgb_offsets(11, 0), (108, 109, 110))
        self.assertEqual(self.fixture.rgb_offsets(0, 0), (141, 142, 143))

    def test_second_fixture_offsets_start_at_channel_153(self) -> None:
        fixture = FixtureConfig(name="Cube B", start_address=153)
        self.assertEqual(fixture.rgb_offsets(11, 3), (152, 153, 154))

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
