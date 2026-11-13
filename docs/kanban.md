# Project Kanban

Last reviewed: 2026-11-13

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

## In progress

No active implementation.

## Ready

No implementation-ready work.

## Validation

### DISPLAY-001 — Adaptive local stage touchscreen umbrella (`P1`, operations)

The touchscreen program is tracked by the independently movable child cards
below. The shared adaptive shell, stage dashboard, trusted leases, optional
kiosk, authoring redesign, and local Operations boundary are implemented. The
umbrella remains in Validation until `DISPLAY-003` records the complete Pi and
Waveshare acceptance run. Detailed design and acceptance steps are in
[`touchscreen-control-roadmap.md`](touchscreen-control-roadmap.md).

Children: `UX-001`, `WEB-002`, `DISPLAY-002`, `SAFE-003`, `OPS-006`, `WEB-003`,
`OPS-007`, and `DISPLAY-003`. The optional `AI-DATA-001` spike is related but
is not a display or live-show dependency.

### UX-001 — Adaptive stage-control information architecture (`P1`)

Perform, Setlist, Build, Settings, and Operations now provide a shared capability
model for touchscreen, phone, and desktop. The implementation uses 56-pixel primary touch
targets, visible keyboard focus, text plus color for state, persistent blackout,
and an explicit stage-lock confirmation before leaving Perform while live.

Acceptance remaining: repeat keyboard, zoom/reflow, contrast, and stage-distance
readability checks on the physical 10.1-inch display.

### WEB-002 — Shared responsive application shell (`P1`)

The previous long page is now a persistent workspace shell with desktop split
views and phone bottom navigation. Chromium validates all five workspaces at
1280 x 800 and 390 x 844 with zero console errors. No controller command or
safety semantic was removed.

Acceptance remaining: physical Pi Chromium at 100% and 200% zoom plus the
complete regression suite on the target OS.

### DISPLAY-002 — Setlist-first touchscreen performance dashboard (`P1`)

Perform includes manual and setlist layouts, current/next song, progress and
remaining time, current scene, transport, master, output state, power profile,
lease count, structured health, compact fixture previews, and blackout. At
1280 x 800 Chromium measured both document and viewport at exactly 800 pixels,
with no Perform workspace overflow.

Acceptance remaining: touch accuracy, glare/readability, wake behavior, and a
full rehearsal on the commissioned display.

### SAFE-003 — Multi-control-plane trusted lease (`P0`)

Named local and remote leases replace the single heartbeat deadline. Losing one
surface preserves output while another is healthy; losing every surface keeps
the existing five-second fail-dark stop, blackout, white disarm, timeline stop,
and Show-power reset. Automated tests cover multiple leases and remote attempts
to claim local authority.

Acceptance remaining: phone-only loss, kiosk-only loss, all-loss, browser crash,
controller restart, render failure, and display blank/wake on the Pi.

### OPS-006 — Optional Chromium kiosk lifecycle (`P0`)

The native supervisor waits for loopback readiness, launches Chromium kiosk,
renews the local lease independently of browser timers, and stops renewing when
Chromium exits. Its graphical service only wants the controller and is not
required by QLC+ or headless control. Installation is opt-in with
`--enable-kiosk`.

Acceptance remaining: missing-GUI fallback, Chromium crash/restart, boot
ordering, LCD blank/wake, and resource measurements on Raspberry Pi OS.

### WEB-003 — Browser authoring and tuning redesign (`P1`)

Songs, cue sheets, and ordered Setlists have a top-level Setlist workspace.
Build contains searchable Looks and the Scene editor. Settings groups RGB,
contrast, preview, audio, whites, persistent bounded venue profiles, and output
controls. Phone and desktop share the same commands and application logic.

Acceptance remaining: complete representative create/edit/publish/reorder
workflows on phone, touchscreen, and desktop Chromium, then confirm persistence
across a Pi service restart.

### OPS-007 — Loopback-only display and network operations (`P0`)

Fixed local endpoints, five enumerated backlight levels, four enumerated
NetworkManager actions, exact typed network confirmation, root-owned helper
units, and an exact polkit allowlist are implemented. Non-loopback requests,
unknown actions, shell-like values, and network changes while output or a song
is active are rejected. Simulation never receives this authority.

Acceptance remaining: verify the Waveshare backlight sysfs device, every fixed
NetworkManager action, loopback continuity, remote rejection, and recovery
messages on the Pi.

### DISPLAY-003 — Pi touchscreen and show-readiness acceptance (`P0`)

Run and record Sprint 6 from
[`touchscreen-control-roadmap.md`](touchscreen-control-roadmap.md): touch and
readability, service ordering, headless fallback, kiosk recovery, blank/wake,
25 FPS, all lease-loss combinations, private-network switching, reserved DMX
channels, and clean shutdown. This card cannot move to Done from desktop tests.

### AI-DATA-001 — Relate offline-memory feasibility spike (`P2`)

The proposed song/analysis/section/feature/proposal/evidence/review graph,
single-writer boundary, read-only MCP access, bounded directory store, export,
backup, and schema-migration gates are documented in
[`relate-ai-memory-spike.md`](relate-ai-memory-spike.md). Relate is not installed
and the JSON libraries remain authoritative.

Acceptance remaining: ARM64 installation, memory and 25 FPS coexistence,
durability/recovery, read-only MCP, migration, and removable JSON export. A
failure is a no-go for on-Pi deployment and does not block show control.

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

Acceptance remaining: install the updated units on the Pi, verify the inhibitor
with `systemd-inhibit --list --what=sleep`, then allow the attached display to
dim/blank for longer than the previous failure interval. QLC+, port 8080, audio,
MIDI, the active timeline, and fixture output must continue uninterrupted.
Stopping `phreqed-dmx.service` must release the inhibitor, and browser clean
shutdown must still power off normally.

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
Pac-Man Chase, Watchful Eyes, and Inside-Out VU additions are covered by geometry,
range, independence, reserved-channel, and timing checks. Browser simulation and
the full band rehearsal provided the final visual acceptance on 2026-11-04.

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
