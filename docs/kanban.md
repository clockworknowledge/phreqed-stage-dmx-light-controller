# Project Kanban

Last reviewed: 2026-11-04

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

### SPRITE-001 — Production sprite renderer (`P2`, visuals)

Promote experimental sprite helpers into the normalized rendering pipeline with
front-view placement, clipping, palette tinting, scaling suitable for a 12 x 4
grid, and optional cross-cube layouts.

Acceptance: sprite rendering is address-independent and deterministic, clips
safely, supports both fixtures independently, and has visual regression tests.

## Validation

### CONTROL-003 — Performance-safe Ampero bank profile (`P0`, reliability)

The intermittent loss of mapped pedal actions was an accidental bank change,
not demonstrated configuration erasure. The repository now documents the
duplicate safe mapping for every reachable bank and supplies
`scripts/ampero-bank-check.py`. The checker opens only the explicit raw-MIDI
path, creates no renderer or Art-Net sender, and requires all five mapped
actions: Note 60/61/62 and CC 23 high/low. Recovery guidance keeps browser
blackout independent and requires no phone app after fallback banks are
programmed.

Acceptance remaining: use the vendor app to duplicate the mapping into bank 0,
bank 1, and every other reachable bank; run the checker separately against each
bank; deliberately exercise adjacent-switch navigation; and pass a
rehearsal-length USB soak. Do not rely on simultaneous-switch chords for new
performance commands.

### SHOW-004 - Manual/setlist performance modes (`P1`, performance control)

The browser now has an explicit Manual/Setlist selector and a large Setlist
Performance view with current/next song, position, state, previous/next, and
start/stop. `PerformanceController` keeps mode and performer commands separate
from rendering and transport. Setlist selection only arms a song; start is
explicit, and completion may arm the next song but never starts it.

Ampero commands are routed by active mode: FS1/FS2 select scenes in Manual mode
or songs in Setlist mode, FS3 is tap tempo or song start/stop, and FS4 remains
the global blackout. Blackout, Stop output, browser-lease loss, render failure,
and shutdown stop the timeline without automatic resume. A restart defaults to
Manual mode, no active timeline, and output stopped. Recovery is documented in
[`setlist-performance.md`](setlist-performance.md).

Windows validation passes all 203 tests, including deterministic selection,
explicit start/stop, no-next-song autostart, blackout cancellation, lease-loss
cancellation, reboot-safe defaults, Manual-mode compatibility, serialized foot
commands, and no Art-Net construction in simulation. Chromium validation
completed mode selection, arm, start, position advance, stop, and return to
Manual mode with zero console errors or warnings.

Acceptance remaining: deploy to the Pi and validate startup defaults, USB pedal
disconnect/reconnect, song skipping, a complete multi-song setlist, browser
loss, and recovery in simulation. Then perform a low-brightness live fixture
check with QLC+ blackout immediately available. Do not infer pedal readiness
from device enumeration; require a mapped event from the intended Ampero bank.

The repeatable Pi sequence is now documented in `setlist-performance.md`, and
`scripts/show-readiness.py --startup-defaults` checks that fixture output is
stopped and the runtime is Manual/inactive/stopped after boot. Physical
acceptance remains intentionally open.

### OPS-003 — Unattended show startup and private control LAN (`P0`, deployment)

A separate `phreqed-dmx.service` now starts after headless QLC+ without waiting
for internet or venue Wi-Fi. It exposes browser-live capability but leaves
Art-Net stopped until the operator explicitly selects **Start live**. The
service restarts after application failure, tolerates an absent Ampero through
the existing reconnect worker, and starts without audio rather than losing the
browser when the Snowball is absent. Safe settings live outside Git in
`/etc/default/phreqed-dmx`.

The browser boundary now accepts a comma-separated list of specific trusted
IPv4 networks. The commissioned home LAN and reserved private stage LAN
`10.42.0.0/24` are permitted by both application and systemd filters. A
dedicated private router with Pi Ethernet is the recommended production path.
The guarded `scripts/pi-stage-hotspot.sh` now implements the alternative
Pi-hosted access point at `10.42.0.1`: configure, activate, and boot enablement
are separate actions, and activation/disable refuses an SSH path using the same
Wi-Fi interface. iPhone join and no-internet behavior are documented. The
read-only readiness check can require either commissioned stage-LAN address.

Pi evidence on 2026-10-22: both enabled services survived an unattended reboot.
QLC+ started first and Phreqed followed five seconds later; the browser logged
`simulation active; output stopped`, Snowball capture was active, and the
operator subsequently reported the full browser, audio, pedal, and two-fixture
live path working with the band. The unsupported `curl -I` response on port
8080 was only an HTTP HEAD limitation; the documented state check now uses GET.

Acceptance remaining: configure and activate the selected network on the Pi,
join it from the iPhone, then enable it at boot only after that test. Repeat a
boot with external Wi-Fi unavailable and confirm QLC+ plus port 8080 recover
while fixtures stay dark. Verify documented no-audio startup behavior. Record
the private SSID/key outside Git.

### HW-002 — Guarded audio peak output for commissioned whites (`P0`, safety)

Browser live can now separately arm audio-onset accents across all eight white
parts on both fixtures. The control requires explicit browser-live activation,
an audio source, and its own toggle; it defaults to 5% with a 10% ceiling. A
higher process-local ceiling is accepted only with explicit `live --web`,
`--white-ceiling`, and `--acknowledge-high-output-whites`; the browser then
shows a persistent warning and constrains its slider to that selected ceiling.
All modes use pulses no longer than 0.10 seconds at no more than 4 Hz and disarm
on blackout, stop, render failure, or browser-lease loss. Simulation and
ordinary live rendering continue to keep the white channels zero.

Acceptance remaining: deploy to the Pi and perform a short 5% audio-triggered
test with fixtures secured, people warned, and QLC+ blackout immediately
available. Confirm blackout, Stop output, and lost-browser handling each disarm
the toggle. Only then validate an elevated ceiling in deliberate small steps;
the browser warning, threshold control, and dynamic slider bound must remain
visible throughout.

### REL-002 — Persistent show controls and MIDI recovery (`P0`, reliability)

Browser preset and scene changes now preserve the operator's master brightness
override. The Ampero raw-MIDI worker no longer terminates permanently after a
transient select/read/disconnect error: it closes the descriptor, retries the
same configured path, contains command/reporting failures, and exposes
connection, message, and reconnect counts in the browser.

The integrated Pi soak now separates recoverable MIDI lifecycle events from
genuine action errors. A recovered reconnect can pass only when the final device
state is connected and all required pedal actions were observed; missing
actions, a lost device, or a command error still fails the gate.

Acceptance remaining: perform a measured rehearsal-length pedal soak without
forced disconnects and record brightness persistence through repeated scene
navigation. Deliberate disconnect/recovery acceptance follows CONTROL-002. The
stable raw-MIDI udev path is implemented; its reboot and unplug/replug behavior
still needs explicit captured verification.

The 2026-10-21 controlled reconnect test proved that reopening the ALSA node is
not sufficient evidence of mapped pedal actions. The reader detected removal,
reopened `/dev/snd/midiC3D0`, and reported connected, but received zero messages;
direct `amidi` and `aseqdump` were also silent. The later operator diagnosis
identified an accidental bank 0-to-1 switch as the intermittent cause, rather
than erased programming. Treat a valid mapped MIDI event after startup or
reconnect as the functional readiness gate. Performance-bank hardening is
tracked by CONTROL-003; optional read-only backup research remains CONTROL-002.

The subsequent current-catalog Pi bench passed all 39 looks and encountered one
unplanned `Errno 19` disconnect. This time the worker reconnected functionally:
the run ended connected after 62 messages, every required action was observed,
and no action errors occurred. This validates the reader recovery path when the
pedal emits the selected bank's mapped messages. The formerly unexplained
silent-pedal case is now covered by CONTROL-003's bank-selection mitigation.

A post-move launch found the explicit `/dev/snd/midiC3D0` path absent and
previously crashed before the reconnect thread started. Initial open failure is
now recoverable: browser/audio control stays running, disconnected status is
visible, and the worker retries only the operator-selected path. A changed ALSA
card number still requires the operator to select the current node or complete
the stable udev-link acceptance item.

### EFFECT-003 — Music-driven stage look expansion (`P1`, visuals)

The expanded deterministic scene pack includes Matrix Rain, a cross-fixture
blaster, a fixed-source flame jet, a dynamics-driven sine ribbon, Pac-Man,
Watchful Eyes, and an inside-out VU. Flame Thrower now has a compact hot muzzle
at the far left of Cube A and five independently varying strands crossing
continuously into Cube B instead of reading as uniform bars. Wave Rider keeps a
stable sine carrier and lets bounded music dynamics vary travel velocity around
the tapped-tempo baseline without changing spatial frequency. Inferno Rise places its heat source on logical
row 3 (the confirmed physical bottom) and advects turbulence upward. Automated
tests cover geometry, determinism, fixture independence, RGB ranges, directional
flame continuity and variation, Pac-Man travel, and zero white-channel output.

Acceptance remaining: review all five looks in browser simulation, confirm the
revised Flame Thrower reads as a left-origin jet across both fixtures, confirm
Inferno Rise rises upward with fixtures upright and printed text readable, and
run a low-brightness live scene check. The added standalone effect expands the
current bench catalog to 40 looks, so rerun the socket-blocked timing gate.

Windows validation passes 139 tests. A clean browser preview shows the anchored
source and cross-cube strands, and a short socket-blocked 40-look smoke reports
zero missed slots, zero over-budget frames, zero reserved-channel output, and a
zero shutdown blackout. Operator review on the Pi remains the visual authority.

Matrix Rain now uses sparse columns with bright heads, short dim tails, explicit
top-to-bottom movement, and randomized blank gaps. Blaster Sweep now fires a
compact muzzle/projectile cycle and exposes left-to-right, right-to-left, and
center-out direction choices. The new Watchful Eyes preset adds a synchronized
opening/blinking eye to each fixture. These additions bring the catalog to 24
effects and 18 presets. Pac-Man Chase adds one cross-fixture sprite effect and
preset, bringing the current catalog to 25 effects, 19 presets, and 44 soak
looks. The 159-test Windows suite passes. Browser simulation confirms the stable
Wave Rider curve and visibly broken-up Flame Thrower strands, and a short
socket-blocked 44-look smoke reports zero missed/over-budget frames, zero
reserved-channel output, and zero shutdown blackout. Pi visual acceptance and
the full five-second-per-look timing gate remain authoritative.

The current 39-look Pi bench passed render timing at 25 FPS with zero reported
missed slots, zero reserved-channel output, and successful shutdown blackout.
Flame Thrower was the heaviest reported preset at 16.182 ms maximum render time,
leaving more than 23 ms within the 40 ms frame budget.

On 2026-10-22 the operator reported the current browser-controlled two-fixture
show working well during a live band test. Detailed per-look visual acceptance
and a current 44-look timing report remain open rather than being inferred from
that overall result.

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
dynamics provide a bounded 0.7x-1.5x motion multiplier. Audio also modulates
output from 55%-100% of the manual master without raising the RGB ceiling.
The browser exposes both live multipliers and an opt-in deep-dim mode with an
adjustable 0%-25% quiet floor. Slow automatic input leveling now restores
analysis headroom when sustained venue volume pins loudness or a frequency band;
the browser exposes its state and current gain. A hue-preserving compositor
contrast control restores visual depth in fill-heavy looks without raising the
master or RGB ceiling. Silence preserves tempo-driven motion. No new runtime
dependency was added.

Acceptance remaining: visually validate every preset with rehearsal-level
Snowball input, tune the response curves, and confirm 25 FPS timing in the Pi
soak before calling the dynamics model performance-ready.

The 2026-10-21 current-catalog bench confirmed 25 FPS timing across all 39
looks. Visual response and rehearsal-level curve tuning remain open.

The 2026-10-22 live band test exercised the Snowball-driven show at actual band
volume and was reported working well. A longer measured run and recorded
response-curve observations remain before this card is performance-complete.

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

### CONTROL-001 — Hotone Ampero foot-controller adapter (`P1`, performance control)

The dependency-free USB MIDI parser and explicit raw-device adapter are
implemented. The operator updated the pedal to firmware 1.13, verified notes
60–62 and CC 23 values 127/0 from `/dev/snd/midiC3D0`, and confirmed scene
navigation, tap tempo, and blackout in browser simulation. Guarded browser-live
operation was subsequently reported working correctly. Same-path automatic
reconnect and browser connection counters now prevent a transient device error
from silently ending the reader thread.

Acceptance: create a stable raw-MIDI udev link and pass a rehearsal-length USB
soak. Deliberate USB recovery is deferred to CONTROL-002. Bluetooth MIDI remains
a separate follow-up until Pi pairing and reconnect behavior are characterized.

The stable-link implementation is now in
`config/udev/70-phreqed-ampero.rules`. It matches USB identity `84ef:0029` and
targets `/dev/snd/phreqed-ampero-midi`; the show-service installer deploys and
reloads it. Pi verification across unplug/replug and reboot remains before this
part of acceptance is closed.

The operator reported scene control and the overall live system working during
the 2026-10-22 band test after the card-renumbering repair. Because the resolved
symlink and reconnect counters were not captured, retain explicit stable-link
and rehearsal-duration evidence as the remaining gate.

The integrated soak's first Pi run observed previous scene 5 times, next scene
4 times, tap tempo 4 times, and both blackout states 3 times without allowing
the probe to alter scenes or enable output. A later loss of pedal response led
to the automatic reconnect fix. Repeat the current-catalog soak with one
ordinary operation using the stable raw-MIDI udev link.

### MAP-002 — Correct LF4808 geometry to 12 x 4 (`P0`, mapping)

The package configuration, fixture defaults, simulators, browser previews,
legacy compatibility engine, diagnostics, documentation, and automated tests
now use the operator-confirmed 12-column by 4-row front view. The immutable
reconstructed baseline retains its historical 8-by-6 assumption. The prior
corner-only check could not distinguish the two geometries because zones 1 and
48 have the same locations under both layouts.

Acceptance: the Windows and Pi test suites pass, browser and Tk previews show
12 x 4 RGB cells, the browser adds two preview-only center-white reference lines,
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

## Backlog

### SONG-003 - Search songs when adding to a setlist (`P2`, authoring UX)

Add a search/filter field to the Setlist Builder's **Add song** control so a
large song library can be narrowed by title and artist before insertion. The
filtered result must remain distinct from the ordered songs already in the
setlist, and choosing a result must not modify the setlist until the operator
explicitly adds it.

Acceptance: matching is case-insensitive and updates without losing unsaved
setlist edits; clearing the query restores the full library; empty and no-match
states are obvious; keyboard and touch operation remain accessible; repeated
songs are still permitted for encores; search never changes playback, active
song, or output state; and automated plus Chromium tests cover filtering and
insertion into a long representative library.

### CONTROL-002 — Ampero configuration backup and inspection (`P2`, reliability)

Build a separately scoped tool for detecting, inspecting, verifying, backing
up, and eventually restoring the known Phreqed banks on the Hotone Ampero
Control. The later diagnosis found that the motivating silent-pedal incident
was an accidental bank change from 0 to 1, not demonstrated configuration loss.
This lowers the urgency and separates immediate show hardening (CONTROL-003)
from useful long-term backup/recovery research. Do not treat an open descriptor
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

### SONG-004 - Style-based default song timelines (`P1`, authoring)

Songs can now be tagged Punk, Rock, Mellow, Funk, Metal, Alternative, Blues,
Reggae, or Electronic. Each style has a distinct,
deterministic sequence of safe existing looks with proportional cue positions
and style-appropriate transitions. **Apply style default** creates a new
unpublished revision, or replaces an existing draft only after confirmation;
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
