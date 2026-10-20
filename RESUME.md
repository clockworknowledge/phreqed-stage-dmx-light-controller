# Codex Resume: Browser Control Validation

Last updated: 2026-10-20

This is the short operational handoff for a new Codex session. Read
`AGENTS.md`, this file, and `docs/kanban.md` before taking action. The detailed
design remains in `docs/architecture.md`, `docs/effects.md`, and
`docs/raspberry-pi-deployment.md`.

## Objective in progress

Integrate and validate the recovered browser show controller, persistent user
look library, and timed scene sequencer without making live output automatic.
The underlying Phase 2 Raspberry Pi, QLC+, soak, and controlled fixture
commissioning checks are complete within their documented scope.

Do not start live Art-Net output merely to inspect the installation.

## Latest checkpoint — recovered Pi development branch

The Pi-only work was preserved on
`pi-recovery-before-sync-20261020` and reviewed on Windows. It adds browser
preview/control, versioned atomic user-look and scene persistence, deterministic
scene sequencing, Pi diagnostic scripts, the managed QLC+ unit, and complete
commissioning evidence. The recovery branch passes all 82 automated tests under
Python 3.12 with `PYTHONPATH=src`; simulation tests prove that browser actions
cannot construct an Art-Net sender. The recovered work is integrated locally
and awaits the guarded Pi update and browser validation described below.

## Prior checkpoint — LAN restriction and boot enablement

### Post-reboot verification — 2026-10-19 21:18 MDT

The scheduled reboot completed. Boot ID changed to
`5220faf7-fa68-446e-b7bd-287e4c2747cc`; boot time is 21:16:07 MDT.
QLC+ started at 21:16:20, enabled and active, with one process (PID 1483),
`NRestarts=0`, the expected `mmorley` user, HOME, and runtime workspace.
Installed unit and runtime workspace both compare equal to repository copies.
QLC+ solely owns UDP 6454 and TCP 9999. HTTP returned 200 over IPv4/IPv6
localhost and `192.168.1.89`; its own global IPv6 address timed out (curl
exit 28). Effective IP allow/deny properties match the configured restrictions.
No live controller process was present. All 57 tests passed using
`.venv/bin/python -m unittest discover -s tests -v` (0.134 seconds).
The system Python lacks the installed package; use the project virtualenv.

Software startup checks passed. The operator confirmed both fixtures stayed
dark through reboot; reboot verification has passed. No live output, restart,
or service configuration change was performed in the reboot verification.
Resume with the remaining acceptance checks; do not repeat the reboot merely
to inspect status.

Recovery was repeated at 21:21:36 MDT with live output off and the operator
asked to observe both fixtures. SIGKILL of verified service PID 1483 triggered
automatic restart at 21:21:41 (PID 2207, `NRestarts=1`, active/running).
QLC+ recovered sole ownership of both ports and HTTP 200; the runtime workspace
still matches Git. The operator confirmed both fixtures stayed dark during
this recovery, completing that check. The operator also confirmed the port
9999 web UI opens on a phone and computer. No live controller was started.
The operator subsequently confirmed the global IPv6 URL was denied from
another device while the standard IPv4 LAN URL still worked, completing the
planned independent permitted/denied browser checks. QLC-002 is Done.
The service and commissioning evidence were committed in `7f6faee`;
LIVE-001, RPI-002, DEPLOY-001, and P2-VAL-001 are also Done.
Raspberry Pi commissioning is complete within the documented test scope.

The following is the retained pre-reboot checkpoint; its pending-reboot
statements are superseded by the verification above.

This checkpoint supersedes earlier disabled-at-boot and isolation-pending
observations below. QLC+ is active and enabled at boot. Its installed unit
matches `config/qlc/qlcplus.service` and now restricts IP traffic to localhost
(IPv4 and IPv6) and the current IPv4 LAN `192.168.1.0/24` using systemd cgroup
IP filtering. The Pi kernel enables BPF syscall and cgroup BPF support.
The nftables ruleset was confirmed empty; no host-wide firewall was changed.
The original unit is backed up at
`/etc/systemd/system/qlcplus.service.before-lan-restriction`.

Verification after the restriction: HTTP 200 from `127.0.0.1`, `::1`, and
`192.168.1.89`; a request to the Pi's own global IPv6 address timed out.
Systemd shows allow entries `127.0.0.0/8`, `::1/128`, `192.168.1.0/24` and
deny entries `0.0.0.0/0`, `::/0`. QLC+ retains sole ownership of UDP 6454
and TCP 9999. These are local-host probes, not independent external tests.
The unauthenticated web UI is available to the allowed LAN; change the allowed
subnet before moving the Pi to a different network. This filter covers QLC+
traffic only, not SSH or other services.

The next action is a controlled reboot and post-boot verification. Before
reboot, boot ID is `e4d1c257-d53f-4745-9471-14f3eb6051c4`.
After reconnecting, verify a changed boot ID, enabled/active `qlcplus.service`,
a single QLC+ process, expected user/HOME/workspace and IP allow/deny settings,
sole port ownership, HTTP 200 locally and from the LAN, and no automatic
`phreqed-dmx live` process. Recheck the denied IPv6 probe and ask the operator
whether both fixtures stayed dark through reboot. Do not start a live check
merely to verify boot. Reboot verification has not yet passed.

The controlled reboot was scheduled successfully for 2026-10-19 21:15:56 MDT
using `sudo shutdown -r +1`. After reconnecting, perform the checks above;
do not infer boot success from the scheduling command.

## Verified repository state

- The Phase 2 engine, simulator, effects, compositor, show-control interfaces,
  tests, documentation, and independent Pi deployment scripts are implemented.
- The integrated recovery branch passes all 82 tests under Python 3.12.
- `scripts/pi-install.sh` creates `.venv`, installs the package, and runs tests.
- `scripts/pi-update.sh` accepts only a clean `main` checkout and a fast-forward
  from `origin/main` before reinstalling and testing.
- The imported baseline directory and ZIP remain immutable.
- The known-good QLC+ workspace is now stored at
  `config/qlc/phreqed_qlc_workspace.qxw`.
- The workspace is valid XML and contains no password, token, API key, private
  path, or web-auth credential fields.
- Its QLC+ configuration records:
  - workspace creator version 4.14.1;
  - universe 0 (`Universe 1`) with passthrough enabled;
  - Art-Net input at `127.0.0.1`, line/universe 0;
  - DMX USB output through `FT232R USB UART (S/N: BH00M7BV)`.

The FTDI serial is a machine-specific device identifier, not an authentication
secret. Keep QLC+ password/authentication files outside Git.

## Verified Raspberry Pi state

- Hostname: `raspberrypi`
- Last observed address: `192.168.1.89` (may change if DHCP changes it)
- User: `mmorley`
- Repository: `/home/mmorley/phreqed-stage-dmx-light-controller`
- SSH access works.
- QLC+ was observed running as:

  ```text
  qlcplus -platform offscreen --nowm --web --operate --open /home/mmorley/.qlcplus/autostart.qxw
  ```

- QLC+ returned HTTP 200 on local TCP port 9999.
- QLC+ owned UDP port 6454 for Art-Net input.
- `/home/mmorley/.qlcplus/autostart.qxw` is the runtime workspace.
- `/etc/systemd/system/qlcplus.service` is enabled and successfully restarted
  QLC+ after a Pi reboot. It runs as `mmorley`, requires the runtime workspace,
  restarts on failure, and uses the already-proven offscreen command.
- The service uses systemd IP filtering: deny all by default, then allow
  loopback and `192.168.1.0/24`. Update this rule before moving the Pi to a
  different subnet.
- QLC+ web access is unauthenticated but restricted to the trusted LAN by the
  service. Do not expose TCP 9999 through a router or public network.
- The service log contains only the expected QLC+ 4.14.1 startup messages and a
  harmless Qt fallback because `XDG_RUNTIME_DIR` is unset.
- After reboot the Pi reported 4 GiB RAM with about 3.5 GiB available, 2 GiB
  unused swap, and 17 GiB free on the root filesystem.
- Persistent systemd journaling is now enabled at `/var/log/journal`; its first
  recorded boot used about 8 MiB. Future reboot/crash investigations can use
  `journalctl -b -1`.
- Managed stop/start, automatic failure recovery, reboot startup, permitted LAN
  access, denied global IPv6 access, and physical darkness during QLC+ restart
  and reboot were subsequently verified. The detailed evidence is retained in
  the commissioning history below.

## Pi Codex/SSH incident

An interactive Codex CLI attempt on the Pi was followed by an unresponsive SSH
service. The host still answered ping and accepted TCP port 22 connections, but
never sent the SSH protocol banner. QLC+ port 9999 also continued listening.
The Pi was rebooted and recovered normally.

The root cause is unknown because the previous boot used volatile journals.
There is no evidence proving an out-of-memory event, thermal fault, storage
error, or Codex defect. After reboot no `codex` or `node` process remained and
resource use was normal. Do not reproduce the failure merely to investigate it.
Keep Codex on the Windows development computer and use SSH for Pi deployment
until persistent logs capture any natural recurrence.

## Not yet verified

- The planned QLC+ reboot, recovery, and permitted/denied network browser
  checks passed. Broader router/firewall coverage was not tested.
- Tkinter drawing has not completed a sustained Raspberry Pi GUI soak test;
  the headless rendering soak below has passed.
- Full per-pixel verification has not been performed; the controlled physical
  smoke test, normal shutdown blackout, and Ctrl+C blackout passed below.
- The new Phreqed browser controller, persistent user-look library, and timed
  scene sequencer pass 82 automated tests on Windows but have not yet completed
  a browser smoke test or guarded live test on the Pi.
- The original source files from the Raspberry Pi have not been imported and
  compared with the preserved reconstructed baseline.
- The eight unverified channels on each fixture remain intentionally unmapped.

## Commissioning history — 2026-10-19

The following records intermediate states; the latest checkpoint above
supersedes historical pending checks and disabled-at-boot observations.

- Running directly on `raspberrypi`, Raspberry Pi 5 Model B Rev 1.1,
  Debian 13.7 (Trixie), aarch64, Python 3.13.5.
- Steps 1 and 2 below are complete: `main` and `origin/main` both resolve to
  `36ab1e5`. The local QLC+ workspace matched the incoming Git copy; its backup
  is `/tmp/phreqed-qlc-backup.eXbL3R/phreqed_qlc_workspace.qxw` (temporary storage).
- Step 3 is complete: the runtime workspace was missing. Restored it from the
  committed master without overwriting an existing file; `cmp` exited 0.
  QLC+ was left running, so this does not verify its currently loaded workspace.
- Initially QLC+ PID 3328 owned UDP 6454 and TCP 9999 and returned HTTP 200.
  Both listeners use wildcard addresses; `olad` is disabled.
- Step 4 is partially verified: after operator confirmation of blackout and
  safe restart conditions, installed `config/qlc/qlcplus.service` into
  `/etc/systemd/system/qlcplus.service`. Syntax verification passed. Gracefully
  stopped the unmanaged process, then started QLC+ through systemd. A managed
  stop exited 0 and released both ports; a subsequent start restored UDP 6454
  and HTTP 200 on TCP 9999. The service runs as `mmorley`, sets the specified
  HOME, and uses the runtime workspace. It remains disabled at boot.
  Reboot, physically observed retained-output
  behavior, and stage LAN isolation still require validation. Do not assume
  blackout survives a QLC+ restart; recheck it in the web UI.
- Step 5 is complete: `bash scripts/pi-install.sh` exited 0, installed version
  0.2.0 into `.venv`, and passed all 57 tests (0.153 seconds).
  `.venv/bin/phreqed-dmx --help` also exited 0. The installer needed host network
  access because the sandbox could not resolve package indexes.
- No live Art-Net controller was started and no baseline files were modified.

The statement above describes the simulation-only commissioning phase. After
the user explicitly authorized a live check and confirmed safe fixture
placement, warning nearby people, and access to QLC+ blackout, ran:

```bash
.venv/bin/phreqed-dmx live --effect plasma --speed 0.2 --brightness 0.25 --duration 15
```

The 15-second run announced universe 0 at `127.0.0.1:6454`, 25 FPS, and exited
0. The normal sender shutdown path requested a complete-universe blackout.
The operator confirmed both cubes came on and went dark when the run ended.
They thought there was some movement, but it was very slow; movement is not
treated as conclusively verified. This confirms initial physical response and
normal timed-shutdown blackout. Independent addressing, front-view orientation,
and handled-interruption blackout were still unchecked at that stage.
No live process remains running.

The next authorized check ran `scripts/fixture-check.py live`: 24 seconds
of red top-left / blue bottom-right markers, Cube A then Cube B, one pixel on
one cube at a time, with blackout between markers and on shutdown. Brightness
was 0.25 with the compositor and safety limiter retained at 25 FPS. Offline
validation confirmed exact one-based channels 142, 3, 294, and 155 with value
64, every other channel zero. The process exited 0, and the operator confirmed
all positions, colours, isolation, and final blackout were correct. LIVE-001
has passed its controlled smoke check and awaits documentation review/commit.
Full per-pixel verification has not been performed. No live process remains
running.

The subsequent authorized Ctrl+C check used the same slow plasma command at
brightness 0.25, speed 0.2, and 25 FPS, with a 15-second fallback duration.
Sent Ctrl+C through the terminal during the run. The controller printed
`Interrupted; live mode requested a blackout before closing.` and exited 0.
The operator confirmed both cubes went dark. Physical handled-interruption
blackout therefore passed. No live process remains running.

Step 6 passed for headless rendering: `scripts/pi-soak.py` completed all
19 effects and four presets, 30 seconds each, at 25 FPS. Across 17,250 frames
there were zero missed slots or render overruns. Slowest preset was
`molten-motion` (mean 9.191 ms, maximum 11.971 ms against a 40 ms budget).
Peak RSS was 25,488 KiB and CPU temperature 50.7 C. Every look passed reserved
channel and in-memory blackout checks. Sockets were blocked throughout.
Raw evidence: `docs/validation/pi-soak-2026-10-19.json`; detailed limits and
measurements are in the Phase 2 report. GUI, transport, and physical output
were excluded.

Resume with the remaining step 4 checks; step 5 need not be repeated unless
the code or environment changes. RPI-002 passed with the socket-blocked
headless harness and awaits review/commit. A single live check was explicitly
authorized and completed as recorded above, followed by the confirmed
independent-fixture corner check. LIVE-001 passed and awaits review/commit.
QLC+ automatic failure recovery passed on 2026-10-19: with live output off,
sent SIGKILL to the service's user-owned main process (PID 5010). The journal
recorded failure at 21:10:15 MDT and restart at 21:10:20. Systemd reported
`NRestarts=1`, new PID 6045, and active/running. UDP 6454 and TCP 9999 returned
to sole QLC+ ownership; a retry after startup returned HTTP 200. The runtime
workspace still matches Git. Physical darkness across this QLC+ failure and
restart has not been separately confirmed by the operator.

Boot startup remains disabled. No conflicting launch entries were found in
the inspected system/user units, desktop autostart, shell startup files,
system cron locations, or user crontab. Missing startup directories were
reported explicitly; this is not an exhaustive audit of every launch mechanism.
The current boot ID is `e4d1c257-d53f-4745-9471-14f3eb6051c4`, boot time
2026-10-19 17:19:58 local. Compare the boot ID after an eventual reboot.

Administrative checks now require fresh sudo authentication: `sudo -n -l`,
firewall inspection, and `sudo -n systemctl kill` returned password-required.
The successful failure test used ordinary ownership permission to signal
QLC+, not sudo. No boot or firewall configuration was changed. The Pi is on
192.168.1.0/24 and has a global IPv6 address; QLC+ listens on wildcard
addresses. IPv4 and IPv6 network isolation are not established. Inspect the
firewall/router policy before boot enablement or acceptance for stage use.

Commissioning acceptance passed, including reboot/recovery darkness and
other-device permitted IPv4 LAN access / denied global IPv6 browser access.
See the deployment guide for
the service installation and validation procedure.

## Important Git handoff detail

The QLC+ workspace originated as an untracked file in the Pi checkout and was
copied to the development checkout for review. After the commit containing the
workspace is pushed, the Pi may refuse to pull because its untracked file would
be overwritten. Preserve it outside the repository before pulling:

```bash
cd /home/mmorley/phreqed-stage-dmx-light-controller
mkdir -p /home/mmorley/phreqed-local-backups
mv config/qlc/phreqed_qlc_workspace.qxw \
  /home/mmorley/phreqed-local-backups/phreqed_qlc_workspace-before-git.qxw
git pull --ff-only origin main
cmp config/qlc/phreqed_qlc_workspace.qxw \
  /home/mmorley/phreqed-local-backups/phreqed_qlc_workspace-before-git.qxw
```

`cmp` exits silently with status 0 when the files are identical. Do not delete
the backup until the committed file and runtime configuration are verified.

## Next actions, in order

1. Merge and push the reviewed `pi-recovery-before-sync-20261020` work, then
   update the Pi only through the guarded deployment workflow.
2. Confirm the runtime workspace still matches the committed master:

   ```bash
   cmp /home/mmorley/phreqed-stage-dmx-light-controller/config/qlc/phreqed_qlc_workspace.qxw \
     /home/mmorley/.qlcplus/autostart.qxw
   ```

3. Run the complete 82-test suite on the Pi after updating the package.
4. Start browser simulation only, verify both previews and persistence from a
   trusted LAN device, and confirm that no Art-Net sender is created.
5. Validate browser-controlled live output separately, only with QLC+ blackout
   available and the fixtures safely positioned; confirm the five-second lost-
   browser lease blackouts the output.
6. Do not repeat completed installation, soak, live, reboot, or recovery checks
   unless a relevant code, configuration, or environment change justifies it.
7. Update the service's allowed subnet and recheck network access before moving
   the Pi to another network. Live output still requires explicit selection.

## Safety invariants

- Simulation remains the default; live transmission requires the literal
  `live` command.
- Never probe or activate fixture channels 145-152. In the 512-channel universe
  these are 145-152 for Cube A and 297-304 for Cube B.
- Cube A remains at A001 and Cube B at A153, both in 152-channel mode.
- Keep the software brightness ceiling at 0.65 and begin hardware validation at
  0.25 or lower.
- Do not enable automatic startup of `phreqed-dmx live` until the manual smoke
  test and shutdown blackout checks have passed.
- Do not edit, import, execute, or reformat files under
  `phreqed-stage-dmx-baseline/` or its ZIP archive.

## Suggested prompt for a new Codex session

```text
Read AGENTS.md, RESUME.md, and docs/kanban.md completely. Verify git status,
hostname, the active QLC+ process, ports 6454 and 9999, and the Python test
environment before changing anything. Continue the Raspberry Pi commissioning
work from the first incomplete item in RESUME.md. Do not start live Art-Net or
modify the baseline. The workspace is already tracked; the older Git handoff
section is retained only for checkouts predating its first commit.
```
