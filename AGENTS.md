# AGENTS.md

## Project purpose

Phreqed Stage DMX Light Controller is a Python 3.11+ lighting and visual-effects
engine for live performances. It renders logical RGB pixel grids and can either
preview them locally or transmit a 512-channel DMX frame to QLC+ using Art-Net.

## Architecture

- `src/phreqed_dmx/frame.py`: address-independent RGB values and pixel grids.
- `src/phreqed_dmx/color.py`: normalized RGB values, palettes, and grids.
- `src/phreqed_dmx/effect_api.py`: effect contract, metadata, context, and parameters.
- `src/phreqed_dmx/effect_library.py`: deterministic procedural effect catalog.
- `src/phreqed_dmx/compositor.py`: layers, blends, masks, transitions, and limits.
- `src/phreqed_dmx/engine.py`: preset and per-fixture normalized scene rendering.
- `src/phreqed_dmx/show_control.py`: transport-independent performance commands.
- `src/phreqed_dmx/scenes.py`: deterministic ordered-cue playback and transitions.
- `src/phreqed_dmx/library.py`: validated, atomic user presets and scene storage.
- `src/phreqed_dmx/fixtures.py`: fixture geometry and logical-pixel-to-DMX mapping.
- `src/phreqed_dmx/render.py`: composes logical grids into one DMX universe.
- `src/phreqed_dmx/artnet.py`: ArtDMX packet construction and UDP transmission.
- `src/phreqed_dmx/effects.py`: v2-compatible effects that operate only on grids.
- `src/phreqed_dmx/sprites.py`: small bitmap sprites and grid drawing helpers.
- `src/phreqed_dmx/simulator.py`: local Tkinter preview; never opens a UDP socket.
- `src/phreqed_dmx/web_control.py`: dependency-free browser preview/control with
  explicit live enablement and a disconnect watchdog.
- `src/phreqed_dmx/app.py`: application controller, timing, and mode selection.
- `config/fixtures.toml`: hardware and controller configuration.
- `tests/`: hardware-free unit tests.

Keep rendering, physical mapping, and transport independent. Effects must not
contain DMX addresses, Art-Net details, or socket operations.

## Confirmed hardware mapping

The canonical model reference is the
[official Betopper LF4808 page](https://betopperdj.com/products/betopper-lf4808-260w-matrix-strobe-effect-light).
It confirms pixel/zone mapping and 152-channel mode. Coordinate orientation and
the 12-by-4 geometry are based on controlled physical fixture testing.

- QLC+ listens for Art-Net on `127.0.0.1:6454`, universe 0, with passthrough.
- Two Betopper LF4808 fixtures use 152-channel mode.
- Cube A starts at one-based DMX address 1; Cube B starts at address 153.
- Each fixture exposes 48 confirmed RGB zones, three channels per zone (R, G, B).
- The front view is 12 columns by 4 rows. This geometry supersedes the 8-by-6
  assumption retained in the immutable reconstructed baseline.
- Each fixture also has two central white strobe/blinder elements. Prior Pi
  testing reportedly controlled them from original scripts, but those scripts
  and their exact channel assignments are not present in this checkout. They
  are not RGB-grid pixels and remain disabled in the package until that source
  is imported and characterized.
- Zone 1 is bottom-right. Zones advance right-to-left across a row, then
  bottom-to-top through the rows.
- Only the first 144 fixture channels are mapped. The last eight channels of
  each fixture are unverified and must remain zero.
- Each Art-Net transmission carries a complete 512-channel DMX payload.
- QLC+ must be the only process bound to UDP 6454. The baseline notes record a
  prior conflict with OLA's `olad`; keep that service disabled while QLC+ is in use.

Logical grid coordinates use `(0, 0)` at the visible top-left. Fixture mapping,
not effect code, converts those coordinates to physical zone order.

## Safety constraints

- Simulation is the default. Live transmission always requires the explicit
  `live` command.
- Never activate, probe, sweep, or infer the eight currently undocumented
  channels on either fixture. Recover the known-working white-strobe assignment
  from original source and physical test notes before adding it to this package.
- Keep the default global brightness at or below 0.65 and retain the frame safety
  limiter unless a documented hardware test justifies a change.
- New default effects must avoid rapid high-intensity full-frame flashes.
- New configuration must be rejected if a fixture falls outside the 512-channel
  universe or overlaps another fixture.
- Validate ArtDMX payload size, universe, sequence, and channel values before
  transmission.
- Live output should send a blackout on normal shutdown and on handled
  interruption. A process kill, power loss, or network failure cannot guarantee
  blackout, so QLC+ should also have an operator-accessible blackout control.
- Browser simulation must never construct `ArtNetSender`. Browser live control
  requires the literal `live --web` combination, an in-page confirmation, and
  an active heartbeat lease; losing the lease must stop with blackout.
- Bind browser control to loopback by default. LAN binding is permitted only on
  a trusted private network with an explicit allow-network range.
- Do not increase the initial 25 FPS output rate without testing the complete
  Raspberry Pi, QLC+, USB-DMX, and fixture chain.

## Coding conventions

- Target Python 3.11+ and prefer the standard library. Add a dependency only
  when its value clearly outweighs deployment and reliability cost.
- Use type hints for public APIs and small, focused modules.
- Treat DMX addresses in configuration as one-based; use zero-based offsets only
  internally and name them accordingly.
- Keep effect output deterministic for a supplied elapsed time when practical.
- Effects implement the standardized per-pixel interface, declare complete
  metadata, and use normalized RGB. Quantize only in `compose_dmx`.
- Every effect exposes speed, effect level, palette, and at least two validated
  effect-specific parameters.
- Do not import Tkinter from core rendering or transport modules.
- Raise clear `ValueError` exceptions at configuration and protocol boundaries.
- Tests must run on Windows without QLC+, network transmission, or DMX hardware.

## Development workflow

1. Run `git status --short` and preserve unrelated user changes.
2. Run `python -m unittest discover -s tests -v` before and after changes.
3. Develop in simulation mode and visually check both cube previews.
4. Add mapping/protocol tests for every boundary or orientation change. A
   geometry check must exercise row transitions, not only zones 1 and 48.
5. Review a diff before committing.
6. Test live output on the Raspberry Pi only with fixtures safely positioned,
   people warned, and QLC+ blackout immediately available.

## Baseline source policy

`phreqed-stage-dmx-baseline/` contains reconstructed conversation snapshots and
`phreqed-stage-dmx-baseline.zip` is their retained archive. Treat both as
immutable evidence: do not format, import, rename, move, or edit them. Several
scripts open a socket at module import and execute live loops, so tests must not
import them. Reproduce behavior through package code and characterize it with
tests instead.

These snapshots are not direct copies from the Raspberry Pi. When the actual Pi
files become available, copy them into a new dated, isolated directory, hash
them, and compare them without overwriting this baseline. See
`docs/pi-script-import.md` and `docs/baseline-inventory.md`.
