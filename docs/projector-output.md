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
show command / pedal
        |
        v
show coordinator
   |             |
   v             v
lighting cue     projection cue
   |             |
25 FPS DMX       separate player/compositor process
renderer         -> selected HDMI output
```

The projection process owns video decoding, frame timing, scaling, overlays,
and the HDMI surface. It communicates with show control through a small command
boundary and never runs inside the DMX render thread. A player crash, missing
file, slow decode, or disconnected projector must not stall DMX, audio capture,
pedal input, browser blackout, or shutdown handling.

Media files should live in an operator-configured directory outside the source
repository. Show data stores validated relative media identifiers rather than
arbitrary commands or remote URLs. Missing media falls back to a black output
and a visible controller error.

## Delivery phases

1. Playback foundation: explicitly enabled local video/image playback, HDMI
   output selection, play/pause/stop/seek/loop, and reliable black output.
2. Projector compositor: video plus procedural or shader overlays with opacity,
   blend modes, crop/fit, global intensity, and smooth transitions.
3. Unified show cues: one cue selects both a lighting preset and an optional
   projection preset, with independent failure handling.
4. Audio response: reuse normalized `AudioAnalysis` values for bounded overlay
   parameters without coupling capture to the video backend.

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
