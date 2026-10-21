from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest

from phreqed_dmx.audio_analysis import AudioAnalysis, FrequencyBands


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "pi-soak.py")
)
FootProbeCommands = SCRIPT["FootProbeCommands"]
foot_control_passed = SCRIPT["foot_control_passed"]
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

    def test_foot_gate_accepts_a_recovered_disconnect(self):
        actions = {
            "previous_scene": 1,
            "next_scene": 1,
            "tap_tempo": 2,
            "blackout_on": 1,
            "blackout_off": 1,
        }
        status = SimpleNamespace(running=True, connected=True)
        events = [
            "Foot controller disconnected; reconnecting: USB reset",
            "Foot controller reconnected",
        ]
        self.assertTrue(
            foot_control_passed(actions, events, status, require_actions=True)
        )

    def test_foot_gate_rejects_missing_actions_lost_device_and_command_errors(self):
        actions = {
            "previous_scene": 1,
            "next_scene": 0,
            "tap_tempo": 2,
            "blackout_on": 1,
            "blackout_off": 1,
        }
        connected = SimpleNamespace(running=True, connected=True)
        disconnected = SimpleNamespace(running=True, connected=False)
        self.assertFalse(
            foot_control_passed(actions, [], connected, require_actions=True)
        )
        actions["next_scene"] = 1
        self.assertFalse(
            foot_control_passed(actions, [], disconnected, require_actions=True)
        )
        self.assertFalse(
            foot_control_passed(
                actions,
                ["Foot action next_scene ignored: invalid scene"],
                connected,
                require_actions=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
