# Phase 2 implementation report

## Delivered

- A normalized RGB pipeline with DMX quantization only at the output boundary.
- A deterministic effect contract with metadata, typed validated parameters,
  fixture identity, and optional performance context.
- Eighteen advanced procedural effects and four legacy-preservation effects,
  all dependency-free.
- A compositor with alpha, additive, and lighten blending; layer opacity;
  per-fixture targeting; radial masks; global limits; and pure crossfades.
- A configurable stateful limiter for large repeated full-frame luminance rises.
- Seventeen built-in multi-layer presets, including independent and cross-cube
  show looks.
- Transport-independent show commands for effect and parameter changes, preset
  activation, events, blackout, tap tempo, and scene navigation.
- A normalized audio-analysis contract with deterministic manual and recorded
  sources plus explicit, dependency-free ALSA capture and browser meters.
- A shared audio-reactive clock: tempo sets every effect's baseline motion,
  smoothed dynamics provide bounded motion and brightness multipliers, and the
  browser exposes both values.
- An explicit show-time RGB ceiling override that requires live mode and a
  high-output acknowledgement while retaining frame-rise safeguards.
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

- 138 automated tests pass on Python 3.12 after browser control, persistent user
  looks, foot control, the show scene pack, opt-in audio capture, shared audio
  dynamics, white-channel commissioning, and the explicit RGB ceiling gate
  were integrated.
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
- Tap tempo, event context, normalized audio inputs, and explicit ALSA capture
  are implemented; automatic scene selection remains out of scope. Capture
  still requires Raspberry Pi timing and latency acceptance.
- PPM export avoids dependencies; PNG export would require either a platform
  conversion step or an image library.
- USB foot control is implemented and has passed an initial browser-simulation
  and guarded-live operator check; a stable udev link and rehearsal-length soak
  remain. Bluetooth MIDI and video-to-RGB mapping remain future work.
- The eight white channels per fixture are now commissioned. They remain zero
  by default and are accessible only through the separately gated, capped
  browser-live peak control described in the latest section below.

## Show scene pack and Ampero validation — 2026-10-20

Eight additional built-in looks extend the original four presets: Midnight
Current, Acid Mirrors, Phase Collider, Neon Blades, Inferno Rise, Split Signal,
Hypnotic Drive, and Crossfire. The pack uses the existing deterministic effect
and compositor APIs; no effect, transport, fixture mapping, or Art-Net code was
changed. Acid Mirrors, Split Signal, and Crossfire deliberately target Cube A
and Cube B independently. All new global brightness levels are 0.48 or lower,
and none can address the fixtures' reserved channels.

The Windows Python 3.12 suite passes 95 tests. New coverage validates unique
preset IDs, conservative global levels, independent fixture targeting,
deterministic rendering, complete DMX frames, and zero output on channels
145–152 and 297–304.

The operator updated the Hotone Ampero Control to firmware 1.13 and observed
the documented USB MIDI messages on `/dev/snd/midiC3D0`. Previous/next scene,
tap tempo, and explicit blackout toggling worked in trusted-LAN simulation;
the subsequent guarded browser-live check was also reported working correctly.
This is an initial functional acceptance, not the planned rehearsal-length USB
soak. Automatic audio capture remains deferred until the visual scene vocabulary
and manual tempo behavior are accepted.

On 2026-10-21 a controlled USB reconnect showed a second failure mode: the
reader correctly detected device removal and reopened the raw-MIDI path, but no
messages or mapped actions followed. Direct ALSA tools were also silent until
the bank was reinitialized with the iOS app. Reopening the node is now treated
as transport recovery only; a valid mapped event is required for functional
readiness. Protocol research and a possible read-only inspect/verify plus gated
restore tool are deferred to `CONTROL-002`, with no vendor application binary
stored in the repository and no unknown write commands permitted during normal
testing.

## Audio-analysis contract — 2026-10-20

`AudioAnalysis` and `FrequencyBands` add normalized loudness, onset, bass, mid,
and treble values to the optional performance context. Manual and recorded
sources implement a capture-independent boundary, including deterministic
previous-sample replay. `Controller` can consume any conforming source, while an
explicitly supplied render context continues to take precedence.

Radial Pulse was the first bounded effect-local audio consumer. Analysis scales
its existing ring energy and slightly shifts colour; it does not add a new
full-frame onset flash. The shared `AudioReactiveClock` now supplies every
effect with continuous tempo-based time, a bounded 1.0x-2.0x dynamics motion
multiplier, and a 55%-100% brightness multiplier below the manual master. The
global brightness ceiling, frame-rise limiter, blackout behavior, and DMX
reserved-channel rules remain downstream and unchanged. With no audio source,
both shared multipliers are exactly 1.0 and no capture module is imported.

The complete Python 3.12 suite passes 101 tests. Coverage includes invalid and
non-finite values, manual updates, deterministic recorded replay, controller
source injection, explicit-context precedence, repeatable audio-reactive output,
normalized RGB bounds, and zero output on both fixtures' reserved channels.

## Explicit ALSA capture — 2026-10-20

The Pi detected the ambient Blue Snowball as `plughw:CARD=Snowball,DEV=0` and
passed direct `arecord` format and input-level checks. `ArecordAudioSource` now
starts only when `--audio-device` is present, requests 44.1 kHz signed 16-bit
mono PCM, and performs analysis on a dedicated worker. The analyzer uses two
lightweight crossover filters, adaptive ambient-noise tracking, attack/release
smoothing, and bounded onset detection without NumPy or an audio dependency.

The browser reports capture health and five meters. EOF or capture error clears
analysis to silence while leaving rendering and blackout available. Automated
tests use generated PCM and fake processes; no test opens a microphone or
network socket. Application-level Pi CPU, latency, and missed-frame measurements
remain the final AUDIO-002 acceptance gate.

The operator then ran Phase Collider through simulation-only browser control on
the Pi with the explicit Snowball device and reported the whole path working:
capture, five meters, and audio-reactive rendering. Art-Net could not be enabled
in that mode. This passes functional Pi validation; it does not replace the
remaining sustained performance and rehearsal-level sensitivity checks.

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

Each physical fixture also has two central white strobe/blinder elements. They
are not included in the 12-by-4 RGB frame data. The browser canvas depicts them
as two disabled grey lines between the upper and lower RGB row pairs so its
physical layout matches the fixture; the Tk preview remains RGB-only. Their DMX
mapping was reportedly exercised successfully by original Pi scripts, but
those files and exact assignments are absent from this checkout and its Git
history. The controller continues to transmit zero for all eight currently
undocumented channels until the original evidence is imported and tested.

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

## Music-driven look expansion and controller reliability — 2026-10-20

Cross-Cube Blaster, Dynamic Sine Wave, and Inside-Out VU extend the catalog to
22 registered effects. Matrix Rain, Blaster Sweep, Flame Thrower, Wave Rider,
and Inside-Out VU extend the built-in catalog to 17 presets. The cross-fixture
effects use one logical 24-by-4 coordinate surface and remain independent of DMX
addresses. Inferno Rise's fire gradient was corrected so its heat source is the
confirmed physical bottom row and its noise motion rises upward.

Browser preset/scene actions previously cleared
`global_brightness_override`, causing the master slider to jump to each preset's
saved level. Those resets were removed, making master brightness persistent
through manual, timed, and foot-controlled scene navigation.

The Ampero reader previously returned from its worker after the first ALSA
select/read error. It now closes and reopens the same configured device, resets
the MIDI parser, contains command and reporting exceptions, and publishes
connection/message/reconnect status. ALSA card renumbering still requires a
stable udev link and remains a deployment acceptance item.

Audio deep dim is explicit and disabled by default. When enabled, the operator
can choose a 0%-25% near-black floor below the persistent manual master. A
center-white onset visualization is also available in the browser, but it is
preview-only: all normal frames continue to hold DMX 145-152 and 297-304 at
zero. The complete Windows Python 3.12 suite passes 138 tests.

The operator's earlier integrated Raspberry Pi bench report passed all 31 looks
present at that time. Its render-timing, audio-capture, and foot-control checks
were true; the Snowball source ended healthy after 6,681 chunks, and every
mapped pedal action was observed multiple times. This is retained as valid
hardware evidence for that revision. The expanded 22-effect/17-preset catalog
requires a new 39-look run under ordinary connected operation before closing
the current visual, audio, and pedal acceptance cards. Deliberate MIDI recovery
is separated into `CONTROL-002` because ALSA reconnection alone did not restore
pedal output in the 2026-10-21 test.

The soak harness originally classified every MIDI reporting callback as a fatal
error, including the expected disconnect and reconnected messages from a
successful recovery test. It now records lifecycle messages separately and
evaluates the final connection state, required action counts, and genuine
mapped-action failures. Automated coverage verifies recovered reconnect,
missing-action, final-disconnected, and command-error outcomes.

The current 39-look Raspberry Pi rerun passed on 2026-10-21. Every look held
25 FPS with no reported missed slots or over-budget frames, unmapped channels
remained zero, and each shutdown blackout was zero. Audio finished healthy after
8,404 chunks. Flame Thrower was the heaviest reported preset at 12.129 ms mean,
14.616 ms p95, and 16.182 ms maximum render time, still below the 40 ms frame
budget; process temperature peaked at 49.05 C.

The pedal produced 18 previous-scene, 17 next-scene, 16 tap-tempo, 6 blackout-on,
and 5 blackout-off actions. An unplanned `Errno 19` disconnect occurred, after
which the worker reconnected; the final status was connected with 62 messages
received and no action errors. This is a successful functional recovery case,
but it does not invalidate the earlier silent-after-reopen case tracked by
`CONTROL-002`.

Following visual review, Flame Thrower was separated from the travelling
Cross-Cube Blaster. The new `flame-jet` effect keeps a compact hot source at the
far left of Cube A and carries three turbulent strands through the Cube A/B
boundary to the far edge of Cube B. Its length breathes modestly with bounded
audio dynamics while direction remains fixed. The preset no longer overlays the
single-fixture rising spark effect. This increases the current catalog to 23
effects and 40 soak looks; the prior 39-look Pi pass remains valid for its
revision and the new catalog requires a fresh full-duration Pi timing run. The
Windows suite passes 139 tests; a short socket-blocked 40-look smoke also passed
with zero missed slots, zero over-budget frames, zero reserved-channel output,
and zero shutdown blackout. The revised Flame Thrower measured 2.883 ms mean,
3.129 ms p95, and 3.129 ms maximum in that abbreviated Windows smoke.

Wave Rider was then refined so tempo remains its baseline phase clock while
music pulses shape the ribbon locally. Audio onset temporarily increases the
number of cycles across the combined 24-by-4 surface and crossfades its sine
carrier toward a cosine variant; treble contributes a smaller secondary ripple.
The `pulse_frequency` and `cosine_morph` parameters bound these responses, and
quiet input returns to the sine-led baseline without changing output limits.

## LF4808 white commissioning and guarded peaks — 2026-10-21

The operator completed the steady 5% diagnostic and confirmed that white Parts
1-8 progress right-to-left, each part drives both center rows together, and the
two fixtures match. The configuration now records this physical mapping and
tests resolve logical left-to-right positions to Parts 8-1.

Physical audio peaks remain independent of presets and normal rendering. They
require explicit `live --web`, active browser output, an audio source, and a
separate toggle. Output defaults to 5%, is hard-capped at 10%, and converts only
onset threshold crossings into pulses no longer than 0.10 seconds and no faster
than 4 Hz. Blackout, Stop output, rendering failure, and browser-lease loss
disarm the feature. Simulation and all default output paths keep DMX 145-152 and
297-304 at zero.
