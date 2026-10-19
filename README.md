# Phreqed Stage DMX Light Controller

A simulation-first Python 3.11+ lighting engine for a Calgary rock band's two
Betopper LF4808 RGB matrix fixtures. It renders effects into logical 8x6 grids,
previews both grids locally, and can explicitly send full 512-channel Art-Net
frames to QLC+.

The reconstructed conversation baseline is preserved unchanged under
`phreqed-stage-dmx-baseline/`. The package implementation reproduces its plasma,
tunnel, pulse, chase, cross-cube chase, and dual-cube operating modes. These
snapshots are not direct Pi exports; see the [baseline inventory](docs/baseline-inventory.md)
and [Pi comparison checklist](docs/pi-script-import.md).

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
phreqed-dmx simulate --effect pulse
phreqed-dmx simulate --effect chase --mode independent --second-effect tunnel
phreqed-dmx simulate --effect cross-cube
```

The preview shows the two cubes from the front with top-left logical origins.

## Run live on the Raspberry Pi

Live network output requires the explicit flag:

```bash
phreqed-dmx live --effect plasma --mode mirror
```

Do this only after checking QLC+, fixture modes, addresses, physical safety, and
the operator blackout control. On handled shutdown, the app sends a best-effort
blackout. See [Raspberry Pi deployment](docs/raspberry-pi-deployment.md).

Both commands accept `--brightness 0.35` and `--speed 1.0`. Supported effects
are `plasma`, `tunnel`, `pulse`, `chase`, and `cross-cube`; supported two-cube
modes are `mirror`, `complementary`, and `independent`. With no command, the CLI
defaults to simulation. `live` can only be selected explicitly.

## Test

Tests construct packets and exercise mapping entirely in memory; they need no
QLC+, network access, or DMX hardware:

```powershell
python -m unittest discover -s tests -v
```

## Design

See [architecture](docs/architecture.md) for module boundaries and the exact
pixel map. Contributor and safety rules are in [`AGENTS.md`](AGENTS.md).
