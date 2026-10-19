# Phreqed Stage DMX Light Controller - Conversation Baseline

This folder contains **reconstructed copies of Python scripts shared in the ChatGPT conversation** as of October 19, 2026. It is **not** a direct download of files from the Raspberry Pi and it has **not** been tested against the fixtures in this environment. If there are later changes on the Pi, preserve and compare those before replacing anything.

## Copy into the Windows Git repo

Target: `D:\DevelopmentClockwork\phreqed-stage-dmx-light-controller`

Extract this ZIP into the repository root. It will add `scripts/` and `docs/`, plus this README. **Review any existing README before overwriting it.** Ideally unzip to a temporary folder first and copy `scripts/` and `docs/` into the repo.

## Tested by user on Raspberry Pi

| Script | Status |
| --- | --- |
| `scripts/phreqed_test.py` | RGB basic Art-Net test worked after OLA stopped competing for UDP port 6454 |
| `scripts/phreqed_map.py` | Sequential zones visibly animated through all 48 zones |
| `scripts/phreqed_wave.py` | Full-grid psychedelic rainbow wave visibly worked |
| `scripts/phreqed_dual_test.py` | Independent control worked after fixing Cube B's start address |
| `scripts/phreqed_visuals_v2.py` | User reported modes likely working, and the pixel chase previously worked well in v1 |
| `scripts/phreqed_sprite.py` | Experimental; looked messy/unrecognizable; not a validated stage effect |
| `scripts/phreqed_smiley.py` | Experimental static diagnostic; no result received yet |

The first five are operational baselines based on user reports, not automated hardware test results.

## Hardware and protocol

- Raspberry Pi 5 / Debian Trixie.
- QLC+ **Art-Net input**, **DMX USB output**, **passthrough enabled**.
- Art-Net destination `127.0.0.1:6454`, Art-Net universe **0** (QLC+ universe 1).
- USB DMX: FTDI FT232R adapter, QLC+ `DMX USB` output (verified by direct QLC+ Simple Desk control).
- Avoid letting OLA's `olad` service bind UDP 6454 alongside QLC+. Previously fixed with `sudo systemctl disable --now olad`.
- Two Betopper LF4808 fixtures, both in **152-channel DMX mode**.
- Cube A: address A001, RGB DMX channels 1-144.
- Cube B: address A153, RGB DMX channels 153-296.
- Each fixture: 48 RGB zones = 8 columns x 6 rows. Viewed from the front, zone 1 is bottom-right; zones progress right-to-left and bottom-to-top.
- Final 8 channels in each 152-channel fixture are **unverified** and left zero.
- Scripts currently use a 512-byte Art-Net DMX payload.

## Running on Raspberry Pi

With QLC+ configured and the fixtures pointed away from eyes:

```bash
python3 scripts/phreqed_dual_test.py
python3 scripts/phreqed_visuals_v2.py
```

The v2 engine uses terminal raw-mode APIs (`termios`, `tty`) available on Linux, **not native Windows**. Do not expect direct execution of the live controller in Windows PowerShell. Build and test a simulator and modular transport separation before attempting Windows support.

V2 shortcuts: `1`-`4` effects, `5` cross-cube chase, `m` mirror, `c` complementary, `i` independent, `n` next Cube B effect, `+`/`-` brightness, `[`/`]` speed, Space blackout, `q` quit.

## Safety / development notes

- Python scripts send actual lighting commands. Don't run while fixtures are pointed toward people.
- Normal termination sends blackout frames, but a power or process failure cannot guarantee blackout. A DMX hold-last-look behavior is possible.
- Fixtures are high-output lighting equipment: ensure heat clearance, ventilation and compatible diffusion materials in cubes.
- Avoid strobe/white-control channels until the fixture's DMX chart is verified.
- `phreqed_visuals_v2.py` is the most complete live-effects starting point. Refactor toward a testable pixel buffer, effect generators and separately mockable Art-Net transport.
- No external Python packages required for these reconstructed scripts.

See `docs/RECONSTRUCTION_NOTES.md` for source fidelity and next steps.
