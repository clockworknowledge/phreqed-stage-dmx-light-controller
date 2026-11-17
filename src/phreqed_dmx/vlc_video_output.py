"""Managed, package-ID-only VLC output for the optional Video song lane."""

from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import threading
from typing import Callable, Mapping, Protocol, Sequence

from .projection import ProjectionPackageRegistry
from .video_show import VideoScene
from .vlc_player import build_vlc_command


class ManagedProcess(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...


ProcessFactory = Callable[[Sequence[str], Mapping[str, str]], ManagedProcess]


def _start_process(
    command: Sequence[str], environment: Mapping[str, str]
) -> ManagedProcess:
    return subprocess.Popen(
        list(command),
        env=dict(environment),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        # Preserve VLC decoder/display diagnostics in the managed service journal.
        stderr=None,
        start_new_session=True,
    )


class VlcVideoTrackOutput:
    """Launch one verified rendition at a cue offset and stop it on black."""

    def __init__(
        self,
        registry: ProjectionPackageRegistry,
        *,
        surface_id: str,
        vlc_executable: str | Path,
        screen_number: int,
        environment: Mapping[str, str] | None = None,
        process_factory: ProcessFactory = _start_process,
        stop_timeout_seconds: float = 3.0,
    ) -> None:
        if not isinstance(surface_id, str) or not surface_id.strip():
            raise ValueError("Video output surface ID must be nonempty text")
        if (
            isinstance(stop_timeout_seconds, bool)
            or not isinstance(stop_timeout_seconds, (int, float))
            or not math.isfinite(stop_timeout_seconds)
            or not 0.1 <= stop_timeout_seconds <= 10.0
        ):
            raise ValueError("Video output stop timeout must be between 0.1 and 10 seconds")
        self.registry = registry
        self.surface_id = surface_id.strip()
        self.vlc_executable = str(vlc_executable)
        self.screen_number = screen_number
        self.environment = dict(os.environ if environment is None else environment)
        self.process_factory = process_factory
        self.stop_timeout_seconds = float(stop_timeout_seconds)
        self._process: ManagedProcess | None = None
        self._lock = threading.RLock()
        self.package_id: str | None = None
        self.position_seconds = 0.0
        self.last_error: str | None = None

    def _stop_locked(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=self.stop_timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=self.stop_timeout_seconds)

    def activate(
        self,
        scene: VideoScene,
        position_seconds: float,
        scheduled_at: float,
    ) -> None:
        del scheduled_at
        if scene.surface_id != self.surface_id:
            raise ValueError(
                f"Video Scene targets {scene.surface_id}, not {self.surface_id}"
            )
        if scene.loop:
            raise ValueError("looping Video Scenes are not commissioned for VLC output")
        package = self.registry.resolve(scene.package_id)
        command = build_vlc_command(
            package,
            vlc_executable=self.vlc_executable,
            screen_number=self.screen_number,
            start_seconds=position_seconds,
        )
        with self._lock:
            self._stop_locked()
            try:
                process = self.process_factory(command, self.environment)
                returncode = process.poll()
                if returncode is not None:
                    raise RuntimeError(f"VLC exited during launch with status {returncode}")
            except Exception as exc:
                self.package_id = None
                self.position_seconds = 0.0
                self.last_error = str(exc) or type(exc).__name__
                raise
            self._process = process
            self.package_id = package.package_id
            self.position_seconds = float(position_seconds)
            self.last_error = None

    def black(self) -> None:
        with self._lock:
            self._stop_locked()
            self.package_id = None
            self.position_seconds = 0.0

    def check(self) -> None:
        """Raise when an active VLC process exits before the Video lane stops."""

        with self._lock:
            process = self._process
            if process is None:
                return
            returncode = process.poll()
            if returncode is None:
                return
            self._process = None
            self.package_id = None
            self.position_seconds = 0.0
            self.last_error = f"VLC exited unexpectedly with status {returncode}"
            raise RuntimeError(self.last_error)

    def close(self) -> None:
        self.black()

    def status(self) -> dict:
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            return {
                "surface_id": self.surface_id,
                "running": running,
                "package_id": self.package_id if running else None,
                "position_seconds": self.position_seconds if running else 0.0,
                "last_error": self.last_error,
                "blackout_strategy": "stop-player",
            }
