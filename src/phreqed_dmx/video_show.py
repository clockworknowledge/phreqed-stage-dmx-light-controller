"""Versioned Video Scenes and a lighting-independent parallel song lane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Protocol

from .song_timeline import SongTimelineRunner, TimelineState
from .songs import MAX_SONG_SECONDS, SongLibrary


MAX_VIDEO_SHOW_BYTES = 2_000_000
_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
_PACKAGE_ID_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]{0,95}(?:--[a-z0-9][a-z0-9-]{0,95})?"
)


def _identifier(value: object, prefix: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _ID_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}-")
    ):
        raise ValueError(
            f"{label} must start with {prefix}- and use lowercase letters, "
            "digits, or hyphens"
        )
    return value


def _number(value: object, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or not low <= parsed <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return parsed


def _fields(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} requires fields: {', '.join(sorted(expected))}")
    return value


@dataclass(frozen=True, slots=True)
class VideoScene:
    scene_id: str
    name: str
    package_id: str
    surface_id: str = "portrait-character"
    loop: bool = False

    def __post_init__(self) -> None:
        _identifier(self.scene_id, "vscene", "Video Scene ID")
        if not isinstance(self.name, str) or not 1 <= len(self.name.strip()) <= 200:
            raise ValueError("Video Scene name must contain 1-200 characters")
        if (
            not isinstance(self.package_id, str)
            or not _PACKAGE_ID_PATTERN.fullmatch(self.package_id)
        ):
            raise ValueError("Video Scene package ID is invalid")
        if not isinstance(self.surface_id, str) or not _ID_PATTERN.fullmatch(
            self.surface_id
        ):
            raise ValueError("Video Scene surface ID is invalid")
        if not isinstance(self.loop, bool):
            raise ValueError("Video Scene loop flag must be boolean")

    def as_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "name": self.name.strip(),
            "package_id": self.package_id,
            "surface_id": self.surface_id,
            "loop": self.loop,
        }


@dataclass(frozen=True, slots=True)
class VideoCue:
    at_seconds: float
    scene_id: str | None

    def __post_init__(self) -> None:
        _number(self.at_seconds, "Video cue time", 0.0, MAX_SONG_SECONDS)
        if self.scene_id is not None:
            _identifier(self.scene_id, "vscene", "Video cue scene ID")

    @property
    def is_black(self) -> bool:
        return self.scene_id is None

    def as_dict(self) -> dict:
        return {"at_seconds": self.at_seconds, "scene_id": self.scene_id}


@dataclass(frozen=True, slots=True)
class SongVideoTrack:
    track_id: str
    song_id: str
    revision: int
    cues: tuple[VideoCue, ...]
    published: bool = False

    def __post_init__(self) -> None:
        _identifier(self.track_id, "vtrack", "Video track ID")
        _identifier(self.song_id, "song", "Video track song ID")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise ValueError("Video track revision must be a positive integer")
        if not isinstance(self.published, bool):
            raise ValueError("Video track published flag must be boolean")
        if not isinstance(self.cues, tuple) or not 1 <= len(self.cues) <= 1000:
            raise ValueError("Video track must contain 1-1000 cues")
        if any(not isinstance(cue, VideoCue) for cue in self.cues):
            raise ValueError("Video track contains an invalid cue")
        times = [cue.at_seconds for cue in self.cues]
        if any(right <= left for left, right in zip(times, times[1:])):
            raise ValueError("Video cue times must be strictly increasing")

    def as_dict(self) -> dict:
        return {
            "track_id": self.track_id,
            "song_id": self.song_id,
            "revision": self.revision,
            "published": self.published,
            "cues": [cue.as_dict() for cue in self.cues],
        }


def _parse_scene(value: object) -> VideoScene:
    data = _fields(
        value,
        {"scene_id", "name", "package_id", "surface_id", "loop"},
        "Video Scene",
    )
    return VideoScene(**data)


def _parse_cue(value: object) -> VideoCue:
    data = _fields(value, {"at_seconds", "scene_id"}, "Video cue")
    return VideoCue(data["at_seconds"], data["scene_id"])


def _parse_track(value: object) -> SongVideoTrack:
    data = _fields(
        value,
        {"track_id", "song_id", "revision", "published", "cues"},
        "Video track",
    )
    if not isinstance(data["cues"], list):
        raise ValueError("Video track cues must be a list")
    return SongVideoTrack(
        data["track_id"],
        data["song_id"],
        data["revision"],
        tuple(_parse_cue(cue) for cue in data["cues"]),
        data["published"],
    )


class VideoShowLibrary:
    """Atomic sidecar metadata; existing songs.json remains unchanged."""

    def __init__(self, path: Path, songs: SongLibrary) -> None:
        self.path = path
        self.songs = songs
        self.scenes: dict[str, VideoScene] = {}
        self.tracks: dict[str, SongVideoTrack] = {}
        self.active_tracks: dict[str, str] = {}
        if path.exists():
            try:
                if path.stat().st_size > MAX_VIDEO_SHOW_BYTES:
                    raise ValueError("Video Show library exceeds 2 MB")
                value = json.loads(path.read_text(encoding="utf-8"))
                self.scenes, self.tracks, self.active_tracks = self.validate(value)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"cannot load Video Show library {path}: {exc}") from exc

    def document(self) -> dict:
        return {
            "version": 1,
            "scenes": [scene.as_dict() for scene in self.scenes.values()],
            "tracks": [track.as_dict() for track in self.tracks.values()],
            "active_tracks": [
                {"song_id": song_id, "track_id": track_id}
                for song_id, track_id in self.active_tracks.items()
            ],
        }

    def validate(
        self, value: object
    ) -> tuple[
        dict[str, VideoScene], dict[str, SongVideoTrack], dict[str, str]
    ]:
        data = _fields(
            value,
            {"version", "scenes", "tracks", "active_tracks"},
            "Video Show library",
        )
        if type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("unsupported Video Show library version; expected 1")
        for field, maximum in (("scenes", 2000), ("tracks", 5000), ("active_tracks", 1000)):
            if not isinstance(data[field], list) or len(data[field]) > maximum:
                raise ValueError(f"Video Show library {field} are invalid")
        parsed_scenes = [_parse_scene(item) for item in data["scenes"]]
        parsed_tracks = [_parse_track(item) for item in data["tracks"]]
        scenes = {scene.scene_id: scene for scene in parsed_scenes}
        tracks = {track.track_id: track for track in parsed_tracks}
        if len(scenes) != len(parsed_scenes):
            raise ValueError("duplicate Video Scene IDs")
        if len(tracks) != len(parsed_tracks):
            raise ValueError("duplicate Video track IDs")
        for track in tracks.values():
            song = self.songs.songs.get(track.song_id)
            if song is None:
                raise ValueError("Video track references an unknown song")
            if track.cues[-1].at_seconds >= song.duration_seconds:
                raise ValueError("Video cue must occur before the song duration")
            if any(
                cue.scene_id is not None and cue.scene_id not in scenes
                for cue in track.cues
            ):
                raise ValueError("Video cue references an unknown Video Scene")
        active_tracks: dict[str, str] = {}
        for item in data["active_tracks"]:
            assignment = _fields(
                item, {"song_id", "track_id"}, "active Video track"
            )
            song_id = _identifier(
                assignment["song_id"], "song", "active Video track song ID"
            )
            track_id = _identifier(
                assignment["track_id"], "vtrack", "active Video track ID"
            )
            if song_id in active_tracks:
                raise ValueError("song has multiple active Video tracks")
            track = tracks.get(track_id)
            if track is None or track.song_id != song_id or not track.published:
                raise ValueError("active Video track assignment is invalid")
            active_tracks[song_id] = track_id
        return scenes, tracks, active_tracks

    def save(self, value: object) -> None:
        scenes, tracks, active_tracks = self.validate(value)
        for track_id, existing in self.tracks.items():
            if existing.published:
                replacement = tracks.get(track_id)
                if replacement is None or replacement.as_dict() != existing.as_dict():
                    raise ValueError("published Video tracks are immutable")
        locked_scene_ids = {
            cue.scene_id
            for track in self.tracks.values()
            if track.published
            for cue in track.cues
            if cue.scene_id is not None
        }
        for scene_id in locked_scene_ids:
            existing = self.scenes[scene_id]
            replacement = scenes.get(scene_id)
            if replacement is None or replacement.as_dict() != existing.as_dict():
                raise ValueError("published Video Scene references are immutable")
        encoded = json.dumps(value, indent=2, allow_nan=False) + "\n"
        if len(encoded.encode("utf-8")) > MAX_VIDEO_SHOW_BYTES:
            raise ValueError("Video Show library exceeds 2 MB")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=".video-show-",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.scenes = scenes
        self.tracks = tracks
        self.active_tracks = active_tracks

    def active_track(self, song_id: str) -> SongVideoTrack | None:
        track_id = self.active_tracks.get(song_id)
        return None if track_id is None else self.tracks.get(track_id)


class VideoTrackOutput(Protocol):
    def activate(
        self,
        scene: VideoScene,
        position_seconds: float,
        scheduled_at: float,
    ) -> None: ...

    def black(self) -> None: ...


class VideoRunnerState(str, Enum):
    BLACK = "black"
    RUNNING = "running"
    ERROR = "error"


class SongVideoRunner:
    """Run one optional Video lane without allowing failure into Lighting."""

    def __init__(self, library: VideoShowLibrary, output: VideoTrackOutput) -> None:
        self.library = library
        self.output = output
        self.state = VideoRunnerState.BLACK
        self.song_id: str | None = None
        self.started_at: float | None = None
        self.next_cue_index = 0
        self.last_error: str | None = None

    @property
    def track(self) -> SongVideoTrack | None:
        return None if self.song_id is None else self.library.active_track(self.song_id)

    def _fail(self, exc: Exception) -> None:
        self.last_error = str(exc) or type(exc).__name__
        try:
            self.output.black()
        except Exception:
            pass
        self.state = VideoRunnerState.ERROR

    def start(self, song_id: str, started_at: float) -> None:
        _identifier(song_id, "song", "Video runner song ID")
        _number(started_at, "Video runner start time", 0.0, float("inf"))
        self.song_id = song_id
        self.started_at = float(started_at)
        self.next_cue_index = 0
        self.last_error = None
        self.state = VideoRunnerState.RUNNING
        self.sync(0.0)

    def sync(self, position_seconds: float) -> None:
        if self.state is not VideoRunnerState.RUNNING:
            return
        position = _number(
            position_seconds, "Video runner position", 0.0, MAX_SONG_SECONDS
        )
        track = self.track
        if track is None or self.started_at is None:
            try:
                self.output.black()
                self.state = VideoRunnerState.BLACK
            except Exception as exc:
                self._fail(exc)
            return
        last_due_index: int | None = None
        while (
            self.next_cue_index < len(track.cues)
            and track.cues[self.next_cue_index].at_seconds <= position
        ):
            last_due_index = self.next_cue_index
            self.next_cue_index += 1
        if last_due_index is None:
            return
        cue = track.cues[last_due_index]
        try:
            if cue.is_black:
                self.output.black()
            else:
                scene = self.library.scenes[cue.scene_id]
                self.output.activate(
                    scene,
                    position - cue.at_seconds,
                    self.started_at + cue.at_seconds,
                )
        except Exception as exc:
            self._fail(exc)

    def stop(self) -> None:
        self.song_id = None
        self.started_at = None
        self.next_cue_index = 0
        try:
            self.output.black()
            self.state = VideoRunnerState.BLACK
        except Exception as exc:
            self._fail(exc)

    def status(self) -> dict:
        track = self.track
        return {
            "state": self.state.value,
            "song_id": self.song_id,
            "track_id": track.track_id if track else None,
            "next_cue_index": self.next_cue_index,
            "last_error": self.last_error,
        }


class ParallelSongTransport:
    """Coordinate Lighting and Video from one existing song timeline clock."""

    def __init__(self, lighting: SongTimelineRunner, video: SongVideoRunner) -> None:
        self.lighting = lighting
        self.video = video

    def load(self, setlist_id: str) -> None:
        self.video.stop()
        self.lighting.load(setlist_id)

    def select(self, index: int) -> None:
        self.video.stop()
        self.lighting.select(index)

    def move(self, direction: int) -> None:
        self.video.stop()
        self.lighting.move(direction)

    def start(self) -> None:
        self.video.stop()
        self.lighting.start()
        song = self.lighting.song
        started_at = self.lighting.started_at
        if song is not None and started_at is not None:
            self.video.start(song.song_id, started_at)

    def stop(self) -> None:
        self.lighting.stop()
        self.video.stop()

    def update(self) -> None:
        self.lighting.update()
        if self.lighting.state is TimelineState.RUNNING:
            song = self.lighting.song
            if song is None or self.lighting.started_at is None:
                self.video.stop()
                return
            if self.video.song_id != song.song_id:
                self.video.start(song.song_id, self.lighting.started_at)
            self.video.sync(self.lighting.position_seconds)
        elif self.video.state is not VideoRunnerState.BLACK:
            self.video.stop()
