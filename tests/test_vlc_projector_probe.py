from __future__ import annotations

import runpy
from pathlib import Path
import unittest

from phreqed_dmx.projection import StageVideoPackage


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "vlc-projector-probe.py"),
    run_name="vlc_projector_probe",
)
build_vlc_command = SCRIPT["build_vlc_command"]
build_display_environment = SCRIPT["build_display_environment"]


class VlcProjectorProbeTests(unittest.TestCase):
    def test_discovers_wayland_socket_for_tty_launch(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            (runtime / "wayland-1").touch()
            (runtime / "wayland-1.lock").touch()
            environment = build_display_environment(
                {}, user_id=1000, runtime_directory=runtime
            )
        self.assertEqual(environment["XDG_RUNTIME_DIR"], str(runtime))
        self.assertEqual(environment["WAYLAND_DISPLAY"], "wayland-1")
        self.assertEqual(environment["QT_QPA_PLATFORM"], "wayland")

    def test_builds_fixed_audio_free_selected_screen_command(self) -> None:
        package = StageVideoPackage(
            package_id="video-probe--portrait",
            manifest_path=Path("manifest.json"),
            video_path=Path("video.mp4"),
            duration_seconds=5.0,
            width=1280,
            height=720,
            frame_rate=30.0,
            sha256="0" * 64,
        )
        command = build_vlc_command(
            package, vlc_executable="/usr/bin/vlc", screen_number=1
        )
        self.assertEqual(command[0], "/usr/bin/vlc")
        self.assertIn("--qt-fullscreen-screennumber=1", command)
        self.assertIn("--fullscreen", command)
        self.assertIn("--no-audio", command)
        self.assertIn("--play-and-exit", command)
        self.assertEqual(command[-1], "video.mp4")
        resumed = build_vlc_command(
            package,
            vlc_executable="/usr/bin/vlc",
            screen_number=1,
            start_seconds=1.25,
        )
        self.assertIn("--start-time=1.250000", resumed)
        with self.assertRaisesRegex(ValueError, "outside the package"):
            build_vlc_command(
                package,
                vlc_executable="vlc",
                screen_number=1,
                start_seconds=5.0,
            )
        with self.assertRaisesRegex(ValueError, "between 0 and 7"):
            build_vlc_command(
                package, vlc_executable="vlc", screen_number=8
            )


if __name__ == "__main__":
    unittest.main()
