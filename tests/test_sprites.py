import unittest

from phreqed_dmx.color import BLACK_NORMALIZED, NormalizedGrid, NormalizedRGB
from phreqed_dmx.frame import BLACK, PixelGrid, RGB
from phreqed_dmx.sprites import (
    SPRITE_ANIMATIONS,
    Sprite,
    SpriteAnimation,
    draw_normalized_sprite,
    draw_sprite,
    render_cross_fixture_sprite,
)


class SpriteTests(unittest.TestCase):
    def test_draws_address_independent_sprite_with_clipping(self) -> None:
        grid = PixelGrid(3, 2)
        sprite = Sprite(("##", ".#"))
        color = RGB(20, 30, 40)
        draw_sprite(grid, sprite, color, x_offset=2)

        self.assertEqual(grid[2, 0], color)
        self.assertEqual(grid[0, 0], BLACK)
        self.assertEqual(grid[2, 1], BLACK)

    def test_normalized_transform_scales_flips_and_clips(self) -> None:
        grid = NormalizedGrid(4, 3)
        color = NormalizedRGB(0.2, 0.6, 0.9)
        sprite = Sprite(("#.", ".#"))
        draw_normalized_sprite(
            grid, sprite, color, x_offset=-1, scale=2, flip_x=True
        )

        self.assertEqual(grid[1, 0], color)
        self.assertEqual(grid[0, 0], BLACK_NORMALIZED)
        self.assertEqual(grid[0, 2], color)
        self.assertEqual(grid[2, 2], BLACK_NORMALIZED)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            draw_normalized_sprite(grid, sprite, color, scale=0)

    def test_animation_selection_is_deterministic_and_validated(self) -> None:
        first = Sprite(("#.", ".."))
        second = Sprite(("..", ".#"))
        animation = SpriteAnimation((first, second), frame_seconds=0.25)
        self.assertIs(animation.frame_at(0.0), first)
        self.assertIs(animation.frame_at(0.25), second)
        self.assertIs(animation.frame_at(0.5), first)
        self.assertIs(animation.frame_at(0.25), animation.frame_at(0.25))
        with self.assertRaisesRegex(ValueError, "matching dimensions"):
            SpriteAnimation((first, Sprite(("#",))), frame_seconds=0.1)

    def test_cross_fixture_rendering_preserves_seam_and_independence(self) -> None:
        color = NormalizedRGB(0.8, 0.3, 0.1)
        scene = render_cross_fixture_sprite(
            {"Cube A": (12, 4), "Cube B": (12, 4)},
            Sprite(("##",)),
            color,
            x_offset=11,
            y_offset=2,
        )

        self.assertEqual(scene["Cube A"][11, 2], color)
        self.assertEqual(scene["Cube B"][0, 2], color)
        self.assertEqual(scene["Cube A"][0, 0], BLACK_NORMALIZED)
        scene["Cube A"][11, 2] = BLACK_NORMALIZED
        self.assertEqual(scene["Cube B"][0, 2], color)

    def test_production_catalog_fits_four_row_fixture(self) -> None:
        self.assertEqual(
            set(SPRITE_ANIMATIONS),
            {"bird", "stickman", "triangle", "circle", "diamond"},
        )
        for animation in SPRITE_ANIMATIONS.values():
            self.assertLessEqual(animation.height, 4)
            self.assertGreater(animation.width, 0)

    def test_bird_visual_regression_crosses_fixture_seam(self) -> None:
        color = NormalizedRGB(0.4, 0.8, 1.0)
        geometry = {"Cube A": (12, 4), "Cube B": (12, 4)}
        animation = SPRITE_ANIMATIONS["bird"]

        wings_up = render_cross_fixture_sprite(
            geometry, animation.frame_at(0.0), color, x_offset=10
        )
        lit_up = {
            (name, x, y)
            for name, grid in wings_up.items()
            for y, row in enumerate(grid.rows())
            for x, pixel in enumerate(row)
            if pixel != BLACK_NORMALIZED
        }
        self.assertEqual(lit_up, {
            ("Cube A", 10, 0), ("Cube B", 2, 0),
            ("Cube A", 11, 1), ("Cube B", 0, 1), ("Cube B", 1, 1),
            ("Cube B", 0, 2),
        })

        wings_down = render_cross_fixture_sprite(
            geometry, animation.frame_at(0.16), color, x_offset=10
        )
        self.assertNotEqual(wings_down["Cube A"].rows(), wings_up["Cube A"].rows())
        self.assertNotEqual(wings_down["Cube B"].rows(), wings_up["Cube B"].rows())


if __name__ == "__main__":
    unittest.main()
