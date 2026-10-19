import unittest

from phreqed_dmx.color import BLACK_NORMALIZED
from phreqed_dmx.engine import SceneEngine
from phreqed_dmx.fixtures import FixtureConfig
from phreqed_dmx.presets import EXAMPLE_PRESETS
from phreqed_dmx.render import compose_dmx
from phreqed_dmx.show_control import ShowController


FIXTURES = (
    FixtureConfig(name="Cube A", start_address=1),
    FixtureConfig(name="Cube B", start_address=153),
)


class SceneEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SceneEngine(FIXTURES)

    def test_example_presets_exist_and_render_deterministically(self) -> None:
        self.assertGreaterEqual(len(EXAMPLE_PRESETS), 3)
        for preset in EXAMPLE_PRESETS:
            with self.subTest(preset=preset.preset_id):
                first = self.engine.render_preset(preset.preset_id, 1.25)
                second = self.engine.render_preset(preset.preset_id, 1.25)
                self.assertEqual(first["Cube A"].rows(), second["Cube A"].rows())
                self.assertEqual(set(first), {"Cube A", "Cube B"})

    def test_manual_fixture_effects_remain_independent(self) -> None:
        self.engine.select_effect("Cube A", "plasma")
        self.engine.select_effect("Cube B", "tunnel")
        first = self.engine.render(0.75)
        cube_b_before = first["Cube B"].rows()

        self.engine.select_effect("Cube A", "fire")
        second = self.engine.render(0.75)

        self.assertNotEqual(first["Cube A"].rows(), second["Cube A"].rows())
        self.assertEqual(cube_b_before, second["Cube B"].rows())

    def test_parameter_updates_are_validated(self) -> None:
        self.engine.select_effect("Cube A", "fire")
        self.engine.update_parameter("Cube A", "cooling", 0.5)
        with self.assertRaises(ValueError):
            self.engine.update_parameter("Cube A", "cooling", 2.0)

    def test_blackout_returns_black_scene(self) -> None:
        self.engine.set_blackout(True)
        scene = self.engine.render(3.0)
        self.assertTrue(
            all(color == BLACK_NORMALIZED for grid in scene.values() for row in grid.rows() for color in row)
        )

    def test_normalized_scene_quantizes_only_at_dmx_boundary(self) -> None:
        scene = self.engine.render(0.5)
        dmx = compose_dmx(FIXTURES, scene)
        self.assertEqual(len(dmx), 512)
        self.assertEqual(dmx[144:152], bytes(8))
        self.assertEqual(dmx[296:304], bytes(8))
        self.assertLessEqual(max(dmx), round(0.65 * 255))

    def test_preset_transition_preserves_geometry(self) -> None:
        scene = self.engine.transition_presets(
            "psychedelic-bloom", "molten-motion", 0.8, 0.5
        )
        self.assertEqual(len(scene["Cube A"].rows()), 6)
        self.assertTrue(all(len(row) == 8 for row in scene["Cube B"].rows()))


class ShowControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SceneEngine(FIXTURES)
        self.controls = ShowController(self.engine)

    def test_blackout_and_effect_commands_are_transport_independent(self) -> None:
        self.controls.select_effect("Cube A", "vortex")
        self.controls.update_parameter("Cube A", "arms", 5.0)
        self.controls.blackout()
        self.assertTrue(self.engine.blackout_enabled)
        self.controls.blackout(False)
        self.assertFalse(self.engine.blackout_enabled)

    def test_tap_tempo_and_scene_navigation(self) -> None:
        self.controls.tap_tempo(10.0)
        self.assertEqual(self.controls.tap_tempo(10.5), 120.0)
        original = self.engine.active_preset_id
        selected = self.controls.next_scene()
        self.assertNotEqual(original, selected)
        self.assertEqual(self.controls.previous_scene(), original)

    def test_trigger_event_updates_performance_context(self) -> None:
        self.controls.trigger_event("accent")
        self.assertEqual(self.controls.context(1.0).event, "accent")


if __name__ == "__main__":
    unittest.main()
