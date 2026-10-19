import unittest

from phreqed_dmx.color import BLACK_NORMALIZED, NormalizedGrid, NormalizedRGB


class NormalizedColorTests(unittest.TestCase):
    def test_rejects_channels_outside_normalized_range(self) -> None:
        with self.assertRaises(ValueError):
            NormalizedRGB(1.01, 0.0, 0.0)
        with self.assertRaises(ValueError):
            NormalizedRGB(float("nan"), 0.0, 0.0)

    def test_grid_geometry_and_copy_are_independent(self) -> None:
        grid = NormalizedGrid(8, 6)
        copied = grid.copy()
        copied[0, 0] = NormalizedRGB(1.0, 0.5, 0.0)

        self.assertEqual(len(grid.rows()), 6)
        self.assertTrue(all(len(row) == 8 for row in grid.rows()))
        self.assertEqual(grid[0, 0], BLACK_NORMALIZED)
        self.assertNotEqual(copied[0, 0], grid[0, 0])


if __name__ == "__main__":
    unittest.main()
