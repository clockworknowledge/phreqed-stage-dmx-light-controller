# Project Kanban

Last reviewed: 2026-10-20

This board is the repository's source of truth for feature status. Keep card IDs
stable in commits, issues, and implementation reports. Move a card between
lanes when its status changes; do not duplicate it. New work normally enters
the backlog and moves to Ready only when its acceptance criteria and safety
impact are understood.

## Workflow

`Backlog -> Ready -> In progress -> Validation -> Done`

- **Backlog:** useful work that is not yet sufficiently defined or prioritized.
- **Ready:** scoped work with testable acceptance criteria and no known blocker.
- **In progress:** actively being implemented; keep this lane small.
- **Validation:** implementation is complete but still needs automated, visual,
  Raspberry Pi, or physical-hardware verification.
- **Blocked:** work waiting for hardware, source files, a decision, or another
  explicit dependency.
- **Done:** implemented, documented, tested, and committed.

Priority uses `P0` for safety/release blockers, `P1` for the next major project
outcome, `P2` for important improvements, and `P3` for optional polish.

## In progress

No active implementation.

## Ready

### SPRITE-001 — Production sprite renderer (`P2`, visuals)

Promote experimental sprite helpers into the normalized rendering pipeline with
front-view placement, clipping, palette tinting, scaling suitable for a 12 x 4
grid, and optional cross-cube layouts.

Acceptance: sprite rendering is address-independent and deterministic, clips
safely, supports both fixtures independently, and has visual regression tests.

## Validation

### REL-002 — Persistent show controls and MIDI recovery (`P0`, reliability)

Browser preset and scene changes now preserve the operator's master brightness
override. The Ampero raw-MIDI worker no longer terminates permanently after a
transient select/read/disconnect error: it closes the descriptor, retries the
same configured path, contains command/reporting failures, and exposes
connection, message, and reconnect counts in the browser.

Acceptance remaining: deploy to the Pi, verify brightness through repeated
scene navigation, then perform a rehearsal-length pedal soak including one
controlled USB disconnect/reconnect. A stable udev path is still required to
survive ALSA card renumbering.

### EFFECT-003 — Music-driven stage look expansion (`P1`, visuals)

Three deterministic effects and five presets add Matrix Rain, cross-fixture
blaster/flame sweeps, a dynamics-driven sine/cosine ribbon, and an inside-out
VU. Inferno Rise now places its heat source on logical row 3 (the confirmed
physical bottom) and advects turbulence upward. Automated tests cover geometry,
determinism, fixture independence, RGB ranges, and zero white-channel output.

Acceptance remaining: review all five looks in browser simulation, confirm
Inferno Rise rises upward with fixtures upright and printed text readable, and
run a low-brightness live scene check.

### SAFE-002 — Explicit show-time RGB ceiling (`P0`, safety)

The default 0.65 RGB ceiling remains unchanged. A higher process-local ceiling
now requires the literal `live` command and `--acknowledge-high-output`; both
the compositor and frame limiter receive the selected value. Browser live still
starts at 0.25 or lower, displays the elevated ceiling and warning, and rejects
master levels above it. Saved presets remain capped at 0.65, luminance-rise and
flash-interval safeguards remain active, and the white commissioning tool keeps
its independent 10% ceiling.

Acceptance remaining: pull to the Pi, verify default and elevated browser
slider bounds without fixtures, then perform a deliberate stepped live check on
the physically secured show rig with QLC+ blackout immediately available.

### AUDIO-003 — Shared tempo and dynamics clock (`P1`, music)

All registered effects now use a shared continuous animation clock. Tap tempo
sets the baseline rate, `--speed` remains an operator trim, and smoothed music
dynamics provide a bounded 1.0x-2.0x motion multiplier. Audio also modulates
output from 55%-100% of the manual master without raising the RGB ceiling.
The browser exposes both live multipliers and an opt-in deep-dim mode with an
adjustable 0%-25% quiet floor. Silence preserves tempo-driven motion. No new
runtime dependency was added.

Acceptance remaining: visually validate every preset with rehearsal-level
Snowball input, tune the response curves, and confirm 25 FPS timing in the Pi
soak before calling the dynamics model performance-ready.

### AUDIO-002 — Real-time audio synchronization (`P1`, music)

Explicit `arecord` mono capture, deterministic PCM analysis, adaptive ambient
noise handling, capture health, browser meters, and silence-on-input-loss are
implemented without a new dependency. The Blue Snowball hardware name and raw
input levels have been verified on the Pi. Capture remains off unless an ALSA
device is explicitly supplied and cannot select or enable Art-Net output.

The operator subsequently confirmed the full simulation path on the Pi: audio
capture, browser meters, and the reactive Phase Collider visual all responded.
No Art-Net output was enabled during this test.

Acceptance remaining: document sustained CPU use, analysis latency, and missed
25 FPS frames, then tune sensitivity under rehearsal-level sound. Automatic
scene switching and hard onset flashes remain out of scope.

An integrated, socket-blocked bench mode is now available in `scripts/pi-soak.py`.
It records capture continuity and signal peaks for every effect and preset; its
first Raspberry Pi report remains pending.

### AUDIO-001 — Audio-analysis input contract (`P1`, music)

Normalized loudness, onset, bass, mid, and treble values now enter effects only
through `PerformanceContext.audio`. Dependency-free manual and recorded sources
support deterministic injection and previous-sample replay. The controller can
accept a source without knowing its capture implementation, and radial pulse is
the first bounded consumer. An absent source preserves non-audio behavior.

Acceptance: complete automated validation of ranges, deterministic replay,
controller injection, bounded effect output, simulation isolation, and reserved
DMX channels before merging. Real-time device capture belongs to AUDIO-002.

### SHOWPACK-001 — First performance scene pack (`P1`, visuals)

Eight built-in looks extend the catalog to twelve presets using the existing
deterministic effect and compositor APIs. Three presets deliberately target the
fixtures independently; cross-cube and tap-tempo-aware layers are included.
All new global brightness levels are at or below 0.48, and automated tests
verify deterministic output and zero values on all reserved fixture channels.

Acceptance: visually review all eight looks in browser simulation, then perform
a deliberate low-brightness Pi check before promoting the pack to Done.

### CONTROL-001 — Hotone Ampero foot-controller adapter (`P1`, performance control)

The dependency-free USB MIDI parser and explicit raw-device adapter are
implemented. The operator updated the pedal to firmware 1.1.8, verified notes
60–62 and CC 23 values 127/0 from `/dev/snd/midiC3D0`, and confirmed scene
navigation, tap tempo, and blackout in browser simulation. Guarded browser-live
operation was subsequently reported working correctly. Same-path automatic
reconnect and browser connection counters now prevent a transient device error
from silently ending the reader thread.

Acceptance: create a stable udev link and pass a rehearsal-length USB soak.
Bluetooth MIDI remains a separate follow-up until Pi pairing and reconnect
behavior are characterized.

The integrated soak can now require every mapped action while using a probe
that cannot alter scenes or enable output. Its first Raspberry Pi report remains
pending; the raw device path must still be replaced with a stable udev link.

### MAP-002 — Correct LF4808 geometry to 12 x 4 (`P0`, mapping)

The package configuration, fixture defaults, simulators, browser previews,
legacy compatibility engine, diagnostics, documentation, and automated tests
now use the operator-confirmed 12-column by 4-row front view. The immutable
reconstructed baseline retains its historical 8-by-6 assumption. The prior
corner-only check could not distinguish the two geometries because zones 1 and
48 have the same locations under both layouts.

Acceptance: the Windows and Pi test suites pass, browser and Tk previews show
12 x 4 RGB cells, the browser adds two disabled center strobe reference lines,
and a low-brightness physical test confirms the zone 12-to-13 row transition
independently on both fixtures. White-zone commissioning is tracked separately
by HW-001 and must use its capped steady-output procedure, never a flashing sweep.

### WEB-001 — Validate browser show control on the Pi (`P0`, show control)

The dependency-free browser controller, versioned user-look library, and timed
scene sequencer are implemented and pass the complete 82-test Windows suite.
Simulation and live capability remain separate CLI choices; live activation
requires an additional confirmation and a five-second browser lease.

Pi update and automated validation passed on 2026-10-20: all 82 tests completed
in 0.299 seconds. The operator accepted the trusted-LAN browser simulation, and
a separate ten-second direct plasma test at brightness 0.15 lit and animated
both cubes before normal-shutdown blackout. This confirms the existing direct
live path. The operator subsequently reported that a basic guarded browser-live
check worked; that check exposed the preview's obsolete 8-by-6 geometry, now
tracked by MAP-002.

Remaining acceptance: complete MAP-002, confirm saved looks and scenes survive
a restart, and separately observe the lost-browser timeout safely on both
fixtures.

### PRESET-002 — User preset persistence (`P1`, show control)

The versioned JSON library validates complete documents before atomically
replacing them, preserves typed layer configuration, and keeps built-ins
immutable. Unit coverage includes round trips and failure preservation.

Acceptance: complete after WEB-001 confirms persistence on the Pi.

### SCENE-001 — Scene list and timed transitions (`P1`, show control)

The transport-independent sequencer implements direct, next/previous, timed,
and final-hold behavior with deterministic crossfades and blackout override.

Acceptance: complete after WEB-001 confirms browser operation on the Pi.

## Blocked

### PI-DIAG-001 — Root-cause Pi SSH banner stall (`P1`, reliability)

An interactive Pi Codex session was followed by SSH accepting TCP connections
without sending a protocol banner. A reboot recovered the Pi, but the prior
boot had no persistent journal, so no cause can be established. Persistent
journaling is now enabled. Do not deliberately reproduce this on the lighting
controller; investigate only if it recurs naturally with retained logs.

### RPI-001 — Import and compare original Raspberry Pi scripts (`P1`, baseline)

Blocked on receiving a copy of the actual Raspberry Pi source tree. When it is
available, follow `docs/pi-script-import.md`: copy it into a new dated directory,
hash it, and compare it without changing either preserved baseline.

### HW-001 — Commission LF4808 white-zone mapping (`P0`, safety)

The recovered 152-channel manual identifies channels 145-152 as eight directly,
linearly dimmed white parts. The package mapping and a steady-output diagnostic
are implemented with normalized values, fixture isolation, a hard 10% ceiling,
blackout gaps, and final shutdown blackout. Normal show rendering still leaves
all eight channels zero unless an explicit white-zone frame is supplied.

Acceptance remaining: run `scripts/white-zone-check.py` offline and live at 5%,
record the physical order of Parts 1-8 and whether both white rows respond
together on both fixtures, then add the verified orientation to tests before
building pulse or strobe effects. See `docs/lf4808-white-commissioning.md`.

## Backlog

### WEAR-001 — Performer-safe wearable lighting prototype (`P2`, visual output)

Build one low-profile 20-to-50-pixel prototype using diffused LEDs on a guitar
strap, vest, or shoulder/torso channel. Keep hands and forearms clear; place the
enclosed controller and protected power pack at the rear waist; provide local
power-off, strain relief, quick disconnection, current limiting, and removable
electronics. Begin with WLED/ESP32 or Pixelblaze only as a prototype platform.

Acceptance: a full-motion rehearsal shows no playing restriction, snag hazard,
pressure point, excessive heat, or audible instrument interference; measured
worst-case current and runtime meet the show requirement; startup and fault
states are black; and the unit can be removed quickly. Do not replicate it for
the band before this prototype passes. See `docs/wearable-lighting.md`.

### WEAR-002 — Reliable wireless wearable synchronization (`P2`, transport)

Prototype cue-level synchronization from the Pi using a private WLED network,
then compare it with an ESP-NOW gateway and professional wireless-DMX pixel
hardware. Wearables render locally from cue, palette, level, tempo/phase, and
bounded audio values rather than receiving continuous full-pixel video.

Acceptance: the chosen link has measured latency, loss, recovery, range, and
congested-venue behavior; sequence and heartbeat handling reject stale packets;
brief loss coasts safely and sustained loss fades black; device identity and
group targeting are deterministic; and failures cannot disturb Art-Net, QLC+,
DMX timing, audio capture, MIDI, browser control, or projector output.

### SHOW-003 — Wearables in unified show cues (`P2`, show control)

Add optional wearable states to the planned unified lighting/projector cue.
The current Ampero previous/next and tap-tempo actions control the combined cue,
so no second pedal is required initially. Keep wearable blank separate from the
existing lighting blackout until both paths have independent failure tests; an
additional Ampero bank or second pedal remains optional for wearable-only
triggers.

Acceptance: cues remain valid when no wearable is paired; target groups and
performer assignments are explicit; missing devices report health without
blocking scene changes; show shutdown fades all wearables black; and no pedal
message can implicitly enable DMX or wearable output.

### PROJ-001 — Projector playback foundation (`P2`, visual output)

Add an explicitly enabled projection adapter that plays validated local video
and image assets on a selected Pi HDMI output. Playback runs in a separate
process from the 25 FPS DMX loop and supports load, play, pause, stop, loop,
seek, output blank, and clean shutdown. Media lives outside Git in an
operator-configured library. Compare VLC, `mpv`, and GStreamer/direct-rendering
behavior on the current Debian Trixie Pi before selecting the backend.

Acceptance: no projector is opened by default; hardware-free tests use a fake
player; missing media and player failure fall back to black without disrupting
DMX, audio, MIDI, browser control, or blackout; and a Pi soak documents video
drops, CPU/GPU/memory/temperature, and DMX missed frames at an initial 1080p
target. See `docs/projector-output.md`.

### PROJ-002 — Projector effects and overlay compositor (`P2`, visuals)

Composite local video, stills, colour fields, and lightweight procedural or
shader overlays with crop/fit, opacity, blend modes, intensity limits, and
smooth transitions. Reuse normalized audio analysis only through the existing
performance context. Keep projector frames and RGB fixture grids as distinct
render targets.

Acceptance: deterministic controls and fallback frames are testable without a
display; overlays cannot stall DMX; audio response is bounded; and the target
Pi sustains the selected projector frame rate alongside QLC+, browser control,
microphone analysis, and MIDI input.

### SHOW-002 — Unified lighting and projection cues (`P2`, show control)

Extend show cues so one transport-independent cue can select a lighting preset
and an optional projection preset. The existing Ampero remains sufficient for
the first version: previous/next advance the unified cue, tap tempo is shared,
and the safety switch can blank projection after that path is separately tested.
A second pedal is optional for future independent video transport, not a
requirement for the foundation.

Acceptance: projector failure cannot block lighting commands; lighting blackout
and projector blank remain independently testable; unified cue transitions are
repeatable; missing projection content fails black; and pedal mappings cannot
start live DMX or projector output implicitly.

### VIDEO-001 — Video-to-grid sampler (`P2`, visuals)

Sample video into two normalized 12 x 4 frames with configurable crop, fit,
gamma, brightness, and fixture assignment. Quantization remains at the DMX
boundary.

### SIM-004 — Simulator usability polish (`P2`, simulator)

Add keyboard shortcuts, clearer validation feedback, parameter reset controls,
and an optional dependency-free animation capture workflow.

### EFFECT-020 — Effect gallery and regression frames (`P3`, documentation)

Generate representative simulator images for every effect and preset at fixed
times so performers can browse looks and reviewers can spot visual changes.

## Done

### QLC-002 — Manage headless QLC+ with systemd (`P0`, reliability)

Installed and enabled `config/qlc/qlcplus.service` on 2026-10-19. Managed
stop/start, automatic failure recovery, and reboot startup passed. The service
runs as `mmorley` with the expected HOME and runtime workspace, which matches
Git, and solely owns UDP 6454 and TCP 9999. Automatic live output remains off.

The operator confirmed both fixtures stayed dark through reboot and the
21:21 MDT process-failure recovery. Recovery took five seconds, changing PID
1483 to 2207 with `NRestarts=1`; ports and HTTP 200 recovered. All 57 tests pass.
The operator also confirmed the port 9999 web UI opens on a phone and computer.

Systemd IP filtering permits localhost and `192.168.1.0/24`, denying other
IPv4/IPv6 traffic. Local probes pass on permitted addresses and time out on the
Pi's global IPv6 address. The operator confirmed the global IPv6 URL was
denied from another device while the standard IPv4 LAN URL still worked.
This completes the planned independent permitted/denied browser checks.
The service and commissioning evidence were reviewed and committed in
`7f6faee`; this update records final network acceptance.

Acceptance: a service running as `mmorley` loads
`/home/mmorley/.qlcplus/autostart.qxw`, starts after reboot without a physical
display, owns the expected ports, exposes its web UI only on the trusted stage
LAN, and stops/restarts without unsafe retained output.

### LIVE-001 — Controlled two-fixture live smoke test (`P0`, hardware)

Passed on 2026-10-19 at brightness 0.25 and 25 FPS. The 15-second slow plasma
check confirmed both cubes respond and go dark on normal shutdown. The
24-second `scripts/fixture-check.py live` sequence then confirmed independent
A001/A153 control, red top-left and blue bottom-right positions, colours,
isolation, and final blackout through operator observation. Exact marker
frames were validated offline; all unverified channels remained zero.
Both live commands exited 0. Results were reviewed and committed with this update.

Acceptance: Cube A responds only at A001, Cube B only at A153, front-view
orientation is correct, normal shutdown blackouts both cubes, and all sixteen
unverified channels remain zero. Evidence is in the Phase 2 report. Physical
handled-interruption blackout subsequently passed: Ctrl+C was handled with
exit 0, and the operator confirmed both cubes went dark. A full per-pixel
sweep was not tested.

### RPI-002 — Raspberry Pi 25 FPS soak test (`P0`, reliability)

Passed 2026-10-19 with `scripts/pi-soak.py`: 30 seconds for each of the
19 effects and four presets, 17,250 frames over 690 seconds, 25.0 FPS,
zero missed slots or overruns. Worst frame was 11.971 ms; peak RSS was
25,488 KiB and CPU temperature 50.7 C. All reserved-channel and in-memory
blackout checks passed. Harness exited 0; results were reviewed and committed with this update.

Both cubes, safety limiting, and DMX serialization were exercised in memory
with sockets blocked. Tkinter, transport, and physical output were excluded.
Raw evidence: `docs/validation/pi-soak-2026-10-19.json`; measurements and limits
are recorded in the Phase 2 implementation report.

Acceptance: every effect and preset sustains 25 FPS with useful headroom,
CPU/memory measurements and shutdown checks are recorded, the harness exits
cleanly, and results are added to the report. Slow effects receive a repeatable
benchmark and either optimization or a documented limit.

### DEPLOY-001 — Complete independent Pi installation (`P0`, deployment)

Pi verification on 2026-10-19: `bash scripts/pi-install.sh` exited 0 on
Debian 13.7 / Python 3.13.5, package 0.2.0 installed, all 57 tests passed,
and `.venv/bin/phreqed-dmx --help` loaded. Evidence is recorded in `RESUME.md`;
the evidence was reviewed and committed with this update.

Acceptance: installer completes on the Pi, all 57 tests pass, CLI help loads
from `.venv`, and the evidence is added to the handoff or implementation report.

### P2-VAL-001 — Phase 2 validation on target hardware (`P0`, release)

The Phase 2 engine passes Windows automated and simulator checks, the Pi
headless rendering soak, and the controlled physical smoke check. RPI-002 and
LIVE-001 are Done; reviewed results and limits are in the Phase 2 report.

Acceptance: both linked cards are Done and the Phase 2 report contains their
measured results and any resulting operating limits.

- **QLC-001 (`P0`)** — Captured and reviewed the known-good QLC+ 4.14.1
  workspace with universe 0 Art-Net input, passthrough, and the FT232R USB-DMX
  output; no credentials or private paths are embedded.
- **OPS-001 (`P1`)** — Added independent Raspberry Pi install and guarded update
  scripts that require no Codex, VS Code, or Windows host after deployment.
- **OPS-002 (`P1`)** — Enabled persistent systemd journaling on the Pi so future
  crashes and previous-boot kernel/service events remain diagnosable.
- **FOUND-001 (`P0`)** — Python 3.11+ package, simulation-first CLI, fixture
  configuration, ArtDMX transport, and hardware-free test environment.
- **MAP-001 (`P0`)** — Independent A001/A153 start-address mapping, RGB channel
  order, endpoint orientation, and zero output on unverified channels. Its
  historical 8-by-6 geometry claim is superseded by MAP-002.
- **SAFE-001 (`P0`)** — Explicit-only live mode, brightness ceiling, frame-rise
  limiting, clamping, and best-effort shutdown blackout.
- **EFFECT-001 (`P1`)** — Standard typed, metadata-rich, address-independent,
  deterministic effect interface.
- **EFFECT-002 (`P1`)** — Nineteen registered effects: the fifteen Phase 2
  procedural generators plus the four preserved baseline families.
- **COMP-001 (`P1`)** — Normalized multi-layer compositor with opacity, alpha,
  additive and lighten blends, spatial masks, fixture targeting, and crossfades.
- **SIM-001 (`P1`)** — Interactive dual-cube Tkinter simulator with independent
  effects, validated parameters, pause/step, FPS, blackout, and PPM export.
- **SIM-002 (`P0`)** — Regression coverage proving simulator execution never
  constructs an Art-Net sender.
- **SHOW-001 (`P1`)** — Transport-independent effect, parameter, preset, event,
  blackout, tap-tempo, and scene-navigation commands.
- **PRESET-001 (`P1`)** — Psychedelic Bloom, Molten Motion, Digital Storm, and
  Energy Bridge example presets. SHOWPACK-001 adds the next eight looks.
- **TEST-001 (`P0`)** — One hundred one Windows-compatible tests covering effects,
  composition, fixtures, scenes, persistence, browser safety, blackout, ArtDMX
  integrity, and simulation network isolation.
- **DOC-001 (`P1`)** — Architecture, effect catalog, installation, operation,
  deployment, baseline, and Phase 2 implementation documentation.

## Safety gate for every card

Before moving work to Done, confirm that simulation remains the default, live
output still requires explicit selection, both fixtures remain independent,
DMX values are bounded, and channels 145–152 on each fixture are untouched.
Changes affecting timing or live output also require the relevant shutdown and
blackout tests.
