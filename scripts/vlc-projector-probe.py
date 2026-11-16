#!/usr/bin/env python3
"""Play one preflighted Stage rendition on a selected VLC Qt screen."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from phreqed_dmx.projection import load_stage_video_package
from phreqed_dmx.vlc_player import (
    active_user_id,
    build_display_environment,
    build_vlc_command,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--screen", type=int, default=1)
    parser.add_argument("--vlc", default="vlc")
    parser.add_argument(
        "--confirm-projector-output",
        action="store_true",
        help="required acknowledgment that a visible five-second probe is intended",
    )
    args = parser.parse_args()
    if not args.confirm_projector_output:
        parser.error("--confirm-projector-output is required")
    executable = shutil.which(args.vlc) if Path(args.vlc).name == args.vlc else args.vlc
    if not executable or not Path(executable).is_file():
        raise SystemExit(f"VLC executable is unavailable: {args.vlc}")
    package = load_stage_video_package(args.manifest)
    command = build_vlc_command(
        package,
        vlc_executable=executable,
        screen_number=args.screen,
    )
    environment = build_display_environment(
        os.environ,
        user_id=active_user_id(),
    )
    timeout = max(15.0, package.duration_seconds + 10.0)
    try:
        completed = subprocess.run(
            command,
            check=False,
            env=environment,
            shell=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit("VLC projector probe did not exit on schedule") from exc
    if completed.returncode != 0:
        raise SystemExit(
            f"VLC projector probe exited with status {completed.returncode}"
        )
    print(
        f"VLC projector probe completed on screen {args.screen}: "
        f"{package.package_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
