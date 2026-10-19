# Raspberry Pi deployment

## Independent terminal deployment

The deployed controller does not require Codex, ChatGPT, VS Code, or a
connection to the Windows development computer. GitHub carries the source and
the checked-in scripts perform installation, validation, and later updates.

## First installation

On the Raspberry Pi 5 running Debian Trixie:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
git clone https://github.com/clockworknowledge/phreqed-stage-dmx-light-controller.git
cd phreqed-stage-dmx-light-controller
bash scripts/pi-install.sh
```

The installer requires Python 3.11 or newer, creates `.venv`, installs the
package, and runs the complete hardware-free test suite. It stops immediately
if installation or a test fails.

Tkinter is needed only for local simulation. If it is absent on Debian, install
the distribution's `python3-tk` package. Live mode itself does not use Tkinter.

## Updating an existing clean checkout

Push and review changes on the development computer first. Then, on the Pi:

```bash
cd ~/phreqed-stage-dmx-light-controller
bash scripts/pi-update.sh
```

The updater refuses to run when the checkout has modified or untracked files,
requires the `main` branch, fetches `origin/main`, permits only a fast-forward,
and reruns installation and all tests. This protects Pi-only diagnostic scripts
from accidental replacement. Preserve any such files outside the checkout or
follow `docs/pi-script-import.md` before updating.

## QLC+ and live run

Confirm QLC+ is listening for Art-Net on `127.0.0.1:6454`, universe 0, its
passthrough is enabled, and its output is the intended FTDI FT232R USB-DMX
adapter. Confirm Cube A is A001 and Cube B is A153 in 152-channel mode.
Ensure OLA's `olad` is not also bound to UDP 6454; the reconstructed baseline
records that this conflict previously prevented Python-to-QLC+ Art-Net input.

Keep QLC+'s blackout control immediately available. With fixtures pointed away
from people and no unverified channels enabled, start:

```bash
.venv/bin/phreqed-dmx live --preset psychedelic-bloom
```

Press Ctrl+C for a handled shutdown. The sender requests one full-universe
blackout before closing, but abrupt termination, power failure, or network
failure cannot guarantee it. Configure an operational blackout procedure in
QLC+ as the final safety layer.

The default command remains safe simulation mode:

```bash
.venv/bin/phreqed-dmx simulate
```

Before a performance, run a sustained 25 FPS soak test on the Pi while watching
CPU temperature and QLC+ input stability. Start with `--brightness 0.25` during
fixture validation. Phase 2 defaults retain a hard 0.65 software ceiling, but
that limit is not a substitute for safe fixture placement or QLC+ blackout.
