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

## Prepared headless QLC+ service

`config/qlc/qlcplus.service` uses the observed working offscreen command, runs
as `mmorley` with `HOME=/home/mmorley`, and loads the runtime workspace at
`/home/mmorley/.qlcplus/autostart.qxw`. It restarts after a process failure,
with a limit of three starts per minute. It never starts the Python controller.
The unit passed `systemd-analyze verify` and a managed stop/start on the Pi
on 2026-10-19. It is installed, running, and now enabled at boot.
Automatic process-failure recovery also passed: systemd restarted QLC+ after
five seconds and its ports/web UI recovered. Local checks of service IP filtering
also passed. Reboot verification passed, including operator-confirmed darkness
of both fixtures. The operator also confirmed darkness during process-failure
recovery and web access from a phone and computer.

Before installing or starting it, activate QLC+ blackout and confirm fixtures
are safe for a restart. Confirm the runtime file matches the committed master:

```bash
cmp config/qlc/phreqed_qlc_workspace.qxw /home/mmorley/.qlcplus/autostart.qxw
systemd-analyze verify config/qlc/qlcplus.service
```

With blackout confirmed, install the unit:

```bash
sudo install -m 0644 config/qlc/qlcplus.service /etc/systemd/system/qlcplus.service
sudo systemctl daemon-reload
```

Identify the existing unmanaged QLC+ PID with `pgrep -a -x qlcplus` and stop
that process gracefully before starting the service. Do not run two instances
against the USB adapter or UDP 6454. Start with `sudo systemctl start qlcplus`
and inspect `systemctl status qlcplus --no-pager`,
`journalctl -u qlcplus --no-pager -n 50`, and
`ss -luntp 'sport = :6454 or sport = :9999'`.
Verify HTTP 200 from `http://127.0.0.1:9999` and recheck blackout in the web UI.

This command enables unauthenticated web access and listens on wildcard
addresses. The service now filters QLC+ IP traffic using `IPAddressDeny=any`
with exceptions for localhost (IPv4/IPv6) and `192.168.1.0/24`. Update the
allowed subnet before moving to another network. The filter requires cgroup
BPF support; check startup logs and permitted/denied requests after installation.
It does not change SSH or the host-wide firewall. Localhost and LAN HTTP
returned 200 on this Pi; its own global IPv6 HTTP probe timed out. External-host
filter checks remain separate verification. Authentication can still be added
outside Git. Only enable boot startup
with `sudo systemctl enable qlcplus` after safe stop/restart and retained-output
checks. Reboot and recovery tests remain separate acceptance checks; syntax
validation does not establish safe fixture behavior.

The current deployment is enabled for boot; post-reboot software checks passed
on 2026-10-19 at 21:18 MDT. QLC+ started automatically with the expected user,
HOME, workspace, sole port ownership, and IP restrictions. Localhost and the
Pi's LAN-address HTTP probes returned 200; its own global IPv6 probe timed out.
No live controller was running. The operator confirmed both fixtures stayed
dark through reboot and process-failure recovery, completing both checks, and
confirmed web access from a phone and computer. Independent denial checks
from outside the allowed subnet remain untested.
For future reboot verification:
After reconnecting, compare `/proc/sys/kernel/random/boot_id` with the prior ID
in `RESUME.md`, then check enabled/active state, one QLC+ process, allow/deny
properties, expected ports and HTTP responses, and absence of automatic live
lighting output. Confirm physically that both fixtures stayed dark.

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

## Headless simulation-only soak test

From the repository root after installation:

```bash
.venv/bin/python scripts/pi-soak.py --output /tmp/phreqed-pi-soak.json
```

The default run takes about 11.5 minutes: 30 seconds each for all 19 effects
and four presets at the configured 25 FPS. `--seconds-per-look` changes the
duration. Each look renders both fixtures through the safety limiter and
serializes a 512-channel payload in memory. Python sockets and the application's
Art-Net sender constructor are blocked throughout the run; QLC+ is not needed.
The harness checks unmapped channels and an in-memory blackout for every look.

The JSON report records achieved FPS, missed schedule slots, render time,
process CPU use relative to one core, Linux resident memory, and CPU temperature
when available. Each result is saved as it completes. A complete successful
report includes `completed_utc` and `passed: true`; timing failures exit nonzero.
This is a rendering soak test, excluding Tkinter drawing, Art-Net, QLC+ output,
USB-DMX, and physical shutdown blackout. It does not replace the controlled
hardware smoke test.
