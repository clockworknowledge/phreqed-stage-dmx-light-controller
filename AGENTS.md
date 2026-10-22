# AGENTS.md

## Project purpose

Phreqed Stage DMX Light Controller is a Python 3.11+ lighting and visual-effects
engine for live performances. It renders logical RGB pixel grids and can either
preview them locally or transmit a 512-channel DMX frame to QLC+ using Art-Net.

## Architecture

- `src/phreqed_dmx/frame.py`: address-independent RGB values and pixel grids.
- `src/phreqed_dmx/color.py`: normalized RGB values, palettes, and grids.
- `src/phreqed_dmx/effect_api.py`: effect contract, metadata, context, and parameters.
- `src/phreqed_dmx/audio_analysis.py`: normalized audio-analysis contract and
  deterministic/manual sources; it never opens a capture device.
- `src/phreqed_dmx/audio_capture.py`: explicit ALSA `arecord` worker and
  dependency-free mono PCM analysis; importing it never opens a device.
- `src/phreqed_dmx/effect_library.py`: deterministic procedural effect catalog.
- `src/phreqed_dmx/compositor.py`: layers, blends, masks, transitions, and limits.
- `src/phreqed_dmx/engine.py`: preset and per-fixture normalized scene rendering.
- `src/phreqed_dmx/show_control.py`: transport-independent performance commands.
- `src/phreqed_dmx/foot_control.py`: dependency-free MIDI parsing and explicit
  Ampero Control input; it maps pedal messages only to show commands.
- `src/phreqed_dmx/white_output.py`: commissioned white-part output, onset pulse
  shaping, default 10% ceiling, explicit live override boundary, and independent
  0.10-second/4 Hz safety limits.
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
- Each fixture also has two central rows of white strobe/blinder LEDs. The
  recovered LF4808 152-channel table maps them as eight linearly dimmed white
  parts on fixture channels 145-152. Physical commissioning on 2026-10-21
  confirmed Parts 1-8 progress right-to-left and each part drives both rows,
  identically on both fixtures.
- Zone 1 is bottom-right. Zones advance right-to-left across a row, then
  bottom-to-top through the rows.
- RGB uses the first 144 fixture channels. The final eight white channels remain
  zero during normal show rendering unless the commissioned browser-live white
  peak control is separately enabled.
- Each Art-Net transmission carries a complete 512-channel DMX payload.
- QLC+ must be the only process bound to UDP 6454. The baseline notes record a
  prior conflict with OLA's `olad`; keep that service disabled while QLC+ is in use.

Logical grid coordinates use `(0, 0)` at the visible top-left. Fixture mapping,
not effect code, converts those coordinates to physical zone order.

## Safety constraints

- Simulation is the default. Live transmission always requires the explicit
  `live` command.
- Keep fixture channels 145-152 zero by default. Physical white output requires
  explicit `live --web`, active browser-live output, an audio source, and the
  separate white-output toggle. The default ceiling is 10%. A higher
  process-local ceiling requires `--white-ceiling` plus
  `--acknowledge-high-output-whites`, is forbidden outside explicit
  `live --web`, and must display a persistent browser warning. Always use onset
  threshold crossings and limit pulses to at most 0.10 seconds and 4 Hz.
- Blackout, live stop, render failure, and browser-lease loss must immediately
  disable white output. Releasing blackout must not silently re-arm it.
- Keep the default RGB ceiling at 0.65. A higher ceiling is a temporary
  show-time override only: require explicit `live` mode plus
  `--acknowledge-high-output`, display the selected ceiling to the operator,
  and retain the luminance-rise and flash-interval limiter. Saved presets stay
  at or below 0.65. The RGB override must never alter the separately configured
  white-channel ceiling.
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
- Foot control is disabled unless an explicit raw-MIDI device path is supplied.
  MIDI input must not enable live output or bypass the browser live gate.
  Initial absence or later loss of that path must not stop browser/audio
  control; retry only the explicit path and report disconnected status rather
  than scanning for another MIDI device.
- Audio capture must remain disabled unless an explicit device is supplied.
  Audio analysis may modulate bounded effect parameters but must not enable live
  output, bypass blackout, or introduce unrestricted full-frame flashes.
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
- Keep audio-reactive rendering deterministic for supplied analysis frames;
  isolate real-time capture behind `AudioAnalysisSource`.
- Route tempo and audio dynamics through the shared bounded animation clock so
  every effect receives the same continuous time base. Audio brightness is a
  multiplier below the manual master and must never raise an output ceiling.
- Keep capture auto-leveling bounded and independent of output ceilings. It may
  restore analysis headroom after sustained clipping but must not create DMX
  gain or replace the operator's persistent master control.
- Apply visual contrast in normalized RGB space before the master/ceiling. It
  must preserve hue, clamp all channels, and never expand the safety ceiling.
- Treat the browser master brightness as a persistent operator override; preset
  and scene navigation must not silently clear or replace it.
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
