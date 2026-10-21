# Architecture

The engine follows a one-way data flow:

```text
audio analysis -> performance context -> effect samples
                                      -> normalized grids -> layers/masks/blends -> safety limiter
                                                        |-> Tk simulator
                                                        |-> browser preview
                                                        `-> DMX quantizer
                                                            -> ArtDMX UDP
                                                            -> QLC+ -> USB-DMX
```

Effects know logical coordinates, fixture identity, animation time, validated
parameters, and optional performance context. They do not know DMX addresses or
transport details. `FixtureConfig` owns physical ordering and one-based DMX
start addresses. `compose_dmx` is the only layer that quantizes normalized RGB
and writes logical colors into a universe. The simulator calls `render_scene()`;
only the explicit live loop calls `render_dmx()` and constructs `ArtNetSender`.

`UserLibrary` validates complete versioned JSON documents before atomically
replacing the on-disk file. Built-in presets remain immutable. `SceneSequencer`
uses caller-supplied elapsed time for deterministic cue selection, timed holds,
and crossfades without importing GUI or transport code.

`BrowserControl` serializes access to one controller from an HTTP server and a
25 FPS render thread. The `web` command is simulation-only and cannot create an
Art-Net sender. `live --web` merely makes live activation available; the user
must confirm it in the page. A five-second heartbeat lease closes the sender
with blackout if the browser disappears. The HTTP server binds to loopback by
default and limits non-loopback clients to an explicit trusted IPv4 network.

`VisualEngine` preserves the four formulas from the reconstructed v2 baseline:
plasma, tunnel, pulse, and chase. It also treats both cubes as one logical 24x4
surface for cross-cube chase. Mirror, complementary, and independent modes are
resolved entirely in logical-grid space before DMX composition.

Phase 2 adds a standardized effect registry beside the legacy compatibility
engine. `SceneEngine` renders registry effects into `NormalizedGrid` instances.
`Compositor` applies per-layer fixture targeting, opacity, alpha/additive/lighten
blending, masks, global brightness limiting, and crossfades. `ShowController`
provides effect, parameter, preset, event, blackout, tap-tempo, and scene
navigation commands without importing Art-Net.

The compositor and final frame limiter share the same RGB ceiling. It defaults
to 0.65; a higher process-local ceiling can be constructed only by the CLI's
explicit live acknowledgement path. Browser state publishes that ceiling so
the master control cannot request a value above it. Saved preset brightness is
still limited to 0.65. The manual master is a peak level; audio may only scale
the rendered scene below it and cannot alter the ceiling. Browser preset and
scene selection preserve the active manual master override rather than
reapplying each preset's stored global brightness.

`AudioReactiveClock` integrates a continuous animation time shared by every
effect. Tempo establishes the baseline rate, `--speed` is the operator trim,
and smoothed audio energy provides a bounded 1.0x-2.0x motion multiplier.
Audio also supplies a bounded 55%-100% brightness multiplier below the manual
master. An explicit deep-dim setting can replace the 55% floor with an
operator-selected 0%-25% floor. With no audio source, both multipliers remain
exactly 1.0, preserving the deterministic non-audio path.

`audio_analysis.py` defines normalized loudness, onset, and three-band values
plus a small `AudioAnalysisSource` boundary. Manual and recorded sources are
dependency-free and deterministic. `audio_capture.py` optionally runs explicit
ALSA capture and PCM analysis on a worker outside the render deadline. With no
source configured, the capture module is not imported and rendering follows the
existing non-audio path unchanged.

`foot_control.py` parses standard MIDI channel messages without a third-party
runtime dependency and maps an explicitly selected Hotone Ampero Control input
onto that command boundary. It does not import Art-Net or fixture mapping and
cannot enable live output. Browser-mode pedal actions are routed through the
browser controller's existing serialized command path so cue navigation,
blackout, and safety state remain consistent. Its worker reopens the same raw
MIDI path after transient read/device errors and publishes connection and
reconnect status; a stable udev link is still needed if ALSA renumbers the card.

## Future projector output

Projector playback and overlays will be a separate render target, not another
branch of DMX composition. A future show coordinator can send the same unified
cue to the existing lighting controller and an independently supervised
projection process. Video decode, overlay timing, and HDMI presentation must
never execute on or block the 25 FPS DMX thread. The existing Ampero can advance
unified cues; a second pedal is optional only for independent projector
transport. See `docs/projector-output.md` and PROJ-001/PROJ-002/SHOW-002 in the
Kanban.

Wireless wearables follow the same future show-coordinator boundary. Each unit
renders a local effect from compact cue, palette, brightness, tempo/phase, and
bounded audio state; it does not receive DMX-universe frames or block the DMX
thread. Link loss affects only that wearable and must fade it to black. See
`docs/wearable-lighting.md` and WEAR-001/WEAR-002/SHOW-003 in the Kanban.

## Coordinates and physical zones

Logical `(0, 0)` is top-left when looking at a cube from the front. For the
confirmed LF4808 orientation:

```text
48 47 46 45 44 43 42 41 40 39 38 37
36 35 34 33 32 31 30 29 28 27 26 25
24 23 22 21 20 19 18 17 16 15 14 13
12 11 10  9  8  7  6  5  4  3  2  1
```

The physical grid is 12 columns by 4 rows. The earlier 8-by-6 reconstruction
was not distinguishable by its zone-48/top-left and zone-1/bottom-right test;
both candidate geometries share those endpoints. Row-boundary markers are
therefore required for physical geometry validation.

The diagram covers only the 48 RGB zones. Two central rows of white
strobe/blinder LEDs are physically present and remain separate from the RGB
grid. The LF4808 152-channel table defines eight linearly dimmed white parts on
fixture channels 145-152. Physical testing confirmed Parts 1-8 progress
right-to-left from the front and each part drives both visible rows on both
fixtures.

The browser canvas represents the two white rows between the upper and lower
RGB row pairs. Preview remains available in simulation. Physical peak output is
a separate browser-live state outside presets and RGB effects: it requires an
audio source and explicit toggle, is capped at 10%, uses short threshold-crossing
pulses no faster than 4 Hz, and is disarmed by every stop/blackout path.

Every RGB zone maps to R, G, then B. Cube A's RGB data occupies DMX 1-144 and
its white parts occupy 145-152. Cube B's RGB data occupies 153-296 and its white
parts occupy 297-304. `compose_dmx` accepts optional normalized white levels;
omitting them produces zeros. The commissioned mapping and original capped,
steady procedure are recorded in `lf4808-white-commissioning.md`.

## Extension points

- Preserve the legacy grid renderer only for baseline compatibility tests.
- Add new effects through the per-pixel `Effect.sample` contract with complete
  metadata and no transport imports.
- Add sprites as `Sprite` data and render them onto any `PixelGrid`.
- Add fixture variants in TOML only when their channel layout is known.
- Add transports behind a small `send(bytes)` boundary without changing effects.
