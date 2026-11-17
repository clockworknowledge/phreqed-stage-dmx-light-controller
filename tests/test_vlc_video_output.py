from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from phreqed_dmx.projection import ProjectionPackageRegistry
from phreqed_dmx.video_show import VideoScene
from phreqed_dmx.vlc_video_output import VlcVideoTrackOutput
from tests.test_projection import write_package


class FakeProcess:
    def __init__(self, returncode=None) -> None:
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


class VlcVideoTrackOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        write_package(root)
        self.registry = ProjectionPackageRegistry(root)
        self.registry.refresh()
        self.scene = VideoScene(
            "vscene-test",
            "Test",
            "video-edl-test--portrait-test",
            "portrait-character",
            False,
        )

    def test_launches_fixed_command_at_offset_and_stops_on_black(self):
        launches = []
        process = FakeProcess()

        def launch(command, environment):
            launches.append((list(command), dict(environment)))
            return process

        output = VlcVideoTrackOutput(
            self.registry,
            surface_id="portrait-character",
            vlc_executable="/usr/bin/vlc",
            output_name="HDMI-A-2",
            environment={"DISPLAY": ":0"},
            process_factory=launch,
        )
        output.activate(self.scene, 1.5, 100.0)
        self.assertIn("--vout=xcb_x11", launches[0][0])
        self.assertNotIn("--fullscreen", launches[0][0])
        self.assertIn("--start-time=1.500000", launches[0][0])
        self.assertEqual(launches[0][0][-1], str(self.registry.resolve(
            "video-edl-test--portrait-test"
        ).video_path))
        self.assertTrue(output.status()["running"])
        self.assertEqual(output.status()["output_name"], "HDMI-A-2")
        output.black()
        self.assertTrue(process.terminated)
        self.assertFalse(output.status()["running"])

    def test_rejects_wrong_surface_loop_and_unavailable_package(self):
        output = VlcVideoTrackOutput(
            self.registry,
            surface_id="portrait-character",
            vlc_executable="vlc",
            output_name="HDMI-A-2",
            environment={},
            process_factory=lambda _command, _environment: FakeProcess(),
        )
        with self.assertRaisesRegex(ValueError, "not portrait-character"):
            output.activate(
                VideoScene("vscene-wrong", "Wrong", self.scene.package_id, "landscape-main", False),
                0.0,
                0.0,
            )
        with self.assertRaisesRegex(ValueError, "not commissioned"):
            output.activate(
                VideoScene("vscene-loop", "Loop", self.scene.package_id, self.scene.surface_id, True),
                0.0,
                0.0,
            )
        with self.assertRaisesRegex(ValueError, "unavailable"):
            output.activate(
                VideoScene("vscene-missing", "Missing", "missing--portrait", self.scene.surface_id, False),
                0.0,
                0.0,
            )

    def test_check_reports_an_unexpected_player_exit(self):
        process = FakeProcess()
        output = VlcVideoTrackOutput(
            self.registry,
            surface_id="portrait-character",
            vlc_executable="vlc",
            output_name="HDMI-A-2",
            environment={},
            process_factory=lambda _command, _environment: process,
        )
        output.activate(self.scene, 0.0, 0.0)
        process.returncode = 7
        with self.assertRaisesRegex(RuntimeError, "unexpectedly with status 7"):
            output.check()
        self.assertFalse(output.status()["running"])
        self.assertIn("status 7", output.status()["last_error"])


if __name__ == "__main__":
    unittest.main()
