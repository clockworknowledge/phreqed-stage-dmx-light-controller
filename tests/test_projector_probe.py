from __future__ import annotations

import runpy
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "projector-probe.py"),
    run_name="projector_probe",
)
collect_probe = SCRIPT["collect_probe"]
run_command = SCRIPT["run_command"]


class ProjectorProbeTests(unittest.TestCase):
    def test_command_is_read_only_shell_free_and_bounded(self) -> None:
        completed = type("Completed", (), {
            "returncode": 0,
            "stdout": "HDMI-A-1 connected\n",
            "stderr": "",
        })()
        with patch("subprocess.run", return_value=completed) as runner:
            result = run_command(("/usr/bin/wlr-randr",))
        self.assertEqual(result["returncode"], 0)
        runner.assert_called_once_with(
            ("/usr/bin/wlr-randr",),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )

    def test_collects_only_available_display_tools_and_players(self) -> None:
        available = {
            "wlr-randr": "/usr/bin/wlr-randr",
            "mpv": "/usr/bin/mpv",
            "ffmpeg": "/usr/bin/ffmpeg",
        }
        with (
            patch.dict(collect_probe.__globals__, {
                "run_command": lambda arguments: {
                    "returncode": 0, "stdout": arguments[0], "stderr": ""
                },
            }),
            patch("shutil.which", side_effect=lambda name: available.get(name)),
        ):
            result = collect_probe()
        self.assertEqual(set(result["display_commands"]), {"wlr-randr"})
        self.assertEqual(
            set(result["candidate_players"]), {"mpv", "ffmpeg"}
        )


if __name__ == "__main__":
    unittest.main()
