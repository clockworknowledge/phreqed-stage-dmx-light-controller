"""Fail-black projection package validation and player command boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Protocol

from .video_edl import parse_video_edl


MAX_PROJECTION_MANIFEST_BYTES = 5_000_000
_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,95}(?:--[a-z0-9][a-z0-9-]{0,95})?")


class ProjectionState(str, Enum):
    DISABLED = "disabled"
    BLACK = "black"
    READY = "ready"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class ProjectionBackend(Protocol):
    """Minimal adapter implemented later by the selected Pi player."""

    def load(self, path: Path) -> None: ...
    def play(self, position_seconds: float) -> None: ...
    def pause(self) -> None: ...
    def seek(self, position_seconds: float) -> None: ...
    def stop(self) -> None: ...
    def set_black(self, enabled: bool) -> None: ...
    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StageVideoPackage:
    package_id: str
    manifest_path: Path
    video_path: Path
    duration_seconds: float
    width: int
    height: int
    frame_rate: float
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_stage_video_package(path: str | Path) -> StageVideoPackage:
    """Preflight one local manifest and its exact hash-verified rendition."""

    manifest_path = Path(path).resolve()
    try:
        if manifest_path.stat().st_size > MAX_PROJECTION_MANIFEST_BYTES:
            raise ValueError("projection manifest exceeds 5 MB")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load projection manifest: {exc}") from exc
    required = {
        "version",
        "package_id",
        "edl_sha256",
        "edl",
        "duration_seconds",
        "sources",
        "rendition",
    }
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("projection manifest fields are invalid")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("unsupported projection manifest version")
    try:
        edl = parse_video_edl(data["edl"])
    except ValueError as exc:
        raise ValueError(f"projection EDL is invalid: {exc}") from exc
    expected_edl_hash = hashlib.sha256(edl.canonical_bytes()).hexdigest()
    if data["edl_sha256"] != expected_edl_hash:
        raise ValueError("projection EDL hash does not match its manifest")
    duration = data["duration_seconds"]
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or duration <= 0
        or not math.isclose(duration, edl.duration_seconds, abs_tol=1e-6)
    ):
        raise ValueError("projection duration is invalid")
    sources = data["sources"]
    if not isinstance(sources, list):
        raise ValueError("projection sources are invalid")
    referenced_ids = {clip.asset_id for clip in edl.clips}
    source_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {
            "asset_id", "size_bytes", "sha256"
        }:
            raise ValueError("projection source record is invalid")
        asset_id = source["asset_id"]
        size = source["size_bytes"]
        source_hash = source["sha256"]
        if not isinstance(asset_id, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]{0,95}", asset_id
        ):
            raise ValueError("projection source asset ID is invalid")
        if asset_id in source_ids:
            raise ValueError("projection source asset IDs must be unique")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError("projection source size is invalid")
        if (
            not isinstance(source_hash, str)
            or len(source_hash) != 64
            or any(character not in "0123456789abcdef" for character in source_hash)
        ):
            raise ValueError("projection source hash is invalid")
        source_ids.add(asset_id)
    if source_ids != referenced_ids:
        raise ValueError("projection sources do not match the EDL")
    rendition = data["rendition"]
    rendition_fields = {
        "file",
        "size_bytes",
        "sha256",
        "width",
        "height",
        "frame_rate",
        "video_codec",
        "pixel_format",
        "audio",
    }
    if not isinstance(rendition, dict) or set(rendition) != rendition_fields:
        raise ValueError("projection rendition fields are invalid")
    filename = rendition["file"]
    if (
        not isinstance(filename, str)
        or not filename
        or Path(filename).name != filename
        or Path(filename).suffix.casefold() != ".mp4"
    ):
        raise ValueError("projection rendition must be a local MP4 filename")
    video_path = (manifest_path.parent / filename).resolve()
    if video_path.parent != manifest_path.parent:
        raise ValueError("projection rendition escapes its package directory")
    if not video_path.is_file():
        raise ValueError("projection rendition is missing")
    size = rendition["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ValueError("projection rendition size is invalid")
    if video_path.stat().st_size != size:
        raise ValueError("projection rendition size does not match its manifest")
    expected_hash = rendition["sha256"]
    if (
        not isinstance(expected_hash, str)
        or len(expected_hash) != 64
        or any(character not in "0123456789abcdef" for character in expected_hash)
    ):
        raise ValueError("projection rendition hash is invalid")
    if _sha256(video_path) != expected_hash:
        raise ValueError("projection rendition hash does not match its manifest")
    frame_rate = rendition["frame_rate"]
    if (
        isinstance(frame_rate, bool)
        or not isinstance(frame_rate, (int, float))
        or not math.isfinite(frame_rate)
        or not 1 <= frame_rate <= 60
    ):
        raise ValueError("projection frame rate is invalid")
    for key in ("width", "height"):
        value = rendition[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 16
            or value > 4096
            or value % 2
        ):
            raise ValueError(f"projection {key} is invalid")
    if rendition["video_codec"] != "h264-high-4.1":
        raise ValueError("projection video codec is unsupported")
    if rendition["pixel_format"] != "yuv420p" or rendition["audio"] is not False:
        raise ValueError("projection rendition format is unsupported")
    package_id = data["package_id"]
    expected_package_id = f"{edl.edl_id}--{edl.projection.profile_id}"
    if (
        not isinstance(package_id, str)
        or not _ID_PATTERN.fullmatch(package_id)
        or package_id != expected_package_id
    ):
        raise ValueError("projection package ID is invalid")
    expected_dimensions = edl.projection.output_dimensions
    if (rendition["width"], rendition["height"]) != expected_dimensions:
        raise ValueError("projection rendition dimensions do not match the EDL")
    if not math.isclose(
        float(frame_rate), edl.projection.frame_rate, abs_tol=1e-6
    ):
        raise ValueError("projection frame rate does not match the EDL")
    return StageVideoPackage(
        package_id=package_id,
        manifest_path=manifest_path,
        video_path=video_path,
        duration_seconds=float(duration),
        width=rendition["width"],
        height=rendition["height"],
        frame_rate=float(frame_rate),
        sha256=expected_hash,
    )


class ProjectionController:
    """Transport-independent controls; no backend means safely disabled."""

    def __init__(self, backend: ProjectionBackend | None = None) -> None:
        self.backend = backend
        self.package: StageVideoPackage | None = None
        self.state = (
            ProjectionState.BLACK if backend is not None
            else ProjectionState.DISABLED
        )
        self.output_black = True
        self.position_seconds = 0.0

    def _require_backend(self) -> ProjectionBackend:
        if self.backend is None:
            raise RuntimeError("projection output is disabled")
        return self.backend

    def load(self, manifest_path: str | Path) -> StageVideoPackage:
        backend = self._require_backend()
        backend.set_black(True)
        self.output_black = True
        self.state = ProjectionState.BLACK
        try:
            package = load_stage_video_package(manifest_path)
            backend.load(package.video_path)
        except Exception:
            self.state = ProjectionState.ERROR
            raise
        self.package = package
        self.position_seconds = 0.0
        self.output_black = True
        self.state = ProjectionState.READY
        return package

    def play(self, position_seconds: float = 0.0) -> None:
        backend = self._require_backend()
        if self.package is None:
            raise RuntimeError("load a projection package before playback")
        if (
            isinstance(position_seconds, bool)
            or not isinstance(position_seconds, (int, float))
            or not math.isfinite(position_seconds)
            or not 0 <= position_seconds < self.package.duration_seconds
        ):
            raise ValueError("projection position is outside the package")
        backend.play(float(position_seconds))
        backend.set_black(False)
        self.position_seconds = float(position_seconds)
        self.output_black = False
        self.state = ProjectionState.PLAYING

    def pause(self) -> None:
        if self.state is not ProjectionState.PLAYING:
            raise RuntimeError("projection is not playing")
        self._require_backend().pause()
        self.state = ProjectionState.PAUSED

    def seek(self, position_seconds: float) -> None:
        backend = self._require_backend()
        if self.package is None:
            raise RuntimeError("load a projection package before seeking")
        if (
            isinstance(position_seconds, bool)
            or not isinstance(position_seconds, (int, float))
            or not math.isfinite(position_seconds)
            or not 0 <= position_seconds < self.package.duration_seconds
        ):
            raise ValueError("projection position is outside the package")
        backend.seek(float(position_seconds))
        self.position_seconds = float(position_seconds)

    def stop(self) -> None:
        backend = self._require_backend()
        backend.set_black(True)
        backend.stop()
        self.position_seconds = 0.0
        self.output_black = True
        self.state = ProjectionState.STOPPED

    def black(self) -> None:
        backend = self._require_backend()
        backend.set_black(True)
        self.output_black = True
        self.state = ProjectionState.BLACK

    def close(self) -> None:
        if self.backend is None:
            return
        try:
            self.backend.set_black(True)
            self.backend.stop()
        finally:
            self.backend.close()
            self.output_black = True
            self.state = ProjectionState.BLACK

    def status(self) -> dict:
        return {
            "enabled": self.backend is not None,
            "state": self.state.value,
            "output_black": self.output_black,
            "package_id": self.package.package_id if self.package else None,
            "position_seconds": self.position_seconds,
        }
