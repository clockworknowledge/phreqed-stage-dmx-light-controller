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
front-view placement, clipping, palette tinting, scaling suitable for an 8 x 6
grid, and optional cross-cube layouts.

Acceptance: sprite rendering is address-independent and deterministic, clips
safely, supports both fixtures independently, and has visual regression tests.

## Validation

### WEB-001 — Validate browser show control on the Pi (`P0`, show control)

The dependency-free browser controller, versioned user-look library, and timed
scene sequencer are implemented and pass the complete 82-test Windows suite.
Simulation and live capability remain separate CLI choices; live activation
requires an additional confirmation and a five-second browser lease.

Acceptance: the Pi passes all 82 tests; browser simulation is usable from a
trusted LAN device without Art-Net transmission; looks and scenes survive a
restart; guarded live start, explicit stop, blackout, and lost-browser timeout
are observed safely on both fixtures.

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

### HW-001 — Identify LF4808 channels 145–152 (`P0`, safety)

Blocked on authoritative fixture documentation or a separately approved,
controlled hardware investigation. These channels may include strobe or other
high-output functions and must remain zero throughout normal development.

Acceptance: each function is confirmed from trustworthy evidence and any live
test has an explicit low-risk procedure before configuration or code changes.

## Backlog

### AUDIO-001 — Manual audio-analysis input contract (`P1`, music)

Define transport-independent tempo, beat, onset, loudness, and frequency-band
inputs in the performance context before selecting an audio capture library.

### AUDIO-002 — Real-time audio synchronization (`P1`, music)

Add opt-in audio capture and analysis after AUDIO-001. Effects must continue to
render deterministically when supplied recorded analysis frames.

### CONTROL-001 — Foot-controller adapter (`P1`, performance control)

Map future hardware events onto the existing show-command interface. Hardware
drivers must not be imported by the visual engine or simulator.

### VIDEO-001 — Video-to-grid sampler (`P2`, visuals)

Sample video into two normalized 8 x 6 frames with configurable crop, fit,
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
- **MAP-001 (`P0`)** — Independent A001/A153 fixture mapping with verified 8 x 6
  front-view orientation and zero output on the unverified channels.
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
  Energy Bridge example presets.
- **TEST-001 (`P0`)** — Eighty-two Windows-compatible tests covering effects,
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
