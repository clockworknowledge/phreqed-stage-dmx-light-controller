# Effect catalog

Every Phase 2 effect implements the deterministic per-pixel contract in
`effect_api.py`. Inputs are logical coordinates, frame geometry, animation time,
fixture identity, validated `EffectParameters`, and optional
`PerformanceContext`. Outputs are normalized RGB values; effects never access
DMX addresses or sockets.

All effects provide:

- `speed`: 0.1-5.0 animation multiplier;
- `brightness`: 0.0-1.0 effect-local level;
- `palette`: spectrum, magma, ocean, neon, ember, monochrome, or matrix;
- at least two validated effect-specific parameters.

The compositor imposes a separate default global level and a hard default
ceiling of 0.65.

| ID | Name | Category | Effect-specific parameters |
| --- | --- | --- | --- |
| `plasma` | Advanced Plasma | psychedelic | `x_scale` 0.1-2.5, `y_scale` 0.1-2.5, `diagonal_scale` 0.1-2.5 |
| `flow-noise` | Flowing Noise | organic | `scale` 1.0-9.0, `drift` 0.05-1.5 |
| `lava-lamp` | Lava Lamp | organic | `blob_size` 0.2-1.2, `wobble` 0.1-1.0 |
| `vortex` | Colour Vortex | psychedelic | `arms` 1-8, `twist` 0.2-6.0 |
| `kaleidoscope` | Kaleidoscope | geometric | `segments` 2-12, `zoom` 0.4-4.0 |
| `rings` | Concentric Rings | geometric | `spacing` 0.5-4.0, `thickness` 0.1-1.0 |
| `interference` | Wave Interference | psychedelic | `frequency` 2-15, `sources` 2-6 |
| `bars` | Sweeping Bars | geometric | `bar_width` 0.05-0.48, `angle` -90-90 degrees |
| `checkerboard` | Animated Checkerboard | geometric | `size` 1-4, `contrast` 0-1, `motion` 0.1-4.0 |
| `fire` | Fire | organic | `turbulence` 1-8, `cooling` 0-0.8 |
| `digital-rain` | Digital Rain | digital | `density` 0.1-1.0, `trail` 0.3-5.0 |
| `glitch` | Glitch Distortion | digital | `block_size` 1-4, `jitter` 0.5-12.0 |
| `sparks` | Spark Trail | particle | `count` 3-24, `decay` 0.15-1.5 |
| `energy-transfer` | Cross-Cube Energy | cross-fixture | `rate` 0.5-16, `trail` 0.5-8.0 |
| `cross-blaster` | Cross-Cube Blaster | cross-fixture | `rate` 1-24, `trail` 1-18, `core_width` 0.25-4, `spread` 0.2-3 |
| `flame-jet` | Anchored Flame Jet | cross-fixture | `length` 0.45-1.25, `turbulence` 0.25-2, `strand_width` 0.18-1.2, `muzzle_size` 0.4-3 |
| `dynamic-wave` | Dynamic Sine Wave | musical | `cycles` 0.5-6, `amplitude` 0.1-1.8, `thickness` 0.12-1.5 |
| `inside-out-vu` | Inside-Out VU | musical | `sensitivity` 0.25-2.5, `peak_width` 0.015-0.25 |
| `radial-pulse` | Radial Pulse | musical | `frequency` 0.5-6.0, `sharpness` 1-6 |
| `tunnel` | Legacy Tunnel | legacy | `ring_frequency` 0.5-6.0, `floor` 0-0.5 |
| `pulse` | Legacy Pulse | legacy | `rate` 0.2-6.0, `sharpness` 1-6 |
| `chase` | Legacy Chase | legacy | `rate` 1-24, `trail` 2-16 |
| `cross-cube` | Legacy Cross-Cube Chase | legacy | `rate` 1-30, `trail` 2-24 |

`radial-pulse` is the first effect that can consume an optional normalized
audio-analysis frame. Loudness and band energy scale the existing ring, onset
adds a limited accent, and bass/treble balance supplies a small hue offset. With
no audio frame, its established tempo-aware rendering remains unchanged.

`flame-jet` anchors a compact white-hot source at the far left of Cube A and
forks a persistent ember jet across Cube A, the fixture boundary, and Cube B.
Audio dynamics make its reach and motion breathe without reversing its fixed
left-to-right direction.

`inside-out-vu` uses normalized audio energy when present and expands from the
gap between Cube A and Cube B toward the outside edges. `dynamic-wave` and
`cross-blaster` treat both fixtures as one logical 24-by-4 surface. Their motion
still passes through the shared tempo and dynamics clock. The `fire` gradient
is hottest at logical row 3, the physical bottom row; turbulence advects upward
toward row 0. Fixtures should remain upright with their printed text readable.

## Included presets

- `psychedelic-bloom`: neon plasma plus additive concentric rings.
- `molten-motion`: magma lava forms plus restrained ember sparks.
- `digital-storm`: ocean digital rain plus a low-opacity neon glitch layer.
- `energy-bridge`: cross-cube energy transfer plus a subtle radial pulse.
- `midnight-current`: slow ocean flow and faint neon shafts for intros.
- `acid-mirrors`: independent vortex and kaleidoscope motion with a shared pulse.
- `phase-collider`: wave interference reinforced by tempo-aware radial motion.
- `neon-blades`: diagonal neon bars cutting across a restrained moving grid.
- `inferno-rise`: turbulent ember fire with a smooth particle overlay.
- `split-signal`: independent digital rain and glitch fields joined by moving energy.
- `hypnotic-drive`: a forward tunnel reinforced by expanding neon rings.
- `crossfire`: hot and cool independent cube fields with cross-cube energy transfer.
- `matrix-rain`: matrix-green code columns with restrained scan distortion.
- `blaster-sweep`: a neon bolt travelling left-to-right across both fixtures.
- `flame-thrower`: a fixed far-left muzzle firing long, turbulent ember strands
  across the full combined display.
- `wave-rider`: a continuous sine/cosine ribbon whose velocity follows dynamics.
- `inside-out-vu`: music energy growing from the shared centre to both outer edges.

All presets default below the 0.65 global safety ceiling and contain no
strobe-channel behavior. The added show pack is capped at 0.48 global
brightness and avoids hard full-frame flashing. `acid-mirrors`, `split-signal`,
and `crossfire` deliberately render different material on each fixture. All five
new musical looks keep the center-white DMX channels at zero.
