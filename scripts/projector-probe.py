#!/usr/bin/env python3
"""Read-only projector/display and candidate-player inventory for the Stage Pi."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess


DISPLAY_COMMANDS = {
    "wlr-randr": ("wlr-randr",),
    "kmsprint": ("kmsprint",),
    "xrandr": ("xrandr", "--query"),
}
PLAYER_COMMANDS = (
    "cvlc",
    "vlc",
    "mpv",
    "gst-launch-1.0",
    "ffmpeg",
    "ffprobe",
)


def run_command(arguments: tuple[str, ...]) -> dict:
    try:
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def collect_probe() -> dict:
    displays = {}
    for name, arguments in DISPLAY_COMMANDS.items():
        executable = shutil.which(arguments[0])
        if executable is not None:
            displays[name] = run_command((executable, *arguments[1:]))
    players = {
        name: path
        for name in PLAYER_COMMANDS
        if (path := shutil.which(name)) is not None
    }
    return {
        "version": 1,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "session": {
            "type": os.environ.get("XDG_SESSION_TYPE"),
            "runtime_directory": os.environ.get("XDG_RUNTIME_DIR"),
            "wayland_display": os.environ.get("WAYLAND_DISPLAY"),
            "x_display": os.environ.get("DISPLAY"),
        },
        "display_commands": displays,
        "candidate_players": players,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = collect_probe()
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
