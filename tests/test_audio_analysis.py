import unittest

from phreqed_dmx.app import Controller
from phreqed_dmx.audio_analysis import (
    AudioAnalysis,
    FrequencyBands,
    ManualAudioAnalysisSource,
    RecordedAudioAnalysisSource,
    RecordedAudioFrame,
    SILENT_AUDIO,
)
from phreqed_dmx.config import ControllerConfig
from phreqed_dmx.effect_api import FixtureIdentity, PerformanceContext
from phreqed_dmx.effect_library import EFFECT_REGISTRY
from phreqed_dmx.fixtures import FixtureConfig


FIXTURES = (
    FixtureConfig(name="Cube A", start_address=1),
    FixtureConfig(name="Cube B", start_address=153),
)


class AudioAnalysisTests(unittest.TestCase):
    def test_normalized_values_reject_invalid_inputs(self) -> None:
        invalid_factories = (
            lambda: AudioAnalysis(loudness=-0.1),
            lambda: AudioAnalysis(onset=1.1),
            lambda: FrequencyBands(bass=float("nan")),
            lambda: FrequencyBands(mid=True),
            lambda: AudioAnalysis(bands="invalid"),
            lambda: RecordedAudioFrame(-1.0, SILENT_AUDIO),
        )
        for factory in invalid_factories:
            with self.subTest(factory=factory), self.assertRaises((TypeError, ValueError)):
                factory()

    def test_manual_source_updates_without_capture_or_network(self) -> None:
        source = ManualAudioAnalysisSource()
        self.assertEqual(source.sample(0.0), SILENT_AUDIO)
        analysis = AudioAnalysis(0.7, 0.4, FrequencyBands(0.9, 0.5, 0.2))
        source.update(analysis)
        self.assertEqual(source.sample(20.0), analysis)

    def test_recorded_source_uses_deterministic_previous_sample_hold(self) -> None:
        first = AudioAnalysis(0.2, 0.0, FrequencyBands(0.5, 0.1, 0.0))
        second = AudioAnalysis(0.8, 1.0, FrequencyBands(0.9, 0.6, 0.3))
        source = RecordedAudioAnalysisSource(
            (RecordedAudioFrame(1.0, first), RecordedAudioFrame(2.0, second))
        )
        self.assertEqual(source.sample(0.5), SILENT_AUDIO)
        self.assertEqual(source.sample(1.0), first)
        self.assertEqual(source.sample(1.9), first)
        self.assertEqual(source.sample(2.0), second)
        self.assertEqual(source.sample(99.0), second)

        with self.assertRaises(ValueError):
            RecordedAudioAnalysisSource(
                (RecordedAudioFrame(1.0, first), RecordedAudioFrame(1.0, second))
            )

    def test_controller_injects_source_only_when_context_is_not_explicit(self) -> None:
        analysis = AudioAnalysis(0.8, 0.6, FrequencyBands(0.9, 0.4, 0.2))
        source = ManualAudioAnalysisSource(analysis)
        config = ControllerConfig("127.0.0.1", 6454, 0, 25, FIXTURES)
        controller = Controller(config, audio_source=source)
        controller.engine.activate_preset("phase-collider")

        sourced = controller.render_scene(1.25, apply_safety=False)
        explicit = controller.render_scene(
            1.25, context=PerformanceContext(), apply_safety=False
        )
        self.assertNotEqual(sourced["Cube A"].rows(), explicit["Cube A"].rows())
        dmx = controller.render_dmx(1.25, context=PerformanceContext(audio=analysis))
        self.assertEqual(dmx[144:152], bytes(8))
        self.assertEqual(dmx[296:304], bytes(8))

    def test_show_control_accepts_and_clears_manual_analysis(self) -> None:
        analysis = AudioAnalysis(0.6, 0.2, FrequencyBands(0.8, 0.3, 0.1))
        config = ControllerConfig("127.0.0.1", 6454, 0, 25, FIXTURES)
        controller = Controller(config)
        controller.show.update_audio_analysis(analysis)
        self.assertEqual(controller.show.context(1.0).audio, analysis)
        controller.show.update_audio_analysis(None)
        self.assertIsNone(controller.show.context(1.0).audio)

    def test_radial_pulse_reacts_deterministically_and_stays_normalized(self) -> None:
        effect = EFFECT_REGISTRY.get("radial-pulse")
        parameters = EFFECT_REGISTRY.parameters("radial-pulse")
        fixture = FixtureIdentity("Cube A", 0, 2)
        audio = AudioAnalysis(0.9, 0.8, FrequencyBands(1.0, 0.4, 0.2))
        reactive_context = PerformanceContext(audio=audio)
        plain_context = PerformanceContext()

        reactive = [
            effect.sample(x, y, 12, 4, 0.75, fixture, parameters, reactive_context)
            for y in range(4)
            for x in range(12)
        ]
        repeated = [
            effect.sample(x, y, 12, 4, 0.75, fixture, parameters, reactive_context)
            for y in range(4)
            for x in range(12)
        ]
        plain = [
            effect.sample(x, y, 12, 4, 0.75, fixture, parameters, plain_context)
            for y in range(4)
            for x in range(12)
        ]
        self.assertEqual(reactive, repeated)
        self.assertNotEqual(reactive, plain)
        self.assertTrue(
            all(
                0.0 <= channel <= 1.0
                for color in reactive
                for channel in (color.red, color.green, color.blue)
            )
        )


if __name__ == "__main__":
    unittest.main()
