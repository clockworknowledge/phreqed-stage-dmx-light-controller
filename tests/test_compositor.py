import unittest

from phreqed_dmx.color import NormalizedGrid, NormalizedRGB
from phreqed_dmx.compositor import (
    BlendMode,
    Compositor,
    FrameSafetyLimiter,
    Layer,
    RadialMask,
)


def solid(color: NormalizedRGB, width: int = 2, height: int = 2) -> NormalizedGrid:
    return NormalizedGrid(width, height, color)


class CompositorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.geometry = {"Cube A": (2, 2)}
        self.compositor = Compositor(global_brightness=1.0, maximum_brightness=1.0)

    def test_alpha_blending(self) -> None:
        scene = self.compositor.compose(
            self.geometry,
            (Layer({"Cube A": solid(NormalizedRGB(1.0, 0.0, 0.0))}, opacity=0.5),),
        )
        self.assertEqual(scene["Cube A"][0, 0], NormalizedRGB(0.5, 0.0, 0.0))

    def test_additive_blending_clamps(self) -> None:
        scene = self.compositor.compose(
            self.geometry,
            (
                Layer({"Cube A": solid(NormalizedRGB(0.8, 0.1, 0.0))}),
                Layer(
                    {"Cube A": solid(NormalizedRGB(0.5, 0.2, 0.0))},
                    blend_mode=BlendMode.ADDITIVE,
                ),
            ),
        )
        color = scene["Cube A"][0, 0]
        self.assertEqual(color.red, 1.0)
        self.assertAlmostEqual(color.green, 0.3)
        self.assertEqual(color.blue, 0.0)

    def test_lighten_blending_uses_channel_maximum(self) -> None:
        scene = self.compositor.compose(
            self.geometry,
            (
                Layer({"Cube A": solid(NormalizedRGB(0.2, 0.7, 0.1))}),
                Layer(
                    {"Cube A": solid(NormalizedRGB(0.8, 0.1, 0.4))},
                    blend_mode=BlendMode.LIGHTEN,
                ),
            ),
        )
        self.assertEqual(scene["Cube A"][0, 0], NormalizedRGB(0.8, 0.7, 0.4))

    def test_spatial_mask_limits_layer(self) -> None:
        scene = self.compositor.compose(
            {"Cube A": (3, 3)},
            (
                Layer(
                    {"Cube A": solid(NormalizedRGB(1.0, 1.0, 1.0), 3, 3)},
                    mask=RadialMask(radius=0.6, feather=0.2),
                ),
            ),
        )
        self.assertEqual(scene["Cube A"][1, 1], NormalizedRGB(1.0, 1.0, 1.0))
        self.assertEqual(scene["Cube A"][0, 0], NormalizedRGB(0.0, 0.0, 0.0))

    def test_global_brightness_is_limited(self) -> None:
        compositor = Compositor(global_brightness=1.0, maximum_brightness=0.65)
        scene = compositor.compose(
            self.geometry, (Layer({"Cube A": solid(NormalizedRGB(1.0, 1.0, 1.0))}),)
        )
        self.assertEqual(scene["Cube A"][0, 0], NormalizedRGB(0.65, 0.65, 0.65))

    def test_contrast_preserves_hue_and_expands_brightness_separation(self) -> None:
        source = NormalizedGrid(2, 1)
        source[0, 0] = NormalizedRGB(0.25, 0.125, 0.0)
        source[1, 0] = NormalizedRGB(0.8, 0.4, 0.0)
        normal = Compositor(
            global_brightness=1.0, maximum_brightness=1.0, contrast=1.0
        ).compose({"Cube A": (2, 1)}, (Layer({"Cube A": source}),))["Cube A"]
        shaped = Compositor(
            global_brightness=1.0, maximum_brightness=1.0, contrast=2.0
        ).compose({"Cube A": (2, 1)}, (Layer({"Cube A": source}),))["Cube A"]

        self.assertGreater(
            shaped[1, 0].red / shaped[0, 0].red,
            normal[1, 0].red / normal[0, 0].red,
        )
        self.assertAlmostEqual(shaped[0, 0].green / shaped[0, 0].red, 0.5)
        self.assertLessEqual(shaped[1, 0].red, 1.0)

    def test_contrast_boundaries_are_validated(self) -> None:
        for invalid in (True, 0.99, 3.01, float("inf")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                Compositor(contrast=invalid)

    def test_transition_crossfades_frames(self) -> None:
        first = {"Cube A": solid(NormalizedRGB(1.0, 0.0, 0.0))}
        second = {"Cube A": solid(NormalizedRGB(0.0, 0.0, 1.0))}
        result = self.compositor.transition(first, second, 0.25)
        self.assertEqual(result["Cube A"][0, 0], NormalizedRGB(0.75, 0.0, 0.25))

    def test_safety_limiter_restricts_repeated_full_frame_rises(self) -> None:
        limiter = FrameSafetyLimiter()
        dark = {"Cube A": solid(NormalizedRGB(0.0, 0.0, 0.0))}
        bright = {"Cube A": solid(NormalizedRGB(1.0, 1.0, 1.0))}
        limiter.apply(dark, 0.0)
        first = limiter.apply(bright, 0.01)
        second = limiter.apply(bright, 0.02)

        self.assertLessEqual(first["Cube A"][0, 0].red, 0.22)
        self.assertLessEqual(second["Cube A"][0, 0].red, 0.275)


if __name__ == "__main__":
    unittest.main()
