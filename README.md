# Phreqed Stage DMX Light Controller

A simulation-first Python 3.11+ visual engine for a Calgary rock band's two
Betopper LF4808 RGB matrix fixtures. It provides deterministic procedural
effects, normalized RGB layer compositing, presets, an interactive two-cube
simulator, and explicit live 512-channel Art-Net output through QLC+.

To continue deployment or development in a fresh Codex session, start with the
[current resume](RESUME.md), then read [`AGENTS.md`](AGENTS.md) and the
[project Kanban](docs/kanban.md).

The reconstructed conversation baseline is preserved unchanged under
`phreqed-stage-dmx-baseline/`. The package retains its plasma, tunnel, pulse,
chase, and cross-cube chase while adding fifteen advanced effects. These
snapshots are not direct Pi exports; see the [baseline inventory](docs/baseline-inventory.md)
and [Pi comparison checklist](docs/pi-script-import.md).

## Phase 2 capabilities

- 19 registered effects with validated metadata and deterministic output
- spectrum, magma, ocean, neon, ember, and monochrome palettes
- alpha, additive, and lighten layers with opacity and masks
- independent per-cube effects or continuous cross-cube effects
- four example multi-layer presets
- conservative global brightness ceiling and frame-rise limiter
- transport-independent blackout, preset, event, tap-tempo, and navigation APIs
- interactive Tk simulator with live FPS, pause, step, parameters, and PPM export

See the complete [effect catalog](docs/effects.md) and
[Phase 2 implementation report](docs/phase-2-implementation-report.md). Feature
status and upcoming work are tracked on the [project Kanban](docs/kanban.md).

## Hardware configuration

- Art-Net target: `127.0.0.1:6454`, universe 0
- QLC+ passthrough to an FTDI FT232R USB-DMX adapter
- Cube A: 152-channel mode, starts at DMX 1
- Cube B: 152-channel mode, starts at DMX 153
- 48 RGB zones per cube; front-view zone 1 is bottom-right
- zones advance right-to-left, then bottom-to-top
- the last eight channels on each cube are unverified and always remain zero

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

Both commands accept `--brightness` up to the 0.65 safety ceiling and `--speed`.
Use `--effect` for manual mode, with `--mode mirror|complementary|independent`
and `--second-effect` where needed. Run `phreqed-dmx --help` for the complete
effect and preset lists. With no command, the CLI defaults to simulation;
network output can only be selected with the literal `live` command.

## Test

Tests construct packets and exercise mapping entirely in memory; they need no
QLC+, network access, or DMX hardware:

```powershell
python -m unittest discover -s tests -v
```

## Design

See [architecture](docs/architecture.md) for module boundaries and the exact
pixel map. Contributor and safety rules are in [`AGENTS.md`](AGENTS.md).
