#!/usr/bin/env python3
"""Play one preflighted Stage rendition on a selected VLC Qt screen."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from phreqed_dmx.projection import StageVideoPackage, load_stage_video_package


def build_display_environment(
    base: dict[str, str], *, user_id: int,
    runtime_directory: str | Path | None = None,
) -> dict[str, str]:
    """Resolve the active user Wayland socket for an SSH/TTY-launched probe."""

    environment = dict(base)
    runtime = Path(
        environment.get("XDG_RUNTIME_DIR")
        or runtime_directory
        or Path("/run/user") / str(user_id)
    )
    environment.setdefault("XDG_RUNTIME_DIR", str(runtime))
    if not environment.get("WAYLAND_DISPLAY") and runtime.is_dir():
        sockets = sorted(
            path for path in runtime.glob("wayland-*")
            if not path.name.endswith(".lock")
        )
        if sockets:
            environment["WAYLAND_DISPLAY"] = sockets[0].name
    if environment.get("WAYLAND_DISPLAY"):
        environment.setdefault("QT_QPA_PLATFORM", "wayland")
    return environment


def build_vlc_command(
    package: StageVideoPackage,
    *,
    vlc_executable: str | Path,
    screen_number: int,
) -> list[str]:
    if isinstance(screen_number, bool) or not 0 <= screen_number <= 7:
        raise ValueError("VLC screen number must be between 0 and 7")
    return [
        str(vlc_executable),
        "--intf", "qt",
        "--no-one-instance",
        "--no-media-library",
        "--no-qt-privacy-ask",
        "--qt-minimal-view",
        "--no-qt-fs-controller",
        f"--qt-fullscreen-screennumber={screen_number}",
        "--fullscreen",
        "--no-video-title-show",
        "--no-osd",
        "--no-audio",
        "--play-and-exit",
        str(package.video_path),
    ]


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
        user_id=getattr(os, "getuid", lambda: 0)(),
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
