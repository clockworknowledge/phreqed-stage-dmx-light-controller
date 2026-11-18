# Travelling sparse-hybrid workstation render

Date: 2026-11-17  
Card: `SHOW-005`; production follow-up: `MEDIA-003`

## Result

The first complete sparse hybrid package for **Travelling on a Floating Rock**
rendered successfully and passed local Stage package preflight. This validates
the version-2 layered EDL concept, but the measured build time and lack of
incremental progress make the monolithic FFmpeg graph unsuitable for the
production Studio pipeline.

## Reference workstation and tools

- CPU: Intel Core i7-10750H at 2.60 GHz
- RAM: 63.8 GiB visible
- Python: 3.12.10
- FFmpeg: 4.2.3, ImageMagick distribution
- Filter workers: 4
- Master source: 285 MB, 146 seconds, Google Drive-mounted volume
- VFX sources: eight local Infinity VFX assets

## Composition and command

- EDL: `travelling-on-a-floating-rock-hybrid-v1.edl.json`
- Song duration: 180.0 seconds
- Logical canvas: 720×1280 portrait
- Stage signal: 1280×720, clockwise rotation, rear-screen horizontal mirror
- Frame rate: 30 FPS
- Authored layers: 23
- Visible phrases: 7, totalling 69 seconds
- Intentional black: 111 seconds
- Output: audio-free H.264 High 4.1, `yuv420p`

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-on-a-floating-rock-hybrid-v1.edl.json `
  --assets output/travelling-hybrid-assets.local.json `
  --output output/video-render `
  --ffmpeg "C:\Program Files\ImageMagick\ffmpeg.exe" `
  --filter-threads 4
```

## Measurements

- Wall time: 70 minutes 48 seconds
- Observed RSS: approximately 1.1 GiB initially; 4.78 GiB near completion
- CPU: sustained multiple cores; 13,439 CPU seconds at 69.5 minutes elapsed
- Source reads observed near completion: 618 MB across master and VFX inputs
- Intermediate writes observed near completion: 51.5 MB
- Final MP4 size: 55,413,480 bytes
- Final MP4 SHA-256:
  `b3e9049e4e908e9e62de7d03646f0e5b085b0055e31dacb7e0fb2661fd376274`
- FFmpeg warnings/errors: none observed
- Final package exposure: atomic; no reviewable partial MP4 or frame progress
  was available during the long filter-graph preparation pass

## Validation

- `load_stage_video_package` passed the embedded EDL, source records, duration,
  rendition dimensions/rate, file size, and SHA-256 checks.
- Package ID:
  `travelling-floating-rock-hybrid-v1--stage-portrait-hdmi720-clockwise-rear`
- Contact-sheet frames were extracted at 2, 8, 20, 36, 50, 67, 80, 96, 110,
  125, 140, 154, 165, 172, 177, and 179.5 seconds.
- Samples at 8, 36, 67, 96, 125, 154, 172, and 177 seconds show the intended
  seven phrases/finale progression.
- Samples at 2, 20, 50, 80, 110, 140, 165, and 179.5 seconds are consistently
  near-black after H.264/JPEG decode; all eight JPEG means were `0.00395062`.
- Desktop frames appear sideways because the Stage rendition includes the
  commissioned clockwise physical projector rotation. This must be reviewed on
  the vertical rear-screen path rather than "corrected" in the authored layout.

## Production requirements derived from the run

`MEDIA-003` now requires local content-addressed source staging, disjoint phrase
and black-gap compilation, cached intermediates, low-resolution proxies,
resumable chunks, visible job phases/progress, cancellation, bounded workers,
atomic assembly, audit metadata, and explicit failure recovery. Targets are a
proxy within 60 seconds, a changed phrase within 30 seconds, a complete reference
Stage build within 10 minutes, and no more than 4 GiB worker RSS unless a
measured platform exception is reviewed.

## Remaining show acceptance

1. Watch the complete MP4 with the song and inspect motion, crop, transitions,
   visual restraint, and every black gap.
2. Copy the MP4 and manifest to the Pi package directory without replacing the
   current baseline package.
3. Run Pi package preflight, projection playback, Start/Stop/Blackout,
   Video-disabled, and full-song Lighting/video drift checks.
4. Publish a new Video Show revision only after that review passes.
