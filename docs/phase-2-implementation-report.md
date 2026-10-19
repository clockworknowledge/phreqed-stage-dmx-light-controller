# Phase 2 implementation report

## Delivered

- A normalized RGB pipeline with DMX quantization only at the output boundary.
- A deterministic effect contract with metadata, typed validated parameters,
  fixture identity, and optional performance context.
- Fifteen requested advanced procedural effects and four legacy-preservation
  effects, all dependency-free.
- A compositor with alpha, additive, and lighten blending; layer opacity;
  per-fixture targeting; radial masks; global limits; and pure crossfades.
- A configurable stateful limiter for large repeated full-frame luminance rises.
- Four example multi-layer presets.
- Transport-independent show commands for effect and parameter changes, preset
  activation, events, blackout, tap tempo, and scene navigation.
- An interactive two-cube Tk simulator with dynamic parameters, independent
  cube effects, speed and brightness, FPS display, pause/resume, stepping,
  blackout, and dependency-free PPM screenshot export.
- Explicit scene versus DMX rendering paths. Simulation never constructs the
  Art-Net sender.

## Verification

- 57 automated tests pass on Python 3.12.
- A real Tk smoke run constructed two 48-cell grids and both parameter panels.
- The deadline scheduler measured 25.0 FPS over a 2.2-second local GUI run.
- On the Windows development machine, the slowest single-effect two-cube frame
  averaged 5.151 ms (`sparks`); the 25 FPS budget is 40 ms. Raspberry Pi timing
  still requires direct measurement.
- Existing fixture mapping, packet, blackout, baseline-effect, and no-network
  simulation tests continue to pass.
- The imported baseline hashes remain the acceptance reference and are checked
  again at final handoff.

## Remaining risks and follow-up

- No Phase 2 code has yet been exercised against the physical fixtures.
- Raspberry Pi 5 CPU load and thermal behavior need a sustained soak test.
- The actual current Pi files still need comparison with the reconstructed
  conversation baseline.
- Preset, effect, and palette changes crossfade over 0.45 seconds in the
  simulator. Parameter sliders remain immediate for responsive tuning.
- Tap tempo and event context are defined and tested; automatic audio analysis
  is intentionally out of scope.
- PPM export avoids dependencies; PNG export would require either a platform
  conversion step or an image library.
- Foot-controller drivers and video-to-RGB mapping remain future work.
- The eight unverified fixture channels remain zero and inaccessible.
