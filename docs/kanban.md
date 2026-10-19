# Project Kanban

Last reviewed: 2026-10-19

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

No cards currently in progress.

## Ready

### RPI-002 — Raspberry Pi 25 FPS soak test (`P0`, reliability)

Run every registered effect and example preset on the Raspberry Pi 5 for an
extended simulation-only session. Record render time, achieved FPS, CPU load,
memory stability, and any dropped-frame or shutdown issues.

Acceptance: the engine sustains 25 FPS with useful headroom, exits cleanly, and
the results are added to the implementation report. Any slow effect receives a
repeatable benchmark and either an optimization or a documented limit.

### LIVE-001 — Controlled two-fixture live smoke test (`P0`, hardware)

Verify the packaged engine through the known-good QLC+ and FTDI path using low
brightness, static or slowly moving output, and an operator-accessible blackout.

Acceptance: Cube A responds only at A001, Cube B only at A153, front-view pixel
orientation is correct, normal shutdown blackouts both cubes, and all sixteen
unverified channels remain zero. Record the test date and configuration.

### PRESET-002 — User preset persistence (`P1`, show control)

Add a versioned, human-readable preset file format for named layers,
per-fixture selections, palettes, and validated effect parameters. Keep built-in
presets immutable and distinguish them from user presets.

Acceptance: presets round-trip without losing typed values, invalid files fail
with useful messages, simulator loading cannot enable live output, and tests
cover schema/version handling.

### SCENE-001 — Scene list and timed transitions (`P1`, show control)

Build a transport-independent ordered scene model on top of the existing show
commands and compositor transitions.

Acceptance: next/previous/direct selection and timed crossfades are deterministic,
blackout overrides every scene, and the model runs without Art-Net or Tkinter.

### SPRITE-001 — Production sprite renderer (`P2`, visuals)

Promote experimental sprite helpers into the normalized rendering pipeline with
front-view placement, clipping, palette tinting, scaling suitable for an 8 x 6
grid, and optional cross-cube layouts.

Acceptance: sprite rendering is address-independent and deterministic, clips
safely, supports both fixtures independently, and has visual regression tests.

## Validation

### P2-VAL-001 — Phase 2 validation on target hardware (`P0`, release)

The Phase 2 engine passes all Windows automated and simulator checks. Raspberry
Pi timing and physical output remain to be validated by RPI-002 and LIVE-001.

Acceptance: both linked cards are Done and the Phase 2 report contains their
measured results and any resulting operating limits.

## Blocked

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

### CUE-001 — Show-file and cue sequencing (`P2`, show control)

Persist ordered scenes, transitions, labels, and safe defaults in a portable
show file after PRESET-002 and SCENE-001 establish their formats.

### SIM-004 — Simulator usability polish (`P2`, simulator)

Add keyboard shortcuts, clearer validation feedback, parameter reset controls,
and an optional dependency-free animation capture workflow.

### EFFECT-020 — Effect gallery and regression frames (`P3`, documentation)

Generate representative simulator images for every effect and preset at fixed
times so performers can browse looks and reviewers can spot visual changes.

## Done

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
- **TEST-001 (`P0`)** — Fifty-seven Windows-compatible tests covering effects,
  composition, fixtures, blackout, ArtDMX integrity, and network isolation.
- **DOC-001 (`P1`)** — Architecture, effect catalog, installation, operation,
  deployment, baseline, and Phase 2 implementation documentation.

## Safety gate for every card

Before moving work to Done, confirm that simulation remains the default, live
output still requires explicit selection, both fixtures remain independent,
DMX values are bounded, and channels 145–152 on each fixture are untouched.
Changes affecting timing or live output also require the relevant shutdown and
blackout tests.
