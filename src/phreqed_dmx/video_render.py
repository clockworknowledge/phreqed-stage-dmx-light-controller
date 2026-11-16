"""Compile validated video EDLs into conservative Stage renditions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Callable
import uuid

from .video_edl import VideoClip, VideoEdl


RENDER_MANIFEST_VERSION = 1


@dataclass(frozen=True, slots=True)
class VideoRenderResult:
    video_path: Path
    manifest_path: Path
    manifest: dict


def _decimal(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _clip_filter(clip: VideoClip, index: int, edl: VideoEdl) -> str:
    width = edl.projection.canvas_width
    height = edl.projection.canvas_height
    focal_x = _decimal(clip.focal_x)
    focal_y = _decimal(clip.focal_y)
    if clip.fit_mode == "cover":
        geometry = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:"
            f"(in_w-out_w)*{focal_x}:(in_h-out_h)*{focal_y}"
        )
    else:
        geometry = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:"
            f"(out_w-in_w)*{focal_x}:(out_h-in_h)*{focal_y}:black"
        )
    filters = [
        f"[{index}:v]fps={_decimal(edl.projection.frame_rate)}",
        geometry,
        "setsar=1",
        f"trim=duration={_decimal(clip.duration_seconds)}",
        "setpts=PTS-STARTPTS",
    ]
    if clip.fade_in_seconds:
        filters.append(
            f"fade=t=in:st=0:d={_decimal(clip.fade_in_seconds)}"
        )
    if clip.fade_out_seconds:
        start = clip.duration_seconds - clip.fade_out_seconds
        filters.append(
            "fade=t=out:"
            f"st={_decimal(start)}:d={_decimal(clip.fade_out_seconds)}"
        )
    return ",".join(filters) + f"[clip{index}]"


def build_ffmpeg_command(
    edl: VideoEdl,
    assets: dict[str, Path],
    output_path: str | Path,
    *,
    ffmpeg_executable: str | Path = "ffmpeg",
) -> list[str]:
    """Return a shell-free FFmpeg argument vector for a complete EDL."""

    referenced = {clip.asset_id for clip in edl.clips}
    missing = referenced.difference(assets)
    if missing:
        raise ValueError(f"asset map is missing IDs: {sorted(missing)}")
    resolved: dict[str, Path] = {}
    for asset_id in referenced:
        path = Path(assets[asset_id]).expanduser()
        if not path.is_file():
            raise ValueError(f"video asset does not exist: {asset_id}")
        resolved[asset_id] = path.resolve()

    command = [str(ffmpeg_executable), "-nostdin", "-hide_banner", "-loglevel", "warning"]
    for clip in edl.clips:
        command.extend([
            "-ss",
            _decimal(clip.source_in_seconds),
            "-t",
            _decimal(clip.duration_seconds),
            "-i",
            str(resolved[clip.asset_id]),
        ])

    filter_parts = [
        _clip_filter(clip, index, edl)
        for index, clip in enumerate(edl.clips)
    ]
    clip_inputs = "".join(f"[clip{index}]" for index in range(len(edl.clips)))
    filter_parts.append(
        f"{clip_inputs}concat=n={len(edl.clips)}:v=1:a=0[sequence]"
    )
    output_filters = []
    if edl.projection.horizontal_flip:
        output_filters.append("hflip")
    rotation = edl.projection.output_rotation
    if rotation == "clockwise":
        output_filters.append("transpose=clock")
    elif rotation == "counterclockwise":
        output_filters.append("transpose=cclock")
    output_filters.append("format=yuv420p")
    filter_parts.append(
        "[sequence]" + ",".join(output_filters) + "[video]"
    )

    frame_rate = _decimal(edl.projection.frame_rate)
    command.extend([
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[video]",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-profile:v",
        "high",
        "-level:v",
        "4.1",
        "-pix_fmt",
        "yuv420p",
        "-r",
        frame_rate,
        "-g",
        str(max(1, round(edl.projection.frame_rate * 2))),
        "-keyint_min",
        str(max(1, round(edl.projection.frame_rate * 2))),
        "-sc_threshold",
        "0",
        "-movflags",
        "+faststart",
        str(Path(output_path)),
    ])
    return command


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: dict) -> None:
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def render_video_edl(
    edl: VideoEdl,
    assets: dict[str, Path],
    output_directory: str | Path,
    *,
    ffmpeg_executable: str | Path = "ffmpeg",
    overwrite: bool = False,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> VideoRenderResult:
    """Render one immutable Stage rendition and checksummed package manifest."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    base_name = f"{edl.edl_id}--{edl.projection.profile_id}"
    video_path = output / f"{base_name}.mp4"
    manifest_path = output / f"{base_name}.manifest.json"
    if not overwrite and (video_path.exists() or manifest_path.exists()):
        raise FileExistsError(
            "Stage rendition already exists; use explicit overwrite to replace it"
        )

    temporary_video = output / f".{base_name}-{uuid.uuid4().hex}.partial.mp4"
    command = build_ffmpeg_command(
        edl,
        assets,
        temporary_video,
        ffmpeg_executable=ffmpeg_executable,
    )
    try:
        completed = runner(
            command,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(
                f"FFmpeg render failed with exit {completed.returncode}: {detail}"
            )
        if not temporary_video.is_file() or temporary_video.stat().st_size == 0:
            raise RuntimeError("FFmpeg reported success without a rendered video")

        referenced_ids = tuple(dict.fromkeys(clip.asset_id for clip in edl.clips))
        source_records = []
        for asset_id in referenced_ids:
            source = Path(assets[asset_id]).expanduser().resolve()
            source_records.append({
                "asset_id": asset_id,
                "size_bytes": source.stat().st_size,
                "sha256": _sha256(source),
            })
        width, height = edl.projection.output_dimensions
        manifest = {
            "version": RENDER_MANIFEST_VERSION,
            "package_id": base_name,
            "edl_sha256": hashlib.sha256(edl.canonical_bytes()).hexdigest(),
            "edl": edl.as_dict(),
            "duration_seconds": edl.duration_seconds,
            "sources": source_records,
            "rendition": {
                "file": video_path.name,
                "size_bytes": temporary_video.stat().st_size,
                "sha256": _sha256(temporary_video),
                "width": width,
                "height": height,
                "frame_rate": edl.projection.frame_rate,
                "video_codec": "h264-high-4.1",
                "pixel_format": "yuv420p",
                "audio": False,
            },
        }
        os.replace(temporary_video, video_path)
        _write_json_atomic(manifest_path, manifest)
        return VideoRenderResult(video_path, manifest_path, manifest)
    except Exception:
        try:
            temporary_video.unlink(missing_ok=True)
        except OSError:
            pass
        raise
