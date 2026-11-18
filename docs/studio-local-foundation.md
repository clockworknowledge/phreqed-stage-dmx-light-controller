# Local Phreqed Studio foundation

Date: 2026-11-18

This is the first hardware-independent Studio vertical slice. It runs as a
separate loopback-only process and never imports Art-Net, QLC+, audio capture,
MIDI, Stage leases, or fixture-control code.

## Capabilities

- atomic content-addressed media import under `blobs/sha256/`;
- immutable source identity from SHA-256, size, type, original name, family,
  title, and import time;
- versioned Storylet records with duration, loop intent, and ordered semantic
  markers;
- append-only catalog events suitable for later graph indexing;
- deterministic graph projection containing Workspace, AssetRevision,
  StoryletRevision, and Marker nodes plus their relationships;
- responsive Assets, Storylets, and Graph browser workspaces;
- loopback-only HTTP, fixed command enums, request-size bounds, same-origin
  checks, and a per-process command token.

The JSON catalog and content-addressed blobs are authoritative. The graph
projection is rebuildable and contains no media bytes. Relate ingestion and
benchmarking remain `MEDIA-004`; the Studio already exposes the stable IDs and
relationships that sprint will consume.

## Install and start

```powershell
cd D:\DevelopmentClockwork\phreqed-stage-dmx-light-controller
py -3.12 -m pip install -e .

py -3.12 -m phreqed_dmx.studio_app `
  --workspace output/studio-workspace `
  serve
```

Open <http://127.0.0.1:8090>. Studio currently refuses non-loopback binding.

An activated virtual environment also installs the shorter
`phreqed-studio` console entry point.

```powershell
phreqed-studio `
  --workspace output/studio-workspace `
  serve
```

## Import reference media

```powershell
py -3.12 -m phreqed_dmx.studio_app `
  --workspace output/studio-workspace `
  import output/vfx-concepts/fuse-bomb-keyframes-v2-simple.png `
  --title "Fuse Bomb keyframes" `
  --family storylet-source

py -3.12 -m phreqed_dmx.studio_app `
  --workspace output/studio-workspace `
  import "G:\My Drive\albums\Heart Zones\Heart Zones Artwork\Elastic Stage 12 Vinyl\260408 phredqed digital art 1.png" `
  --title "Phreqed Heart Zones" `
  --family brand-artwork
```

The browser provides the same explicit local import operation. Reimporting the
same bytes is idempotent and cannot change the immutable source record.

## Create Storylets

Use the asset ID returned by import:

```powershell
py -3.12 -m phreqed_dmx.studio_app `
  --workspace output/studio-workspace `
  storylet `
  --id storylet-fuse-bomb-v1 `
  --asset ASSET_ID `
  --title "Fuse Bomb" `
  --duration 15 `
  --marker reveal=0.5 `
  --marker ignite=2 `
  --marker impact=11.5 `
  --marker decay=12 `
  --marker black=15
```

For the Heart Zones loop, select `--loop` and markers such as `pulse-a`,
`pulse-b`, `charge`, `discharge`, and `recover`.

## Export the Relate projection

```powershell
py -3.12 -m phreqed_dmx.studio_app `
  --workspace output/studio-workspace `
  export-graph
```

This writes `graph-projection.json` atomically. It is an interchange/test
boundary, not a graph-only source of truth. The upcoming Relate sprint will pin
one release, translate this projection through idempotent parameterized Cypher,
benchmark it, and prove full rebuild/removal.

## Current limitations

- local single-workspace prototype; no hosted identity or tenant authorization;
- local file-path import rather than resumable browser upload;
- no media probing, thumbnails, transcoding, proxies, or playback yet;
- Storylets are draft records; no revision editor or package publishing;
- graph projection only; Relate is not installed or queried by this process;
- no Stage delivery, activation, or live-output authority.

These are deliberate boundaries for the first slice rather than hidden
production claims.
