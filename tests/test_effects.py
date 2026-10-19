import unittest

from phreqed_dmx.effects import EFFECT_NAMES, VisualEngine
from phreqed_dmx.frame import PixelGrid, RGB


def two_grids() -> tuple[PixelGrid, PixelGrid]:
    return PixelGrid(8, 6), PixelGrid(8, 6)


class VisualEngineTests(unittest.TestCase):
    def test_all_baseline_effects_render(self) -> None:
        expected_samples = {
            "plasma": RGB(0, 35, 89),
            "tunnel": RGB(82, 49, 0),
            "pulse": RGB(62, 9, 0),
            "chase": RGB(0, 0, 0),
        }
        for effect, expected in expected_samples.items():
            with self.subTest(effect=effect):
                first, second = two_grids()
                VisualEngine(effect).render(0.75, (first, second))
                self.assertEqual(first[2, 3], expected)
                self.assertEqual(first.rows(), second.rows())

        self.assertEqual(
            set(EFFECT_NAMES), {"plasma", "tunnel", "pulse", "chase", "cross-cube"}
        )

    def test_chase_preserves_baseline_head_and_tail(self) -> None:
        first, second = two_grids()
        VisualEngine("chase").render(0.75, (first, second))
        self.assertEqual(first[0, 0], RGB(0, 0, 0))
        self.assertEqual(first[7, 0], RGB(80, 89, 0))

    def test_cross_cube_chase_is_continuous_across_cube_boundary(self) -> None:
        first, second = two_grids()
        VisualEngine("cross-cube", brightness=1.0).render(8 / 15, (first, second))

        self.assertEqual(second[0, 0], RGB(255, 176, 0))
        self.assertEqual(first[7, 0], RGB(206, 130, 0))
        self.assertNotEqual(first.rows(), second.rows())

    def test_independent_mode_uses_distinct_effects(self) -> None:
        first, second = two_grids()
        VisualEngine(
            "pulse", mode="independent", second_effect="tunnel"
        ).render(0.75, (first, second))
        self.assertNotEqual(first.rows(), second.rows())

    def test_complementary_mode_changes_second_cube(self) -> None:
        first, second = two_grids()
        VisualEngine("plasma", mode="complementary").render(0.75, (first, second))
        self.assertNotEqual(first.rows(), second.rows())

    def test_rejects_invalid_engine_settings(self) -> None:
        with self.assertRaises(ValueError):
            VisualEngine("unknown")
        with self.assertRaises(ValueError):
            VisualEngine("plasma", brightness=1.1)


if __name__ == "__main__":
    unittest.main()
