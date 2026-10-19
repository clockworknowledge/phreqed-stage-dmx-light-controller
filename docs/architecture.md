# Architecture

The engine follows a one-way data flow:

```text
effect / sprite -> logical 8x6 PixelGrid -> fixture mapper -> 512-byte DMX frame
                                                         |-> Tk simulator
                                                         `-> ArtDMX UDP -> QLC+ -> USB-DMX
```

Effects and sprites know only grid dimensions and RGB values. `FixtureConfig`
owns physical ordering and one-based DMX start addresses. `compose_dmx` is the
only layer that writes logical colors into a universe. The simulator reads the
same logical grids without constructing a socket; the live controller sends the
composed universe through `ArtNetSender`.

`VisualEngine` preserves the four formulas from the reconstructed v2 baseline:
plasma, tunnel, pulse, and chase. It also treats both cubes as one logical 16x6
surface for cross-cube chase. Mirror, complementary, and independent modes are
resolved entirely in logical-grid space before DMX composition.

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

- Add effects by implementing `Effect.render(elapsed, grids)` with no transport
  imports.
- Add sprites as `Sprite` data and render them onto any `PixelGrid`.
- Add fixture variants in TOML only when their channel layout is known.
- Add transports behind a small `send(bytes)` boundary without changing effects.
