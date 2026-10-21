import unittest
import hashlib

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
    "cross-blaster",
    "flame-jet",
    "dynamic-wave",
    "inside-out-vu",
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

    def test_representative_animation_sequences_match_fingerprints(self) -> None:
        expected = {
            "flow-noise": "e08695bfb4a4d03d393072fe4cbba87dd310e9a1ab4bfb5943d254863b37c60f",
            "vortex": "3653c5e47df75a6b60fa957492f3378d99a5139453ca12db2f96ba2a18b407cb",
            "fire": "09a7d59b55ffbb0ab58d3b83db0c5b1409cb46a348779c39e3db293a6684cd02",
            "energy-transfer": "4c6425ebe8dd6f0caea2f50b98950b95367b1c63918e5f31032631d64b8eb2c3",
            "glitch": "2eea8c4428c5292f842b7b14daf4f483b8de57548ae61469c265130809691aea",
        }
        for effect_id, fingerprint in expected.items():
            effect = EFFECT_REGISTRY.get(effect_id)
            parameters = EFFECT_REGISTRY.parameters(effect_id)
            frames = bytearray()
            for animation_time in (0.0, 0.4, 0.8):
                for y in range(6):
                    for x in range(8):
                        color = effect.sample(
                            x,
                            y,
                            8,
                            6,
                            animation_time,
                            self.fixture,
                            parameters,
                            self.context,
                        )
                        frames.extend(
                            (
                                round(color.red * 255),
                                round(color.green * 255),
                                round(color.blue * 255),
                            )
                        )
            with self.subTest(effect=effect_id):
                self.assertEqual(hashlib.sha256(frames).hexdigest(), fingerprint)

    def test_fire_is_hotter_at_physical_bottom_and_moves_upward(self) -> None:
        effect = EFFECT_REGISTRY.get("fire")
        parameters = EFFECT_REGISTRY.parameters("fire")
        for animation_time in (0.0, 0.4, 0.8, 1.2):
            rows = []
            for y in range(4):
                colors = [
                    effect.sample(
                        x, y, 12, 4, animation_time, self.fixture, parameters,
                        self.context,
                    )
                    for x in range(12)
                ]
                rows.append(
                    sum(c.red + c.green + c.blue for c in colors) / len(colors)
                )
            with self.subTest(animation_time=animation_time):
                self.assertGreater(rows[-1], rows[0])

    def test_flame_jet_has_left_muzzle_and_crosses_fixture_boundary(self) -> None:
        effect = EFFECT_REGISTRY.get("flame-jet")
        parameters = EFFECT_REGISTRY.parameters("flame-jet")
        fixture_a = FixtureIdentity("Cube A", 0, 2)
        fixture_b = FixtureIdentity("Cube B", 1, 2)

        def energy(fixture: FixtureIdentity, x: int, animation_time: float) -> float:
            return sum(
                sum((color.red, color.green, color.blue))
                for y in range(4)
                for color in (
                    effect.sample(
                        x, y, 12, 4, animation_time, fixture, parameters,
                        self.context,
                    ),
                )
            )

        for animation_time in (0.0, 0.6, 1.2):
            with self.subTest(animation_time=animation_time):
                muzzle = energy(fixture_a, 0, animation_time)
                left_seam = energy(fixture_a, 11, animation_time)
                right_seam = energy(fixture_b, 0, animation_time)
                far_tip = energy(fixture_b, 11, animation_time)
                self.assertGreater(muzzle, far_tip)
                self.assertGreater(left_seam, 0.05)
                self.assertGreater(right_seam, 0.05)
                self.assertGreater(far_tip, 0.01)


if __name__ == "__main__":
    unittest.main()
