import unittest

from phreqed_dmx.config import load_config
from phreqed_dmx.white_output import (
    WhitePeakLimiter,
    commissioned_white_levels,
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


if __name__ == "__main__":
    unittest.main()
