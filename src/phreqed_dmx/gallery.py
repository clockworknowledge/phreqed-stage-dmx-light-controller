"""Deterministic, hardware-free effect and preset gallery generation."""

from __future__ import annotations

import hashlib
import html
import json
import math
from pathlib import Path
from typing import Iterable

from .config import ControllerConfig
from .effect_api import PerformanceContext
from .effect_library import EFFECT_REGISTRY
from .engine import SceneEngine
from .presets import PRESETS
from .simulator import export_scene_png


GALLERY_VERSION = 1
FIXED_GALLERY_TIMES = (0.0, 1.75, 4.0)


def generate_effect_gallery(
    config: ControllerConfig,
    output_directory: str | Path,
    *,
    effect_ids: Iterable[str] | None = None,
    preset_ids: Iterable[str] | None = None,
    times: Iterable[float] = FIXED_GALLERY_TIMES,
    pixel_size: int = 16,
    gap: int = 8,
) -> dict:
    """Generate PNG frames, a stable manifest, and a browsable HTML index."""

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    selected_effects = _selected_ids(
        effect_ids,
        tuple(metadata.effect_id for metadata in EFFECT_REGISTRY.metadata()),
        "effect",
    )
    selected_presets = _selected_ids(
        preset_ids, tuple(PRESETS), "preset"
    )
    fixed_times = tuple(_gallery_time(value) for value in times)
    if not fixed_times:
        raise ValueError("gallery requires at least one fixed time")
    if pixel_size <= 0 or gap < 0:
        raise ValueError("pixel_size must be positive and gap cannot be negative")

    engine = SceneEngine(config.fixtures)
    context = PerformanceContext()
    items: list[dict] = []
    metadata_by_id = {
        metadata.effect_id: metadata for metadata in EFFECT_REGISTRY.metadata()
    }

    for kind, identifiers in (
        ("effect", selected_effects),
        ("preset", selected_presets),
    ):
        for identifier in identifiers:
            if kind == "effect":
                metadata = metadata_by_id[identifier]
                for fixture in config.fixtures:
                    engine.select_effect(fixture.name, identifier)
                render = lambda value: engine.render(value, context)
                name = metadata.name
                description = metadata.description
                category = metadata.category
            else:
                preset = PRESETS[identifier]
                render = lambda value, preset_id=identifier: engine.render_preset(
                    preset_id, value, context
                )
                name = preset.name
                description = preset.description
                category = "preset"

            frames = []
            for index, fixed_time in enumerate(fixed_times):
                filename = f"{kind}-{identifier}-t{index + 1}.png"
                path = output / filename
                export_scene_png(
                    render(fixed_time), path, pixel_size=pixel_size, gap=gap
                )
                frames.append({
                    "time_seconds": fixed_time,
                    "file": filename,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
            items.append({
                "kind": kind,
                "id": identifier,
                "name": name,
                "category": category,
                "description": description,
                "frames": frames,
            })

    manifest = {
        "version": GALLERY_VERSION,
        "hardware_output": False,
        "fixtures": [
            {
                "name": fixture.name,
                "width": fixture.width,
                "height": fixture.height,
            }
            for fixture in config.fixtures
        ],
        "times_seconds": list(fixed_times),
        "pixel_size": pixel_size,
        "gap": gap,
        "items": items,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "index.html").write_text(
        _gallery_html(manifest), encoding="utf-8"
    )
    return manifest


def _selected_ids(
    requested: Iterable[str] | None,
    available: tuple[str, ...],
    label: str,
) -> tuple[str, ...]:
    selected = available if requested is None else tuple(requested)
    if len(selected) != len(set(selected)):
        raise ValueError(f"duplicate {label} id")
    unknown = set(selected).difference(available)
    if unknown:
        raise ValueError(f"unknown {label} ids: {sorted(unknown)}")
    return selected


def _gallery_time(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0.0
    ):
        raise ValueError("gallery times must be finite and nonnegative")
    return float(value)


def _gallery_html(manifest: dict) -> str:
    cards = []
    for item in manifest["items"]:
        images = "".join(
            "<figure>"
            f'<img src="{html.escape(frame["file"])}" '
            f'alt="{html.escape(item["name"])} at '
            f'{frame["time_seconds"]:.2f} seconds">'
            f'<figcaption>{frame["time_seconds"]:.2f} s</figcaption>'
            "</figure>"
            for frame in item["frames"]
        )
        cards.append(
            '<article class="look">'
            f'<p class="kind">{html.escape(item["kind"])} · '
            f'{html.escape(item["category"])}</p>'
            f'<h2>{html.escape(item["name"])}</h2>'
            f'<code>{html.escape(item["id"])}</code>'
            f'<p>{html.escape(item["description"])}</p>'
            f'<div class="frames">{images}</div>'
            "</article>"
        )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<title>Phreqed effect gallery</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0d120f;color:#edf4ec}
body{max-width:1500px;margin:auto;padding:28px}h1{color:#c4f487}.summary{color:#aeb9ae}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:16px}
.look{background:#161d18;border:1px solid #334037;border-radius:14px;padding:16px}
.look h2{margin:.2rem 0}.kind{color:#c4f487;text-transform:uppercase;letter-spacing:.1em;font-size:.72rem}
.look>p:not(.kind){min-height:2.5em;color:#b8c2b8}.frames{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
figure{margin:0;background:#080b09;border-radius:8px;padding:7px}img{display:block;width:100%;image-rendering:pixelated}
figcaption{text-align:center;color:#91a092;font-size:.75rem;margin-top:5px}code{color:#d9e4d7}
@media (max-width:600px){body{padding:20px}.grid{grid-template-columns:minmax(0,1fr)}
.look{min-width:0}.frames{grid-template-columns:repeat(3,minmax(0,1fr))}figure{min-width:0;padding:5px}}
</style></head><body>
<h1>Phreqed effect gallery</h1>
<p class="summary">Deterministic RGB simulator frames. No Art-Net, white-channel, or projector output.</p>
<main class="grid">""" + "".join(cards) + """</main></body></html>
"""
