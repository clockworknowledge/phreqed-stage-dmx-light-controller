#!/usr/bin/env python3
"""Generate deterministic simulator previews without opening output hardware."""

from __future__ import annotations

import argparse
from pathlib import Path

from phreqed_dmx.config import DEFAULT_CONFIG_PATH, load_config
from phreqed_dmx.gallery import FIXED_GALLERY_TIMES, generate_effect_gallery


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--output", type=Path, default=Path("output/effect-gallery")
    )
    parser.add_argument(
        "--times",
        type=float,
        nargs="+",
        default=FIXED_GALLERY_TIMES,
        help="fixed animation times in seconds",
    )
    parser.add_argument("--pixel-size", type=int, default=16)
    args = parser.parse_args()
    manifest = generate_effect_gallery(
        load_config(args.config),
        args.output,
        times=args.times,
        pixel_size=args.pixel_size,
    )
    effects = sum(item["kind"] == "effect" for item in manifest["items"])
    presets = sum(item["kind"] == "preset" for item in manifest["items"])
    print(
        f"Generated {effects} effects and {presets} presets at "
        f"{len(manifest['times_seconds'])} fixed times: "
        f"{args.output.resolve() / 'index.html'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
