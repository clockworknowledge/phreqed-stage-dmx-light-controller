import unittest

from phreqed_dmx.color import NormalizedRGB, Palette, palette_color
from phreqed_dmx.effect_api import FixtureIdentity, PerformanceContext
from phreqed_dmx.effect_library import EFFECT_REGISTRY


REQUIRED_ADVANCED_EFFECTS = {
    "plasma",
    "flow-noise",
    "lava-lamp",
    "vortex",
    "kaleidoscope",
    "rings",
    "interference",
    "bars",
    "checkerboard",
    "fire",
    "digital-rain",
    "glitch",
    "sparks",
    "energy-transfer",
    "radial-pulse",
}


class EffectLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = FixtureIdentity("Cube A", 0, 2)
        self.context = PerformanceContext(tempo_bpm=128, energy=0.7, seed=42)

    def test_catalog_contains_advanced_and_legacy_effects(self) -> None:
        effect_ids = {metadata.effect_id for metadata in EFFECT_REGISTRY.metadata()}
        self.assertTrue(REQUIRED_ADVANCED_EFFECTS.issubset(effect_ids))
        self.assertTrue({"tunnel", "pulse", "chase", "cross-cube"}.issubset(effect_ids))

    def test_every_effect_has_metadata_and_adjustable_common_parameters(self) -> None:
        for metadata in EFFECT_REGISTRY.metadata():
            with self.subTest(effect=metadata.effect_id):
                self.assertTrue(metadata.name)
                self.assertTrue(metadata.description)
                self.assertTrue(metadata.category)
                keys = {parameter.key for parameter in metadata.parameters}
                self.assertTrue({"speed", "brightness", "palette"}.issubset(keys))
                self.assertGreaterEqual(len(keys - {"speed", "brightness", "palette"}), 2)

    def test_every_effect_is_deterministic_and_returns_valid_rgb(self) -> None:
        for metadata in EFFECT_REGISTRY.metadata():
            effect = EFFECT_REGISTRY.get(metadata.effect_id)
            parameters = EFFECT_REGISTRY.parameters(metadata.effect_id)
            with self.subTest(effect=metadata.effect_id):
                first = effect.sample(
                    3, 2, 8, 6, 1.2345, self.fixture, parameters, self.context
                )
                second = effect.sample(
                    3, 2, 8, 6, 1.2345, self.fixture, parameters, self.context
                )
                self.assertEqual(first, second)
                self.assertIsInstance(first, NormalizedRGB)
                self.assertTrue(all(0.0 <= value <= 1.0 for value in (
                    first.red, first.green, first.blue
                )))

    def test_all_effects_render_complete_frame_geometry(self) -> None:
        for metadata in EFFECT_REGISTRY.metadata():
            effect = EFFECT_REGISTRY.get(metadata.effect_id)
            parameters = EFFECT_REGISTRY.parameters(metadata.effect_id)
            with self.subTest(effect=metadata.effect_id):
                frame = [
                    effect.sample(x, y, 8, 6, 0.5, self.fixture, parameters, self.context)
                    for y in range(6)
                    for x in range(8)
                ]
                self.assertEqual(len(frame), 48)

    def test_parameters_reject_unknown_and_out_of_range_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown parameters"):
            EFFECT_REGISTRY.parameters("plasma", {"missing": 1.0})
        with self.assertRaisesRegex(ValueError, "at most"):
            EFFECT_REGISTRY.parameters("plasma", {"brightness": 1.1})
        with self.assertRaisesRegex(ValueError, "one of"):
            EFFECT_REGISTRY.parameters("plasma", {"palette": "invalid"})

    def test_palette_selection_changes_output(self) -> None:
        self.assertNotEqual(
            palette_color(Palette.SPECTRUM, 0.25),
            palette_color(Palette.EMBER, 0.25),
        )

    def test_plasma_defaults_preserve_baseline_sample(self) -> None:
        effect = EFFECT_REGISTRY.get("plasma")
        color = effect.sample(
            2,
            3,
            8,
            6,
            0.75,
            self.fixture,
            EFFECT_REGISTRY.parameters("plasma"),
            self.context,
        )
        self.assertEqual(
            tuple(int(channel * 255) for channel in (color.red, color.green, color.blue)),
            (0, 35, 89),
        )

    def test_cross_fixture_effect_uses_fixture_identity(self) -> None:
        effect = EFFECT_REGISTRY.get("energy-transfer")
        parameters = EFFECT_REGISTRY.parameters("energy-transfer")
        left = effect.sample(0, 0, 8, 6, 0.5, self.fixture, parameters, self.context)
        right = effect.sample(
            0,
            0,
            8,
            6,
            0.5,
            FixtureIdentity("Cube B", 1, 2),
            parameters,
            self.context,
        )
        self.assertNotEqual(left, right)


if __name__ == "__main__":
    unittest.main()
