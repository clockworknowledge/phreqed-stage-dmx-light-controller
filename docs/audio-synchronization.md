# Audio synchronization sprint

Audio synchronization is split into a deterministic visual contract and an
optional capture implementation. Effects consume normalized analysis values;
they never open microphones, import capture libraries, or depend on operating
system device identifiers.

## Delivered contract — AUDIO-001

`audio_analysis.py` defines:

- `AudioAnalysis`: normalized `loudness` and transient `onset` values;
- `FrequencyBands`: normalized `bass`, `mid`, and `treble` energy;
- `AudioAnalysisSource`: the source boundary used by the controller;
- `ManualAudioAnalysisSource`: a thread-safe injection point for controls and a
  future capture worker;
- `RecordedAudioAnalysisSource`: deterministic previous-sample playback for
  tests and recorded analysis sessions.

Every value is finite and within `0.0..1.0`. `PerformanceContext.audio` is
optional, so existing effects and shows retain their exact non-audio behavior
when no source is configured. The older `energy` field remains a manual
performance control and is not treated as measured loudness.

`AudioReactiveClock` is the shared consumer for every effect. Tap tempo/BPM sets
the baseline clock rate (120 BPM is 1.0x), and the manual `--speed` value is an
additional operator trim. Smoothed loudness, onset, and band energy raise the
motion multiplier from 1.0x to at most 2.0x. Silence therefore retains steady
tempo-driven motion instead of freezing the stage.

The operator's master brightness remains the peak level. With an audio source,
smoothed dynamics modulate visual output between 55% and 100% of that master;
they can never raise it or the RGB ceiling. Radial Pulse also retains its
effect-local ring and colour response. All normalized output remains clamped,
and the frame-rise limiter still applies after modulation.

## Real-time capture sprint — AUDIO-002

The first capture implementation is complete and awaiting Pi application-level
timing validation. `audio_capture.py` provides:

1. an explicitly started `ArecordAudioSource`; construction and import do not
   enumerate or open devices;
2. 44.1 kHz, signed 16-bit, mono PCM capture in a worker outside the 25 FPS
   render loop;
3. a deterministic, standard-library analyzer with smoothed loudness, bounded
   onset, and lightweight bass/mid/treble crossover filters;
4. adaptive ambient-noise-floor tracking and adjustable input sensitivity;
5. capture health plus five analysis meters in browser control; and
6. silence-on-EOF/error behavior, leaving render, blackout, and browser control
   running if the microphone disappears.

The Pi detected the Blue Snowball as USB ID `0d8c:0005` and ALSA capture device
`hw:CARD=Snowball,DEV=0`. A direct `arecord` hardware-format and level-meter
check passed. The application uses `plughw:CARD=Snowball,DEV=0` so ALSA may
perform safe format conversion without relying on the unstable numeric card
index. PipeWire/PulseAudio and `pactl` are not required.

The operator also completed an application-level browser simulation on the Pi
with Phase Collider and reported that capture, all browser meters, and the
audio-reactive visual worked. Art-Net remained unavailable in this mode. This
is functional acceptance, not the outstanding sustained performance test.

Capture will remain optional and disabled by default. Starting capture will not
select live mode, start Art-Net, change scenes, or bypass browser confirmation.
Initial audio response will modulate continuous visual parameters only; automatic
scene changes and aggressive full-frame onset flashes are outside this sprint.

Safe microphone preview on the Pi:

```bash
.venv/bin/phreqed-dmx web --host 0.0.0.0 \
  --allow-network 192.168.1.0/24 \
  --preset phase-collider \
  --audio-device plughw:CARD=Snowball,DEV=0
```

This uses the simulation-only `web` command. The default sensitivity is `12`;
override it with `--audio-sensitivity` in the range `0.1..40`. The browser shows
the resulting shared motion and brightness multipliers below the five analysis
meters. Tempo supplies the base motion rate for every effect; audio dynamics
modulate that rate and scale brightness below the manual master. Microphone
analysis cannot raise a configured show-time ceiling.

## Acceptance gates

- With no explicit audio device, the capture module is not imported and
  rendered output matches the current deterministic baseline.
- Generated and recorded input produces deterministic normalized analysis.
- Invalid, NaN, infinite, and out-of-range analysis values are rejected.
- Audio loss cannot stop blackout handling or the 25 FPS control loop.
- Simulator mode remains incapable of sending Art-Net.
- Reserved LF4808 channels remain zero for every audio-driven frame.
- Raspberry Pi CPU, analysis latency, and missed-frame measurements are
  documented before performance acceptance. This final gate remains open.
