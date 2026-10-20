import unittest

from phreqed_dmx.fixtures import FixtureConfig
from phreqed_dmx.frame import PixelGrid, RGB
from phreqed_dmx.color import NormalizedGrid, NormalizedRGB
from phreqed_dmx.render import compose_dmx


class RenderTests(unittest.TestCase):
    def test_composes_known_pixels_and_leaves_optional_white_channels_black(self) -> None:
        fixture_a = FixtureConfig(name="Cube A", start_address=1)
        fixture_b = FixtureConfig(name="Cube B", start_address=153)
        grid_a = PixelGrid(12, 4)
        grid_b = PixelGrid(12, 4)
        grid_a[11, 3] = RGB(1, 2, 3)
        grid_a[0, 0] = RGB(4, 5, 6)
        grid_b[11, 3] = RGB(7, 8, 9)

        dmx = compose_dmx(
            (fixture_a, fixture_b), {"Cube A": grid_a, "Cube B": grid_b}
        )

        self.assertEqual(len(dmx), 512)
        self.assertEqual(dmx[0:3], bytes((1, 2, 3)))
        self.assertEqual(dmx[141:144], bytes((4, 5, 6)))
        self.assertEqual(dmx[144:152], bytes(8))
        self.assertEqual(dmx[152:155], bytes((7, 8, 9)))
        self.assertEqual(dmx[296:304], bytes(8))

    def test_requires_matching_grid_dimensions(self) -> None:
        fixture = FixtureConfig(name="Cube A", start_address=1)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            compose_dmx((fixture,), {"Cube A": PixelGrid(1, 1)})

    def test_fixture_frames_are_independent(self) -> None:
        fixture_a = FixtureConfig(name="Cube A", start_address=1)
        fixture_b = FixtureConfig(name="Cube B", start_address=153)
        grid_a = PixelGrid(12, 4, RGB(25, 50, 75))
        grid_b = PixelGrid(12, 4)

        dmx = compose_dmx(
            (fixture_a, fixture_b), {"Cube A": grid_a, "Cube B": grid_b}
        )

        self.assertTrue(any(dmx[0:144]))
        self.assertEqual(dmx[152:296], bytes(144))

    def test_normalized_rgb_is_quantized_at_output_boundary(self) -> None:
        fixture = FixtureConfig(name="Cube A", start_address=1)
        grid = NormalizedGrid(12, 4)
        grid[11, 3] = NormalizedRGB(0.5, 0.25, 1.0)

        dmx = compose_dmx((fixture,), {"Cube A": grid})

        self.assertEqual(dmx[0:3], bytes((128, 64, 255)))

    def test_normalized_white_zones_are_quantized_and_fixture_independent(self) -> None:
        fixture_a = FixtureConfig(name="Cube A", start_address=1)
        fixture_b = FixtureConfig(name="Cube B", start_address=153)
        grids = {"Cube A": NormalizedGrid(12, 4), "Cube B": NormalizedGrid(12, 4)}

        dmx = compose_dmx(
            (fixture_a, fixture_b),
            grids,
            white_zones={"Cube A": (0.1, 0, 0, 0, 0, 0, 0, 0)},
        )

        self.assertEqual(dmx[144:152], bytes((26, 0, 0, 0, 0, 0, 0, 0)))
        self.assertEqual(dmx[296:304], bytes(8))
        self.assertEqual(dmx[:144], bytes(144))

    def test_white_zone_shape_range_and_fixture_names_are_validated(self) -> None:
        fixture = FixtureConfig(name="Cube A", start_address=1)
        grid = {"Cube A": NormalizedGrid(12, 4)}
        for levels in ((0.0,), (0, 0, 0, 0, 0, 0, 0, 1.01),
                       (0, 0, 0, 0, 0, 0, 0, float("nan"))):
            with self.subTest(levels=levels), self.assertRaises(ValueError):
                compose_dmx((fixture,), grid, white_zones={"Cube A": levels})
        with self.assertRaisesRegex(ValueError, "unknown fixture"):
            compose_dmx((fixture,), grid, white_zones={"Other": (0,) * 8})


if __name__ == "__main__":
    unittest.main()
