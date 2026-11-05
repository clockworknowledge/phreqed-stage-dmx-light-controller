import unittest

from phreqed_dmx.config import load_config
from phreqed_dmx.white_output import (
    WhitePeakLimiter,
    animated_white_pattern,
    commissioned_white_levels,
    logical_white_levels,
    scale_white_pattern,
    select_white_pattern,
)


class WhiteOutputTests(unittest.TestCase):
    def test_peak_is_short_requires_rearm_and_is_limited_to_four_hz(self) -> None:
        limiter = WhitePeakLimiter()
        first = limiter.update(1.0, 0.8, enabled=True, threshold=0.6)
        self.assertGreater(first, 0.0)
        self.assertEqual(limiter.update(1.09, 0.8, enabled=True, threshold=0.6), 0.0)
        self.assertEqual(limiter.update(1.12, 0.2, enabled=True, threshold=0.6), 0.0)
        self.assertEqual(limiter.update(1.20, 0.8, enabled=True, threshold=0.6), 0.0)
        self.assertGreater(limiter.update(1.26, 0.8, enabled=True, threshold=0.6), 0.0)

    def test_disabled_or_reset_peak_is_dark(self) -> None:
        limiter = WhitePeakLimiter()
        self.assertGreater(limiter.update(1.0, 1.0, enabled=True, threshold=0.6), 0.0)
        self.assertEqual(limiter.update(1.01, 1.0, enabled=False, threshold=0.6), 0.0)
        self.assertEqual(limiter.update(1.02, 1.0, enabled=True, threshold=0.6), 0.0)
        self.assertGreater(limiter.update(1.26, 1.0, enabled=True, threshold=0.6), 0.0)

    def test_commissioned_levels_are_bounded_and_fixture_independent(self) -> None:
        fixtures = load_config().fixtures
        levels = commissioned_white_levels(fixtures, 0.05)
        self.assertEqual(levels["Cube A"], (0.05,) * 8)
        self.assertEqual(levels["Cube B"], (0.05,) * 8)
        self.assertIsNot(levels["Cube A"], levels["Cube B"])
        with self.assertRaises(ValueError):
            commissioned_white_levels(fixtures, 0.11)

    def test_elevated_level_requires_an_explicit_ceiling(self) -> None:
        fixtures = load_config().fixtures
        levels = commissioned_white_levels(fixtures, 0.55, maximum=0.60)
        self.assertEqual(levels["Cube A"], (0.55,) * 8)
        self.assertEqual(levels["Cube B"], (0.55,) * 8)
        with self.assertRaises(ValueError):
            commissioned_white_levels(fixtures, 0.61, maximum=0.60)
        with self.assertRaises(ValueError):
            commissioned_white_levels(fixtures, 0.05, maximum=1.01)

    def test_scene_pattern_selection_is_effect_based_and_defaults_dark(self) -> None:
        self.assertEqual(select_white_pattern(("plasma", "cross-blaster")), "blaster")
        self.assertEqual(select_white_pattern(("flame-jet",)), "flame")
        self.assertEqual(select_white_pattern(("dynamic-wave",)), "wave")
        self.assertEqual(select_white_pattern(("inside-out-vu",)), "vu")
        self.assertEqual(select_white_pattern(("sprite-parade",)), "glint")
        self.assertEqual(select_white_pattern(("plasma", "rings")), "dark")

    def test_segmented_patterns_are_deterministic_bounded_and_fixture_independent(self) -> None:
        fixtures = load_config().fixtures
        first = animated_white_pattern(fixtures, "blaster", 1.25, loudness=0.4)
        second = animated_white_pattern(fixtures, "blaster", 1.25, loudness=0.4)
        self.assertEqual(first, second)
        self.assertIsNot(first["Cube A"], first["Cube B"])
        self.assertTrue(any(value > 0.0 for values in first.values() for value in values))
        self.assertTrue(all(0.0 <= value <= 1.0
                            for values in first.values() for value in values))
        scaled = scale_white_pattern(fixtures, first, 0.05)
        self.assertTrue(all(0.0 <= value <= 0.05
                            for values in scaled.values() for value in values))
        self.assertLessEqual(sum(map(sum, scaled.values())), 16 * 0.05)

    def test_physical_part_order_round_trips_to_logical_left_to_right(self) -> None:
        fixtures = load_config().fixtures
        physical = animated_white_pattern(fixtures, "blaster", 0.0)
        logical = logical_white_levels(fixtures, physical)
        # At time zero the bolt enters at the far left, physical Part 8.
        self.assertGreater(logical["Cube A"][0], logical["Cube A"][-1])
        self.assertEqual(logical["Cube A"][0], physical["Cube A"][7])
        self.assertEqual(logical["Cube B"][0], physical["Cube B"][7])

    def test_dark_pattern_and_zero_level_recover_every_part_to_zero(self) -> None:
        fixtures = load_config().fixtures
        dark = animated_white_pattern(fixtures, "dark", 10.0, loudness=1.0)
        zero = scale_white_pattern(
            fixtures,
            animated_white_pattern(fixtures, "wave", 10.0, loudness=1.0),
            0.0,
        )
        expected = {fixture.name: (0.0,) * 8 for fixture in fixtures}
        self.assertEqual(dark, expected)
        self.assertEqual(zero, expected)


if __name__ == "__main__":
    unittest.main()
