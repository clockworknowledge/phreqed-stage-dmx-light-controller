"""Transport-independent, normalized audio-analysis values and sources."""

from __future__ import annotations

import bisect
import math
import threading
from dataclasses import dataclass, field
from typing import Protocol


def _normalized(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class FrequencyBands:
    """Normalized low-, mid-, and high-frequency energy."""

    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0

    def __post_init__(self) -> None:
        _normalized("bass", self.bass)
        _normalized("mid", self.mid)
        _normalized("treble", self.treble)


@dataclass(frozen=True, slots=True)
class AudioAnalysis:
    """One dependency-free analysis result consumed by visual effects."""

    loudness: float = 0.0
    onset: float = 0.0
    bands: FrequencyBands = field(default_factory=FrequencyBands)

    def __post_init__(self) -> None:
        _normalized("loudness", self.loudness)
        _normalized("onset", self.onset)
        if not isinstance(self.bands, FrequencyBands):
            raise TypeError("bands must be FrequencyBands")


SILENT_AUDIO = AudioAnalysis()


class AudioAnalysisSource(Protocol):
    """Produces normalized analysis without exposing capture implementation."""

    def sample(self, elapsed: float) -> AudioAnalysis: ...


class ManualAudioAnalysisSource:
    """Thread-safe source for tests, controls, and a future capture worker."""

    def __init__(self, initial: AudioAnalysis = SILENT_AUDIO) -> None:
        if not isinstance(initial, AudioAnalysis):
            raise TypeError("initial analysis must be AudioAnalysis")
        self._lock = threading.Lock()
        self._analysis = initial

    def update(self, analysis: AudioAnalysis) -> None:
        if not isinstance(analysis, AudioAnalysis):
            raise TypeError("analysis must be AudioAnalysis")
        with self._lock:
            self._analysis = analysis

    def sample(self, elapsed: float) -> AudioAnalysis:
        if not math.isfinite(elapsed) or elapsed < 0.0:
            raise ValueError("elapsed must be finite and nonnegative")
        with self._lock:
            return self._analysis


@dataclass(frozen=True, slots=True)
class RecordedAudioFrame:
    """Analysis value at a deterministic elapsed time."""

    elapsed: float
    analysis: AudioAnalysis

    def __post_init__(self) -> None:
        if not math.isfinite(self.elapsed) or self.elapsed < 0.0:
            raise ValueError("recorded frame elapsed must be finite and nonnegative")
        if not isinstance(self.analysis, AudioAnalysis):
            raise TypeError("recorded frame analysis must be AudioAnalysis")


class RecordedAudioAnalysisSource:
    """Replays analysis frames with deterministic previous-sample hold."""

    def __init__(self, frames: tuple[RecordedAudioFrame, ...]) -> None:
        if any(not isinstance(frame, RecordedAudioFrame) for frame in frames):
            raise TypeError("frames must contain RecordedAudioFrame values")
        times = tuple(frame.elapsed for frame in frames)
        if any(right <= left for left, right in zip(times, times[1:])):
            raise ValueError("recorded audio frame times must strictly increase")
        self._frames = frames
        self._times = times

    def sample(self, elapsed: float) -> AudioAnalysis:
        if not math.isfinite(elapsed) or elapsed < 0.0:
            raise ValueError("elapsed must be finite and nonnegative")
        index = bisect.bisect_right(self._times, elapsed) - 1
        if index < 0:
            return SILENT_AUDIO
        return self._frames[index].analysis
