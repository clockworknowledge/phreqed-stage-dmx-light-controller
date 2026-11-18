# Project Kanban

Last reviewed: 2026-11-17

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

The planned Song Builder and setlist work is sequenced in
[`song-setlist-roadmap.md`](song-setlist-roadmap.md). Its sprint numbers express
dependency order; the cards below remain the source of truth for status.

The planned separation between the show-critical Stage appliance and the
browser-based Studio authoring application is sequenced in
[`studio-stage-roadmap.md`](studio-stage-roadmap.md). That roadmap contains the
detailed user stories, package/sync rules, and sprint acceptance. The cards
below remain independently movable and are the source of truth for status.

Active checkpoint (updated 2026-11-16): `PROJ-001` and the first `SHOW-002`
transport slice are in progress. Perform touch
polish, timeline editing, venue-profile shortcuts, prepared-white adjustment,
the Pac-Man ghost/power-pellet cycle, and the Burning Dynamite animation are
implemented. The White Output v2 drive/power contract and the base touchscreen
iteration are accepted in deployed Pi use; the complete controller is covered
by the Windows Python 3.12 suite. Remaining touchscreen work is
ongoing performance acceptance under `DISPLAY-003`, the `OPS-007` local-action
checks, and the controlled shutdown/power-cycle evidence under `OPS-005`. Pi
thermal telemetry is optional follow-up work and is not a show-control
dependency.

Planning checkpoint (2026-11-16): Phreqed Studio is now planned as a hosted,
multi-tenant, AI-augmented SaaS product with Free, Artist (`$`), and Pro (`$$$`)
capability envelopes. The current reference persona is a Pro band customer with
private VFX/video storage, clip preparation, full lighting and Video Scene
authoring, AI proposal allowances, and paired Stage delivery. Published Stage
packages remain complete, cached, and playable offline; subscription or cloud
failure can block new hosted work but never an active show.

## In progress

### PROJ-001 — Projector playback foundation (`P1`, visual output)

Add an explicitly enabled projection adapter that plays validated packaged
video/image renditions on a selected Pi HDMI output. Playback runs in a separate
process from the 25 FPS DMX loop and supports pre-load, invisible pre-roll,
play, pause, stop, loop, seek, output black, position/health reporting, and clean
shutdown. It never streams show-critical media from Studio.

Implementation checkpoint (2026-11-16): package preflight, the disabled-by-
default transport boundary, fixed confirmation-gated VLC launch, commissioned
clockwise rear-screen profile, and full-length soak harness are implemented.
The 146-second package passes local preflight. The commissioned Pi soak passed
all automated checks on 2026-11-16: VLC exited 0 after 146.444 seconds; the
independent renderer delivered 3,662 frames at 25.006 FPS with zero missed slots
and zero overruns; mean/p95/max render times were 4.578/5.650/13.389 ms; player
and renderer CPU were 20.44% and 11.63% of one core; player RSS peaked at
145,808 KiB; and CPU temperature peaked at 41.35 C. Reserved channels stayed
zero and final renderer blackout passed. Evidence is in
`docs/validation/projection-soak-2026-11-16.json`.

Operator review reported clean visual playback with no observed stall or
judder, completing the initial smoothness observation. VLC again fell back from
unavailable V4L2 H.264 decoding to I420 Wayland `wl_dmabuf` output. The
SSH/Wayland `globalhotkeys` and `xset` warnings did not prevent playback or clean
exit. VLC 3 dropped-frame telemetry remains explicitly unavailable rather than
assumed to be zero.

The test also confirmed a layout requirement: `contain` made the landscape
source too small on the vertical screen. Stage media now has two explicit
authoring layouts—Stage Portrait 9:16 fill and Standard Landscape 16:9 fill—with
front/rear mirroring independent of layout. Portrait character scenes use
`cover` and reviewed focal framing so dancers can appear stage-sized.
The 15-second Stage Portrait rear-screen probe then passed physical review on
the vertical projector; the operator confirmed the larger fill presentation
looked correct. Standard Landscape remains logically/preflight validated but
awaits a physically horizontal screen.

The next adapter slice is now implemented behind explicit `live --web` and
`--video-output` opt-ins. A bounded local registry preflights and hash-verifies
every direct-child package manifest before output starts. The managed VLC
process launches only a resolved package ID, can begin at the current cue
offset with VLC `--start-time`, and is terminated on Video black/stop. This
does not yet satisfy the final fail-black contract: stopping VLC currently
reveals the commissioned compositor/desktop background rather than an
independently supervised black surface.

Physical routing checkpoint (2026-11-16): the Pi exposes `DSI-1` at desktop
position `0,0` and `HDMI-A-2` at `1280,0`. VLC's Qt numeric screen selector was
rejected because both screen values opened on the touchscreen. A direct
XWayland/XCB VLC window plus a Labwc `identifier="vlc"` rule using
`MoveToOutput output="HDMI-A-2"` and `ToggleFullscreen` passed physical review:
projection appeared on HDMI while the Stage touchscreen remained visible.
Labwc reported no configuration errors. The managed adapter and idempotent
Labwc configuration helper now encode that route.

Bench acceptance checkpoint (2026-11-16): the redeployed managed service kept
Stage control on `DSI-1` and projected Video on `HDMI-A-2`. Foot-controlled
Start and Stop operated the Video lane while the song's Lighting sequence ran
in parallel. Blackout stopped output and returned the song and Video transport
to the start. The operator observed no obvious playback lag, although a longer
full-song drift/soak check remains open. Stop and blackout currently reveal the
projector desktop, confirming the need for `PROJ-004` before fail-black
acceptance.

Acceptance remaining: compare or instrument a backend with queryable frame
telemetry, run actual-DMX coexistence, then fault-test and complete managed
pre-load/pause/seek/output-black behavior.
Missing media, player crash, and display loss must fail black without disturbing
lighting, audio, MIDI, browser control, or shutdown. See
`docs/projector-output.md`.

### SHOW-002 — Parallel lighting and video song transport (`P1`, show control)

Extend each song revision with separate Lighting and Video tracks aligned to one
transport-independent clock. Track cue boundaries may differ; Video cues select
versioned Video Scenes and may include intentional black gaps.

Implementation checkpoint (2026-11-16): the first Stage-bound transport slice
is implemented. A separate atomic Video Show sidecar stores versioned Video
Scenes, published song Video tracks, active-track assignments, logical surface
IDs, and package IDs without media paths. Existing `songs.json`, cue sheets, and
setlists remain unchanged. The parallel runner derives Video timing from the
existing Lighting timeline start and position, jumps skipped updates directly
to the current Video cue/offset, blacks on selection/stop/completion, preserves
no-autostart, and contains Video output failure without stopping Lighting.
Published tracks and their referenced scenes are immutable. The first reference
track is **Travelling on a Floating Rock** targeting `portrait-character` with
the full-length Stage Portrait package. That 146-second 1280×720/30 FPS
portrait-fill package now renders and passes Stage preflight. The existing
Setlist Start/Stop path can now own this optional Video runner without changing
the Lighting timeline: Start launches the active Video Scene from the same
clock, while stop, song selection, completion, blackout, or Manual mode stop
the player. Video state is reported under the performance state, and player
failure remains contained from Lighting.

The reference publisher resolves the exact existing title **Travelling on a
Floating Rock** to its real `songs.json` ID, confirms setlist membership and a
locally preflighted package, then creates only `video-show.json`. It is
idempotent for the same publication and refuses to replace a different existing
sidecar; it never rewrites song, cue-sheet, setlist, or tuning data.

Acceptance remaining: verify full-song audio/video/Lighting alignment and drift
with fixtures, add shared
pause/resume/seek, expose a Video lane in Song Builder, and wire Ampero
show-level transport only after projection black is fault-tested.

## Ready

### SHOW-006 — Cross-surface Lighting/Video choreography (`P1`, show authoring)

Create a reusable stage language for short **Echo**, **Throw**, **Catch**,
**Ping-pong**, **Bridge**, **Unison**, and **Counterpoint** phrases across Cube A,
the portrait projector, and Cube B. Use the existing shared song clock,
deterministic Lighting cues, and pre-rendered Video package; do not add a live
compositor or allow Video timing/failure into the 25 FPS Lighting loop.

User outcome: primary clips can breathe while selected VFX cycle through the
spaces between them, and motion can appear to bounce from light to screen to
light as one intentional stage composition. Preserve black/rest intervals and
keep the performer, not the projection, as the focal point.

Acceptance: calibrate the audience-view stage path; prove at least five named
patterns in a Travelling revision; record every event's musical anchor,
initiating/receiving surface, direction, palette, intensity, transition, and
fallback; retain Start/Stop/Blackout/no-autostart/Video-disabled/fail-black
behavior; sustain 25 FPS with measured Pi CPU/RSS/temperature and final drift;
publish beside the accepted hybrid revision with rollback. Extract the proven
fields and preview needs into `STUDIO-004` rather than making Studio or AI a
Stage runtime dependency.

Dependencies: the accepted parts of `SHOW-002`, `PROJ-001`, `PROJ-004`, and the
deployed `SHOW-005` hybrid. Detailed slices and user stories are in
[`integrated-vfx-sprint.md`](integrated-vfx-sprint.md).

### SHOW-007 — Christmas integrated VFX mini-pack (`P1`, seasonal show authoring)

Author a small optional seasonal pack using the `SHOW-006` cross-surface
language: **Neon Snow**, **Signal Garland**, and **Electric Ornament / Starburst**,
with an optional darker **Krampus Signal** variant. Keep the visual direction
consistent with the existing charcoal, acid-green, energetic stage identity
rather than producing continuous novelty footage.

User outcome: upcoming Christmas shows can gain recognizable seasonal moments
that interact with the cubes and projection while remaining suitable for a
live band and removable from any non-seasonal show.

Acceptance: each motif has owned/licensed or procedural sources, portrait and
future-landscape notes, palette/intensity variants, an explicit black fallback,
and one real-song example; deliberate white accents retain all current White
Output controls; the pack is optional, versioned, rollback-safe, and passes the
same Pi coexistence/fail-black rehearsal as `SHOW-006`.

Dependencies: `SHOW-006`; source preparation uses `MEDIA-001/002` concepts but
the Stage proof may use the current local EDL workflow. Target the upcoming
Christmas performances without making an untested pack show-critical.

## Validation

### SHOW-005 — Travelling synchronized Lighting/Video scene (`P1`, show authoring)

Build the first intentionally authored hybrid scene for **Travelling on a
Floating Rock**. As a performer, I want selected VFX segments and the song's
Lighting scenes to change on one reviewed musical timeline so the projection
and Betopper cubes feel like one designed show rather than two parallel loops.

Use non-destructive source ranges from the existing Infinity VFX library,
retain immutable source hashes, and create a new versioned Video EDL/package.
Map Video Scene boundaries, fades, and intentional black intervals to reviewed
Lighting cue boundaries without rewriting the authoritative song, setlist, or
existing published baseline. Publish through the separate Video Show sidecar.

Acceptance: a cue map documents the musical section, Lighting scene, Video
segment, transition, and expected start time; package preflight passes; Start,
Stop, Blackout, and no-autostart semantics remain intact; the full song has no
obvious transition discontinuity or cumulative drift; and failure of the Video
lane leaves Lighting and stage control available. The resulting structure must
remain suitable for the later Studio Video Scene/timeline editor.

Dependencies: physical acceptance of `PROJ-004`, reviewed VFX source selection,
and the existing `SHOW-002` shared transport.

Implementation checkpoint (2026-11-17): version 2 of the non-destructive Video
EDL now supports an absolute song clock, a persistent black canvas, overlapping
layers, opacity/fades, and normal/screen/add/lighten blends while version 1
packages remain backward compatible. The first 180-second Travelling hybrid map
uses seven sparse phrases (69 visible seconds total) aligned to the current
Lighting cue boundaries, with long intentional black intervals. It selects
Chaotic Energy, Duality, Energy Disperse, Ember Patterns, Fluid Smoke, Electric
Ribbons, and two shockwave sources from the existing Infinity VFX library and
combines them with master-video fragments no longer than ten seconds. A local
source-review board and four-second previews support source review without
committing licensed media.

Render checkpoint (2026-11-17): the complete 180-second Stage package rendered
successfully in 70 minutes 48 seconds and passed local hash/package preflight at
1280×720/30 FPS. The 55,413,480-byte MP4 has SHA-256
`b3e9049e4e908e9e62de7d03646f0e5b085b0055e31dacb7e0fb2661fd376274`.
Contact-sheet sampling confirms all seven visual phrases and every sampled
intentional-black interval.

Pi checkpoint (2026-11-17): the hybrid package was transferred, preflighted,
and published as a new immutable Video revision while preserving the baseline
revision and existing song/setlist/configuration data. Bench operation is
working well and the operator reports that the sparse primary clips and VFX
already create promising interplay with the Lighting sequence. Remaining
acceptance is a recorded full-song drift observation plus player-failure and
projector-disconnect confirmation for this exact package. The successful
interplay seeds `SHOW-006` rather than expanding this card indefinitely.

### DISPLAY-001 — Adaptive local stage touchscreen umbrella (`P1`, operations)

The touchscreen program is tracked by the independently movable child cards
below. The shared adaptive shell, stage dashboard, trusted leases, optional
kiosk, authoring redesign, and local Operations boundary are implemented. The
umbrella remains in Validation until `DISPLAY-003` records the complete Pi and
Waveshare acceptance run. Detailed design and acceptance steps are in
[`touchscreen-control-roadmap.md`](touchscreen-control-roadmap.md).

Iteration checkpoint (2026-11-16): the operator reports that the base interface
and UX improvements are solid in current Pi use. Future performance-driven
refinements will be logged as focused follow-up cards rather than reopening the
accepted foundation children.

Children: `UX-001`, `WEB-002`, `DISPLAY-002`, `SAFE-003`, `OPS-006`, `WEB-003`,
`OPS-007`, and `DISPLAY-003`. The optional `AI-DATA-001` spike is related but
is not a display or live-show dependency.

### OPS-007 — Loopback-only display and network operations (`P0`)

Fixed local endpoints, five enumerated backlight levels, four enumerated
NetworkManager actions, exact typed network confirmation, root-owned helper
units, and an exact polkit allowlist are implemented. Non-loopback requests,
unknown actions, shell-like values, and network changes while output or a song
is active are rejected. Simulation never receives this authority.

Acceptance remaining: verify the Waveshare backlight sysfs device, every fixed
NetworkManager action, loopback continuity, remote rejection, and recovery
messages on the Pi.

The 2026-11-16 report of stable kiosk operation and no display blanking or
timeouts supports `OPS-006`; it does not yet exercise this card's backlight and
network mutation boundaries, so `OPS-007` remains in Validation.

### DISPLAY-003 — Pi touchscreen and show-readiness acceptance (`P0`)

Run and record Sprint 6 from
[`touchscreen-control-roadmap.md`](touchscreen-control-roadmap.md): touch and
readability, service ordering, headless fallback, kiosk recovery, blank/wake,
25 FPS, all lease-loss combinations, private-network switching, reserved DMX
channels, and clean shutdown. This card cannot move to Done from desktop tests.

Iteration checkpoint (2026-11-16): the base touchscreen is looking good during
Pi testing. Keep this card in Validation while real performance use reveals any
remaining touch, readability, or workflow adjustments.

### OPS-008 — Pi thermal telemetry in Operations (`P2`, diagnostics)

Operations now exposes read-only CPU temperature through structured health. A
small injected reader parses `/sys/class/thermal/thermal_zone0/temp` without a
shell, rejects malformed, non-finite, negative, or implausible values, and
reports **Unknown** without changing output, leases, timelines, startup, or
headless operation. Informational bands are Normal below 70 C, Warm from 70 C
to below 80 C, and Hot at 80 C or above. Windows-compatible tests cover parsing,
thresholds, injection, and the read-only live-state boundary.

Acceptance remaining: confirm a numeric reading and correct state label on the
commissioned Pi during the next deployment.

### SIM-004 — Simulator usability polish (`P2`, simulator)

The Tk simulator now provides visible shortcut guidance and status feedback,
Space pause/resume, Right-arrow frame step, `B` blackout, `R` reset, per-fixture
and global parameter reset controls, and dependency-free PNG as well as PPM
capture. Resetting keeps the selected effects while restoring their validated
defaults and the deterministic clock.

Acceptance remaining: exercise the complete control set in the actual Tk window
on Windows and the Pi, including both fixture previews and saved PNG output.

### EFFECT-020 — Effect gallery and regression frames (`P3`, documentation)

`scripts/render-effect-gallery.py` now generates a responsive, hardware-free
catalog for all 27 effects and 23 presets at fixed 0.00, 1.75, and 4.00 second
marks. It writes dependency-free RGB PNGs plus a manifest with stable SHA-256
digests, calls the scene engine directly, and is tested with socket creation
blocked. Desktop and phone-width Chromium review confirmed both-fixture previews
without horizontal overflow.

Acceptance remaining: perform the first human catalog review and decide which
curated images, if any, should become committed regression baselines. Generated
working output remains ignored until that policy is chosen.

### VIDEO-002 — Local Video EDL and Stage rendition baseline (`P1`, media)

A versioned, non-destructive Video EDL now references logical asset IDs rather
than developer filesystem paths. The shell-free build pass validates sequential
clip ranges, cover/contain fitting, focal points, fades, logical portrait or
landscape canvases, and optional output rotation before producing an audio-free
H.264 High 4.1 `yuv420p` Stage rendition. The package manifest records the full
EDL plus source, EDL, and output SHA-256 hashes. Stage preflight rejects missing,
tampered, escaping, mismatched, or unsupported renditions. Projection remains
disabled and black without an explicitly injected player backend.

The five-second Travelling probe rendered successfully at 1080×1920, 30 FPS
with no audio, and its generated package passed the same Stage preflight.
`scripts/projector-probe.py` inventories display connectors and installed player
candidates without changing the Pi or opening a projector.

Pi checkpoint (2026-11-16): `DSI-1` is the 1280×800 touchscreen and connected
`HDMI-A-2` is the projector at its current/preferred 1280×720@60 mode, positioned
at `1280,0` with compositor transform `normal`. VLC/cVLC and FFmpeg/FFprobe are
installed; mpv and GStreamer are absent. Clockwise and counter-clockwise logical
720×1280-to-signal-1280×720 probes covered physical commissioning, and the
operator-run VLC probe is bounded, audio-free, screen
selectable, Wayland-aware, and confirmation-gated. Both front-projection probes
displayed and exited successfully. The V4L2 H.264 decoder attempt fell back to
Wayland I420 output, so full-song CPU, temperature, and frame-drop soak remains
open. An EDL-level rear-screen horizontal mirror and matching two orientation
probes keep front/rear placement independent of physical rotation. Physical
testing selected `clockwise` plus `horizontal_flip: true` for the commissioned
vertical rear-screen setup; counter-clockwise remains diagnostic only.

Acceptance remaining: select and soak a player backend under `PROJ-001`, author
the first real Travelling clip/VFX EDL, and verify playback fails black without
disturbing the 25 FPS lighting path. Overlays and parallel song
transport remain `PROJ-002` and `SHOW-002` rather than expanding this baseline.

### AI-DATA-001 — Relate offline-memory feasibility spike (`P2`)

The proposed song/analysis/section/feature/proposal/evidence/review graph,
single-writer boundary, read-only MCP access, bounded directory store, export,
backup, and schema-migration gates are documented in
[`relate-ai-memory-spike.md`](relate-ai-memory-spike.md). Relate is not installed
and the JSON libraries remain authoritative.

The Studio/Stage boundary makes the Studio host the preferred first adoption
target. The graph may help Studio recall and reconcile relationships, but
revisioned packages and reviewed change sets remain the sync protocol. An
optional Pi sidecar is a separate optimization and never a Stage dependency.

Acceptance remaining: on the selected Studio host, record installation,
memory, durability/recovery, read-only MCP, migration, and removable JSON
export. If an on-Pi sidecar is still pursued, also complete ARM64 installation
and 25 FPS coexistence. A host-specific failure is a no-go for that deployment
target and does not block show control or ordinary Studio publishing.

Design checkpoint (2026-11-17): current Relate 1.0.1 documentation reinforces
the boundary. The graph is held in memory, belongs to one application on one
machine, and permits only one writer; `relate serve` exposes that one open store
rather than providing replication. Studio may use it to relate analysis,
sections, assets, authored Lighting/Video revisions, evidence, reviews,
packages, and returned Stage adjustments. Studio must compile those decisions
into the existing deterministic EDL, cue-sheet, Video Show, and package
contracts. The Pi never queries the graph to select or advance a live cue. Any
Pi copy is optional/read-only diagnostics or adjustment provenance, supplied by
a versioned snapshot between publishes and removable without affecting show
operation.

### OPS-005 — Prevent Pi suspend during managed shows (`P0`, reliability)

The live show on 2026-11-06 exposed a release-blocking operating-system power
policy problem: the Pi could suspend or stop servicing the controller when its
attached display entered power saving. A connected screen/mouse and an
operator-applied administrative workaround kept the show running, but that is
not an acceptable show dependency.

`phreqed-show-inhibit.service` now holds a systemd `sleep:idle` block for the
entire lifetime of the managed `phreqed-dmx.service`. It deliberately excludes
shutdown, so the confirmed clean-poweroff helper remains usable, and it is
released when the controller service stops. The installer deploys and verifies
the unit; the readiness check treats an inactive inhibitor as a failure.

Iteration checkpoint (2026-11-16): current Pi use reports no screen blanking,
controller timeout, or suspend recurrence. Remaining acceptance is to record
inhibitor release when `phreqed-dmx.service` stops, confirm browser clean
shutdown, and complete the requested controlled power-cycle/recovery check with
fixtures stopped and QLC+ blackout available. Abrupt power loss cannot
guarantee a DMX blackout and is not a substitute for the normal shutdown path.

### OPS-004 — Confirmed browser clean shutdown (`P0`, deployment safety)

The browser now exposes an opt-in **Shut down Pi** action only when the process
was started with explicit `live --web --allow-system-shutdown`. The action
requires typing the exact phrase `SHUTDOWN`; its backend independently checks
that phrase, stops the song timeline, blackouts and closes live output, resets
white/show-power state, and then requests a normal asynchronous systemd
power-off. Simulation cannot receive shutdown authority. The OS command is an
absolute argument vector with no shell, force, reboot, or inhibit override.

The managed installation includes a root-owned one-shot
`phreqed-poweroff.service` plus a polkit rule restricted to user `mmorley`,
system unit `phreqed-dmx.service`, `NoNewPrivileges`, and only the exact start
verb for that helper. The environment switch defaults off. Windows passes 209
tests, and Chromium verified disabled confirmation for incorrect
text, enabled confirmation for exact text, cancellation, responsive layout, and
zero console errors without executing power-off.

Acceptance remaining: the button was present but stayed disabled during the
2026-11-06 show setup. Confirm `/etc/default/phreqed-dmx` contains
`PHREQED_ALLOW_SYSTEM_SHUTDOWN=1`, rerun the service installer so the helper and
polkit rule are current, restart `phreqed-dmx.service`, and verify
`system_shutdown_available` is true in `/api/state`. Then perform one deliberate
shutdown with fixtures already stopped and one conservative live shutdown with
QLC+ blackout available. Confirm fixture blackout precedes power loss and the
journal contains no authorization error.

### AUDIO-002 — Real-time audio synchronization (`P1`, music)

Explicit `arecord` mono capture, deterministic PCM analysis, adaptive ambient
noise handling and auto-leveling, capture health, browser meters, and silence-on-input-loss are
implemented without a new dependency. The Blue Snowball hardware name and raw
input levels have been verified on the Pi. Capture remains off unless an ALSA
device is explicitly supplied and cannot select or enable Art-Net output.

The operator subsequently confirmed the full simulation path on the Pi: audio
capture, browser meters, and the reactive Phase Collider visual all responded.
No Art-Net output was enabled during this test.

Acceptance remaining: document sustained CPU use, analysis latency, and missed
25 FPS frames, then tune sensitivity under rehearsal-level sound. Automatic
scene switching and hard onset flashes remain out of scope.

The first integrated, socket-blocked Raspberry Pi bench run passed all 31 looks
in that revision. The current 39-look rerun also passed: audio ended healthy
after 8,404 chunks, all three top-level checks were true, no reported frame slot
was missed, and peak temperature was 49.05 C. Rehearsal-level sensitivity and
longer-duration resource measurements remain before final performance
acceptance.

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

### MAP-002 — Correct LF4808 geometry to 12 x 4 (`P0`, mapping)

The package configuration, fixture defaults, simulators, browser previews,
legacy compatibility engine, diagnostics, documentation, and automated tests
now use the operator-confirmed 12-column by 4-row front view. The immutable
reconstructed baseline retains its historical 8-by-6 assumption. The prior
corner-only check could not distinguish the two geometries because zones 1 and
48 have the same locations under both layouts.

The remaining historical check is narrow: `scripts/fixture-check.py live` has
steady markers for blue zone 12 at the bottom-left and green zone 13 at the
right side of the next row. Observing those two markers on each fixture proves
the physical row wraps after 12 columns rather than after the obsolete 8-column
baseline. The live-show visuals strongly support the corrected geometry, but
this exact row-boundary observation was not recorded, so retain it as a short
low-brightness acceptance check rather than repeating broad commissioning.

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

The operator later deliberately confirmed the five-second lost-browser boundary:
it blackouts and closes live output. The MIDI reader remains connected, but the
pedal cannot restart live output by itself. DISPLAY-001 now requires a healthy
local touchscreen lease to keep output available when only the phone disconnects.

Remaining acceptance: complete the narrow MAP-002 row-boundary observation and
confirm saved looks and scenes survive a restart.

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

## Backlog

### STUDIO-000 — Phreqed Studio and Stage separation umbrella (`P1`, architecture)

Separate advanced authoring from the show-critical runtime before lighting,
video, projection, analysis, and AI workflows make the Stage application too
complex. Phreqed Studio is a hosted multi-tenant SaaS control plane with a
curated catalog plus private customer libraries. It owns editable history and
publishes immutable, validated, fully cached show packages. Phreqed Stage runs
an explicitly activated package offline and records bounded local changes in a
separate adjustment journal for reviewed return sync.

Children: `STUDIO-001`, `PUBLISH-001`, `SYNC-002`, `STUDIO-002`, `STUDIO-003`,
`SAAS-001`, `SAAS-002`, `SAAS-003`, `CATALOG-001`, `MEDIA-001`, `MEDIA-002`,
`STAGE-LINK-001`, `STUDIO-004`, `AI-DATA-002`, `AI-STUDIO-001`, `STAGE-001`,
and `STUDIO-005`.
Existing `PROJ-001`, `PROJ-002`, `SHOW-002`, `VIDEO-001`, `AI-DATA-001`,
`ANALYSIS-001`, and `AI-SONG-001` remain linked implementation or research
cards rather than being duplicated. Detailed user stories and Sprints 0-11 are
in [`studio-stage-roadmap.md`](studio-stage-roadmap.md).

Umbrella acceptance: two hosted tenants remain isolated; the Pro reference
customer can ingest private band media, author parallel Lighting/Video tracks,
publish and deliver a complete package through cloud/LAN/removable media, run it
offline on Stage, return local adjustments for review, and restore the previous
package. Projection failure remains isolated, and Stage runs a lighting-only
show with Studio, graph, Internet, and media services absent.

### STUDIO-001 — Shared domain identity and revision model (`P1`, architecture)

Define stable IDs, object and library revisions, schema versions, origin
identity, supersession metadata, and explicit migrations for shows, songs,
setlists, looks, scenes, Lighting/Video tracks, Video Scenes, cues, fixtures,
catalog items, projection designs, assets, renditions, and clips. Existing
Pi `library.json`, `songs.json`, and `tuning-profiles.json` remain authoritative
and must migrate without loss, live behavior changes, or overwrite.

User outcome: designers retain references through edits, operators can identify
the exact loaded revision, and maintainers can round-trip legacy libraries.

Acceptance: core models stay independent of HTTP, graph, Art-Net, and media
decode; duplicate IDs, broken references, revision regressions, unknown schemas,
fixture overflow, and reserved-channel violations are rejected; migration is
backed up, idempotent, and covered by representative legacy fixtures.

Dependency: none. This is Sprint 0 and blocks all new Studio, package, sync, and
graph-integration cards.

### SAAS-001 — Tenant, workspace, identity, and role foundation (`P1`, platform)

Create the hosted account boundary for tenants, band workspaces, memberships,
roles, users, sessions, service identities, Stage devices, audit events, and
export/deletion requests. Initial roles are owner, administrator, designer,
operator, and viewer with server-enforced permissions.

User outcome: subscribers sign in to isolated band libraries, invite the right
people, and revoke access without altering downloaded Stage packages.

Acceptance: tenant/workspace scope is enforced in persistence, APIs, object
keys, background jobs, caches, logs, and tests; two test tenants cannot observe
or mutate one another; session revocation, recovery, audit, export, retention,
backup, and restore paths pass before production media is accepted.

Dependency: `STUDIO-001`. Planned Sprints 0-1.

### SAAS-002 — Subscription entitlements, quotas, and usage ledger (`P1`, product)

Represent Free, Artist (`$`), and Pro (`$$$`) as configurable capabilities and
numeric quotas rather than separate applications. Cover catalog access, private
upload, storage, processing, AI allowance, package count, paired devices, team
roles, and revision retention. The Pro reference customer has the complete
authoring/media/AI/device capability set.

User outcome: customers understand what is available and consumed, while tier
names, prices, and quotas can change without forking Studio or Stage.

Acceptance: server-side checks exist at upload, job, AI, publish, pairing, and
retention boundaries; async usage uses idempotent reserve/commit/release and an
append-only ledger; failures cannot double-charge; downgrade, billing outage,
or SaaS outage never disables a downloaded or active Stage package.

Dependencies: `STUDIO-001`, `SAAS-001`. Planned Sprint 2.

### CATALOG-001 — Curated base asset and scene catalog (`P1`, content)

Publish versioned base looks, lighting scenes, Video Scenes, VFX clips, and
deterministic song templates with stable IDs, previews, tags, provenance,
license/usage terms, compatibility, entitlements, and retirement metadata.

User outcome: free users can start from useful entitled material, and higher-
tier users can copy a base item into a private editable draft without losing
attribution or provenance.

Acceptance: shows pin exact catalog revisions; catalog edits/retirement never
mutate customer drafts or packages; free/paid access reuses asset bytes without
leaking private media; initial taxonomy covers mood, energy, palette, motion,
genre, tempo suitability, loopability, aspect ratio, and projection suitability.

Dependencies: `STUDIO-001`, `SAAS-001`, `SAAS-002`. Planned Sprint 2.

### SAAS-003 — Hosted operations, audit, portability, and recovery (`P1`, reliability)

Define hosted environments, secrets, migrations, backups, restore drills,
observability, job replay/dead-letter handling, retention, rate limits, abuse
controls, customer export/deletion, and support audit access.

User outcome: customer data is recoverable and portable, and support can
diagnose failures without reading private media/prompts by default.

Acceptance: jobs are idempotent/resumable; metadata never commits a derived
asset before durable object verification; versioned export includes revisions,
provenance, reviews, packages, and hashes; deletion is staged/auditable;
disaster-recovery and data-residency targets are explicit before launch.

Dependency: `SAAS-001`; foundation in Sprint 1 and release acceptance in Sprint
11.

### PUBLISH-001 — Immutable show package lifecycle (`P1`, deployment)

Create deterministic package manifests containing show revisions, fixture
requirements, cues, asset hashes, compatibility bounds, and integrity data.
Stage imports packages into a staging area, validates them completely, activates
only through an explicit stopped-output operation, and retains a known-good
rollback package.

User outcome: a designer sees errors before transfer, while an operator can
import without affecting the current show, activate deliberately, and roll back
using hosted delivery, trusted LAN, or removable media.

Acceptance: interrupted or rejected import leaves the active show unchanged;
activation is blocked while output or a timeline is active and never starts
playback; path traversal, unbounded archives, duplicate entries, executable
content, missing assets, and incompatible fixtures are rejected.

Dependency: `STUDIO-001`. Planned Sprint 3.

### STAGE-LINK-001 — Secure Stage pairing and hosted package delivery (`P1`, deployment)

Pair Stage to a tenant/workspace with short-lived enrollment and a revocable
per-device identity. Deliver signed packages through resumable, hash-verified
downloads into the existing staging boundary; every rendition must preflight
before local activation becomes available.

User outcome: a higher-tier customer can send a show to one or more Stage units,
then disconnect the Internet and run or roll back locally.

Acceptance: Stage stores no user password, browser/billing secret, tenant-wide
object credential, or remote-start capability; delivery cannot activate or
start output; revocation blocks future downloads without interrupting cached
shows; replay, expiry, skew, partial download, outage, and replacement recover;
the same package validates through cloud, LAN, and removable media.

Dependencies: `STUDIO-001`, `SAAS-001`, `PUBLISH-001`. Planned Sprint 3.

### SYNC-002 — Stage adjustment journal and reviewed return sync (`P1`, synchronization)

Record allowlisted venue changes separately from the immutable package. The
first allowlist covers setlist order/omission, cue timing, bounded scene/master
scaling, tuning-profile selection/copy, approved fixture substitution, and
operator notes. Export the same change-set format over LAN or removable media.

User outcome: performers can make necessary local corrections and designers can
bring them back to Studio without silently overwriting newer work.

Acceptance: every change records unit, package, base revision, object, old/new
values, and time; corrupt journals are quarantined; Studio performs a three-way
comparison and exposes clean changes and conflicts; every accept, reject, or
manual resolution is explicit and accepted changes create a new revision.

Dependencies: `STUDIO-001`, then `PUBLISH-001` for end-to-end transfer. Planned
Sprint 10.

### STUDIO-002 — Browser Studio foundation and authoring migration (`P1`, authoring)

Build the tenant-aware browser Studio shell for workspace/library/show
navigation, search, master-detail editing, autosaved drafts, validation,
revision history, entitlement visibility, usage status, and explicit publish.
Move songs, setlists, looks, scenes, and tuning-profile design into Studio
through shared domain/validation code rather than duplicated controller logic.

User outcome: show design receives a spacious dedicated application without
live-output controls, and existing operators can import their current libraries
instead of rebuilding them.

Acceptance: Studio cannot construct `ArtNetSender` or acquire a Stage control
lease; current libraries import and export through a normalized representation;
representative workflows reach capability parity before any Stage authoring is
deprecated; package publishing uses `PUBLISH-001`.

Dependencies: `STUDIO-001`, `SAAS-001`, `PUBLISH-001`. Planned Sprint 4.

### STUDIO-003 — Lighting timeline and preview designer (`P1`, authoring)

Provide a zoomable, multi-lane timeline with cue and scene lanes, selection
inspector, snapping, keyboard/touch editing, undo/redo, copy/paste, validation
markers, and injected-time simulator scrubbing. The shared clock can align a
future projection lane without moving media work into the DMX renderer.

User outcome: lighting designers can build and inspect a show visually without
long forms, nested scrolling, or fixture output.

Acceptance: preview cannot enable Art-Net, commissioned whites, or projector
hardware; missing and superseded references are visible before publish; cues
reference explicit immutable revisions or drafts; a lighting-only package is
published and run before media integration begins.

Dependencies: `STUDIO-001`, `STUDIO-002`. Planned Sprint 4.

### MEDIA-001 — Content-addressed media asset library (`P1`, media)

Store imported video, image, and later audio bytes outside the repository in
tenant-scoped object storage, addressed by content hash. Local development may
use a filesystem adapter. Keep original names as display metadata and record
size, type, duration/dimensions, provenance, and compatibility information.

User outcome: designers can reuse and transfer assets without accidental
duplicates, and Stage can prove all required media is present before activation.

Acceptance: no remote URL or embedded command is executable; missing, changed,
unsupported, and oversized assets fail package validation; asset removal is
explicit and reference-aware; retained packages and revisions protect their
assets from garbage collection.

Dependencies: `STUDIO-001`, `SAAS-001`, `PUBLISH-001`. Planned Sprint 5.

### MEDIA-002 — Hosted ingest, rendition, and clip-preparation pipeline (`P1`, media)

Provide resumable private upload, bounded probing, checksum/duplicate checks,
quarantine, thumbnails/storyboards, non-destructive in/out clip ranges, preview
proxies, and one conservative Stage rendition. Originals remain immutable;
derived assets record tool/version/settings and hashes.

User outcome: the Pro reference band can bulk-upload its VFX/video suite, cut it
into reusable short clips, tag it, and publish only required Stage renditions.

Acceptance: jobs are visible, cancellable, retryable, idempotent, quota-bound,
and tenant-isolated; manual metadata covers mood, energy, palette, motion,
tempo suitability, loopability, aspect and rights; automated shot/tag/loop
results remain proposals; representative band clips package and play on the Pi.

Dependencies: `SAAS-001`, `SAAS-002`, `MEDIA-001`. Planned Sprint 5.

### MEDIA-003 — Incremental cached composition renderer (`P1`, media production)

Replace the monolithic multi-layer FFmpeg graph with a production job pipeline
that stages sources locally, renders only active timeline intervals, caches
content-addressed intermediates, assembles intentional-black gaps, and resumes
without recomputing completed phrases. The Stage output remains one atomic,
audio-free, hash-verified H.264 package; the Pi never runs this build pipeline.

User outcome: a Studio designer receives a fast proxy for visual review, sees
honest progress for the full Stage rendition, can cancel/retry/resume a job, and
does not lose completed work when one source or worker fails.

Measured baseline (2026-11-17): the first Travelling sparse hybrid build uses a
180-second 720×1280 logical canvas rotated/mirrored to 1280×720 at 30 FPS, 23
layers, one 285 MB/146-second master on a Google Drive-mounted volume, eight
local Infinity VFX sources, H.264 High 4.1 output, and four complex-filter
workers. The current FFmpeg 4.2.3 graph shares decoders and completed correctly,
but performs a long pre-output buffer pass: the reference workstation took 70
minutes 48 seconds, grew from about 1.1 GB to an observed 4.78 GiB RSS, sustained
multiple CPU cores, and exposed no frame-level progress or reviewable partial
file before final atomic completion. The 55.4 MB result passed hash/package
preflight and structural frame sampling. This is valid for an initial proof but
fails Studio UX and capacity requirements. Dated evidence is in
[`validation/travelling-hybrid-render-2026-11-17.md`](validation/travelling-hybrid-render-2026-11-17.md).

Implementation requirements:

- Stage cloud/remote-mounted originals into a local content-addressed cache and
  verify their hashes before decoding. Source locality is a first-class job
  phase, not an incidental filesystem assumption.
- Compile the EDL into disjoint active intervals. Render sparse visual phrases
  and explicit black spans as deterministic chunks, then assemble them without
  cumulative timing drift or re-encoding unchanged chunks.
- Key intermediates by source hash, source range, transform/crop, opacity,
  blend/fade semantics, projection profile, renderer version, and encoding
  profile. A changed phrase invalidates only dependent chunks.
- Provide separate low-resolution review proxies and conservative Stage
  renditions. Proxy generation must not weaken final package preflight or allow
  proxy media to be activated on Stage accidentally.
- Persist job states for queued, staging, probing, rendering chunk N/M,
  assembling, hashing, preflighting, complete, cancelled, and failed. Emit
  monotonic progress, recent activity, resource use, and actionable errors.
- Make cancellation bounded and recoverable. Completed chunks survive retry;
  abandoned partials are quarantined or garbage-collected only when no retained
  job/package references them.
- Run isolated workers with explicit CPU, memory, wall-time, temporary-disk,
  tenant-quota, and concurrency limits. Never render in the Studio web process
  or any Stage/DMX service.
- Record FFmpeg build, command plan, source/intermediate hashes, durations,
  worker metrics, warnings, final manifest hash, and preflight result.

Acceptance: on a documented reference worker, cached-source proxy review begins
within 60 seconds and a changed sparse phrase is reviewable within 30 seconds;
the complete Travelling Stage rendition finishes within 10 minutes or records a
reviewed platform-specific exception; peak worker RSS remains at or below 4
GiB; progress updates at least every five seconds; cancel/resume avoids
re-rendering completed chunks; unchanged reruns hit the cache; black intervals,
fades, orientation, 180-second duration, package hashes, and Pi preflight match
the reference composition. Worker loss, corrupt cache entries, quota failure,
and missing sources fail explicitly without publishing a partial package.

Dependencies: `MEDIA-001`, `MEDIA-002`, and the version-2 EDL contract proven
by `SHOW-005`. Required by `STUDIO-004`; planned Sprint 5 before the production
Video Scene editor.

### STUDIO-004 — Video Scene manager and parallel song track (`P1`, media authoring)

Add reusable Video Scenes and a separate Video track beside the Lighting track
on the shared song clock. Video Scenes contain clip ranges, stills, colour or
black layers, crop/fit, loop, opacity, fades, intensity, and bounded overlays.
The timeline provides trim/split, snapping, gaps, explicit overlap rules,
preview, validation, and shared transport. Reuse the existing projection
runtime and unified-cue cards rather than creating a second architecture.

User outcome: designers can prepare synchronized lighting and projection in one
show while an absent or failed clip remains black and never delays lighting.

Acceptance: the package manifest carries versioned projection interpretation
and content-addressed asset/rendition/clip references; deterministic metadata
templates create editable draft video layouts; preview and Stage agree on
timing and fallback; explicit song start/stop/pause/seek addresses both runners
without autostart; a multi-clip band song publishes and plays while player kill
fails black and the 25 FPS lighting runner stays on time.

Dependencies: `STUDIO-003`, `MEDIA-001`, `MEDIA-002`, `MEDIA-003`, `PROJ-001`,
and the required subset of `SHOW-002`; later work uses `PROJ-002`. Planned
Sprint 7.

### AI-DATA-002 — Studio knowledge graph and agent-memory integration (`P2`, AI/data)

Index Studio revisions, song analysis, sections, evidence, cue proposals,
reviews, assets, packages, and returned Stage changes in an optional graph
sidecar. Stable library IDs remain the join boundary, and authoritative Studio
stores plus exported evidence must be sufficient to rebuild the graph.

User outcome: designers can trace why a cue was proposed and how it relates to
song structure and prior decisions, while reviewers can distinguish measured,
generated, superseded, approved, and published information.

Acceptance: one controlled writer and read-only agent access where possible;
generated cues remain drafts requiring ordinary review and publish; JSON export
and rebuild are tested; graph loss never blocks ordinary package publishing;
media bytes, credentials, leases, and mutable Stage runtime state never enter
the graph.

Sequencing boundary: graph-backed authoring may propose or explain a timeline,
but publishing compiles stable ordered cues and package hashes. Stage playback
uses only that compiled snapshot and the monotonic song clock; no graph lookup,
MCP call, Studio connection, or AI decision occurs in the live cue path.

Dependencies: `STUDIO-001` and the relevant `AI-DATA-001` feasibility gates.
Planned Sprint 9; linked to `ANALYSIS-001`, `AI-SONG-001`, and
`AI-STUDIO-001`.

### AI-STUDIO-001 — Reviewed AI lighting and video-layout proposals (`P1`, AI authoring)

Generate structured Lighting and Video track proposals from explicit song
revisions, analysis evidence, instructions, allowed private/catalog assets,
metadata, and prior reviewed decisions. Include rationale, evidence, rights/
entitlement state, confidence, source revisions, and reserved usage.

User outcome: a Pro customer can get a credible first-pass dual-track song
layout, preview it, accept selected cues/clips, reject others with reasons, and
continue editing manually.

Acceptance: output is schema validated and references stable revisions; review
supports compare/selective accept/reject/undo; acceptance creates a draft only;
AI cannot publish, pair, activate, or control Stage; provider/graph/quota failure
leaves the draft untouched; deterministic metadata templates remain available;
private tenant media/prompts never silently enter the shared catalog or training.

Dependencies: `STUDIO-003`, `STUDIO-004`, `AI-DATA-002`, `ANALYSIS-001`, and
`AI-SONG-001`. Planned Sprint 9.

### STAGE-001 — Runtime-focused Stage interface (`P1`, operations)

After Studio reaches feature parity, focus the touchscreen on Perform, Shows,
Adjust, Settings, and Operations. Shows manages installed packages, validation,
activation, and rollback. Adjust exposes only `SYNC-002` changes and clearly
marks them as unreviewed differences from the published revision.

User outcome: performers see only stage-critical controls, while technicians
retain bounded local correction and existing users are not cut off during the
transition.

Acceptance: activation remains stopped-output-only; local adjustments cannot
raise ceilings or auto-arm whites; persistent blackout and local-only operations
remain unchanged; Setlist/Build authoring is hidden or removed only after
migration, publish, rollback, adjustment, and return-sync evidence is recorded.

Dependencies: `STUDIO-002`, `PUBLISH-001`, `SYNC-002`. Planned Sprint 10.

### STUDIO-005 — End-to-end Studio/Stage release validation (`P0`, release)

Validate tenant isolation, entitlements, hosted recovery, design, package,
cloud/LAN/removable delivery, activation, offline rehearsal, local correction,
return sync, republish, and rollback. Include lighting-only operation, parallel
Lighting/Video operation, and operation with Studio and graph unavailable.

User outcome: an operator has a documented, recoverable workflow from show
design through performance and back to the authoritative library.

Acceptance: exercise cross-tenant denial, quota accounting, export/deletion,
backup/restore, cloud outage, delivery replay/expiry/interruption, LAN/removable
fallback, invalid import, clean/conflicting sync, corrupt journal, missing media,
player crash, projector disconnect, package rollback, and all existing automated/
Chromium/Pi/25 FPS/lease/blackout/white/reserved-channel/kiosk/shutdown suites.
Publish the operating handbook before reducing Stage authoring.

Dependencies: all `STUDIO-000` children plus the linked projection cards used by
the first release. Planned Sprint 11.

### RIG-001 — Multi-fixture and multi-universe expansion (`P2`, scaling)

Generalize fixture layout, browser previews, scene targeting, and Art-Net output
for future LF4808 additions. The effect API already receives fixture index and
count, so continuous logical-canvas motion can extend naturally. The current
controller, configuration, browser layout, and sender still assume two fixtures
inside one 512-channel universe.

At 152 channels each, three LF4808 fixtures fit in universe 0 at starts 1, 153,
and 305 (ending at channel 456). A fourth would end at channel 608 and therefore
requires a second Art-Net/DMX universe and matching QLC+ output hardware/config.
Do not silently wrap fixture addresses or split a fixture across universes.

Acceptance: an ordered fixture layout defines logical placement independently
of DMX addresses; previews are generated dynamically; effects remain continuous
or explicitly targeted across any configured fixture count; complete 512-byte
ArtDMX frames are built independently per universe; blackout covers every
universe; missing output hardware fails dark; and Windows tests cover both a
three-fixture single-universe rig and a four-fixture multi-universe rig before
physical expansion.

### CONTROL-002 — Ampero configuration backup and inspection (`P2`, reliability)

Build a separately scoped tool for detecting, inspecting, verifying, backing
up, and eventually restoring the known Phreqed banks on the Hotone Ampero
Control. The later diagnosis found that the motivating silent-pedal incident
was an accidental bank change from 0 to 1, not demonstrated configuration loss.
This lowers the urgency and separates the completed bank-000 operational
hardening (CONTROL-003) from useful long-term backup/recovery research. Do not
treat an open descriptor
or ALSA enumeration as proof that the expected bank mapping is selected.

Initial static research used the official firmware-1.13 Android application
archive without committing the vendor binary. The archive SHA-256 is
`3F8645221B4C6B8386211FFC914F751B79D6C54379E189464CE766EDFF5D6192`.
It is a Flutter application using `flutter_blue`; strings identify preset
request/send/acknowledgement paths, SysEx, CRC32, and custom GATT services. This
makes controlled backup and recovery plausible, but the framing, checksum,
firmware compatibility, and read-back behavior are not yet understood.

Proposed interface: `phreqed-dmx ampero inspect` performs read-only discovery;
`ampero verify config/ampero/light-control.toml` compares the observed bank to
the expected mapping; and `ampero restore ...` remains unavailable until the
write protocol is proven. Execute this as a dedicated sprint: static protocol
extraction, read-only Pi GATT enumeration, characteristic identification,
differential capture of configurations that differ by one value, framing/CRC
decoding, read-only inspection, and only then an explicitly confirmed,
single-bank write experiment.

Acceptance: fake-transport tests never access hardware by default; inspect and
verify are read-only; the exact device and firmware are checked; a restorable
backup and dry-run exist; writes require explicit confirmation and are limited
to one bank; every write is followed by read-back and round-trip validation;
power-loss and partial-write behavior are understood; firmware-update endpoints
are excluded; and failure leaves the live controller usable through its browser
backup. Never commit the vendor APK or attempt writes during ordinary bench
testing. See `docs/ampero-control.md`.

### ANALYSIS-001 - Rights-safe offline song analysis (`P1`, authoring)

Accept user-owned/licensed MP3 files with rights attestation and an explicit
retention policy. Produce versioned tempo, beat/bar, energy/onset,
frequency-band, and section artifacts in an optional offline worker. Streaming
links, WAV, and FLAC are out of scope for the initial upload workflow.

Acceptance: uploaded audio and credentials are excluded from Git and logs;
malformed/oversized files fail safely; results are deterministic within stated
tolerances; decoding cannot block the 25 FPS controller; and Windows/Pi resource
measurements determine the supported authoring host. See the roadmap, Sprint 4A.

### ANALYSIS-002 - Rehearsal microphone song capture (`P1`, authoring)

Add an explicitly armed listening session that uses the configured microphone
while the band performs a complete song. Capture time-indexed normalized audio
features and timing markers, then feed the same analysis and cue-proposal
contract as ANALYSIS-001. Retain derived features by default, not raw rehearsal
audio. This authoring capture is separate from the existing show-time microphone
dynamics layer.

Acceptance: listening requires deliberate Start/Stop and visibly reports device,
level, clipping, elapsed time, and capture health; device loss, gaps, long
silence, and incomplete captures prevent silent publication; raw PCM is removed
after feature extraction unless a future explicit retention option is approved;
capture cannot construct an Art-Net sender or block the 25 FPS controller; and
the resulting `SongAnalysis` is interchangeable with an MP3-derived analysis.
See the roadmap, Sprint 4B.

### AI-SONG-001 - Structured AI cue proposal and review (`P1`, authoring)

Generate a proposed cue sheet from bounded derived analysis, effect metadata,
and operator preferences. The derived analysis may originate from an uploaded
MP3 or a rehearsal listening session. Validate a versioned JSON response before
showing it in the existing editor. Never send raw rehearsal or streaming audio
to a model, and never call a model during a performance.

Acceptance: unknown presets, invalid times, excessive brightness, and unsafe
white-output requests are rejected; the operator can compare, edit, simulate,
approve, and publish a proposal; provider failures preserve manual authoring;
and a published setlist runs entirely offline. See the roadmap, Sprint 5.

### SYNC-001 - Bounded live-band timeline correction (`P2`, experimental audio)

Evaluate Snowball onset/beat tracking for gentle phase correction of a prepared
song timeline. This is separate from basic elapsed-time playback because a live
band will drift from a studio recording.

Acceptance: corrections are bounded and confidence-visible; low confidence
falls back smoothly to the authored clock; no correction can skip safety cues,
enable output, or block manual control; and rehearsal data demonstrates an
improvement before this becomes a show option. See the roadmap, Sprint 6.

### CONTROL-004 - Optional Ampero song-number feedback (`P3`, hardware research)

Determine whether the commissioned Ampero exposes documented, reversible host
feedback or arbitrary display control. The browser remains the required large
song-number/name display. Do not equate the pedal's bank number with the setlist
index and do not transmit reverse-engineered writes during a show.

The [official firmware-1.13 support listing](https://cdn.hotoneaudio.com/support/1)
and [current product description](https://shop.hotoneaudio.com/products/ampero-control)
document a programmable controller that sends MIDI over DIN, USB, or Bluetooth;
they do not document arbitrary host-to-pedal display text or song-number
feedback. Treat a writable song display as unsupported unless later protocol
research proves a reversible input path. The practical show solution remains
the phone browser or a dedicated small Pi display.

Acceptance: official capability or a safely captured protocol is documented;
unsupported hardware falls back to the browser or a dedicated small display;
and feedback failure cannot affect input, blackout, or the setlist clock. See
the roadmap, Sprint 7.

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

### PROJ-003 — Dual-surface Stage projection (`P1`, visual output)

Add two named, independently supervised projection surfaces for the December 18
show target: `portrait-character` on the commissioned vertical rear screen and
`landscape-main` on a standard horizontal screen. Keep `DSI-1` dedicated to
local touch control and keep both Betopper cubes on the independent 25 FPS DMX
path. One song clock addresses both Video Scene variants and Lighting, but each
projector has separate package preflight, process health, black, and recovery.

Dependencies: the managed player and fault boundaries in `PROJ-001`; the second
projector/screen and cable for physical acceptance; `SHOW-002` for unified song
transport. Studio authoring in `STUDIO-004` uses logical surface IDs rather than
Qt screen numbers or desktop coordinates.

Acceptance: commission `HDMI-A-1`, `HDMI-A-2`, and `DSI-1` together; preserve
touch mapping; resolve each projector by connector/EDID; run independent
portrait and landscape 720p30 players beside QLC+, browser, audio, MIDI, and
actual low-level DMX; record zero lighting deadline misses, temperature,
CPU/RSS, video drift, and visual smoothness; independently crash/disconnect and
recover each player; and prove one failed surface blacks without disturbing the
other surface or lighting. Planned as the December 18 hardware milestone.

### VIDEO-001 — Video-to-grid sampler (`P2`, visuals)

Sample video into two normalized 12 x 4 frames with configurable crop, fit,
gamma, brightness, and fixture assignment. Quantization remains at the DMX
boundary.

### EFFECT-021 — Curated center-white scene language (`P2`, visuals)

Review the existing look catalog for scenes where the commissioned center-white
strip can act as an intentional visual layer: travelling paths, segmented
accents, impact flashes, sweeps, pulses, and character props. Build on the
proven Burning Dynamite fuse pattern without making every scene use white or
turning the strip into an undifferentiated audio strobe.

User outcome: suitable scenes gain a readable RGB-plus-white composition while
the performer retains the existing drive, prepared-level, White Show, arm,
blackout, lease-loss, and shutdown controls.

Acceptance: inventory and rank candidate looks; define fixed-time regression
frames for each selected pattern; keep continuous authored whites inside the
Rehearsal envelope and route deliberate high-output events through the existing
bounded effect-flash path; prove deterministic timing, physical part order,
fixture independence, full blackout recovery, and unchanged RGB-only behavior
when whites are disarmed. Validate the final set on both commissioned fixtures
before enabling any pattern by default in a show package.

## Done

### PROJ-004 — Persistent black projection underlay (`P1`, visual output)

An optional independently supervised `phreqed-projection-black.service` uses
the Raspberry Pi OS-provided `swaybg` client to bind solid black only to the
named `HDMI-A-2` Wayland output. It has no dependency from the DMX controller or
kiosk, remains present independently of VLC, follows connector reconnects, and
cannot migrate onto `DSI-1`.

Acceptance completed on the commissioned Pi on 2026-11-17: idle was black;
Video appeared above the underlay while Lighting sequenced; Stop and Blackout
returned to black; the underlay remained black through a controller restart;
HDMI disconnect/reconnect returned to black; and Stage control remained usable
on `DSI-1`. The controller correctly remained stopped after restart. A stale
kiosk “connection lost” notice observed after successful reconnection was fixed
to clear on the first recovered state response without auto-starting live
output.

### UX-001 — Adaptive stage-control information architecture (`P1`)

Perform, Setlist, Build, Settings, and Operations now provide the accepted base
capability model across touchscreen, phone, and desktop. Large touch targets,
visible state, persistent blackout, and explicit live stage-lock behavior are
implemented. The operator accepted this iteration on the Pi on 2026-11-16;
future refinements discovered in performance use become focused follow-up cards.

### WEB-002 — Shared responsive application shell (`P1`)

The former long page is replaced by the shared workspace shell with touchscreen,
phone, and desktop layouts. Chromium validation covers 1280 x 800 and 390 x 844
without removing controller or safety capability. The operator accepted the
deployed shell for this iteration on 2026-11-16.

### DISPLAY-002 — Setlist-first touchscreen performance dashboard (`P1`)

The deployed Perform dashboard provides setlist-first and manual operation,
song timing, current/next context, fixture previews, stage profiles, prepared
white adjustment, output controls, health, and persistent blackout without
vertical scrolling at 1280 x 800. The touch look picker removes the precision
dropdown dependency. The operator accepted the base dashboard on 2026-11-16;
ongoing show-use refinements are tracked separately under `DISPLAY-003`.

### SAFE-003 — Multi-control-plane trusted lease (`P0`)

Named local and remote leases preserve output while any trusted surface is
healthy and retain the five-second fail-dark stop, blackout, white disarm,
timeline stop, and Show-power reset when every lease is lost. Automated failure
coverage and deployed Pi operation support the operator's 2026-11-16 acceptance
for the current release.

### SAFE-004 — White output drive and Show-power contract (`P0`)

Effect, Audio Accents, and Hybrid white drive now separate configured capability,
Rehearsal/Show power, prepared level, and session-only arming. Continuous authored
motion remains in the Rehearsal envelope; deliberate pulses can use an explicitly
acknowledged White Show ceiling. Every safety boundary disarms output and restores
the required power state. The operator reported on 2026-11-16 that the deployed
controls provide the needed creative latitude while preserving safety.

### OPS-006 — Optional Chromium kiosk lifecycle (`P0`)

The native supervisor waits for controller readiness, owns Chromium, and renews
the local lease independently of browser timers without becoming a dependency
of QLC+ or headless control. Current Pi testing reports stable kiosk operation
with no screen blanking or controller timeouts; the operator accepted the card
on 2026-11-16.

### WEB-003 — Browser authoring and tuning redesign (`P1`)

Setlist, Song, Look, Scene, and Settings workflows now use separate focused
workspaces, touch-sized editing controls, persistent venue profiles, and shared
phone/desktop application logic. The operator accepted the deployed iteration
on 2026-11-16. Further authoring expansion belongs to Phreqed Studio rather than
reopening this Stage-focused redesign.

### OPS-003 — Unattended show startup and private control LAN (`P0`, deployment)

The operator confirmed the private/offline control network, iPhone access,
unattended service sequence, and show operation fully working. The complete rig
ran a live show on 2026-11-06 with QLC+, browser control, audio, Ampero, and both
fixtures. Fixture output still starts stopped and requires the explicit browser
live action. The later display-suspend problem is an operating-system power
policy issue tracked separately by OPS-005, not a failure of the stage LAN.

### CONTROL-003 — Performance-safe Ampero bank recovery (`P0`, reliability)

The apparent pedal failure was an accidental change away from bank 000, not
configuration loss. The accepted operating procedure is to return to bank 000;
duplicating the mapping into every bank is intentionally not required. The
hardware-free bank checker remains available if the profile is changed later.
Browser and future local-touchscreen control remain independent backups.

### HW-002 — Guarded audio peak output for commissioned whites (`P0`, safety)

The operator confirmed the commissioned segmented-white path, including the
lost-browser disarm boundary, during physical operation. Browser lease loss
correctly blackouts, stops the timeline, closes live output, and disarms whites.
It does not disconnect the MIDI reader, although output cannot be restarted by
the pedal alone; the future local touchscreen lease addresses that operational
availability concern without removing the fail-dark boundary.

### REL-002 — Persistent show controls and MIDI recovery (`P0`, reliability)

Persistent master brightness, the stable Ampero device path, ordinary MIDI
operation, and reconnect behavior are operator-confirmed. The rig completed the
2026-11-06 live show with foot control available. A mapped event remains the
readiness proof; opening the ALSA node alone is not sufficient.

### CONTROL-001 — Hotone Ampero foot-controller adapter (`P1`, performance control)

USB MIDI scene/song navigation, tap tempo, blackout, the stable
`/dev/snd/phreqed-ampero-midi` link, same-path reconnect, and browser status are
implemented and operator-confirmed through rehearsal and the 2026-11-06 live
show. Bluetooth MIDI remains optional future work rather than an acceptance
requirement.

### SPRITE-001 — Production sprite renderer (`P2`, visuals)

Deterministic bitmap animation, transforms, clipping, palette tinting, and the
joined 24-by-4 canvas are covered by automated, Chromium, timing, and safe-DMX
checks. The operator confirmed the figures and cross-fixture motion working on
the physical rig. Pixel Flight, Stickman Step, and Shape Shifter remain the
built-in starting looks.

### WHITE-ANIM-002 — Curated white accents across the show pack (`P1`, visuals)

Every registered effect and built-in scene now has a deterministic segmented
white pattern. Lower-gain bloom, lava, rain, current, mirror, collision, blade,
ember, and tunnel families complement the original signature animations. Energy
Bridge follows the travelling packet and widens into outward wings on stronger
onsets. Layered custom looks use explicit priority so foreground signature motion
wins over background texture. All additions remain behind the existing
audio-onset gate, operator level, independent ceiling, 0.10-second/4 Hz limiter,
and physical-white arm control. Automated coverage verifies every catalog effect,
normalization, determinism, spatial variation, and peak-dependent energy spread.
Windows Python 3.12 passes 223 tests. Chromium simulation verified Energy Bridge,
rain, collision, blade, ember, and tunnel selections expose the expected pattern
labels while live controls remain unavailable. A low-level Pi visual review of
the extended scene set remains the deployment acceptance step.

### WHITE-ANIM-001 — Scene-aware segmented white animation (`P1`, visual safety)

The eight commissioned white parts per fixture form a joined sixteen-part accent
canvas. Effect-driven blaster, flame, wave, center-out VU, and sprite-glint
patterns work for built-in and user looks; unsupported looks remain dark. The
browser previews exact per-part arrays without creating live output. Physical
output retains separate live/audio/white arming, the 10% default ceiling,
0.10-second/4 Hz limiter, per-part/aggregate clamps, and every disarm path.
Automated tests and Chromium simulation passed. The operator completed the Pi
fixture run and confirmed the segmented animation behaved correctly on
2026-11-05. Exact RGB-column boundary measurements were not transcribed and are
informational only; the confirmed Part order remains the physical mapping.

### SONG-003 - Search songs when adding to a setlist (`P2`, authoring UX)

The Setlist Builder now filters its Add song selector by title or artist with a
case-insensitive search field. Filtering leaves the ordered setlist untouched
until Add song is pressed, preserves a selected result through periodic catalog
refresh, supports repeated songs, reports result counts, and disables insertion
with an explicit no-match message. Search does not call a performance or output
action. The 203-test suite passes. Chromium exercised a 12-song library,
case-insensitive artist filtering, refresh persistence, correct insertion, and
the no-match state with zero console errors or warnings.

### SHOW-004 - Manual/setlist performance modes (`P1`, performance control)

Manual and Setlist modes provide current/next song, explicit song start/stop,
safe no-autostart progression, and mode-aware Ampero routing while retaining
global blackout. Automated and Chromium acceptance passed, and the operator
confirmed the deployed Setlist mode working in rehearsal on 2026-11-05.

### SAFE-002 — Explicit show-time RGB ceiling (`P0`, safety)

Rehearsal power remains capped while explicitly acknowledged Show power exposes
the configured higher RGB ceiling without changing the independent white limit.
Reset paths, saved-preset bounds, and frame safeguards remain active. The
operator completed the deliberate Pi/fixture check and reported it solid on
2026-11-05.

### EFFECT-003 — Music-driven stage look expansion (`P1`, visuals)

The deterministic Matrix Rain, Blaster Sweep, Flame Thrower, Wave Rider,
Pac-Man Chase, Burning Dynamite, Watchful Eyes, and Inside-Out VU additions are
covered by geometry, range, independence, reserved-channel, and timing checks.
Browser simulation and the full band rehearsal provided the initial visual-pack
acceptance on 2026-11-04.
Pac-Man Chase now adds colored ghosts with directional eyes, a deterministic
power pellet, and a bounded frightened interval in which the ghosts turn blue
and reverse smoothly before resuming the chase. Its commissioned-white pattern
uses sparse travelling pellets, but physical whites remain behind explicit
browser-live, drive-mode, prepared-level, White Show, arm, blackout, lease, and
shutdown controls. Fixed-time frames and the complete 254-test suite cover the
enhancement.
Burning Dynamite uses five columns across the complete four-row height of Cube
B: four red body columns and one yellow fuse-cap column, with rounded row
shading for a clearer stage-scale cylinder. The center-white strip is the
fuse, with a dim unburned section and much brighter travelling head while its
Effect or Hybrid white layer is armed. Yellow and orange RGB blocks track the
head and alternate above and below the strip eight times per second. It then
produces one broad amber flash, an expanding two-fixture
starburst, embers, and smoke. The original effect and preset IDs remain stable
for saved user looks and cues. Browser simulation at 1280 x 800 exposed the
quick look, rendered both fixture previews, and reported no console errors. The
complete 254-test suite covers deterministic phase timing, alternating spark
rows, the dim/bright white-pattern relationship, and reserved white
channels; physical-fixture visual acceptance remains part of `DISPLAY-003`.

### AUDIO-003 — Shared tempo and dynamics clock (`P1`, music)

Tap tempo supplies the baseline, bounded audio dynamics modulate shared motion
and brightness below the operator ceiling, and auto-level/deep-dim/contrast
controls retain their safety boundaries. Bench timing passed and the operator
accepted the response during a full band rehearsal on 2026-11-04.

### SONG-004 - Style-based default song timelines (`P1`, authoring)

Songs can now be tagged Punk, Rock, Mellow, Funk, Metal, Alternative, Blues,
Reggae, or Electronic. Each style has a distinct,
deterministic sequence of safe existing looks with proportional cue positions
and style-appropriate transitions. **Create [style] revision** creates a new
unpublished style-generated revision, or **Replace draft with [style]** replaces
an existing draft only after confirmation. **Copy published revision** remains
the separate manual-editing path and intentionally preserves the prior cues;
published revisions remain immutable and active until a new draft is reviewed
and explicitly published.

The version-1 song document remains backward compatible: existing Pi songs
without style metadata load as Unspecified and round-trip unchanged. Generation
validates duration and preset availability, cannot start playback or construct
Art-Net, and produces strictly increasing cue times even at the minimum song
duration. Automated tests cover all nine distinct templates, invalid styles,
legacy loading, draft replacement, publication isolation, and network safety.
A real Chromium simulation saved Rock on a legacy song and generated its
editable eight-cue draft with zero console errors or warnings.

### SONG-002 - Song, cue-sheet, and setlist authoring UI (`P1`, show control)

The browser now provides a Song Library, manual baseline cue timeline editor,
immutable publish/revision workflow, per-cue simulation preview, and ordered
Setlist Builder. Song metadata is stored atomically in `songs.json` beside the
existing user library. MP3 and rehearsal media remain outside this store and
AI is not involved.

Acceptance passed on Windows Python 3.12: backend tests cover persistence,
malformed writes, preset references, published-version immutability, and
simulation-only preview; a real Chromium workflow created a song, added and
previewed cues, published a revision, and created a setlist with zero console
errors. The complete suite passes 185 tests. Runtime performance mode remains
separate under SHOW-004, which is now implemented and awaiting Pi validation.
See [`song-setlist-roadmap.md`](song-setlist-roadmap.md), Sprint 2.

### SONG-001 — Song library and deterministic cue timeline (`P1`, show control)

Implemented versioned `Song`, `SongCueSheet`, `SongCue`, and `Setlist` models,
strict cross-reference validation, and atomic metadata-only JSON persistence.
The injected-clock timeline runner supports explicit load/select/start/stop and
restart, deterministic skipped-time cue deadlines, previous/next selection,
blackout cancellation without resume, mode deactivation, and song completion
that arms the next song without starting it. It imports no renderer, media,
network, fixture, or transport code.

Acceptance passed on Windows Python 3.12: eighteen focused tests cover atomic
failure preservation, corrupt input, schema and preset boundaries, application
restart, cue timing, callback failure, blackout priority, completion, and
network isolation. Browser authoring is now complete under SONG-002; runtime
integration is implemented under SHOW-004 and awaiting Pi validation. See
[`song-setlist-roadmap.md`](song-setlist-roadmap.md), Sprint 1.

### HW-001 — Commission LF4808 white-zone mapping (`P0`, safety)

The offline diagnostic verified sixteen isolated 5% frames with no socket. On
2026-10-21 the operator completed the steady physical test and confirmed Parts
1-8 progress right-to-left, every part drives both visible rows together, and
Cube A and Cube B match. The mapping is encoded in fixture configuration and
automated tests. Guarded peak behavior is tracked separately by HW-002.

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
