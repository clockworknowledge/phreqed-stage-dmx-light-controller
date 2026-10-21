import unittest
from unittest.mock import Mock

from phreqed_dmx.app import Controller
from phreqed_dmx.config import load_config
from phreqed_dmx.library import Cue
from phreqed_dmx.scenes import SceneSequencer


class SceneSequenceTests(unittest.TestCase):
    def setUp(self):
        self.controller = Controller(load_config())
        self.engine = self.controller.engine
        self.scenes = self.controller.scenes
        self.cues = (Cue('First', 'psychedelic-bloom', 2, 1),
                     Cue('Second', 'molten-motion', 3, 0.5),
                     Cue('Third', 'digital-storm', 4, 0))
        self.scenes.replace(self.cues)

    def test_direct_next_previous_selection_and_wrap(self):
        self.scenes.move(1, 0)
        self.assertEqual(self.scenes.index, 0)
        self.scenes.move(-1, 1)
        self.assertEqual(self.scenes.index, 2)
        self.scenes.move(1, 2)
        self.assertEqual(self.scenes.index, 0)
        self.scenes.select(1, 3)
        self.assertEqual(self.engine.active_preset_id, 'molten-motion')

    def test_master_brightness_override_survives_scene_changes(self):
        self.engine.set_global_brightness(0.37)
        self.scenes.select(0, 0)
        self.controller.render_scene(0, apply_safety=False)
        self.assertEqual(self.engine.compositor.global_brightness, 0.37)
        self.scenes.select(1, 1)
        self.controller.render_scene(1, apply_safety=False)
        self.assertEqual(self.engine.compositor.global_brightness, 0.37)

    def test_timing_boundaries_and_final_hold(self):
        self.scenes.play(10)
        for timestamp, index in ((11.99, 0), (12, 1), (14.99, 1), (15, 2), (19, 2)):
            self.scenes.update(timestamp)
            self.assertEqual(self.scenes.index, index)
        self.assertFalse(self.scenes.playing)

    def test_skipped_time_uses_cue_deadlines(self):
        self.scenes.play(0)
        self.scenes.update(5.5)
        self.assertEqual(self.scenes.index, 2)
        self.assertEqual(self.scenes.started, 5)

    def test_blackout_cancels_fade_and_timed_playback_immediately(self):
        self.controller.render_dmx(0)
        self.scenes.play(0)
        self.controller.render_dmx(0.25)
        self.engine.set_blackout(True)
        self.assertEqual(self.controller.render_dmx(0.3), bytes(512))
        self.assertFalse(self.scenes.playing)
        self.engine.set_blackout(False)
        self.controller.render_dmx(100)
        self.assertEqual(self.scenes.index, 0)

    def test_zero_fade_cuts_and_fade_starts_at_previous_frame(self):
        previous = self.controller.render_scene(0, apply_safety=False)
        self.scenes.select(1, 0)
        first = self.controller.render_scene(0, apply_safety=False)
        self.assertEqual(previous['Cube A'].rows(), first['Cube A'].rows())
        end = self.controller.render_scene(0.5, apply_safety=False)
        self.assertNotEqual(end['Cube A'].rows(), first['Cube A'].rows())
        self.scenes.select(2, 1)
        self.assertIsNone(self.controller._transition_from)

    def test_invalid_selection_preserves_current_scene(self):
        self.scenes.select(0, 0)
        for value in (-1, 3, True, '1', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.scenes.select(value, 1)
        self.assertEqual(self.scenes.index, 0)

    def test_empty_and_unknown_scene_lists_fail_without_output(self):
        self.scenes.replace(())
        with self.assertRaises(ValueError):
            self.scenes.play(0)
        with self.assertRaises(ValueError):
            self.scenes.replace((Cue('Unknown', 'missing'),))
        self.assertEqual(self.scenes.cues, ())

    def test_timed_transitions_are_repeatable_at_supplied_times(self):
        def frames():
            controller = Controller(load_config())
            controller.scenes.replace(self.cues)
            controller.scenes.play(0)
            return [controller.render_dmx(t) for t in (0, 0.5, 2, 2.25, 3, 5, 6)]
        self.assertEqual(frames(), frames())
