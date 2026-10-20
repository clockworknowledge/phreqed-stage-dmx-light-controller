# Phase 2 implementation report

## Delivered

- A normalized RGB pipeline with DMX quantization only at the output boundary.
- A deterministic effect contract with metadata, typed validated parameters,
  fixture identity, and optional performance context.
- Fifteen requested advanced procedural effects and four legacy-preservation
  effects, all dependency-free.
- A compositor with alpha, additive, and lighten blending; layer opacity;
  per-fixture targeting; radial masks; global limits; and pure crossfades.
- A configurable stateful limiter for large repeated full-frame luminance rises.
- Four example multi-layer presets.
- Transport-independent show commands for effect and parameter changes, preset
  activation, events, blackout, tap tempo, and scene navigation.
- An interactive two-cube Tk simulator with dynamic parameters, independent
  cube effects, speed and brightness, FPS display, pause/resume, stepping,
  blackout, and dependency-free PPM screenshot export.
- A dependency-free browser controller with dual-cube previews, look editing,
  atomic versioned persistence, ordered scenes, timed playback, tap tempo, and
  blackout controls.
- A strict browser output gate: `web` is simulation-only, `live --web` only
  permits later in-page activation, first activation is limited to 0.25, and a
  five-second lost-browser lease closes live output with blackout.
- Explicit scene versus DMX rendering paths. Simulation never constructs the
  Art-Net sender.

## Verification

- 82 automated tests pass on Python 3.12 after browser control, persistent user
  looks, and deterministic scene sequencing were integrated.
- A real Tk smoke run constructed two 48-cell grids and both parameter panels.
- The deadline scheduler measured 25.0 FPS over a 2.2-second local GUI run.
- On the Windows development machine, the slowest single-effect two-cube frame
  averaged 5.151 ms (`sparks`); the 25 FPS budget is 40 ms. Raspberry Pi
  measurements are recorded below.
- Existing fixture mapping, packet, blackout, baseline-effect, and no-network
  simulation tests continue to pass.
- Browser boundary tests cover same-origin/token checks, request limits, live
  gating, watchdog blackout, reserved channels, persistence, and failure paths.
- The imported baseline hashes remain the acceptance reference and are checked
  again at final handoff.

## Remaining risks and follow-up

- Physical plasma response, independent addressing, diagonal endpoint
  orientation, normal shutdown blackout, and handled-interruption blackout
  passed below. The old endpoint test did not establish row width; the corrected
  12-by-4 geometry still needs a physical row-transition check.
- Raspberry Pi headless timing and thermal results are recorded below;
  sustained GUI and complete live-chain behavior remain unverified.
- The recovered browser controller passes Windows and Pi tests, and its Pi
  trusted-LAN simulation preview was operator-accepted. A basic guarded
  browser-live check was also reported working, but persistence/restart and
  physical observation of its disconnect blackout remain pending.
- The actual current Pi files still need comparison with the reconstructed
  conversation baseline.
- Preset, effect, and palette changes crossfade over 0.45 seconds in the
  simulator. Parameter sliders remain immediate for responsive tuning.
- Tap tempo and event context are defined and tested; automatic audio analysis
  is intentionally out of scope.
- PPM export avoids dependencies; PNG export would require either a platform
  conversion step or an image library.
- Foot-controller drivers and video-to-RGB mapping remain future work.
- The eight unverified fixture channels remain zero and inaccessible.

## Post-integration Pi verification — 2026-10-20

The recovered Pi branch was reconciled with `main` in merge commit `67004ad`
without changing the preserved baseline. `scripts/pi-update.sh` fast-forwarded
the Pi, reinstalled the package, and passed all 82 hardware-free tests in
0.299 seconds.

The operator opened simulation-only browser control from the trusted LAN and
confirmed the dual-fixture preview and controls looked correct. That command
did not permit live activation. After stopping it, the operator ran the direct
controller for ten seconds with plasma at speed 0.2 and brightness 0.15. Both
cubes illuminated with visible animation and returned to darkness on normal
shutdown. This confirms the pre-existing direct live path after integration;
formal browser-controlled explicit-stop, blackout, and heartbeat-loss behavior
still require their own controlled physical validation.

The operator subsequently reported that the basic guarded browser controller
worked against the fixtures. That check exposed the incorrect 8-by-6 visual
geometry. It does not by itself complete the persistence/restart or lost-
heartbeat blackout acceptance checks.

## LF4808 geometry correction — 2026-10-20

The operator identified the physical RGB zone layout as 12 columns by 4 rows,
not the 8-by-6 layout assumed by the reconstructed baseline. Both layouts place
zone 48 at top-left and zone 1 at bottom-right, so the earlier two-corner test
could verify endpoints, RGB order, fixture isolation, and blackout without
distinguishing the row width. The package and previews now model a 12-by-4
front view while preserving the original baseline files unchanged.

Automated mapping coverage includes every row transition. Physical acceptance
remains pending until a low-brightness check observes a marker crossing from
zone 12 to zone 13 independently on Cube A and Cube B. The final eight channels
per fixture remain zero and are not involved in this correction. All 82 Windows
tests, JavaScript syntax checking, Python compilation, and the socket-free
eight-frame diagnostic pass on the correction branch.

## Raspberry Pi commissioning — 2026-10-19

Verified directly on `raspberrypi`, a Raspberry Pi 5 Model B Rev 1.1 running
Debian 13.7 (Trixie), aarch64, Python 3.13.5. The starting checkout was
`36ab1e5` on `main`, matching `origin/main`.

### Installation

`bash scripts/pi-install.sh` exited 0, installed package version 0.2.0 into
`.venv`, and passed all 57 hardware-free tests (0.153 seconds).
`.venv/bin/phreqed-dmx --help` exited 0. Package index access required running
the installer outside the network-restricted sandbox.

### QLC+ service

The runtime workspace was missing despite being named in the existing QLC+
command line. Restored it from the reviewed master and confirmed byte equality
with `cmp`. After operator confirmation that blackout was active and fixtures
were safe for a restart, installed the reviewed `config/qlc/qlcplus.service`.
`systemd-analyze verify` passed on the Pi. The unmanaged process was gracefully
stopped before the service started.

The service runs as `mmorley`, sets `HOME=/home/mmorley`, and loads
`/home/mmorley/.qlcplus/autostart.qxw` using QLC+ 4.14.1's existing offscreen
command. A managed stop completed with status 0 and released both listeners.
A subsequent start restored sole ownership of UDP 6454 and TCP 9999 and
HTTP 200 from the local web UI. OLA remains disabled.

The service is running but disabled at boot. Reboot startup,
physical blackout retention across restart, and stage LAN
isolation remain unverified. Web access is unauthenticated and listens on
wildcard addresses. No Python live controller was started. This validates
process management, not physical output or shutdown blackout.

### Headless 25 FPS soak (RPI-002)

Command:

```bash
.venv/bin/python scripts/pi-soak.py --output docs/validation/pi-soak-2026-10-19.json
```

The run lasted 690 seconds (11.5 minutes), exercised all 19 registered effects
and four example presets, and exited 0. Each of the 23 looks rendered 750
two-cube frames at 25.0 FPS: 17,250 frames total, with zero missed schedule
slots and zero frames exceeding the 40 ms rendering budget.

The slowest effect was `sparks`: mean 8.973 ms, p95 9.133 ms, maximum
9.849 ms. The slowest preset was `molten-motion`: mean 9.191 ms, p95
9.894 ms, maximum 11.971 ms. Even the largest measured frame left about
28 ms of the frame interval unused. Peak process CPU consumption was
23.11% of one core (Molten Motion), including validation and metric sampling.

Resident memory grew from 24,672 KiB on the first sample to 25,488 KiB at
completion (also the sampled maximum). Most growth occurred during the first
few looks; the later samples stayed around 25 MiB without sustained large
growth. These one-second samples over 11.5 minutes do not establish long-term
leak freedom. Highest sampled CPU temperature was 50.7 C.

Every frame had 512 channels, with all unverified and unmapped channels zero.
Every look produced an all-zero in-memory blackout at completion. Python
socket creation and the application's Art-Net sender constructor were blocked
for the entire run. The test rendered both fixtures through `Controller`,
the safety limiter, compositor, and DMX serialization. It did not run Tkinter,
transmit Art-Net, exercise USB-DMX output, or observe physical blackout.
QLC+ remained running independently and was healthy after the run.

Raw per-look measurements and completion status are in
`docs/validation/pi-soak-2026-10-19.json`. Repeat with `--seconds-per-look`
for a longer session. No effect optimization or FPS increase was needed.

### Initial timed live check (LIVE-001, partial verification)

After explicit operator authorization and confirmation of safe fixture
placement, warning nearby people, and immediate QLC+ blackout access, ran:

```bash
.venv/bin/phreqed-dmx live --effect plasma --speed 0.2 --brightness 0.25 --duration 15
```

The process announced Art-Net universe 0 at `127.0.0.1:6454`, 25 FPS, and
exited 0 after the timed run. Its normal shutdown path requested a full-universe
blackout. The exact look was first checked offline for 375 frames: 512-channel
payloads, reserved channels zero, maximum channel value 22/255.
The operator observed both cubes come on and go dark when the run ended,
confirming initial physical response and normal timed-shutdown blackout.
They thought some movement was visible but noted that it was very slow;
animation behavior is not treated as conclusively verified.
Independent addressing and front-view orientation have not been physically
verified by this mirrored plasma check. No live process is left running;
baseline files remain untouched.

### Independent fixture and corner check (LIVE-001, passed)

On 2026-10-19, following operator authorization, ran:

```bash
.venv/bin/python scripts/fixture-check.py live
```

The fixed sequence displayed Cube A red at front-view top-left for five
seconds, then blue at bottom-right for five seconds, followed by the same
sequence on Cube B. Only one pixel on one cube was active at a time, with
one second of transmitted blackout after each marker and final shutdown
blackout. Global brightness was 0.25 through the compositor; the frame safety
limiter remained enabled. Output remained at 25 FPS to localhost universe 0.

Before transmission the harness validated every complete 512-channel frame
against an independent expected channel: A red at 142, A blue at 3, B red at
294, B blue at 155 (one-based). Exactly one channel was 64/255 in each marker;
every other channel, including all unverified channels, was zero. Its default
command performs only these offline checks and never creates a sender.
All 57 automated tests also passed before the live run.

The live process exited 0. The operator confirmed all marker positions,
colours, fixture isolation, and final darkness were correct. Combined with
the timed plasma check, LIVE-001's physical response, independent A001/A153
control, endpoint orientation, and normal shutdown blackout checks have passed.
This checks the two diagonal endpoints, not the 12-column row transitions or
every pixel individually. Automatic
live startup remains disabled, and baseline files remain untouched.

### Handled-interruption blackout (passed)

Following operator authorization to proceed with the next check, ran the slow
plasma live command at brightness 0.25, speed 0.2, 25 FPS, with a 15-second
fallback duration. Sent Ctrl+C through the live terminal before normal expiry.
The controller printed `Interrupted; live mode requested a blackout before
closing.` and exited 0. The operator confirmed that both cubes went dark.
This verifies physical shutdown blackout on a handled keyboard interruption.
Live output is off. Abrupt termination, power loss, and network failure were
not tested and cannot guarantee blackout.

### QLC+ automatic process-failure recovery (passed)

With the live controller off, sent SIGKILL to QLC+'s user-owned service process
on 2026-10-19. The journal recorded failure at 21:10:15 MDT and systemd restart
at 21:10:20. The main PID changed from 5010 to 6045 and `NRestarts` became 1.
The service returned to active/running, solely owned UDP 6454 and TCP 9999,
and served HTTP 200 after the web listener finished startup. The runtime
workspace still matched Git. No controller or lighting output was started.
Physical darkness across QLC+ recovery awaits separate operator observation.

Boot startup remains disabled and reboot behavior is untested. No competing
launch entry was found in the inspected startup locations. Firewall inspection
and further administrative changes require fresh sudo authentication. The Pi
has both the 192.168.1.0/24 LAN interface and a global IPv6 address; wildcard,
unauthenticated web access remains an unresolved isolation check. No firewall,
boot configuration, or baseline files were changed by this recovery test.

### Service IP restriction and boot enablement

Subsequently, administrative access resumed and `sudo nft list ruleset`
confirmed an empty active nftables ruleset. Updated the QLC+ service with
`IPAddressDeny=any`, `IPAddressAllow=localhost`, and
`IPAddressAllow=192.168.1.0/24`. The Pi kernel has cgroup BPF support. The unit
passed `systemd-analyze verify`, was installed after backing up the original,
and QLC+ restarted successfully. This restricts only QLC+ traffic; it does not
change host-wide firewall rules or SSH access.

Post-install local probes returned HTTP 200 through IPv4 loopback, IPv6
loopback, and the Pi's LAN address. HTTP to its own global IPv6 address timed
out. Effective service properties showed the expected IPv4/IPv6 deny-all and
localhost/current-LAN exceptions, with no unsupported-filter warning in the
startup log. These local probes do not substitute for an external-host check.
The web UI remains unauthenticated within the allowed IPv4 LAN; the allowed
subnet must be updated before deploying on a different network.

Enabled `qlcplus.service` for boot and confirmed enabled/active, with the
installed unit and runtime workspace matching Git. Automatic lighting output
remains off. The pre-reboot boot ID is recorded in `RESUME.md`; reboot startup
and physical darkness through reboot remain pending. Preserved baseline files
were not touched.

### Post-reboot software verification — 2026-10-19

The scheduled reboot completed at 21:16:07 MDT with a changed boot ID
(`5220faf7-fa68-446e-b7bd-287e4c2747cc`). QLC+ started automatically at
21:16:20 as `mmorley`, with the expected HOME and runtime workspace. At the
21:18 checkpoint it was enabled/active with one process (PID 1483), zero
service restarts, and sole ownership of UDP 6454 and TCP 9999. The installed
unit and runtime workspace matched repository copies. Effective IP filtering
retained localhost/current-LAN exceptions and IPv4/IPv6 deny-all entries.
HTTP returned 200 through IPv4/IPv6 loopback and the Pi's LAN address; its own
global IPv6 probe timed out after five seconds (curl exit 28). These remain
local-host checks, not independent external-host network validation.

No live controller process was present. All 57 tests passed in the project
virtualenv (0.134 seconds). No live output or service changes were made during
verification. The operator subsequently confirmed both fixtures stayed dark
through reboot, completing reboot verification. Physical darkness across the
earlier QLC+ process-failure recovery still requires separate confirmation.

### Repeated recovery and other-device LAN access (passed)

On 2026-10-19 at 21:21:36 MDT, after verifying no live controller was running,
sent SIGKILL to verified QLC+ service PID 1483. Systemd restarted it at 21:21:41
as PID 2207 with `NRestarts=1`, active/running. The single QLC+ process solely
owned UDP 6454 and TCP 9999, returned HTTP 200 locally, and its runtime workspace
still matched Git. No live output was started. The operator confirmed both
fixtures stayed dark throughout recovery and that the port 9999 web UI opens
on a phone and computer. Physical recovery and other-device LAN access passed.
Independent denial checks from outside the allowed subnet remain untested;
successful LAN access does not establish denial elsewhere.

### Commissioning review

Reviewed the service, both diagnostic scripts, documentation, and stored soak
evidence. The JSON covers exactly the current 19 effects and four presets;
its frame totals, timing, memory, temperature, reserved-channel checks, and
blackout results match this report. Service syntax validation and all 57 unit
tests passed. The corner check passed with socket creation blocked. A short
0.2-second-per-look harness check also passed all 23 looks with sockets blocked;
this verifies the harness and does not replace the stored 30-second-per-look
soak. No live output was started during review. Installation, soak, live smoke,
and Phase 2 validation cards are Done with this commit; QLC-002 remains in
Validation pending independent access-denial checks.

### Final network acceptance (QLC-002, passed)

Following the other-device LAN access check, the operator confirmed the
requested global IPv6 URL (`http://[2001:56a:742e:b000:15bd:c545:fda1:c5a6]:9999`)
was denied while the standard IPv4 LAN URL (`http://192.168.1.89:9999`) still
worked. This records an independent browser observation, alongside the
service's verified IP allow/deny properties and local probes. The planned
permitted/denied browser checks passed; this is not a comprehensive test of
all network paths. QLC-002 is Done and commissioning acceptance is complete
within the documented scope. Live output remains off; no service changes or
additional hardware output were needed for this documentation update.
