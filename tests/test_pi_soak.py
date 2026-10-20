from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest

from phreqed_dmx.audio_analysis import AudioAnalysis, FrequencyBands


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "pi-soak.py")
)
FootProbeCommands = SCRIPT["FootProbeCommands"]
run_look = SCRIPT["run_look"]


class FakeAudioSource:
    def __init__(self) -> None:
        self.chunks = 0

    def sample(self, elapsed: float) -> AudioAnalysis:
        self.chunks += 1
        return AudioAnalysis(0.4, 0.2, FrequencyBands(0.6, 0.3, 0.1))

    def status(self) -> SimpleNamespace:
        return SimpleNamespace(
            running=True,
            healthy=True,
            message="capturing",
            chunks_processed=self.chunks,
        )


class PiSoakTests(unittest.TestCase):
    def test_foot_probe_counts_actions_without_show_side_effects(self):
        probe = FootProbeCommands()
        probe.previous_scene()
        probe.next_scene()
        probe.tap_tempo(1.0)
        probe.tap_tempo(2.0)
        probe.blackout(True)
        probe.blackout(False)
        self.assertEqual(
            probe.snapshot(),
            {
                "previous_scene": 1,
                "next_scene": 1,
                "tap_tempo": 2,
                "blackout_on": 1,
                "blackout_off": 1,
            },
        )

    def test_short_look_checks_audio_and_safe_dmx_frame(self):
        result = run_look(
            "preset", "phase-collider", 0.05, audio_source=FakeAudioSource()
        )
        self.assertEqual(result["frames"], 2)
        self.assertTrue(result["unmapped_channels_zero"])
        self.assertTrue(result["blackout_zero"])
        self.assertTrue(result["audio"]["running"])
        self.assertTrue(result["audio"]["healthy"])
        self.assertGreater(result["audio"]["chunks_processed"], 0)
        self.assertEqual(result["audio"]["loudness_peak"], 0.4)


if __name__ == "__main__":
    unittest.main()
