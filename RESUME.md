# Codex Resume: Audio Contract, Ampero Control, and Show Scene Pack

Last updated: 2026-10-22

## Pause checkpoint -- successful live band test

The unattended Pi deployment and first live band test were operator-confirmed
working on 2026-10-22. After reboot, `qlcplus.service` started at 21:14:10 and
`phreqed-dmx.service` followed five seconds later. QLC+ loaded the commissioned
workspace, the Snowball capture process was active, and Phreqed advertised
simulation with output stopped until the operator explicitly started live
output. The browser, two LF4808 fixtures, audio-reactive operation, scene
control, and Ampero controls were subsequently reported working together with
the band.

The Ampero changed from `/dev/snd/midiC3D0` to `midiC2D0` at that boot. Commit
`55701dd` adds the USB-identity-based `/dev/snd/phreqed-ampero-midi` udev link
and updates the service installer. The operator reported the resulting live
system working, but the resolved-link output and an explicit unplug/replug or
second-reboot observation were not captured in chat; retain those as validation
rather than inferring them.

Current development branch and remote are `feat/audio-context` at `55701dd`.
Do not use the main-only `scripts/pi-update.sh` until this branch is merged;
feature-branch deployments use `git pull --ff-only origin feat/audio-context`,
`scripts/pi-install.sh`, and `scripts/pi-install-show-service.sh`. The Windows
checkout still contains four unrelated user-staged Playwright YAML/PNG
artifacts; preserve them.

Next priorities after the pause are: verify the stable MIDI link across a
reboot and USB reconnect, choose and validate the private stage LAN, perform a
longer band-volume resource/pedal soak, continue CONTROL-002 pedal-bank recovery
research, and complete the deliberately guarded center-white acceptance tests.
The Pi can remain powered off while this work is paused.

## Latest checkpoint -- stable Ampero raw-MIDI identity

The first unattended boot succeeded for QLC+ and Phreqed, with browser output
stopped and Snowball capture active. The Ampero enumerated as
`/dev/snd/midiC2D0` rather than the configured `midiC3D0`, confirming that a
numbered ALSA path cannot be used for unattended deployment.

`config/udev/70-phreqed-ampero.rules` now matches the commissioned Hotone USB
identity `84ef:0029` and creates `/dev/snd/phreqed-ampero-midi`. The show-service
installer deploys and reloads the rule, reports the resolved target, warns when
an existing environment file still uses a numbered path, and now verifies the
browser with GET rather than unsupported HTTP HEAD. Pi unplug/replug and reboot
verification remain pending; this does not address loss of the pedal's internal
bank programming, which remains CONTROL-002.

## Latest checkpoint -- unattended show startup

Headless show startup is prepared for Pi validation. The new
`phreqed-dmx.service` orders the browser controller after `qlcplus.service`,
restarts it after failure, and does not wait for external internet or venue
Wi-Fi. Startup provides live capability but keeps output stopped until the
browser's explicit **Start live** action. Runtime settings are read from
`/etc/default/phreqed-dmx`; the installer preserves an existing local file.

The launcher checks for the configured Snowball name. A missing optional mic
now produces a warning and starts the browser without audio instead of taking
down control. A missing Ampero remains visible and recoverable through the
existing raw-MIDI retry worker. The controller accepts comma-separated trusted
IPv4 networks, and service filters include both the current home LAN and the
reserved private stage LAN `10.42.0.0/24`.

The recommended production topology is Ampero-over-USB for no-screen show
commands plus a dedicated private router for the phone interface, with the Pi
on Ethernet and no internet dependency. A Pi-hosted access point is documented
as an alternative but is not provisioned automatically because changing the
active Wi-Fi profile could interrupt SSH. Windows Python 3.12 passes all 161
tests; both launcher scripts pass `bash -n`, and missing optional/required audio
launcher paths were exercised with a non-networking fake executable. Pi
systemd verification, reboot-darkness observation, and private-LAN acceptance
remain under OPS-003.

## Latest checkpoint -- adaptive audio headroom and visual refinements

Sustained loud microphone input can no longer leave normalized analysis pinned
indefinitely. `Pcm16MonoAnalyzer` now defaults to a slow bounded auto-level that
calibrates against the strongest of loudness/bass/mid/treble, attacks in roughly
one second, releases slowly, and publishes its current gain. The browser exposes
an Auto-level microphone toggle and gain readout. It remains analysis-only and
cannot raise an RGB or center-white ceiling.

The compositor now offers a persistent 1.0x-3.0x hue-preserving Visual contrast
control. It darkens intermediate intensities before master brightness, restoring
separation in fill-heavy looks while remaining downstream-limited. Full RGB
range remains available only through explicit live startup with
`--rgb-ceiling 1.0 --acknowledge-high-output`; default safety behavior is
unchanged.

Wave Rider is restored to one stable sine carrier. Tempo remains the baseline,
while music moves the shared clock only between 0.7x and 1.5x and adds a small
phase push; audio no longer changes wavelength or morphs the carrier. Flame
Thrower now uses five independently varying strands with spatial width changes,
vertical drift, moving breakup pockets, and separate pulses while retaining
cross-seam continuity. A new deterministic `pacman` effect and Pac-Man Chase
preset traverse the combined 24-by-4 display with a chomping character and dim
dotted path. The catalog is now 25 effects and 19 presets (44 soak looks).

The full Windows suite passes 159 tests. A socket-blocked 44-look smoke passes
with zero missed slots, zero over-budget frames, zero reserved-channel output,
and zero shutdown blackout. Browser simulation visually confirms the stable
Wave Rider curve and the Flame Thrower strand breakup; Pi visual authority and
full-duration timing remain pending.

After the rig was shut down and moved, startup failed because the explicit
`/dev/snd/midiC3D0` node did not exist. `RawMidiFootController.start()` now
treats initial absence like a recoverable disconnect: browser/audio control
continues, status reports that MIDI is waiting, and the worker retries only the
operator-selected path. Reconnect or identify the current node with `amidi -l`
and `ls -l /dev/snd/midiC*D*`; a stable udev raw-MIDI link remains outstanding.

## Latest checkpoint — guarded high-output center whites

The commissioned audio-peak white path still defaults to 5% with a 10% ceiling.
An operator can now expose a higher per-process ceiling only with explicit
`live --web --white-ceiling VALUE --acknowledge-high-output-whites`. Elevated
mode is rejected from simulation, simulation-only browser control, ordinary
non-browser live mode, and acknowledged live browser startup without the
white-specific acknowledgement. The browser publishes the selected ceiling,
bounds its physical-white slider to it, and shows a persistent red warning.

This override does not change the onset threshold or relax the 0.10-second,
4 Hz, blackout, Stop output, render-failure, or five-second browser-lease
safeguards. `scripts/white-zone-check.py` retains its independent hard 10%
commissioning cap. The 150-test Windows suite and a clean browser warning/slider
inspection pass without starting Art-Net. Pi stepped-output acceptance remains
to be recorded for this slice.

Python 3.13 exposed an `argparse` help-formatting bug caused by an unescaped
literal percent sign in the deep-dim help text. The CLI help string is corrected
and a regression test now renders the complete help output.

## Latest checkpoint — Matrix, directional blaster, and blinking eyes

Matrix Rain now activates a sparse deterministic subset of columns. Each bright
pale-green head travels from logical row 0 toward row 3, leaves a short darker
tail, pauses below the fixture, and restarts above it. Blaster Sweep now reads as
a gun firing: a compact source flare launches a discrete pulse across the
combined 24-by-4 surface. Its `direction` parameter supports left-to-right,
right-to-left, and mirrored center-out travel.

The new `blinking-eye` effect and Watchful Eyes preset render an almond sclera,
coloured iris, dark pupil, subtle gaze motion, and synchronized close/reopen
cycle on each fixture. The catalog now contains 24 effects and 18 presets, or 42
soak looks. The 144-test Windows suite, browser preview, and a short
socket-blocked 42-look smoke pass. Operator Pi visual acceptance and the full
five-second-per-look timing run remain.

## Latest checkpoint — Wave Rider pulse synchronization

Wave Rider keeps the shared tap-tempo animation clock as its baseline rate. Its
`dynamic-wave` layer now uses detected audio onset to temporarily increase
spatial frequency and crossfade the sine-led carrier toward a cosine pattern;
treble adds a smaller secondary ripple. The response is bounded, deterministic
for a supplied audio frame, and returns to the original sine behavior as onset
decays. New `pulse_frequency` and `cosine_morph` parameters expose both response
depths in the browser look editor. Pi visual and rehearsal-level tuning remain.

## Latest checkpoint — Flame Thrower redesigned as an anchored jet

Flame Thrower no longer reuses the travelling Cross-Cube Blaster plus unrelated
vertical sparks. A dedicated deterministic `flame-jet` effect anchors a compact
white-hot muzzle at the far left of Cube A, then forks three turbulent ember
strands continuously across Cube A and Cube B. Audio dynamics make reach and
motion breathe without reversing the left-to-right direction. Directional tests
cover the source gradient, both sides of the fixture boundary, and the far-right
tip. This adds one standalone effect, so the catalog now contains 23 effects,
17 presets, and 40 total Pi-soak looks. The 139-test Windows suite, browser
preview, and a short socket-blocked 40-look smoke pass; operator Pi visual
acceptance and the full five-second-per-look timing run remain.

## Latest checkpoint — current 39-look Pi bench passed

The 2026-10-21 socket-blocked integrated Pi bench passed all 39 looks at 25 FPS
with render timing, Snowball capture, and foot control all true. No reported
look missed a frame slot; reserved channels and shutdown blackout remained
zero. Audio ended healthy after 8,404 chunks. The heaviest reported preset was
Flame Thrower at 12.129 ms mean, 14.616 ms p95, and 16.182 ms maximum render
time against the 40 ms frame budget; peak temperature was 49.05 C.

The pedal registered 18 previous-scene, 17 next-scene, 16 tap-tempo, 6 blackout
on, and 5 blackout-off actions. One unplanned `Errno 19` disconnect occurred;
the worker reconnected and the run finished connected with 62 received messages
and no action errors. This is positive evidence of functional same-path recovery
when the pedal retains its bank, but it does not close `CONTROL-002`: the earlier
controlled test still showed that a reopened device can remain silent until app
reinitialization.

## Latest checkpoint — Ampero reconnect characterized; recovery sprint deferred

The controlled 2026-10-21 USB reconnect test detected `Errno 19`, reopened the
same raw-MIDI path, and reported one successful reconnect, but received zero
messages and no pedal actions. Direct `amidi` and `aseqdump` were also silent.
Reinitializing the bank with the iOS app restored MIDI output. An open ALSA node
therefore proves transport availability, not a functionally programmed pedal;
a valid mapped event is required after startup or reconnect before show-ready
status.

Automated Ampero configuration inspection and recovery is now deferred to
kanban card `CONTROL-002`. Static inspection of Hotone's official Android app
found Flutter/`flutter_blue`, preset request/send/acknowledgement strings,
SysEx, CRC32, and custom GATT services. The downloaded vendor archive was not
added to the repository; its SHA-256 is
`3F8645221B4C6B8386211FFC914F751B79D6C54379E189464CE766EDFF5D6192`.
The proposed future interface is `ampero inspect`, `ampero verify`, and a gated
`ampero restore`; writes remain prohibited until read-only discovery, protocol
decoding, backup, dry-run, exact firmware checks, and read-back validation pass.
See `docs/ampero-control.md`.

## Latest checkpoint — center whites commissioned and guarded output added

On 2026-10-21 the operator completed the steady 5% physical test: white Parts
1-8 progress right-to-left, each part drives both visible rows together, and
both fixtures match. `config/fixtures.toml` now records the accepted mapping.

Browser live has a separate **Enable physical white peak output** control. It
requires active browser-live output and a microphone, defaults to 5%, cannot
exceed 10%, and turns audio onset threshold crossings into pulses no longer
than 0.10 seconds and no faster than 4 Hz. Blackout, Stop output, render failure,
and browser-lease loss disarm it. Simulation, presets, and ordinary live output
still send zero on DMX 145-152 and 297-304.

## Latest checkpoint — stage-look expansion and reliability fixes

The browser master slider is now a persistent operator override: selecting a
built-in/user preset or moving through a scene list no longer clears it. Audio
response also has an explicit deep-dim toggle and adjustable 0%-25% quiet floor;
the existing 55% floor remains the safe default.

The effect catalog now has 23 effects and 17 built-in presets. New looks are
Matrix Rain, Blaster Sweep, Flame Thrower, Wave Rider, and Inside-Out VU. The
blaster and wave effects treat the fixtures as a continuous 24-by-4 surface.
Inferno Rise was corrected so row 3 is the physical hot bottom and turbulence
rises toward row 0; keep the LF4808s upright with their printed text readable.

Center-white preview remains available without output. Physical output is
isolated from presets and must be explicitly re-armed after every stop path.

The Ampero input worker now reconnects to the same raw-MIDI path after transient
read/device failures and reports connection, message, and reconnect counts in
the browser. A stable udev link remains required for card renumbering. The full
Python 3.12 suite passes 138 tests and browser JavaScript passes syntax checks.

Next Pi steps: pull this branch, run the suite, visually review the five new
presets in simulation, confirm master persistence, and complete a pedal soak
with one controlled USB reconnect. Validate HW-002 at the default 5% with QLC+
blackout immediately available before considering any higher white level.

The earlier integrated Pi bench run is valid evidence for the then-current 31
looks: render timing, Snowball capture, and foot input all passed; capture ended
healthy after 6,681 chunks. The current catalog has 39 looks, so it still needs
one updated bench run. White-channel software commissioning passes offline for
all sixteen isolated 5% frames, and the physical Part 1-8 orientation is now
recorded as right-to-left with both rows moving together on both fixtures.

The Pi soak foot gate now treats a recovered disconnect/reconnect as a lifecycle
event instead of an automatic failure. It still fails when the final MIDI state
is disconnected, required switch counts are missing, or a mapped action raises
an error. Reports include `foot_events`, genuine `foot_errors`, and
`foot_final_status` for diagnosis.

This is the short operational handoff for a new Codex session. Read
`AGENTS.md`, this file, and `docs/kanban.md` before taking action. The detailed
design remains in `docs/architecture.md`, `docs/effects.md`, and
`docs/raspberry-pi-deployment.md`. The future projector architecture is in
`docs/projector-output.md`.

## Latest checkpoint — show ceiling and shared audio dynamics

The safe RGB ceiling still defaults to 0.65. A higher temporary ceiling now
requires the literal `live` command, `--rgb-ceiling`, and
`--acknowledge-high-output`. The same selected value configures both the
compositor and final frame limiter. Browser live continues to start at 0.25 or
lower, exposes the active ceiling in its master slider, and presents a
high-output warning. Saved look brightness stays capped at 0.65; luminance-rise
and flash-interval controls remain active; the white commissioning tool retains
its independent hard 10% ceiling.

`AudioReactiveClock` now drives the continuous animation time used by every
effect. Tempo is the baseline rate, `--speed` is the manual trim, and smoothed
audio dynamics apply a 1.0x-2.0x motion multiplier plus a 55%-100% brightness
multiplier below the manual master. The browser displays both values. With no
audio source, both remain 1.0; silent input keeps steady tempo-driven motion.
Radial Pulse retains its additional local ring and colour response.

The complete Windows Python 3.12 suite passes 124 tests, and the browser
JavaScript passes `node --check`.

Pi acceptance remains: verify the elevated slider bounds with output stopped,
then validate the response curves across every preset at rehearsal level and
perform a gradual live brightness check on the secured rig with QLC+ blackout
available.

## Prior checkpoint — LF4808 white-zone commissioning

The recovered LF4808 152-channel manual maps fixture channels 145-152 as eight
independently, linearly dimmed white parts. Cube A therefore uses universe DMX
145-152 and Cube B uses 297-304. Normal scenes still leave them zero. The new
`scripts/white-zone-check.py` validates all sixteen addresses offline and offers
only an explicit live sequence: one steady part at 5%, at least 0.75 seconds of
blackout between parts, a hard 10% ceiling, and final shutdown blackout.

The physical run subsequently passed: Parts 1-8 progress right-to-left, each
part drives both rows, and both fixtures match. The guarded implementation is
described in the latest checkpoint above.

## Latest checkpoint — Pi audio capture accepted functionally

`feat/audio-context` now includes the first AUDIO-002 capture slice. The Blue
Snowball was detected on the Pi as `plughw:CARD=Snowball,DEV=0`, and direct
ALSA format and level-meter checks passed. The controller now has an explicitly
started, standard-library `arecord` worker, deterministic mono PCM analysis,
adaptive noise-floor handling, capture health, and browser meters. Loudness,
onset, bass, mid, and treble remain normalized behind `AudioAnalysisSource`.

Capture is disabled unless `--audio-device` is supplied, never selects live
mode, and degrades to silent analysis if the input ends. Radial Pulse remains
the first effect-local consumer, while the newer shared dynamics clock applies
bounded motion and intensity to all effects. No runtime dependency was added.
Windows automated
tests cover PCM bands, normalization, lifecycle, start failure, explicit CLI
gating, browser meters, simulation isolation, and the original contract. A Pi
application-level 25 FPS/latency run remains before performance acceptance.

The operator then ran the simulation-only browser command on the Raspberry Pi
with `plughw:CARD=Snowball,DEV=0` and Phase Collider, and reported the complete
path working: capture stayed active, the browser meters responded, and the
audio-reactive visual changed with the room input. This did not enable Art-Net
or exercise physical light output. Functional Pi acceptance has passed; only a
sustained CPU, latency, and missed-frame measurement remains for AUDIO-002.

`scripts/pi-soak.py` now supports an integrated simulation-only bench run with
explicit Snowball capture and Ampero raw-MIDI input. It blocks all sockets and
the Art-Net sender, renders every effect and preset, checks the 512-byte DMX
frame and final blackout, records audio continuity/peaks, and can require all
five mapped pedal actions. The Windows suite passes 112 tests; the first Pi
report is the next validation step.

Projector output is now scoped in the backlog as PROJ-001, PROJ-002, and
SHOW-002. The intended design uses a separate HDMI player/compositor process
and unified light/projection cues. The current Ampero can control those cues, so
a second pedal is not required for the foundation. No projector code or runtime
dependency has been added yet.

Wireless wearable lighting is also scoped in WEAR-001, WEAR-002, and SHOW-003.
The recommended first prototype is a low-pixel-count diffused guitar strap or
torso/shoulder channel with rear belt electronics. Candidate transports are
WLED/ESP32, a custom ESP-NOW gateway, Pixelblaze, and professional wireless DMX.
Wearables render locally from compact synchronized cues and fail black without
touching DMX. The existing Ampero can control unified cues; a second pedal is
optional rather than required. See `docs/wearable-lighting.md`.

## Hotone Ampero Control branch

`feat/ampero-control` is stacked on the 12-by-4 correction branch. It adds a
dependency-free standard MIDI parser, explicit ALSA raw-MIDI activation, and a
documented Ampero bank: FS1 previous scene, FS2 next scene, FS3 tap tempo, and
FS4 explicit blackout on/off. Browser-mode pedal events use the browser's
serialized cue and blackout commands. USB is the initial supported transport;
Bluetooth MIDI remains pending Pi pairing and reconnect characterization.

The adapter is disabled unless `--foot-midi-device` is supplied and cannot
enable Art-Net. On 2026-10-20 the operator updated the pedal to firmware 1.13,
configured the documented bank, and captured the expected raw USB messages on
`/dev/snd/midiC3D0`: notes 60, 61, and 62 at velocity 127, plus CC 23 values
127 and 0. The operator then confirmed previous/next scene, tap tempo, and
blackout in trusted-LAN browser simulation and reported that guarded browser
live control worked correctly. A stable udev link and rehearsal-length USB
soak remain before final acceptance. See `docs/ampero-control.md`.

## Latest checkpoint — show scene pack

`feat/show-scene-pack` is stacked on `feat/ampero-control`. It adds eight
conservative built-in looks, bringing the catalog to twelve presets. The pack
includes three independent-fixture compositions and several tap-tempo-aware or
cross-cube layers. All new preset global levels are at or below 0.48, and no
reserved fixture channels or white-strobe controls are exposed.

The complete Windows suite passes 95 tests on Python 3.12 with `PYTHONPATH=src`.
Every new preset is rendered deterministically, checked for complete 12-by-4
geometry, quantized into a full 512-channel frame, and verified to leave both
fixtures' eight unverified channels at zero. Visual and low-brightness Pi
acceptance of the new looks remains pending.

## Objective in progress

Correct the LF4808 logical layout from the reconstructed baseline's 8-by-6
assumption to the operator-confirmed 12 columns by 4 rows, then validate the
row transitions on the Raspberry Pi without making live output automatic.
Browser show-control validation remains open behind this P0 mapping correction.

Do not start live Art-Net output merely to inspect the installation.

## Latest checkpoint — 12-by-4 geometry correction

The official LF4808 product listing confirms individual zone/pixel mapping and
152-channel mode. The operator identified the physical RGB zone layout as a
12-column by 4-row front view. The previous test lit only zone 48 at top-left
and zone 1 at bottom-right; those endpoints are identical in both 8-by-6 and
12-by-4 row-major layouts, so it did not prove the old row width.

Work is isolated on `fix/lf4808-12x4`. Configuration, mapping defaults,
simulators, browser previews, diagnostics, tests, and current documentation now
use 12 by 4 without modifying the immutable reconstructed baseline. All 82
Windows tests pass, JavaScript syntax and Python compilation pass, and the
offline eight-frame diagnostic validates both fixtures' zone 12/13 boundary
with no socket creation. After deployment, acceptance requires a low-brightness
physical marker test of that row transition on both fixtures. Channels 145-152
and 297-304 remain zero.

Each LF4808 also has two central white rows outside the 12-by-4 RGB grid. Their
eight-part mapping has now been physically commissioned and encoded. The browser
shows both rows and exposes separately gated audio peaks only in browser live.

## Prior checkpoint — integrated Pi validation

The Pi-only work was preserved on
`pi-recovery-before-sync-20261020` and reviewed on Windows. It adds browser
preview/control, versioned atomic user-look and scene persistence, deterministic
scene sequencing, Pi diagnostic scripts, the managed QLC+ unit, and complete
commissioning evidence. The recovery branch passes all 82 automated tests under
Python 3.12 with `PYTHONPATH=src`; simulation tests prove that browser actions
cannot construct an Art-Net sender.

On 2026-10-20 the merged `main` at `67004ad` was deployed through
`scripts/pi-update.sh`. Installation succeeded and all 82 hardware-free tests
passed on the Pi in 0.299 seconds. The operator opened simulation-only browser
control from the trusted LAN and confirmed that the previews and controls looked
correct. Live activation was unavailable in this mode as designed.

After stopping browser simulation, the operator ran a ten-second direct plasma
test at speed 0.2 and brightness 0.15. They confirmed that both cubes lit, the
animation was visible, and both cubes returned to darkness automatically at
normal shutdown. This revalidates the established direct live path after the
merge. Browser-controlled live activation and its lost-heartbeat blackout
remain separate pending checks; do not infer them from the direct live test.

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
- The operator accepted the browser simulation and reported that a basic
  browser-controlled live check worked. Persistence across restart and the
  five-second lost-browser blackout still need explicit observation; the live
  check also exposed the superseded 8-by-6 preview geometry.
- The original source files from the Raspberry Pi have not been imported and
  compared with the preserved reconstructed baseline.
- The eight white channels on each fixture are commissioned; guarded live peak
  output still requires its first post-implementation Pi validation.

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

1. In browser simulation, visually review the five newest presets, confirm
   Inferno Rise moves upward, verify master brightness persists through scene
   changes, and exercise audio deep dim.
2. With fixtures secured and QLC+ blackout immediately available, validate
   `HW-002` at its default 5% and confirm blackout, Stop output, and browser
   lease loss each disarm physical-white peak output.
3. Defer another deliberate pedal disconnect and all configuration writes to
   the `CONTROL-002` sprint. Keep browser control available as the show backup.
4. Validate the optional elevated RGB ceiling under `SAFE-002` only after the
   default-level live sequence passes.

## Safety invariants

- Simulation remains the default; live transmission requires the literal
  `live` command.
- Ordinary rendering must keep fixture channels 145-152 and 297-304 at zero.
  The commissioned white parts may be activated only through the guarded
  browser-live control: separately armed, 5% default, 10% maximum, pulses no
  longer than 0.10 seconds and no faster than 4 Hz, with all stop paths
  disarming it.
- Cube A remains at A001 and Cube B at A153, both in 152-channel mode.
- Keep the software brightness ceiling at 0.65 and begin hardware validation at
  0.25 or lower.
- Do not enable automatic startup of `phreqed-dmx live` until the manual smoke
  test and shutdown blackout checks have passed.
- Do not edit, import, execute, or reformat files under
  `phreqed-stage-dmx-baseline/` or its ZIP archive.

## Suggested prompt for a new Codex session

```text
Read AGENTS.md, RESUME.md, and docs/kanban.md completely. Verify git status and
the Python test environment before changing anything. Continue the current Pi
bench sequence from "Next actions, in order" on `feat/audio-context`. Treat an
open Ampero MIDI device as transport health only; a mapped event is required
for functional readiness. `CONTROL-002` is a deferred protocol-research sprint,
so do not send configuration writes or add vendor binaries. Do not start live
Art-Net or modify the preserved baseline without explicit authorization.
```
