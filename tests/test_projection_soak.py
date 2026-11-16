import json
from pathlib import Path
import runpy
import tempfile
import unittest


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "projection-soak.py")
)
log_diagnostics = SCRIPT["_log_diagnostics"]
run_render_probe = SCRIPT["run_render_probe"]
write_json_atomic = SCRIPT["write_json_atomic"]


class FakeProcess:
    pid = 12345

    def __init__(self, running_polls: int = 3) -> None:
        self.running_polls = running_polls
        self.polls = 0

    def poll(self):
        self.polls += 1
        return None if self.polls <= self.running_polls else 0


class ProjectionSoakTests(unittest.TestCase):
    def test_short_probe_preserves_render_deadline_and_reserved_channels(self):
        result = run_render_probe(
            FakeProcess(),
            maximum_seconds=1.0,
            temperature_reader=lambda: 49.5,
            player_sampler=lambda _pid: {
                "rss_kib": 1234,
                "cpu_seconds": 0.25,
            },
        )
        self.assertGreaterEqual(result["frames"], 2)
        self.assertEqual(result["missed_slots"], 0)
        self.assertEqual(result["over_budget_frames"], 0)
        self.assertTrue(result["unmapped_channels_zero"])
        self.assertTrue(result["blackout_zero"])
        self.assertEqual(result["temperature_max_c"], 49.5)
        self.assertEqual(result["temperature_band"], "normal")
        self.assertFalse(result["timed_out"])

    def test_vlc_fallback_log_is_evidence_not_a_fake_drop_count(self):
        diagnostics = log_diagnostics(
            "h264_v4l2m2m cannot start codec\n"
            "wl_dmabuf vout display: <<< Open:\n"
            'interface "globalhotkeys,none" initialization failed\n'
        )
        self.assertTrue(diagnostics["v4l2_h264_fallback_observed"])
        self.assertTrue(diagnostics["wayland_dmabuf_output_observed"])
        self.assertTrue(diagnostics["global_hotkeys_unavailable"])
        self.assertIsNone(diagnostics["video_dropped_frames"])

    def test_report_write_is_atomic_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            write_json_atomic(path, {"passed": True})
            self.assertEqual(json.loads(path.read_text()), {"passed": True})
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
