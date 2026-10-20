# Architecture

The engine follows a one-way data flow:

```text
effect samples -> normalized grids -> layers/masks/blends -> safety limiter
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
plasma, tunnel, pulse, and chase. It also treats both cubes as one logical 16x6
surface for cross-cube chase. Mirror, complementary, and independent modes are
resolved entirely in logical-grid space before DMX composition.

Phase 2 adds a standardized effect registry beside the legacy compatibility
engine. `SceneEngine` renders registry effects into `NormalizedGrid` instances.
`Compositor` applies per-layer fixture targeting, opacity, alpha/additive/lighten
blending, masks, global brightness limiting, and crossfades. `ShowController`
provides effect, parameter, preset, event, blackout, tap-tempo, and scene
navigation commands without importing Art-Net.

## Coordinates and physical zones

Logical `(0, 0)` is top-left when looking at a cube from the front. For the
confirmed LF4808 orientation:

```text
48 47 46 45 44 43 42 41
40 39 38 37 36 35 34 33
32 31 30 29 28 27 26 25
24 23 22 21 20 19 18 17
16 15 14 13 12 11 10  9
 8  7  6  5  4  3  2  1
```

Every zone maps to R, G, then B. Cube A's RGB data occupies DMX 1-144 and Cube
B's occupies DMX 153-296. Addresses 145-152 and 297-304 are deliberately zero.
Their functions must be verified from reliable fixture documentation and tested
safely before any mapping is added.

## Extension points

- Preserve the legacy grid renderer only for baseline compatibility tests.
- Add new effects through the per-pixel `Effect.sample` contract with complete
  metadata and no transport imports.
- Add sprites as `Sprite` data and render them onto any `PixelGrid`.
- Add fixture variants in TOML only when their channel layout is known.
- Add transports behind a small `send(bytes)` boundary without changing effects.
