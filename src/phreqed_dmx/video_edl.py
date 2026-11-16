"""Validated, transport-independent edit decisions for projected video."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re


EDL_VERSION = 1
MAX_EDL_BYTES = 5_000_000
MAX_VIDEO_SECONDS = 4 * 60 * 60
FIT_MODES = ("cover", "contain")
OUTPUT_ROTATIONS = ("none", "clockwise", "counterclockwise")
_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")


def _fields(value: object, required: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(
            f'{label} requires fields: {", ".join(sorted(required))}'
        )
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ValueError(
            f"{label} must use lowercase letters, digits, or hyphens"
        )
    return value


def _text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must contain 1-{maximum} characters")
    return value.strip()


def _number(value: object, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or not low <= parsed <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return parsed


def _dimension(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 16 <= value <= 1920
        or value % 2
    ):
        raise ValueError(f"{label} must be an even integer between 16 and 1920")
    return value


@dataclass(frozen=True, slots=True)
class ProjectionProfile:
    """Logical composition canvas plus its derived Stage signal orientation."""

    profile_id: str
    canvas_width: int
    canvas_height: int
    output_rotation: str
    frame_rate: float

    def __post_init__(self) -> None:
        _identifier(self.profile_id, "projection profile ID")
        _dimension(self.canvas_width, "canvas width")
        _dimension(self.canvas_height, "canvas height")
        if self.output_rotation not in OUTPUT_ROTATIONS:
            raise ValueError(
                "output rotation must be none, clockwise, or counterclockwise"
            )
        _number(self.frame_rate, "frame rate", 1.0, 30.0)
        if self.canvas_width * self.canvas_height > 1920 * 1080:
            raise ValueError("projection canvas exceeds the initial 1080p target")

    @property
    def output_dimensions(self) -> tuple[int, int]:
        if self.output_rotation == "none":
            return self.canvas_width, self.canvas_height
        return self.canvas_height, self.canvas_width

    def as_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "output_rotation": self.output_rotation,
            "frame_rate": self.frame_rate,
        }


@dataclass(frozen=True, slots=True)
class VideoClip:
    """A non-destructive source range placed sequentially in an EDL."""

    clip_id: str
    asset_id: str
    source_in_seconds: float
    source_out_seconds: float
    fit_mode: str
    focal_x: float
    focal_y: float
    fade_in_seconds: float
    fade_out_seconds: float

    def __post_init__(self) -> None:
        _identifier(self.clip_id, "clip ID")
        _identifier(self.asset_id, "asset ID")
        start = _number(
            self.source_in_seconds,
            "source in",
            0.0,
            MAX_VIDEO_SECONDS,
        )
        end = _number(
            self.source_out_seconds,
            "source out",
            0.0,
            MAX_VIDEO_SECONDS,
        )
        if end <= start:
            raise ValueError("source out must be after source in")
        if self.fit_mode not in FIT_MODES:
            raise ValueError("fit mode must be cover or contain")
        _number(self.focal_x, "horizontal focal point", 0.0, 1.0)
        _number(self.focal_y, "vertical focal point", 0.0, 1.0)
        fade_in = _number(self.fade_in_seconds, "fade in", 0.0, 30.0)
        fade_out = _number(self.fade_out_seconds, "fade out", 0.0, 30.0)
        if fade_in + fade_out > self.duration_seconds:
            raise ValueError("clip fades cannot exceed the clip duration")

    @property
    def duration_seconds(self) -> float:
        return self.source_out_seconds - self.source_in_seconds

    def as_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "asset_id": self.asset_id,
            "source_in_seconds": self.source_in_seconds,
            "source_out_seconds": self.source_out_seconds,
            "fit_mode": self.fit_mode,
            "focal_x": self.focal_x,
            "focal_y": self.focal_y,
            "fade_in_seconds": self.fade_in_seconds,
            "fade_out_seconds": self.fade_out_seconds,
        }


@dataclass(frozen=True, slots=True)
class VideoEdl:
    """A versioned sequence that can be compiled into an immutable rendition."""

    edl_id: str
    title: str
    projection: ProjectionProfile
    clips: tuple[VideoClip, ...]

    def __post_init__(self) -> None:
        _identifier(self.edl_id, "EDL ID")
        _text(self.title, "EDL title", 200)
        if not isinstance(self.projection, ProjectionProfile):
            raise ValueError("EDL projection profile is invalid")
        if not isinstance(self.clips, tuple) or not 1 <= len(self.clips) <= 1000:
            raise ValueError("EDL must contain 1-1000 clips")
        if any(not isinstance(clip, VideoClip) for clip in self.clips):
            raise ValueError("EDL contains an invalid clip")
        clip_ids = [clip.clip_id for clip in self.clips]
        if len(set(clip_ids)) != len(clip_ids):
            raise ValueError("EDL clip IDs must be unique")
        if self.duration_seconds > MAX_VIDEO_SECONDS:
            raise ValueError("EDL duration exceeds four hours")

    @property
    def duration_seconds(self) -> float:
        return sum(clip.duration_seconds for clip in self.clips)

    def as_dict(self) -> dict:
        return {
            "version": EDL_VERSION,
            "edl_id": self.edl_id,
            "title": self.title,
            "projection": self.projection.as_dict(),
            "clips": [clip.as_dict() for clip in self.clips],
        }

    def canonical_bytes(self) -> bytes:
        return (
            json.dumps(
                self.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")


def parse_video_edl(value: object) -> VideoEdl:
    data = _fields(
        value,
        {"version", "edl_id", "title", "projection", "clips"},
        "video EDL",
    )
    if type(data["version"]) is not int or data["version"] != EDL_VERSION:
        raise ValueError("unsupported video EDL version; expected 1")
    projection_data = _fields(
        data["projection"],
        {
            "profile_id",
            "canvas_width",
            "canvas_height",
            "output_rotation",
            "frame_rate",
        },
        "projection profile",
    )
    clips_data = data["clips"]
    if not isinstance(clips_data, list):
        raise ValueError("video EDL clips must be a list")
    projection = ProjectionProfile(**projection_data)
    clips = tuple(
        VideoClip(**_fields(
            clip,
            {
                "clip_id",
                "asset_id",
                "source_in_seconds",
                "source_out_seconds",
                "fit_mode",
                "focal_x",
                "focal_y",
                "fade_in_seconds",
                "fade_out_seconds",
            },
            "video clip",
        ))
        for clip in clips_data
    )
    return VideoEdl(
        edl_id=data["edl_id"],
        title=data["title"],
        projection=projection,
        clips=clips,
    )


def load_video_edl(path: str | Path) -> VideoEdl:
    source = Path(path)
    if source.stat().st_size > MAX_EDL_BYTES:
        raise ValueError("video EDL exceeds 5 MB")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load video EDL {source}: {exc}") from exc
    return parse_video_edl(value)


def parse_asset_map(value: object) -> dict[str, Path]:
    data = _fields(value, {"version", "assets"}, "video asset map")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("unsupported video asset-map version; expected 1")
    if not isinstance(data["assets"], dict) or not data["assets"]:
        raise ValueError("video asset map must contain at least one asset")
    if len(data["assets"]) > 10_000:
        raise ValueError("video asset map contains too many assets")
    result: dict[str, Path] = {}
    for raw_id, raw_path in data["assets"].items():
        asset_id = _identifier(raw_id, "asset ID")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"asset path for {asset_id} must be non-empty text")
        if raw_path.casefold().startswith(("http://", "https://", "file://")):
            raise ValueError("video asset paths must be local filesystem paths")
        result[asset_id] = Path(raw_path)
    return result


def load_asset_map(path: str | Path) -> dict[str, Path]:
    source = Path(path)
    if source.stat().st_size > MAX_EDL_BYTES:
        raise ValueError("video asset map exceeds 5 MB")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load video asset map {source}: {exc}") from exc
    return parse_asset_map(value)
