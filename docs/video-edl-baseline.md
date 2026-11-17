# Video EDL and Stage rendition baseline

The baseline keeps authoring decisions separate from show-critical playback:

```text
immutable local originals
        -> local asset-ID map
        -> versioned Video EDL
        -> validated FFmpeg build
        -> H.264 Stage rendition + checksummed manifest
        -> separately supervised projection player
```

Original media is never edited or copied into the repository. A Video EDL uses
logical asset IDs, source in/out times, fit mode, focal point, fades, and a
projection profile. Local filesystem paths live only in an ignored asset map.
The EDL is therefore portable into the future Studio asset library without
making a developer path part of show data.

## Current baseline

The implemented renderer supports sequential, non-overlapping clips with:

- non-destructive source in/out ranges;
- `cover` or `contain` fitting;
- normalized horizontal and vertical focal points;
- per-clip fade in/out;
- a logical canvas, optional clockwise/counter-clockwise output rotation, and
  an explicit rear-screen horizontal mirror;
- normalized 1-30 FPS output within the initial 1080p pixel budget;
- audio-free H.264 High 4.1, `yuv420p` Stage renditions; and
- source, EDL, and output SHA-256 hashes in a package manifest.

The first profile is a logical 1080×1920 portrait canvas. Use `output_rotation:
"none"` when the Pi compositor already exposes a portrait display. Use
`clockwise` or `counterclockwise` to encode the logical portrait canvas into a
1920×1080 signal for a physically rotated projector that still advertises a
landscape mode.

Set `horizontal_flip: true` only when projecting through the back of a screen.
The renderer mirrors the upright logical canvas before applying the selected
output rotation, so front/rear placement and physical projector rotation remain
independent choices. The default is `false`, and existing front-projection EDLs
and package hashes remain unchanged.

This slice deliberately does not yet render overlapping VFX layers, alpha,
blend modes, live shaders, or song transport. Those remain `PROJ-002` and
`SHOW-002`. The initial Stage player backend also remains unselected until VLC,
mpv, and GStreamer are compared on the commissioned Pi.

## Local render workflow

Create the ignored local asset map from the example:

```powershell
New-Item -ItemType Directory -Force output/video-render | Out-Null
Copy-Item examples/video/assets.local.example.json `
  output/video-render/assets.local.json
```

Edit `output/video-render/assets.local.json` so `travelling-master` resolves to
the immutable source file. Run the short portrait probe first:

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-five-second-probe.edl.json `
  --assets output/video-render/assets.local.json `
  --output output/video-render
```

After reviewing that output, render the complete baseline:

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-baseline.edl.json `
  --assets output/video-render/assets.local.json `
  --output output/video-render
```

Existing renditions are not replaced implicitly. Rebuilding the same package
requires `--overwrite`. FFmpeg is always invoked as an argument vector without
a shell; an EDL cannot contain a command or remote URL.

## Stage preflight and player boundary

`load_stage_video_package()` accepts only a local MP4 filename beside its
manifest. It validates schema version, embedded EDL hash, package identity,
duration, dimensions, frame rate, H.264/pixel format, absence of audio, file
size, and rendition hash before returning a playable package.

`ProjectionController` is disabled and black when no backend is explicitly
injected. Its load, play, pause, seek, stop, black, and close boundary is
independent of DMX. The future Pi backend must keep output black during load and
pre-roll, fail black on error, and never run in the lighting render thread.

## Pi display probe

With the projector attached, run the read-only inventory:

```bash
.venv/bin/python scripts/projector-probe.py \
  --output /tmp/phreqed-projector-probe.json
```

It records the active session, available display inventories (`wlr-randr`,
`kmsprint`, or `xrandr`), and installed VLC/mpv/GStreamer/FFmpeg candidates. It
does not change display configuration or launch playback.

## Commissioned projector checkpoint

The 2026-11-16 Pi probe found the touchscreen on `DSI-1` at 1280×800 and the
projector on `HDMI-A-2` at its preferred/current 1280×720@60 mode, positioned to
the right at `1280,0`. The projector is physically vertical but the compositor
transform remains `normal`. The commissioned profile is therefore a logical
720×1280 portrait canvas rotated clockwise into a 1280×720 signal at build
time. The counter-clockwise package remains a diagnostic probe rather than a
show profile. VLC/cVLC and FFmpeg/FFprobe are present; mpv and GStreamer are not
installed.

Both front-projection orientation packages completed on the commissioned HDMI
output. VLC reported that its V4L2 H.264 decoder could not start, then opened an
I420 Wayland `wl_dmabuf` video output and exited successfully after playback.
That fallback is acceptable for the bounded probe but remains a CPU,
temperature, and dropped-frame soak-test item before full-song use. The Qt
global-hotkey interface warning from the SSH/TTY launch was also non-fatal.

The bounded VLC probe preflights the package, resolves the active user Wayland
socket for an SSH/TTY launch, selects a Qt fullscreen screen, disables audio and
OSD, plays once, and exits. It still requires explicit
`--confirm-projector-output`; it does not start lighting or make projection a
managed service.

Generated media remains outside Git. Transfer the bounded orientation bundle
from the development computer, extract it under the Stage user's data directory,
then run one manifest at a time:

```powershell
scp output/video-render/phreqed-projector-orientation-probes.tar.gz `
  mmorley@192.168.1.89:/tmp/
```

```bash
probe_dir="$HOME/.local/share/phreqed-dmx/video-probes"
mkdir -p "$probe_dir"
tar -xzf /tmp/phreqed-projector-orientation-probes.tar.gz -C "$probe_dir"

cd "$HOME/phreqed-stage-dmx-light-controller"
.venv/bin/python scripts/vlc-projector-probe.py \
  "$probe_dir/travelling-hdmi720-clockwise-probe--portrait-hdmi720-clockwise.manifest.json" \
  --screen 1 --confirm-projector-output
```

If Qt screen 1 targets the touchscreen instead of the projector, let the
five-second probe exit and repeat with `--screen 0`; do not change the DSI or
Wayland display configuration during this orientation check. Physical testing
selected the clockwise package as upright.

For a projector behind the screen, render and transfer the matching `-rear`
EDL instead. The resulting package is pre-mirrored; VLC receives the same fixed
1280×720 signal and needs no runtime video-filter setting:

```powershell
py -3.12 scripts/render-video-edl.py `
  examples/video/travelling-five-second-hdmi720-clockwise-rear.edl.json `
  --assets output/video-render/assets.local.json `
  --output output/video-render
```

The commissioned vertical rear-screen profile is therefore `clockwise` with
`horizontal_flip: true`. Keep both choices explicit in the EDL; do not rotate or
mirror the desktop compositor to achieve this output.

The full-length soak source is
`examples/video/travelling-baseline-hdmi720-clockwise-rear.edl.json`. It compiles
the 146-second Travelling master into the same commissioned 1280×720 profile.
Generated media remains ignored; transfer
`output/video-render/phreqed-projector-full-soak.tar.gz` separately to the Pi.

## Stage layout modes

Stage authoring exposes two named content layouts rather than making an operator
reason about canvas dimensions during a show:

- **Stage Portrait (9:16):** a logical 720×1280 canvas for a physically vertical
  screen. Clips default to `cover` so performers, characters, and VFX occupy the
  full-height stage surface. Per-clip focal points select which part of a wider
  source survives the crop. The commissioned rear-screen output rotates this
  canvas clockwise and mirrors it horizontally into a 1280×720 HDMI signal.
- **Standard Landscape (16:9):** a 1280×720 canvas with no rotation for a normal
  horizontal screen. Clips default to `cover`; `contain` remains an explicit
  editorial choice when preserving every source edge matters more than size.

Front/rear placement is independent from layout. Rear projection applies the
horizontal mirror; front projection does not. Studio should therefore present
**Layout** (Portrait/Landscape) and **Projection side** (Front/Rear) as separate
controls, then derive the output transform from the paired Stage display
profile. The initial probes are
`travelling-fifteen-second-stage-portrait-rear.edl.json` and
`travelling-fifteen-second-stage-landscape-front.edl.json`.

`cover` is only the baseline crop. Character-focused scenes should eventually
support a reviewed focal path or isolated alpha/green-screen character layer so
dancers can be framed large beside the live performers without losing important
motion at the portrait edges.

The first synchronized-song reference is **Travelling on a Floating Rock**.
`travelling-on-a-floating-rock-stage-portrait.edl.json` builds its full 146
seconds with the accepted Stage Portrait fill. The rendered package passes Stage
preflight as
`travelling-floating-rock-stage-portrait--stage-portrait-hdmi720-clockwise-rear`.
Generated media is bundled outside Git as
`output/video-render/phreqed-travelling-reference-package.tar.gz`.

## Publish the first song-bound Video lane

The publication helper reads the Pi's existing `songs.json`, resolves the
exact title **Travelling on a Floating Rock** to its stored song ID, and
requires that song to be present in at least one saved setlist. It preflights
the rendered package directory before atomically creating the separate
`video-show.json` sidecar. It never modifies `songs.json` and refuses to replace
a different existing Video Show sidecar.

If the accepted package is still in the commissioned probe directory:

```bash
cd "$HOME/phreqed-stage-dmx-light-controller"
.venv/bin/python scripts/install-travelling-video-track.py \
  --packages "$HOME/.local/share/phreqed-dmx/video-probes"
```

For normal service use, keep packages in the dedicated directory and publish
against that location instead:

```bash
video_packages="$HOME/.local/share/phreqed-dmx/video-packages"
mkdir -p "$video_packages"
# Extract the transferred reference package into "$video_packages" first.
.venv/bin/python scripts/install-travelling-video-track.py \
  --packages "$video_packages"
```

Video output remains disabled unless explicitly enabled in
`/etc/default/phreqed-dmx`:

```ini
PHREQED_VIDEO_OUTPUT=1
PHREQED_VIDEO_PACKAGES=/home/mmorley/.local/share/phreqed-dmx/video-packages
PHREQED_VIDEO_LIBRARY=/home/mmorley/.local/share/phreqed-dmx/video-show.json
PHREQED_VIDEO_OUTPUT_NAME=HDMI-A-2
PHREQED_VIDEO_SURFACE=portrait-character
```

The commissioned Pi uses one 2560×800 extended Labwc desktop, so VLC's numeric
Qt screen selector is not a reliable output boundary. Install and validate the
named-output window rule before enabling managed Video:

```bash
.venv/bin/python scripts/configure-labwc-projection.py --output HDMI-A-2
env LABWC_PID="$(pgrep -xo labwc)" labwc --reconfigure
.venv/bin/python scripts/configure-labwc-projection.py \
  --output HDMI-A-2 --check
```

The helper preserves the existing Goodix-to-`DSI-1` mapping and unrelated
Labwc settings, replaces only the VLC routing/fullscreen actions, removes the
temporary Phreqed error-capture hook if present, writes atomically, and creates
a timestamped backup only when a change is needed. The commissioned Labwc
0.20.2 build requires `ToggleFullscreen`; it rejects `SetFullscreen`.

Restarting the controller then preflights every package before the web service
starts. The managed player deliberately unsets Wayland selection and launches
an undecorated XCB window; Labwc moves that `vlc` window to the named projector
and makes it fullscreen. Setlist Start launches the active Video Scene from the Lighting song
clock; Stop, selection, completion, blackout, and Manual mode stop Video. A
Video launch failure is reported but cannot stop Lighting. This is still a
commissioning-stage adapter: the projector compositor background must be black,
and the independently supervised output-black surface, pause/seek, drift, and
actual-DMX coexistence acceptance remain open.
