# Travelling hybrid Lighting/Video baseline

This baseline treats projection as a stage accent, not as a continuous music
video. It renders one reliable 180-second H.264 package for the Raspberry Pi,
but the picture is intentionally black for most of the song. Seven short visual
phrases combine non-destructive fragments of the Travelling master with selected
Infinity VFX sources.

The source files are never modified. The committed EDL contains only asset IDs,
source ranges, absolute song times, composition settings, and the portrait rear
projection profile. Local filesystem paths stay in an uncommitted asset map;
the rendered Stage manifest records source hashes.

## Cue map

The times align with the current 180-second song and its published Lighting cue
boundaries. They are a first rehearsal map, not a claim about final musical
section names. Rehearsal should refine the boundaries against the actual audio
without changing the authoritative song or setlist records.

| Song time | Lighting scene | Video phrase | Treatment |
| ---: | --- | --- | --- |
| 0.0 | Midnight Current | Black, then opening at 4.0 | Six-second master fragment with restrained Chaotic Energy |
| 30.6 | Wave Rider | 32.0-42.0 | Master movement with portrait Fluid Smoke |
| 61.2 | Molten Motion | 63.0-72.0 | Warm master fragment with two brief Ember Patterns bursts |
| 91.8 | Inside-Out VU | 93.0-104.0 | Rhythmic master fragment, Electric Ribbons, then Duality |
| 120.6 | Watchful Eyes | 122.0-131.0 | Darker master fragment with Disperse and restrained Chaotic Energy |
| 147.6 | Wave Rider | 149.0-161.0 | Moving master fragment, smoke, then two short shockwave accents |
| 167.4 | Psychedelic Bloom | 168.0-179.0 | Layered finale with Duality, ribbons, ring, and disperse; fade to black |

The union of all visible intervals is 69 seconds. The remaining 111 seconds are
true black from the composition canvas and the persistent projector underlay.
No continuous master fragment exceeds ten seconds.

## Version 2 composition contract

Version 1 EDLs remain unchanged and sequential. Version 2 adds:

- an explicit full-song duration and black base canvas;
- absolute `at_seconds` placement for each layer;
- independent source ranges, fit, focal point, opacity, and fades;
- `normal`, `screen`, `add`, and `lighten` composition modes;
- overlapping layers compiled offline into one Stage rendition.

The Pi does not composite these sources live. It still plays one pre-rendered,
hash-verified H.264 file, which avoids scene-launch latency and keeps Video
failure independent from Lighting.

## Review and render

The source selector is generated locally under
`output/travelling-hybrid-review/review-board.html`. Its selectable items link
to four-second source previews; generated review files remain ignored by Git.

Copy `examples/video/assets.travelling-hybrid.local.example.json` to a local,
uncommitted path and replace the placeholders. Then render with:

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-on-a-floating-rock-hybrid-v1.edl.json `
  --assets output/travelling-hybrid-assets.local.json `
  --output output/video-render `
  --ffmpeg "C:\Program Files\ImageMagick\ffmpeg.exe" `
  --filter-threads 4
```

The default is one conservative filter worker. A workstation with sufficient
CPU/memory may select 2-4 workers for this 23-layer composition; keep the Pi out
of this build path and copy only the completed package to Stage.

After visual review, the package can replace the current Travelling scene in a
new Video Show revision. Do not overwrite the existing published baseline or
the Pi's `songs.json`, setlists, tuning profiles, or current `video-show.json`.

## Bench acceptance

- Review the full 180 seconds with audio and confirm that every black interval
  is intentional and every phrase supports, rather than distracts from, the
  performer.
- Confirm the seven video arrivals feel aligned with the current Lighting cues.
- Confirm the portrait crop keeps the useful character/action area on screen.
- Run Start, Stop, Blackout, no-autostart, controller restart, and Video-disabled
  checks before publishing the new Video Show revision.
- Record drift at the end of the song and adjust the authored song duration or
  cue positions only from measured rehearsal evidence.
