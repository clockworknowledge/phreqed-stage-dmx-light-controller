#!/usr/bin/env python3
"""Render a validated video EDL into a checksummed Stage rendition."""

from __future__ import annotations

import argparse
from pathlib import Path

from phreqed_dmx.video_edl import load_asset_map, load_video_edl
from phreqed_dmx.video_render import render_video_edl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edl", type=Path, help="versioned video EDL JSON")
    parser.add_argument(
        "--assets", type=Path, required=True,
        help="local asset-ID to filesystem-path map",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/video-render")
    )
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = render_video_edl(
        load_video_edl(args.edl),
        load_asset_map(args.assets),
        args.output,
        ffmpeg_executable=args.ffmpeg,
        overwrite=args.overwrite,
    )
    print(f"Rendered Stage video: {result.video_path.resolve()}")
    print(f"Package manifest: {result.manifest_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
