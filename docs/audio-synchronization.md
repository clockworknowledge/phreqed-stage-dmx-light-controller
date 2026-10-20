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

The radial-pulse effect is the first consumer. Audio can scale an existing ring
and shift its colour slightly, but it cannot illuminate a pixel that the ring
left dark. Onset gain is deliberately limited, final normalized output remains
clamped, and the existing frame-rise limiter and global brightness ceiling
still apply.

## Real-time capture sprint — AUDIO-002

The next implementation slice will:

1. inventory Pi and Windows input devices without opening one automatically;
2. select a small optional capture backend after measuring Pi support;
3. require an explicit `--audio-device` option before capture starts;
4. capture mono PCM in a worker isolated from the 25 FPS render deadline;
5. calculate smoothed loudness, onset confidence, and three configurable bands;
6. feed only normalized `AudioAnalysis` values across the source boundary;
7. expose input health and meters in simulation/browser control;
8. degrade to non-audio animation if capture stops or overruns;
9. replay recorded PCM or analysis fixtures in automated tests; and
10. complete a Pi timing test before any performance use.

Capture will remain optional and disabled by default. Starting capture will not
select live mode, start Art-Net, change scenes, or bypass browser confirmation.
Initial audio response will modulate continuous visual parameters only; automatic
scene changes and aggressive full-frame onset flashes are outside this sprint.

## Acceptance gates

- With no explicit audio device, no capture API or third-party audio module is
  imported and rendered output matches the current deterministic baseline.
- Recorded analysis produces identical frames for identical timestamps.
- Invalid, NaN, infinite, and out-of-range analysis values are rejected.
- Audio loss cannot stop blackout handling or the 25 FPS control loop.
- Simulator mode remains incapable of sending Art-Net.
- Reserved LF4808 channels remain zero for every audio-driven frame.
- Raspberry Pi CPU, latency, and missed-frame measurements are documented.
