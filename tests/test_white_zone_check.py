from pathlib import Path
import runpy
import unittest


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "white-zone-check.py")
)
validated_steps = SCRIPT["validated_steps"]


class WhiteZoneCheckTests(unittest.TestCase):
    def test_all_steps_are_steady_isolated_and_low_level(self):
        steps = validated_steps(0.05)
        self.assertEqual(len(steps), 16)
        expected_addresses = list(range(145, 153)) + list(range(297, 305))
        for (label, payload), expected_address in zip(steps, expected_addresses):
            active = [(index + 1, value) for index, value in enumerate(payload) if value]
            self.assertEqual(active, [(expected_address, 13)])
            self.assertIn("all RGB and other white zones DARK", label)

    def test_level_is_positive_and_capped_at_ten_percent(self):
        for level in (0, -0.1, 0.101, float("inf"), float("nan")):
            with self.subTest(level=level), self.assertRaises(ValueError):
                validated_steps(level)


if __name__ == "__main__":
    unittest.main()
