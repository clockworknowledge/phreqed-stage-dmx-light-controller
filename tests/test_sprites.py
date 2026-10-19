import unittest

from phreqed_dmx.frame import BLACK, PixelGrid, RGB
from phreqed_dmx.sprites import Sprite, draw_sprite


class SpriteTests(unittest.TestCase):
    def test_draws_address_independent_sprite_with_clipping(self) -> None:
        grid = PixelGrid(3, 2)
        sprite = Sprite(("##", ".#"))
        color = RGB(20, 30, 40)
        draw_sprite(grid, sprite, color, x_offset=2)

        self.assertEqual(grid[2, 0], color)
        self.assertEqual(grid[0, 0], BLACK)
        self.assertEqual(grid[2, 1], BLACK)


if __name__ == "__main__":
    unittest.main()
