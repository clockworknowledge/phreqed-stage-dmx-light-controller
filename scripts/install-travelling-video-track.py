#!/usr/bin/env python3
"""Publish the Travelling Video lane without modifying the existing song library."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phreqed_dmx.presets import PRESETS
from phreqed_dmx.projection import ProjectionPackageRegistry
from phreqed_dmx.songs import SongLibrary
from phreqed_dmx.video_show import (
    VideoShowLibrary,
    bind_single_song_video_document,
    resolve_song_id_by_title,
)


DEFAULT_DATA_DIRECTORY = Path.home() / ".local" / "share" / "phreqed-dmx"
DEFAULT_TITLE = "Travelling on a Floating Rock"
DEFAULT_TEMPLATE = (
    Path(__file__).parents[1]
    / "examples"
    / "video"
    / "travelling-on-a-floating-rock.video-show.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--songs", type=Path, default=DEFAULT_DATA_DIRECTORY / "songs.json")
    parser.add_argument(
        "--video-show",
        type=Path,
        default=DEFAULT_DATA_DIRECTORY / "video-show.json",
    )
    parser.add_argument(
        "--packages",
        type=Path,
        default=DEFAULT_DATA_DIRECTORY / "video-packages",
        help="directory containing rendered MP4 and manifest pairs",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--song-title", default=DEFAULT_TITLE)
    args = parser.parse_args()

    songs_path = args.songs.expanduser().resolve()
    if not songs_path.is_file():
        raise SystemExit(f"song library is unavailable: {songs_path}")
    songs = SongLibrary(songs_path, set(PRESETS))
    song_id = resolve_song_id_by_title(songs, args.song_title)
    setlists = [
        setlist.name
        for setlist in songs.setlists.values()
        if song_id in setlist.song_ids
    ]
    if not setlists:
        raise SystemExit(
            f"{args.song_title!r} exists but is not present in any saved setlist"
        )

    try:
        template = json.loads(args.template.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot load Video Show template: {exc}") from exc
    document = bind_single_song_video_document(template, songs, args.song_title)

    registry = ProjectionPackageRegistry(args.packages)
    registry.refresh()
    for scene in document.get("scenes", []):
        if not isinstance(scene, dict) or "package_id" not in scene:
            raise SystemExit("Video Show template contains an invalid scene")
        registry.resolve(scene["package_id"])

    video_show_path = args.video_show.expanduser().resolve()
    library = VideoShowLibrary(video_show_path, songs)
    if video_show_path.exists():
        if library.document() == document:
            print(f"Video track already published for {args.song_title} ({song_id})")
            return 0
        raise SystemExit(
            f"refusing to replace existing Video Show library: {video_show_path}"
        )
    library.save(document)
    print(f"Published Video track for {args.song_title} ({song_id})")
    print(f"Setlists: {', '.join(setlists)}")
    print(f"Video Show sidecar: {video_show_path}")
    print("Existing song and setlist metadata was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
