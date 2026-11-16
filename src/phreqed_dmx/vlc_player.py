"""Bounded VLC command and display-environment helpers for Stage projection."""

from __future__ import annotations

import os
from pathlib import Path

from .projection import StageVideoPackage


def build_display_environment(
    base: dict[str, str],
    *,
    user_id: int,
    runtime_directory: str | Path | None = None,
) -> dict[str, str]:
    """Resolve the active user Wayland socket for an SSH/TTY launch."""

    environment = dict(base)
    runtime = Path(
        environment.get("XDG_RUNTIME_DIR")
        or runtime_directory
        or Path("/run/user") / str(user_id)
    )
    environment.setdefault("XDG_RUNTIME_DIR", str(runtime))
    if not environment.get("WAYLAND_DISPLAY") and runtime.is_dir():
        sockets = sorted(
            path
            for path in runtime.glob("wayland-*")
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
    """Build the fixed, audio-free, one-package VLC argument vector."""

    if isinstance(screen_number, bool) or not 0 <= screen_number <= 7:
        raise ValueError("VLC screen number must be between 0 and 7")
    return [
        str(vlc_executable),
        "--intf",
        "qt",
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


def active_user_id() -> int:
    """Return the current Unix user ID without breaking Windows imports."""

    return getattr(os, "getuid", lambda: 0)()
