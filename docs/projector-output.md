# Projector output roadmap

Projector output is feasible on the Raspberry Pi 5, but it must remain isolated
from the 25 FPS DMX deadline. The Pi 5 provides two micro-HDMI outputs, a
VideoCore VII GPU, and hardware HEVC decode. The initial target should still be
conservative 1080p playback and compositing until the complete QLC+, audio,
MIDI, browser, and projection workload has been measured together.

Official hardware references:

- [Raspberry Pi 5 processor and display capabilities](https://www.raspberrypi.com/documentation/computers/processors.html)
- [Raspberry Pi display outputs](https://www.raspberrypi.com/documentation/computers/getting-started.html#connect-a-display)
- [Raspberry Pi OS audio and video playback](https://www.raspberrypi.com/documentation/computers/os.html#play-audio-and-video)

## Proposed architecture

```text
song revision / shared deterministic clock
        |
        v
show coordinator
   |                         |
   v                         v
Lighting track              Video track
scene cues                   Video Scene cues
   |                         |
25 FPS DMX renderer          separate player/compositor process
                             -> selected HDMI output
```

The projection process owns video decoding, frame timing, scaling, overlays,
and the HDMI surface. It communicates with show control through a small command
boundary and never runs inside the DMX render thread. A player crash, missing
file, slow decode, or disconnected projector must not stall DMX, audio capture,
pedal input, browser blackout, or shutdown handling.

Studio originals and derived renditions live in tenant-scoped object storage;
local development may use an operator-configured directory. A published package
contains the exact hash-verified Stage renditions and clip ranges required by
the selected show. Stage downloads and preflights them before activation and
never streams show-critical video from Studio. Show data stores validated media
identifiers rather than arbitrary commands or remote URLs. Missing media falls
back to a black output and a visible controller error.

A reusable Video Scene contains a clip range, still, colour or black layer,
crop/fit, loop behavior, opacity, intensity, fades, and later bounded overlays.
Song revisions place Video Scene cues on a separate Video track beside Lighting.
The two tracks share explicit song start/pause/resume/seek/stop events but may
have different cue boundaries and intentional black gaps. Decoder pre-roll is
permitted only on a non-presenting surface; the projector stays black until
explicit song start.

## Delivery phases

1. Playback foundation: explicitly enabled packaged video/image playback, HDMI
   selection, invisible pre-roll, play/pause/stop/seek/loop, position/health,
   and reliable black output.
2. Parallel song transport: a separate Video track of Video Scene cues shares
   the deterministic song clock with Lighting and keeps independent failures.
3. Projector compositor: video plus procedural or shader overlays with opacity,
   blend modes, crop/fit, global intensity, and smooth transitions.
4. Audio response: reuse normalized `AudioAnalysis` values for bounded overlay
   parameters without coupling capture to the video backend.

The initial build-time foundation is complete: versioned sequential Video EDLs,
local asset-ID resolution, portrait/landscape profiles, a shell-free FFmpeg
compiler, an audio-free H.264 Stage rendition, package hashes, fail-closed
preflight, and a disabled-by-default player boundary. A real player is not yet
selected or enabled. See `docs/video-edl-baseline.md`.

The first measured-runtime slice uses `scripts/projection-soak.py`. It launches
one hash-verified package through the same fixed, audio-free VLC command as the
bounded probe, while independently rendering a safe preset at the configured
25 FPS with Art-Net construction blocked. Its atomic JSON report records player
exit/runtime, VLC fallback evidence, player CPU/RSS where Linux `/proc` exposes
them, Pi CPU temperature, renderer missed slots/overruns, reserved-channel
integrity, and final renderer blackout. This is a candidate-backend soak, not a
managed projection service or unified song transport.

VLC 3's CLI does not provide a dependable per-run dropped-frame count through
this launch path. The report records that field as unavailable rather than
claiming zero drops. Visual smoothness remains an operator observation, and a
backend with queryable frame telemetry is still preferred before `PROJ-001`
acceptance.

VLC is a useful first playback probe because Raspberry Pi OS documents its
hardware acceleration. The implementation should compare VLC, `mpv`, and a
GStreamer or OpenGL path on the actual Debian Trixie installation before fixing
the backend. Runtime overlays may justify an optional graphics dependency;
that decision belongs after a measured prototype.

## Pedal control

One Ampero Control is sufficient for the initial design because scene movement
is a show-level action:

- FS1: previous unified cue;
- FS2: next unified cue;
- FS3: tap tempo shared by lighting and supported overlays; and
- FS4: safety blackout, eventually blanking projection as well as lighting.

The current lighting blackout behavior must not be changed until projection
blanking and failure recovery have dedicated tests. A second pedal is optional
later if the performer needs independent video play/pause, clip selection, or
overlay triggers without changing the lighting scene. Ampero banks can also
provide extra mappings, but switching banks during a performance needs a clear
status display and rehearsal validation.

## Acceptance constraints

- Projection is disabled by default and requires explicit configuration.
- Simulation and automated tests never open an HDMI/DRM surface or launch a
  real player.
- DMX remains at 25 FPS if projection fails or overruns.
- Blackout and projection blank are independently testable, with one deliberate
  show-level panic action available after integration.
- Shutdown requests a black projector frame and stops playback cleanly.
- A target-Pi soak records decode/composite latency, dropped frames, CPU, GPU,
  memory, temperature, and DMX missed frames.
- Initial live validation uses non-flashing test media and conservative output.

## Commissioned Pi soak

The current vertical rear-screen profile is a logical 720×1280 canvas compiled
clockwise with `horizontal_flip: true` into a 1280×720 H.264 signal. Transfer
the generated full-length package into the existing local probe directory, then
run:

```bash
cd "$HOME/phreqed-stage-dmx-light-controller"
.venv/bin/python scripts/projection-soak.py \
  "$HOME/.local/share/phreqed-dmx/video-probes/travelling-hdmi720-clockwise-rear-soak--portrait-hdmi720-clockwise-rear.manifest.json" \
  --screen 1 \
  --output /tmp/phreqed-projection-soak.json \
  --confirm-projector-output
```

The command does not send Art-Net or enable fixture output. Keep QLC+ and the
normal controller services running to reproduce the Pi load, watch the complete
146-second image for visible judder or tearing, and preserve the JSON report.
Passing this harness proves only independent render scheduling and packaged VLC
playback; later validation must exercise the actual DMX transport and queryable
video-frame telemetry.
