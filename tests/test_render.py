import unittest

from phreqed_dmx.fixtures import FixtureConfig
from phreqed_dmx.frame import PixelGrid, RGB
from phreqed_dmx.render import compose_dmx


class RenderTests(unittest.TestCase):
    def test_composes_known_pixels_and_leaves_unverified_channels_black(self) -> None:
        fixture_a = FixtureConfig(name="Cube A", start_address=1)
        fixture_b = FixtureConfig(name="Cube B", start_address=153)
        grid_a = PixelGrid(8, 6)
        grid_b = PixelGrid(8, 6)
        grid_a[7, 5] = RGB(1, 2, 3)
        grid_a[0, 0] = RGB(4, 5, 6)
        grid_b[7, 5] = RGB(7, 8, 9)

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
        grid_a = PixelGrid(8, 6, RGB(25, 50, 75))
        grid_b = PixelGrid(8, 6)

        dmx = compose_dmx(
            (fixture_a, fixture_b), {"Cube A": grid_a, "Cube B": grid_b}
        )

        self.assertTrue(any(dmx[0:144]))
        self.assertEqual(dmx[152:296], bytes(144))


if __name__ == "__main__":
    unittest.main()
