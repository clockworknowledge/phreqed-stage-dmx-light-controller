# Video EDL and Stage rendition baseline

The baseline keeps authoring decisions separate from show-critical playback:

```text
immutable local originals
        -> local asset-ID map
        -> versioned Video EDL
        -> validated FFmpeg build
        -> H.264 Stage rendition + checksummed manifest
        -> separately supervised projection player
```

Original media is never edited or copied into the repository. A Video EDL uses
logical asset IDs, source in/out times, fit mode, focal point, fades, and a
projection profile. Local filesystem paths live only in an ignored asset map.
The EDL is therefore portable into the future Studio asset library without
making a developer path part of show data.

## Current baseline

The implemented renderer supports sequential, non-overlapping clips with:

- non-destructive source in/out ranges;
- `cover` or `contain` fitting;
- normalized horizontal and vertical focal points;
- per-clip fade in/out;
- a logical canvas and optional clockwise/counter-clockwise output rotation;
- normalized 1-30 FPS output within the initial 1080p pixel budget;
- audio-free H.264 High 4.1, `yuv420p` Stage renditions; and
- source, EDL, and output SHA-256 hashes in a package manifest.

The first profile is a logical 1080×1920 portrait canvas. Use `output_rotation:
"none"` when the Pi compositor already exposes a portrait display. Use
`clockwise` or `counterclockwise` to encode the logical portrait canvas into a
1920×1080 signal for a physically rotated projector that still advertises a
landscape mode.

This slice deliberately does not yet render overlapping VFX layers, alpha,
blend modes, live shaders, or song transport. Those remain `PROJ-002` and
`SHOW-002`. The initial Stage player backend also remains unselected until VLC,
mpv, and GStreamer are compared on the commissioned Pi.

## Local render workflow

Create the ignored local asset map from the example:

```powershell
New-Item -ItemType Directory -Force output/video-render | Out-Null
Copy-Item examples/video/assets.local.example.json `
  output/video-render/assets.local.json
```

Edit `output/video-render/assets.local.json` so `travelling-master` resolves to
the immutable source file. Run the short portrait probe first:

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-five-second-probe.edl.json `
  --assets output/video-render/assets.local.json `
  --output output/video-render
```

After reviewing that output, render the complete baseline:

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-baseline.edl.json `
  --assets output/video-render/assets.local.json `
  --output output/video-render
```

Existing renditions are not replaced implicitly. Rebuilding the same package
requires `--overwrite`. FFmpeg is always invoked as an argument vector without
a shell; an EDL cannot contain a command or remote URL.

## Stage preflight and player boundary

`load_stage_video_package()` accepts only a local MP4 filename beside its
manifest. It validates schema version, embedded EDL hash, package identity,
duration, dimensions, frame rate, H.264/pixel format, absence of audio, file
size, and rendition hash before returning a playable package.

`ProjectionController` is disabled and black when no backend is explicitly
injected. Its load, play, pause, seek, stop, black, and close boundary is
independent of DMX. The future Pi backend must keep output black during load and
pre-roll, fail black on error, and never run in the lighting render thread.

## Pi display probe

With the projector attached, run the read-only inventory:

```bash
.venv/bin/python scripts/projector-probe.py \
  --output /tmp/phreqed-projector-probe.json
```

It records the active session, available display inventories (`wlr-randr`,
`kmsprint`, or `xrandr`), and installed VLC/mpv/GStreamer/FFmpeg candidates. It
does not change display configuration or launch playback.
