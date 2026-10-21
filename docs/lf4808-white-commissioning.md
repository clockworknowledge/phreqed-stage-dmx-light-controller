# LF4808 white-zone commissioning

The LF4808 152-channel table assigns channels 1-144 to the 48 RGB zones and
channels 145-152 to eight independently, linearly dimmed white parts. Therefore:

| Fixture | White parts 1-8 |
| --- | --- |
| Cube A, A001 | DMX 145-152 |
| Cube B, A153 | DMX 297-304 |

The [manufacturer product page](https://betopperdj.com/products/betopper-lf4808-260w-matrix-strobe-effect-light)
confirms the 152-channel mode, 112 white LEDs, 1-30 Hz capability, and links the
LF4808 manual. The recovered manual table names the final eight channels
`Part 1` through `Part 8`, each with linear values 0-255. It does not document
their front-view direction, so the application preserves part numbering rather
than assuming left-to-right order.

## Safe first validation

Stop any running Phreqed controller first. QLC+ must be running with the
known-good workspace. Begin with the offline check:

```bash
.venv/bin/python scripts/white-zone-check.py
```

The offline run creates no socket and must report 16 frames: Cube A DMX
145-152 followed by Cube B DMX 297-304. Each frame contains exactly one value
of 13 (about 5%) and every RGB and other white channel is zero.

For the physical commissioning run, position both fixtures away from faces,
warn anyone nearby, and keep the browser/QLC+ blackout available. This command
uses steady light only; it does not flash:

```bash
.venv/bin/python scripts/white-zone-check.py live --level 0.05
```

For each announced part, record its physical position and whether both visible
white rows respond together. There is at least 0.75 seconds of blackout between
parts. `--level` cannot exceed 0.10, and normal shutdown or Ctrl+C requests a
final full-universe blackout.

The original acceptance gate prohibited pulse, beat, or strobe effects until
all sixteen observations were recorded and agreed between fixtures. The result
below satisfies that mapping gate. Normal rendering still sends zero unless the
separately guarded browser-live peak control supplies a white-zone frame.

## Accepted result — 2026-10-21

The operator completed the steady 5% physical test and reported identical
behavior on both fixtures:

- Parts 1-8 progress right-to-left when viewed from the front.
- Every part drives both visible white rows together.
- Cube A and Cube B match.

This result is encoded in `config/fixtures.toml` and fixture mapping tests. The
browser-live controller may now produce audio-onset peak accents, but only after
its separate physical-white toggle is enabled. Output defaults to 5%, has a hard
10% ceiling, uses pulses no longer than 0.10 seconds at no more than 4 Hz, and is
disarmed by blackout, stop, failure, or lease loss. Presets and normal rendering
still leave all white channels zero.
