import unittest
import hashlib

from phreqed_dmx.audio_analysis import AudioAnalysis, FrequencyBands
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
    "pacman",
    "blinking-eye",
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

    def test_flame_jet_strands_vary_across_space_and_time(self) -> None:
        effect = EFFECT_REGISTRY.get("flame-jet")
        parameters = EFFECT_REGISTRY.parameters("flame-jet")

        def combined(animation_time: float) -> tuple[float, ...]:
            columns = []
            for global_x in range(24):
                fixture = FixtureIdentity(
                    "Cube A" if global_x < 12 else "Cube B", global_x // 12, 2
                )
                x = global_x % 12
                columns.append(sum(
                    sum((color.red, color.green, color.blue))
                    for y in range(4)
                    for color in (
                        effect.sample(
                            x, y, 12, 4, animation_time, fixture, parameters,
                            self.context,
                        ),
                    )
                ))
            return tuple(columns)

        first = combined(0.35)
        second = combined(0.73)
        downstream = first[3:21]
        self.assertGreater(max(downstream) - min(downstream), 0.25)
        self.assertGreater(
            sum(abs(left - right) for left, right in zip(first, second)), 0.5
        )

    def test_dynamic_wave_keeps_stable_sine_geometry_on_music_pulse(self) -> None:
        effect = EFFECT_REGISTRY.get("dynamic-wave")
        parameters = EFFECT_REGISTRY.parameters("dynamic-wave")
        quiet = PerformanceContext(audio=AudioAnalysis())
        pulse = PerformanceContext(
            audio=AudioAnalysis(
                loudness=0.8,
                onset=1.0,
                bands=FrequencyBands(bass=0.9, mid=0.5, treble=0.7),
            )
        )

        def frame(context: PerformanceContext) -> tuple[NormalizedRGB, ...]:
            return tuple(
                effect.sample(
                    x, y, 12, 4, 0.75,
                    FixtureIdentity("Cube A", 0, 2),
                    parameters,
                    context,
                )
                for y in range(4)
                for x in range(12)
            )

        self.assertEqual(frame(quiet), frame(quiet))
        self.assertNotEqual(frame(quiet), frame(pulse))

        for context in (quiet, pulse):
            brightest_rows = []
            for global_x in range(24):
                fixture = FixtureIdentity(
                    "Cube A" if global_x < 12 else "Cube B", global_x // 12, 2
                )
                column = [
                    effect.sample(
                        global_x % 12, y, 12, 4, 0.75, fixture, parameters,
                        context,
                    )
                    for y in range(4)
                ]
                brightest_rows.append(max(
                    range(4),
                    key=lambda row: sum((
                        column[row].red, column[row].green, column[row].blue
                    )),
                ))
            self.assertTrue(all(
                abs(left - right) <= 2
                for left, right in zip(brightest_rows, brightest_rows[1:])
            ))

    def test_pacman_moves_continuously_across_combined_fixture_surface(self) -> None:
        effect = EFFECT_REGISTRY.get("pacman")
        parameters = EFFECT_REGISTRY.parameters("pacman", {
            "palette": "ember", "direction": "left-right",
        })

        def bright_centroid(animation_time: float) -> float:
            weighted_x = 0.0
            total = 0.0
            for global_x in range(24):
                fixture = FixtureIdentity(
                    "Cube A" if global_x < 12 else "Cube B", global_x // 12, 2
                )
                for y in range(4):
                    color = effect.sample(
                        global_x % 12, y, 12, 4, animation_time, fixture,
                        parameters, self.context,
                    )
                    weight = max(color.red, color.green, color.blue)
                    if weight > 0.45:
                        weighted_x += global_x * weight
                        total += weight
            return weighted_x / total

        self.assertLess(bright_centroid(1.2), bright_centroid(2.0))

    def test_digital_rain_is_sparse_and_heads_move_downward(self) -> None:
        effect = EFFECT_REGISTRY.get("digital-rain")
        parameters = EFFECT_REGISTRY.parameters(
            "digital-rain",
            {"density": 0.46, "trail": 1.25, "palette": "matrix"},
        )
        fixture = FixtureIdentity("Cube A", 0, 2)

        lit_counts = []
        brightest_rows: dict[int, list[int]] = {x: [] for x in range(12)}
        for animation_time in tuple(index * 0.12 for index in range(80)):
            frame = [
                [
                    effect.sample(
                        x, y, 12, 4, animation_time, fixture, parameters,
                        self.context,
                    )
                    for x in range(12)
                ]
                for y in range(4)
            ]
            lit_counts.append(sum(color.green > 0.01 for row in frame for color in row))
            for x in range(12):
                column = [frame[y][x].green for y in range(4)]
                if max(column) > 0.2:
                    row = max(range(4), key=column.__getitem__)
                    if not brightest_rows[x] or brightest_rows[x][-1] != row:
                        brightest_rows[x].append(row)

        self.assertLess(max(lit_counts), 24)
        progressions = [rows for rows in brightest_rows.values() if len(rows) >= 3]
        self.assertTrue(progressions)
        self.assertTrue(
            any(
                all(right == (left + 1) % 4 for left, right in zip(rows, rows[1:]))
                for rows in progressions
            )
        )

    def test_blaster_supports_mirrored_and_center_out_directions(self) -> None:
        effect = EFFECT_REGISTRY.get("cross-blaster")
        left_parameters = EFFECT_REGISTRY.parameters(
            "cross-blaster", {"direction": "left-right"}
        )
        right_parameters = EFFECT_REGISTRY.parameters(
            "cross-blaster", {"direction": "right-left"}
        )
        center_parameters = EFFECT_REGISTRY.parameters(
            "cross-blaster", {"direction": "center-out"}
        )

        def combined(parameters, animation_time: float) -> tuple[NormalizedRGB, ...]:
            pixels = []
            for fixture_index in range(2):
                fixture = FixtureIdentity(f"Cube {fixture_index}", fixture_index, 2)
                pixels.extend(
                    effect.sample(
                        x, 1, 12, 4, animation_time, fixture, parameters,
                        self.context,
                    )
                    for x in range(12)
                )
            return tuple(pixels)

        left = combined(left_parameters, 0.45)
        right = combined(right_parameters, 0.45)
        self.assertEqual(left, tuple(reversed(right)))
        center = combined(center_parameters, 0.0)
        self.assertEqual(center, tuple(reversed(center)))
        self.assertGreater(
            center[11].red + center[11].green + center[11].blue, 0.0
        )
        self.assertGreater(
            center[12].red + center[12].green + center[12].blue, 0.0
        )

    def test_blinking_eye_closes_and_reopens_deterministically(self) -> None:
        effect = EFFECT_REGISTRY.get("blinking-eye")
        parameters = EFFECT_REGISTRY.parameters("blinking-eye")
        fixture = FixtureIdentity("Cube A", 0, 2)

        def energy(animation_time: float) -> float:
            return sum(
                color.red + color.green + color.blue
                for y in range(4)
                for x in range(12)
                for color in (
                    effect.sample(
                        x, y, 12, 4, animation_time, fixture, parameters,
                        self.context,
                    ),
                )
            )

        open_energy = energy(0.0)
        closed_time = 0.84 / parameters.number("blink_rate")
        closed_energy = energy(closed_time)
        self.assertGreater(open_energy, closed_energy * 2.0)
        self.assertEqual(closed_energy, energy(closed_time))


if __name__ == "__main__":
    unittest.main()
