# Phreqed Stage DMX Light Controller

A simulation-first Python 3.11+ visual engine for Calgary rock band
[Phreqed!](https://www.phreqed.com)'s two
Betopper LF4808 RGB matrix fixtures. It provides deterministic procedural
effects, normalized RGB layer compositing, presets, an interactive two-cube
simulator, a dependency-free browser show controller, and explicit live
512-channel Art-Net output through QLC+.

To continue deployment or development in a fresh Codex session, start with the
[current resume](RESUME.md), then read [`AGENTS.md`](AGENTS.md) and the
[project Kanban](docs/kanban.md).

The reconstructed conversation baseline is preserved unchanged under
`phreqed-stage-dmx-baseline/`. The package retains its plasma, tunnel, pulse,
chase, and cross-cube chase while adding twenty-two advanced effects. These
snapshots are not direct Pi exports; see the [baseline inventory](docs/baseline-inventory.md)
and [Pi comparison checklist](docs/pi-script-import.md).

## Phase 2 capabilities

- 27 registered effects with validated metadata and deterministic output
- spectrum, magma, ocean, neon, ember, monochrome, and matrix palettes
- alpha, additive, and lighten layers with opacity and masks
- independent per-cube effects or continuous cross-cube effects
- twenty-three built-in presets, including animated figures and cross-cube looks
- conservative global brightness ceiling and frame-rise limiter
- transport-independent blackout, preset, event, tap-tempo, and navigation APIs
- normalized, replayable audio analysis with explicit opt-in Blue Snowball/ALSA
  capture, browser meters, and silence-on-input-loss behavior
- optional Hotone Ampero Control input over an explicitly selected ALSA
  raw-MIDI device, with disconnect recovery and browser status; foot input never
  enables Art-Net output
- interactive Tk simulator with live FPS, keyboard transport, parameter resets,
  status feedback, and PNG/PPM export
- versioned user looks and ordered scenes with atomic JSON persistence
- browser previews and show control with an explicit live gate and disconnect blackout

See the complete [effect catalog](docs/effects.md) and
[Phase 2 implementation report](docs/phase-2-implementation-report.md). Feature
status and upcoming work are tracked on the [project Kanban](docs/kanban.md).
The staged audio plan is documented in
[Audio synchronization](docs/audio-synchronization.md).

## Hardware configuration

Fixture reference: [Betopper LF4808 official product page](https://betopperdj.com/products/betopper-lf4808-260w-matrix-strobe-effect-light).
The manufacturer page confirms individual pixel/zone mapping and 152-channel
mode; the 12-by-4 front-view orientation comes from physical fixture testing.

- Art-Net target: `127.0.0.1:6454`, universe 0
- QLC+ passthrough to an FTDI FT232R USB-DMX adapter
- Cube A: 152-channel mode, starts at DMX 1
- Cube B: 152-channel mode, starts at DMX 153
- 48 RGB zones per cube in a 12-column by 4-row front-view grid; zone 1 is
  bottom-right
- zones advance right-to-left, then bottom-to-top
- two center rows contain eight documented, linearly dimmed white parts on
  fixture channels 145-152; they are not part of the RGB grid
- physical commissioning confirmed Parts 1-8 progress right-to-left and each
  part drives both rows, identically on both fixtures
- normal output keeps those parts at zero; browser live can separately arm
  deterministic effect motion, audio accents, or both. Continuous motion stays
  inside the 10% Rehearsal envelope; explicitly authored flashes and audio
  accents retain the 0.10-second/4 Hz pulse limiter

The committed settings are in [`config/fixtures.toml`](config/fixtures.toml).

## Install on Windows

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

There are no third-party runtime dependencies. Tkinter, included with standard
CPython Windows installers, supplies the preview window.

## Run safely in simulation

Simulation is the default and does not create an Art-Net socket:

```powershell
phreqed-dmx simulate
phreqed-dmx simulate --preset molten-motion
phreqed-dmx simulate --effect kaleidoscope --palette neon
phreqed-dmx simulate --effect fire --mode independent --second-effect digital-rain
phreqed-dmx simulate --effect energy-transfer
phreqed-dmx simulate --preset acid-mirrors
phreqed-dmx simulate --preset crossfire
phreqed-dmx simulate --preset matrix-rain
phreqed-dmx simulate --preset blaster-sweep
phreqed-dmx simulate --preset flame-thrower
phreqed-dmx simulate --preset wave-rider
phreqed-dmx simulate --preset pacman-chase
phreqed-dmx simulate --preset pixel-flight
phreqed-dmx simulate --preset stickman-step
phreqed-dmx simulate --preset shape-shifter
phreqed-dmx simulate --preset inside-out-vu
```

The preview shows both cubes from the front and provides:

- preset and independent per-cube effect selection;
- palette and validated parameter controls;
- global speed and brightness;
- pause/resume and manual frame stepping;
- measured frame rate, blackout, one-touch parameter resets, keyboard shortcuts,
  and PNG/PPM screenshot export.

Changing a cube control switches the engine from its active preset to manual
per-fixture mode. Simulation calls normalized scene rendering only and never
constructs an Art-Net sender.

Generate the deterministic browser gallery without opening Tkinter or any
hardware output:

```powershell
python scripts/render-effect-gallery.py --output output/effect-gallery
```

Open `output/effect-gallery/index.html` to compare every effect and preset at
the fixed 0.00, 1.75, and 4.00 second marks. `manifest.json` records each PNG's
SHA-256 digest so later visual changes can be reviewed deliberately.

## Run browser simulation

Browser mode is also simulation-only by default:

```powershell
phreqed-dmx web
```

Open `http://127.0.0.1:8080`. The controller previews both fixtures, edits and
persists user looks, builds timed scene lists, and exposes blackout and show
transport controls. The default library is stored outside the repository at
`~/.local/share/phreqed-dmx/library.json`.

The controller is now one adaptive application with **Perform**, **Setlist**,
**Build**, **Settings**, and **Operations** workspaces. Setlist separates the
full-width Song Builder from the ordered-show builder; Build is reserved for
looks and manual scenes. Setlists can be copied, and Looks, Scenes, Songs,
timeline cues, and running orders use five-item touch pages instead of nested
scroll regions. Song timelines, song details, and scene editing open as focused
task overlays while the persistent blackout remains reachable.
The 1280 x 800 touchscreen Perform
view keeps stage transport, master, health, fixture previews, output state, and
blackout in one non-scrolling viewport. The playing song keeps a prominent time
bar with elapsed and remaining time, while Start live and Stop output share the
bottom safety row with blackout. Setlist is the startup mode, large
Setlist/Manual buttons replace the former mode dropdown, and the bottom stage
bar exposes the three built-in venue profiles plus up to two saved custom
shortcuts. Manual look selection also avoids the native dropdown: a 64-pixel
trigger opens a focused picker with six large choices per touchscreen page and
three or four per phone page, automatically locating the active look. Selecting
a look applies it immediately and closes the picker while BLACKOUT remains
reachable.
Touch-sized minus/plus controls adjust the prepared center-white
level in one-percent steps; the adjacent output button remains separately gated
and level adjustment never arms physical whites. Phones receive compact bottom
navigation and desktops receive denser split editors. The same show and
authoring capabilities remain available on every surface. Only display and
network operating-system actions are loopback-only. See
[`docs/touchscreen-control-roadmap.md`](docs/touchscreen-control-roadmap.md).

The focused song-timeline editor exposes each scene's sequence, duration, and
transition. Large Up/Down controls reorder complete scene segments without a
drag-only gesture. Editing a segment duration preserves the song's fixed total
length by adjusting its neighboring segment, and invalid or too-short segments
are rejected before the cue sheet is saved.

Each browser now renews a distinct trusted lease. An optional native kiosk
supervisor can hold an independent local lease while Chromium is alive, so
losing a phone alone does not stop output. Loss of every trusted surface still
uses the existing five-second fail-dark path. Kiosk startup and local
operations are explicit Pi deployment options and are never enabled by browser
simulation.

Settings includes immutable **Rehearsal**, **Small Stage**, and **Large Stage**
profiles. Rehearsal restores the recommended 25% starting master, Small Stage
uses approximately three quarters of the persistent safe range (49%), and
Large Stage uses the complete persistent safe range (65%). Profiles also group
contrast, audio-dimming, onset, white drive, and prepared white-level settings.
Applying a profile never unlocks Show power, raises a ceiling, or arms physical
whites, even when the profile stores a requested level above 10%.
Configure the Settings controls and choose **Save as new** to create an
atomic user profile in `tuning-profiles.json`; built-ins cannot be overwritten
or deleted. Select an existing user profile and use **Save to _profile_** to
update it in place. Mark up to two custom profiles **Show on Perform** to add
them beside the three built-in stage shortcuts. Small Stage prepares the
commissioned center whites at 5%; their Effect drive works without audio after
explicit live output and separate white arming. Audio mode remains unavailable
without a configured source. The three built-ins come from the package-owned
`tuning_profiles.defaults.json`; upgrades replace that read-only baseline but
never copy it over the user's tuning profile file, song library, or look/scene
library.

For trusted-LAN preview from the Pi, bind explicitly while remaining in the
simulation-only `web` command:

```bash
.venv/bin/phreqed-dmx web --host 0.0.0.0 --allow-network 192.168.1.0/24
```

This opens only the browser HTTP server; it cannot enable Art-Net output.
The Stage Monitor has a browser-only display-brightness slider, defaulting to
2x, so quiet audio-reactive patterns remain visible. Its value is stored only
in that browser and never changes rendered frames, master brightness, Art-Net,
or any fixture safety ceiling.

### Preview microphone response

On the Pi, microphone capture remains off unless a device is named explicitly.
The verified Blue Snowball ALSA name is stable across USB card-number changes:

```bash
.venv/bin/phreqed-dmx web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --preset phase-collider \
  --audio-device plughw:CARD=Snowball,DEV=0
```

This command is still browser simulation and cannot transmit Art-Net. The page
shows loudness, onset, bass, mid, and treble meters. If response is too weak or
too sensitive, add `--audio-sensitivity 8` (valid range `0.1..40`, default
`12`). Tempo establishes the base animation rate for every effect. Smoothed
music dynamics then vary motion from 0.7x to 1.5x around that baseline and
brightness from 55% to 100% of the manual master; they never raise the RGB
ceiling. Automatic microphone leveling is on by default and slowly reduces
analysis gain when sustained venue volume would otherwise pin a meter; it can
be toggled in the browser or disabled with `--no-audio-auto-level`. Input loss clears
the analysis to silence without stopping controls or tempo-driven movement.
Enable **Deep dim on quiet passages** in the browser to replace the normal 55%
floor with an adjustable 0%-25% near-black floor. The setting changes only the
audio multiplier; the master slider remains the persistent peak level when
presets or scenes change.
The browser's **Visual contrast** control (1.0x-3.0x) expands separation between
dim and bright pixels without increasing the master or RGB ceiling. This is
particularly useful for fill-heavy looks at higher master settings.
See [Audio synchronization](docs/audio-synchronization.md) for limitations and
the remaining Raspberry Pi timing gate.

## Hotone Ampero Control

The [Hotone Ampero Control](https://www.hotone.com/products/controlers/Ampero%20Control)
is a four-switch programmable MIDI controller. The initial Phreqed bank maps
switches 1–3 to previous scene, next scene,
and tap tempo. Switch 4 sends explicit blackout-on/off values. USB MIDI is the
recommended first-stage transport because it also powers the controller and
avoids Bluetooth pairing failures.

Foot input is disabled unless `--foot-midi-device` is supplied. For setup,
message assignments, Pi device discovery, and safe testing, see
[`docs/ampero-control.md`](docs/ampero-control.md).

If USB MIDI drops temporarily, the reader closes and reopens the configured
device instead of silently terminating. The browser reports connection state,
message count, and reconnect count. A stable udev path is still required before
unattended stage use because `/dev/snd/midiC3D0` can change after re-enumeration.
The show-service installer now provides `/dev/snd/phreqed-ampero-midi`, matched
to the commissioned Hotone USB identity, for this purpose.
If the explicitly selected node is absent at startup, the browser controller now
stays available and reports that MIDI is waiting while retrying that same path;
it never guesses at or binds another MIDI device.

Adjacent Ampero switches can select another hardware bank when pressed
together. The previously intermittent loss of mapped actions was diagnosed as
an accidental change from bank 0 to bank 1, not erased programming. Keep bank 0
selected until the performance-safe multi-bank profile in `CONTROL-003` is
validated; if actions stop, return to bank 0 and verify all four controls in
simulation before resuming live output.

## Song and setlist control

The browser **Songs** tab now provides a manual Song Library, editable baseline
cue timelines, immutable published revisions, simulation-only cue previews, and
an ordered Setlist Builder. Metadata is saved atomically in `songs.json` beside
the configured user library; no audio media is stored there. Start the safe
browser simulator, open **Songs**, create a song, create a cue-sheet revision,
preview and publish it, then add the song to a setlist.
The Setlist Builder's search field filters the Add song selector by title or
artist; selecting a match does not change the setlist until **Add song** is
pressed.

Each song can optionally be tagged **Punk**, **Rock**, **Mellow**, **Funk**,
**Metal**, **Alternative**, **Blues**, **Reggae**, or **Electronic**.
The timeline editor's **Apply style default** action scales a deterministic
sequence of suitable looks across that song's duration. The result is an
unpublished draft: preview, reorder, edit, or remove cues before publishing it.
Applying a style never overwrites a published revision or starts playback.

| Style | Default character |
| --- | --- |
| Punk | Nine fast, aggressive sections with short cuts |
| Rock | Eight driving sections with a broad finale |
| Mellow | Six long sections with smooth, restrained fades |
| Funk | Eight rhythmic, playful sections emphasizing VU and patterned motion |
| Metal | Ten dense, high-energy sections with heat and hard directional motion |
| Alternative | Eight contrasting textures with unexpected section changes |
| Blues | Seven warm, slow-moving sections with restrained expressive peaks |
| Reggae | Eight relaxed, offbeat sections with rolling patterned motion |
| Electronic | Nine progressive digital sections with crisp synthetic changes |

The browser **Perform** tab has explicit **Manual scenes** and **Setlist
performance** modes. Setlist mode shows the current and next song, elapsed and
remaining time, and previous/start-stop/next controls. Selecting the mode,
setlist, or song only arms it; **Start Song** is always explicit. Completion
selects the next song in an armed state and never starts it automatically.

The Ampero mapping is mode-specific: in Manual mode FS1/FS2 select scenes and
FS3 taps tempo; in Setlist mode FS1/FS2 select songs and FS3 starts or stops the
selected song. FS4 remains the global blackout in both modes. Blackout, Stop
output, loss of every trusted control lease, or application shutdown stops the song timeline
and releasing blackout does not resume it.

The browser is the authoritative current/next-song display. The documented
Ampero Control interface does not expose arbitrary host-controlled display text,
so do not depend on its bank number as the setlist position.

Song playback will always require an explicit performer start; completion may
arm the next song but will not start it automatically. AI is planned only as an
offline authoring assistant whose proposals are reviewed and published before a
show. Initial analysis accepts either a user-owned/licensed MP3 upload or an
explicit rehearsal listening session from the configured microphone; streaming
links are out of scope. Both inputs build a baseline scene timeline. At a show,
the existing microphone-reactive layer still adjusts intensity and motion inside
the selected scenes to follow the actual performance.
See [Song Builder and Setlist Performance Roadmap](docs/song-setlist-roadmap.md).
For show operation and recovery, see
[Setlist performance operation](docs/setlist-performance.md).

## Run live on the Raspberry Pi

The Pi deployment is terminal-only and does not require Codex or VS Code. After
cloning the repository, `bash scripts/pi-install.sh` creates the environment,
installs the controller, and runs its tests. Later clean deployments use
`bash scripts/pi-update.sh`, which restarts and verifies the managed controller
service after the tests pass. Do not update during a performance.

Live network output requires the explicit flag:

```bash
phreqed-dmx live --preset psychedelic-bloom
```

Do this only after checking QLC+, fixture modes, addresses, physical safety, and
the operator blackout control. On handled shutdown, the app sends a best-effort
blackout. See [Raspberry Pi deployment](docs/raspberry-pi-deployment.md).

For unattended shows, the repository now includes a systemd boot sequence that
starts headless QLC+ and then the browser controller while leaving lighting
output stopped. The recommended control layout uses the USB Ampero as the
offline performance control and a private, internet-independent stage LAN for
the phone interface. See
[Headless show control](docs/headless-show-control.md).

The managed controller also pulls in `phreqed-show-inhibit.service`, which
blocks operating-system sleep and idle suspension while the show controller is
active. It does not block shutdown. An attached display may dim or blank, but
that must not suspend QLC+, Phreqed, audio, MIDI, or the active timeline.

Commands accept `--brightness` and `--speed`. The RGB ceiling defaults to 0.65.
For a physically checked show rig, a higher temporary ceiling requires all of
the following explicit live options:

```bash
.venv/bin/phreqed-dmx live --web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --rgb-ceiling 0.85 --acknowledge-high-output
```

Browser live still starts at 0.25 or lower and in the 0.65 **Rehearsal** power
profile. When a higher ceiling was explicitly supplied, the Performance panel
offers a separately confirmed **Show** power profile that unlocks the master
slider to that configured ceiling. Stop output, browser lease loss, render
failure, shutdown, and restart all restore Rehearsal power. The luminance-rise
and flash-interval limiter remain active. Saved presets remain capped at 0.65,
and this RGB override does not change the separately configured white-channel
ceiling. Use `--effect`
for manual mode, with `--mode mirror|complementary|independent` and
`--second-effect` where needed. Run `phreqed-dmx --help` for the complete effect
and preset lists. With no command, the CLI defaults to simulation; network
output can only be selected with the literal `live` command.

The acknowledged ceiling may be set as high as `1.0` when full RGB range is
required for a physically checked show. Treat that as available headroom, not a
recommended starting level: start live output, confirm **Show** power in the
Performance panel, and raise the master gradually. The browser always starts at
25% or lower in Rehearsal power.

Browser-controlled lighting requires both the explicit live command and web
option. It still starts with output stopped and requires confirmation in the
page:

```bash
.venv/bin/phreqed-dmx live --web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --audio-device plughw:CARD=Snowball,DEV=0
```

Live browser output is capped at 25% when first enabled and stops with blackout
if every trusted local and remote lease is absent for five seconds. Keep QLC+
blackout available; leases are an additional safeguard, not a substitute for
physical controls.

An optional browser **Shut down Pi** control can request a clean systemd
power-off after first stopping the song timeline and blacking out/closing live
output. It is disabled by default, requires a narrowly authorized root-owned
power-off helper and the `--allow-system-shutdown` startup flag, and then
requires typing `SHUTDOWN` in
the page. It is never available in simulation-only browser mode. See the
deployment guide before enabling it.

Center-white output is an additional explicit step after browser live starts.
It requires the **Arm physical segmented white output** toggle. Effect drive runs
deterministic motion without a microphone; Audio Accents requires an active
source, and Hybrid combines both. Every registered effect selects a pattern on
the sixteen-part left-to-right accent canvas. Signature motion includes blaster,
flame, wave, VU, sprite, energy-transfer, bloom, rain, current, collision, blade,
ember, mirror, lava, and tunnel accents. Presets select only a pattern; they
cannot arm output.
The default level is 5% and White Rehearsal power is capped at 10%. Blackout, Stop output,
performance-mode changes, render failure, or browser-lease loss disarms it; it
never activates in the simulation-only `web` command or ordinary non-browser
live mode. The simulator displays the exact eight-part array for each fixture.

After low-level commissioning, an operator may explicitly expose a higher
center-white ceiling for one browser-live process. Start conservatively and
raise it only as needed:

```bash
.venv/bin/phreqed-dmx live --web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --audio-device plughw:CARD=Snowball,DEV=0 \
  --white-ceiling 0.40 --acknowledge-high-output-whites
```

Values above 0.10 are rejected without both explicit `live --web` and the
white-specific acknowledgement. The browser shows a persistent warning and
allows that range to be prepared, but a second in-page confirmation must unlock
White Show power and that change disarms physical output. Continuous effect
motion remains capped at 10%; authored flashes and audio accents may reach the
active Show ceiling while retaining the 0.10-second pulse, 4 Hz, blackout, stop,
failure, and lease-loss controls.

## Test

Tests construct packets and exercise mapping entirely in memory; they need no
QLC+, network access, or DMX hardware:

```powershell
python -m unittest discover -s tests -v
```

## Design

See [architecture](docs/architecture.md) for module boundaries and the exact
pixel map. Contributor and safety rules are in [`AGENTS.md`](AGENTS.md).
