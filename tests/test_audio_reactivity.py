import unittest

from phreqed_dmx.app import Controller
from phreqed_dmx.audio_analysis import AudioAnalysis, FrequencyBands
from phreqed_dmx.audio_reactivity import AudioReactiveClock
from phreqed_dmx.config import load_config
from phreqed_dmx.effect_api import PerformanceContext
from phreqed_dmx.effect_library import EFFECT_REGISTRY
from phreqed_dmx.engine import SceneEngine


LOUD = AudioAnalysis(0.9, 0.8, FrequencyBands(1.0, 0.6, 0.4))


class AudioReactiveClockTests(unittest.TestCase):
    def test_tempo_sets_base_rate_without_audio(self) -> None:
        slow = AudioReactiveClock().advance(
            1.0, tempo_bpm=60.0, speed=1.0, audio=None
        )
        normal = AudioReactiveClock().advance(
            1.0, tempo_bpm=120.0, speed=1.0, audio=None
        )
        self.assertAlmostEqual(slow.animation_time, 0.5)
        self.assertAlmostEqual(normal.animation_time, 1.0)
        self.assertEqual(normal.motion_multiplier, 1.0)
        self.assertEqual(normal.brightness_multiplier, 1.0)

    def test_audio_dynamics_are_smoothed_and_bounded(self) -> None:
        clock = AudioReactiveClock()
        quiet = clock.advance(
            0.5, tempo_bpm=120.0, speed=1.0, audio=AudioAnalysis()
        )
        loud = clock.advance(1.0, tempo_bpm=120.0, speed=1.0, audio=LOUD)
        self.assertGreaterEqual(quiet.brightness_multiplier, 0.55)
        self.assertLess(quiet.brightness_multiplier, 1.0)
        self.assertGreater(loud.motion_multiplier, 1.0)
        self.assertLessEqual(loud.motion_multiplier, 2.0)
        self.assertGreater(loud.brightness_multiplier, quiet.brightness_multiplier)
        self.assertLessEqual(loud.brightness_multiplier, 1.0)

    def test_deep_dim_is_explicit_and_uses_configured_near_black_floor(self) -> None:
        normal = AudioReactiveClock().advance(
            2.0, tempo_bpm=120.0, speed=1.0, audio=AudioAnalysis()
        )
        deep = AudioReactiveClock(
            deep_dim_enabled=True, quiet_brightness_floor=0.02
        ).advance(2.0, tempo_bpm=120.0, speed=1.0, audio=AudioAnalysis())
        self.assertGreater(normal.brightness_multiplier, 0.54)
        self.assertLess(deep.brightness_multiplier, 0.03)

        clock = AudioReactiveClock()
        with self.assertRaises(ValueError):
            clock.configure_dimming(enabled=True, quiet_floor=0.5)

    def test_every_registered_effect_uses_shared_reactive_clock(self) -> None:
        config = load_config()
        for metadata in EFFECT_REGISTRY.metadata():
            with self.subTest(effect=metadata.effect_id):
                engine = SceneEngine(config.fixtures)
                for fixture in config.fixtures:
                    engine.select_effect(fixture.name, metadata.effect_id)
                controller = Controller(config, engine)
                controller.render_scene(
                    0.5,
                    context=PerformanceContext(tempo_bpm=120.0, audio=LOUD),
                    apply_safety=False,
                )
                self.assertGreater(controller.audio_motion_multiplier, 1.0)
                self.assertGreater(controller.audio_clock.animation_time, 0.5)
                self.assertLessEqual(controller.audio_brightness_multiplier, 1.0)


if __name__ == "__main__":
    unittest.main()
