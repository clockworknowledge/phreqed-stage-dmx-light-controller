# Phreqed Stage DMX Light Controller

A simulation-first Python 3.11+ visual engine for a Calgary rock band's two
Betopper LF4808 RGB matrix fixtures. It provides deterministic procedural
effects, normalized RGB layer compositing, presets, an interactive two-cube
simulator, a dependency-free browser show controller, and explicit live
512-channel Art-Net output through QLC+.

To continue deployment or development in a fresh Codex session, start with the
[current resume](RESUME.md), then read [`AGENTS.md`](AGENTS.md) and the
[project Kanban](docs/kanban.md).

The reconstructed conversation baseline is preserved unchanged under
`phreqed-stage-dmx-baseline/`. The package retains its plasma, tunnel, pulse,
chase, and cross-cube chase while adding twenty-one advanced effects. These
snapshots are not direct Pi exports; see the [baseline inventory](docs/baseline-inventory.md)
and [Pi comparison checklist](docs/pi-script-import.md).

## Phase 2 capabilities

- 25 registered effects with validated metadata and deterministic output
- spectrum, magma, ocean, neon, ember, monochrome, and matrix palettes
- alpha, additive, and lighten layers with opacity and masks
- independent per-cube effects or continuous cross-cube effects
- nineteen built-in presets, including independent and cross-cube show looks
- conservative global brightness ceiling and frame-rise limiter
- transport-independent blackout, preset, event, tap-tempo, and navigation APIs
- normalized, replayable audio analysis with explicit opt-in Blue Snowball/ALSA
  capture, browser meters, and silence-on-input-loss behavior
- optional Hotone Ampero Control input over an explicitly selected ALSA
  raw-MIDI device, with disconnect recovery and browser status; foot input never
  enables Art-Net output
- interactive Tk simulator with live FPS, pause, step, parameters, and PPM export
- versioned user looks and ordered scenes with atomic JSON persistence
- browser previews and show control with an explicit live gate and disconnect blackout

See the complete [effect catalog](docs/effects.md) and
[Phase 2 implementation report](docs/phase-2-implementation-report.md). Feature
status and upcoming work are tracked on the [project Kanban](docs/kanban.md).
The staged audio plan is documented in
[Audio synchronization](docs/audio-synchronization.md).

## Hardware configuration

Fixture reference: [Betopper LF4808 official product page](https://betopperdj.com/products/betopper-lf4808-260w-matrix-strobe-effect-light).
The manufacturer page confirms individual pixel/zone mapping and 152-channel
mode; the 12-by-4 front-view orientation comes from physical fixture testing.

- Art-Net target: `127.0.0.1:6454`, universe 0
- QLC+ passthrough to an FTDI FT232R USB-DMX adapter
- Cube A: 152-channel mode, starts at DMX 1
- Cube B: 152-channel mode, starts at DMX 153
- 48 RGB zones per cube in a 12-column by 4-row front-view grid; zone 1 is
  bottom-right
- zones advance right-to-left, then bottom-to-top
- two center rows contain eight documented, linearly dimmed white parts on
  fixture channels 145-152; they are not part of the RGB grid
- physical commissioning confirmed Parts 1-8 progress right-to-left and each
  part drives both rows, identically on both fixtures
- normal output keeps those parts at zero; browser live can separately arm
  audio-onset accents with a default 10% ceiling, 0.10-second pulse limit, and
  4 Hz rate limit; a separately acknowledged live override can raise only the
  process-local ceiling

The committed settings are in [`config/fixtures.toml`](config/fixtures.toml).

## Install on Windows

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

There are no third-party runtime dependencies. Tkinter, included with standard
CPython Windows installers, supplies the preview window.

## Run safely in simulation

Simulation is the default and does not create an Art-Net socket:

```powershell
phreqed-dmx simulate
phreqed-dmx simulate --preset molten-motion
phreqed-dmx simulate --effect kaleidoscope --palette neon
phreqed-dmx simulate --effect fire --mode independent --second-effect digital-rain
phreqed-dmx simulate --effect energy-transfer
phreqed-dmx simulate --preset acid-mirrors
phreqed-dmx simulate --preset crossfire
phreqed-dmx simulate --preset matrix-rain
phreqed-dmx simulate --preset blaster-sweep
phreqed-dmx simulate --preset flame-thrower
phreqed-dmx simulate --preset wave-rider
phreqed-dmx simulate --preset pacman-chase
phreqed-dmx simulate --preset inside-out-vu
```

The preview shows both cubes from the front and provides:

- preset and independent per-cube effect selection;
- palette and validated parameter controls;
- global speed and brightness;
- pause/resume and manual frame stepping;
- measured frame rate, blackout, and PPM screenshot export.

Changing a cube control switches the engine from its active preset to manual
per-fixture mode. Simulation calls normalized scene rendering only and never
constructs an Art-Net sender.

## Run browser simulation

Browser mode is also simulation-only by default:

```powershell
phreqed-dmx web
```

Open `http://127.0.0.1:8080`. The controller previews both fixtures, edits and
persists user looks, builds timed scene lists, and exposes blackout and show
transport controls. The default library is stored outside the repository at
`~/.local/share/phreqed-dmx/library.json`.

For trusted-LAN preview from the Pi, bind explicitly while remaining in the
simulation-only `web` command:

```bash
.venv/bin/phreqed-dmx web --host 0.0.0.0 --allow-network 192.168.1.0/24
```

This opens only the browser HTTP server; it cannot enable Art-Net output.

### Preview microphone response

On the Pi, microphone capture remains off unless a device is named explicitly.
The verified Blue Snowball ALSA name is stable across USB card-number changes:

```bash
.venv/bin/phreqed-dmx web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --preset phase-collider \
  --audio-device plughw:CARD=Snowball,DEV=0
```

This command is still browser simulation and cannot transmit Art-Net. The page
shows loudness, onset, bass, mid, and treble meters. If response is too weak or
too sensitive, add `--audio-sensitivity 8` (valid range `0.1..40`, default
`12`). Tempo establishes the base animation rate for every effect. Smoothed
music dynamics then vary motion from 0.7x to 1.5x around that baseline and
brightness from 55% to 100% of the manual master; they never raise the RGB
ceiling. Automatic microphone leveling is on by default and slowly reduces
analysis gain when sustained venue volume would otherwise pin a meter; it can
be toggled in the browser or disabled with `--no-audio-auto-level`. Input loss clears
the analysis to silence without stopping controls or tempo-driven movement.
Enable **Deep dim on quiet passages** in the browser to replace the normal 55%
floor with an adjustable 0%-25% near-black floor. The setting changes only the
audio multiplier; the master slider remains the persistent peak level when
presets or scenes change.
The browser's **Visual contrast** control (1.0x-3.0x) expands separation between
dim and bright pixels without increasing the master or RGB ceiling. This is
particularly useful for fill-heavy looks at higher master settings.
See [Audio synchronization](docs/audio-synchronization.md) for limitations and
the remaining Raspberry Pi timing gate.

## Hotone Ampero Control

The [Hotone Ampero Control](https://www.hotone.com/products/controlers/Ampero%20Control)
is a four-switch programmable MIDI controller. The initial Phreqed bank maps
switches 1–3 to previous scene, next scene,
and tap tempo. Switch 4 sends explicit blackout-on/off values. USB MIDI is the
recommended first-stage transport because it also powers the controller and
avoids Bluetooth pairing failures.

Foot input is disabled unless `--foot-midi-device` is supplied. For setup,
message assignments, Pi device discovery, and safe testing, see
[`docs/ampero-control.md`](docs/ampero-control.md).

If USB MIDI drops temporarily, the reader closes and reopens the configured
device instead of silently terminating. The browser reports connection state,
message count, and reconnect count. A stable udev path is still required before
unattended stage use because `/dev/snd/midiC3D0` can change after re-enumeration.
If the explicitly selected node is absent at startup, the browser controller now
stays available and reports that MIDI is waiting while retrying that same path;
it never guesses at or binds another MIDI device.

## Run live on the Raspberry Pi

The Pi deployment is terminal-only and does not require Codex or VS Code. After
cloning the repository, `bash scripts/pi-install.sh` creates the environment,
installs the controller, and runs its tests. Later clean deployments use
`bash scripts/pi-update.sh`.

Live network output requires the explicit flag:

```bash
phreqed-dmx live --preset psychedelic-bloom
```

Do this only after checking QLC+, fixture modes, addresses, physical safety, and
the operator blackout control. On handled shutdown, the app sends a best-effort
blackout. See [Raspberry Pi deployment](docs/raspberry-pi-deployment.md).

For unattended shows, the repository now includes a systemd boot sequence that
starts headless QLC+ and then the browser controller while leaving lighting
output stopped. The recommended control layout uses the USB Ampero as the
offline performance control and a private, internet-independent stage LAN for
the phone interface. See
[Headless show control](docs/headless-show-control.md).

Commands accept `--brightness` and `--speed`. The RGB ceiling defaults to 0.65.
For a physically checked show rig, a higher temporary ceiling requires all of
the following explicit live options:

```bash
.venv/bin/phreqed-dmx live --web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --rgb-ceiling 0.85 --acknowledge-high-output
```

Browser live still starts at 0.25 or lower; its master slider then shows and
respects the selected ceiling. The luminance-rise and flash-interval limiter
remain active. Saved presets remain capped at 0.65, and this RGB override does
not change the separately configured white-channel ceiling. Use `--effect`
for manual mode, with `--mode mirror|complementary|independent` and
`--second-effect` where needed. Run `phreqed-dmx --help` for the complete effect
and preset lists. With no command, the CLI defaults to simulation; network
output can only be selected with the literal `live` command.

The acknowledged ceiling may be set as high as `1.0` when full RGB range is
required for a physically checked show. Treat that as available headroom, not a
recommended starting level; the browser still starts at 25% or lower.

Browser-controlled lighting requires both the explicit live command and web
option. It still starts with output stopped and requires confirmation in the
page:

```bash
.venv/bin/phreqed-dmx live --web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --audio-device plughw:CARD=Snowball,DEV=0
```

Live browser output is capped at 25% when first enabled and stops with blackout
if browser heartbeats are absent for five seconds. Keep QLC+ blackout available;
the lease is an additional safeguard, not a substitute for physical controls.

Center-white output is an additional explicit step after browser live starts.
It requires an active microphone and the **Enable physical white peak output**
toggle. The default level is 5% and the default ceiling is 10%. Blackout, Stop
output, render failure, or browser-lease loss disarms it; it never activates in
the simulation-only `web` command or ordinary non-browser live mode.

After low-level commissioning, an operator may explicitly expose a higher
center-white ceiling for one browser-live process. Start conservatively and
raise it only as needed:

```bash
.venv/bin/phreqed-dmx live --web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --audio-device plughw:CARD=Snowball,DEV=0 \
  --white-ceiling 0.40 --acknowledge-high-output-whites
```

Values above 0.10 are rejected without both explicit `live --web` and the
white-specific acknowledgement. The browser shows a persistent warning and
limits the physical slider to the selected ceiling. The onset threshold,
0.10-second pulse limit, 4 Hz limiter, blackout, stop, and lease-loss safeguards
remain active even in elevated mode.

## Test

Tests construct packets and exercise mapping entirely in memory; they need no
QLC+, network access, or DMX hardware:

```powershell
python -m unittest discover -s tests -v
```

## Design

See [architecture](docs/architecture.md) for module boundaries and the exact
pixel map. Contributor and safety rules are in [`AGENTS.md`](AGENTS.md).
