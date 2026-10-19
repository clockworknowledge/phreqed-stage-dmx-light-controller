# Raspberry Pi deployment

## Install

On the Raspberry Pi 5 running Debian Trixie:

```bash
git clone https://github.com/clockworknowledge/phreqed-stage-dmx-light-controller.git
cd phreqed-stage-dmx-light-controller
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
```

Tkinter is needed only for local simulation. If it is absent on Debian, install
the distribution's `python3-tk` package. Live mode itself does not use Tkinter.

## QLC+ and live run

Confirm QLC+ is listening for Art-Net on `127.0.0.1:6454`, universe 0, its
passthrough is enabled, and its output is the intended FTDI FT232R USB-DMX
adapter. Confirm Cube A is A001 and Cube B is A153 in 152-channel mode.
Ensure OLA's `olad` is not also bound to UDP 6454; the reconstructed baseline
records that this conflict previously prevented Python-to-QLC+ Art-Net input.

Keep QLC+'s blackout control immediately available. With fixtures pointed away
from people and no unverified channels enabled, start:

```bash
source .venv/bin/activate
phreqed-dmx live --preset psychedelic-bloom
```

Press Ctrl+C for a handled shutdown. The sender requests one full-universe
blackout before closing, but abrupt termination, power failure, or network
failure cannot guarantee it. Configure an operational blackout procedure in
QLC+ as the final safety layer.

The default command remains safe simulation mode:

```bash
phreqed-dmx simulate
```

Before a performance, run a sustained 25 FPS soak test on the Pi while watching
CPU temperature and QLC+ input stability. Start with `--brightness 0.25` during
fixture validation. Phase 2 defaults retain a hard 0.65 software ceiling, but
that limit is not a substitute for safe fixture placement or QLC+ blackout.
