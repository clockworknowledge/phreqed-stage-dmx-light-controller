"""Explicit, dependency-free ALSA capture and mono PCM analysis.

Importing this module does not enumerate or open audio devices.  A capture
process exists only after :meth:`ArecordAudioSource.start` is called.
"""

from __future__ import annotations

import array
import math
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import BinaryIO, Callable

from .audio_analysis import (
    AudioAnalysis,
    FrequencyBands,
    ManualAudioAnalysisSource,
    SILENT_AUDIO,
)


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def _coefficient(duration: float, time_constant: float) -> float:
    return 1.0 - math.exp(-duration / time_constant)


def _smooth(
    current: float,
    target: float,
    duration: float,
    *,
    attack: float,
    release: float,
) -> float:
    time_constant = attack if target > current else release
    return current + (target - current) * _coefficient(duration, time_constant)


class Pcm16MonoAnalyzer:
    """Convert little-endian signed 16-bit mono PCM into normalized features.

    The two one-pole crossover filters are intentionally lightweight enough for
    a Raspberry Pi render appliance.  Analysis is stateful but deterministic
    for a given sequence of PCM chunks.
    """

    def __init__(self, sample_rate: int = 44_100, *, sensitivity: float = 12.0) -> None:
        if isinstance(sample_rate, bool) or not isinstance(sample_rate, int):
            raise TypeError("sample_rate must be an integer")
        if sample_rate < 8_000:
            raise ValueError("sample_rate must be at least 8000 Hz")
        if isinstance(sensitivity, bool) or not isinstance(sensitivity, (int, float)):
            raise TypeError("sensitivity must be numeric")
        if not math.isfinite(sensitivity) or not 0.1 <= sensitivity <= 40.0:
            raise ValueError("sensitivity must be between 0.1 and 40.0")
        self.sample_rate = sample_rate
        self.sensitivity = float(sensitivity)
        self._low_alpha = 1.0 - math.exp(-2.0 * math.pi * 250.0 / sample_rate)
        self._mid_alpha = 1.0 - math.exp(-2.0 * math.pi * 2_000.0 / sample_rate)
        self._low_state = 0.0
        self._mid_state = 0.0
        self._noise_floor = 0.003
        self._loudness = 0.0
        self._bass = 0.0
        self._mid = 0.0
        self._treble = 0.0
        self._onset = 0.0
        self._previous_target = 0.0

    def process(self, pcm: bytes) -> AudioAnalysis:
        """Analyze one non-empty, complete PCM chunk."""
        if not isinstance(pcm, bytes):
            raise TypeError("pcm must be bytes")
        if not pcm or len(pcm) % 2:
            raise ValueError("pcm must contain complete 16-bit samples")

        samples = array.array("h")
        samples.frombytes(pcm)
        if sys.byteorder != "little":
            samples.byteswap()

        full_energy = 0.0
        bass_energy = 0.0
        mid_energy = 0.0
        treble_energy = 0.0
        for sample in samples:
            value = sample / 32_768.0
            self._low_state += self._low_alpha * (value - self._low_state)
            self._mid_state += self._mid_alpha * (value - self._mid_state)
            bass = self._low_state
            mid = self._mid_state - self._low_state
            treble = value - self._mid_state
            full_energy += value * value
            bass_energy += bass * bass
            mid_energy += mid * mid
            treble_energy += treble * treble

        count = len(samples)
        duration = count / self.sample_rate
        rms = math.sqrt(full_energy / count)
        # Venue ambience may rise slowly, while a quieter room should be learned
        # within a few seconds.  The floor never directly creates output.
        floor_tau = 2.0 if rms < self._noise_floor else 20.0
        self._noise_floor += (rms - self._noise_floor) * _coefficient(duration, floor_tau)
        floor = self._noise_floor * 1.15

        target = _clamp(max(0.0, rms - floor) * self.sensitivity)
        bass_target = _clamp(
            max(0.0, math.sqrt(bass_energy / count) - floor * 0.45)
            * self.sensitivity
            * 1.8
        )
        mid_target = _clamp(
            max(0.0, math.sqrt(mid_energy / count) - floor * 0.35)
            * self.sensitivity
            * 1.4
        )
        treble_target = _clamp(
            max(0.0, math.sqrt(treble_energy / count) - floor * 0.25)
            * self.sensitivity
            * 1.2
        )

        onset_target = _clamp(max(0.0, target - self._previous_target) * 6.0)
        self._previous_target = target
        self._loudness = _smooth(
            self._loudness, target, duration, attack=0.045, release=0.35
        )
        self._bass = _smooth(self._bass, bass_target, duration, attack=0.06, release=0.4)
        self._mid = _smooth(self._mid, mid_target, duration, attack=0.06, release=0.4)
        self._treble = _smooth(
            self._treble, treble_target, duration, attack=0.04, release=0.3
        )
        self._onset = _smooth(
            self._onset, onset_target, duration, attack=0.012, release=0.12
        )
        return AudioAnalysis(
            _clamp(self._loudness),
            _clamp(self._onset),
            FrequencyBands(
                _clamp(self._bass), _clamp(self._mid), _clamp(self._treble)
            ),
        )


@dataclass(frozen=True, slots=True)
class AudioCaptureStatus:
    """A thread-safe snapshot of the optional capture worker."""

    running: bool = False
    healthy: bool = False
    message: str = "disabled"
    chunks_processed: int = 0


ProcessFactory = Callable[..., subprocess.Popen[bytes]]


class ArecordAudioSource:
    """Read explicit ALSA mono input through a supervised ``arecord`` worker."""

    def __init__(
        self,
        device: str,
        *,
        sample_rate: int = 44_100,
        chunk_frames: int = 1_024,
        sensitivity: float = 12.0,
        executable: str = "arecord",
        process_factory: ProcessFactory = subprocess.Popen,
    ) -> None:
        if not isinstance(device, str) or not device.strip():
            raise ValueError("audio device must be a non-empty ALSA device name")
        if isinstance(chunk_frames, bool) or not isinstance(chunk_frames, int):
            raise TypeError("chunk_frames must be an integer")
        if not 128 <= chunk_frames <= 16_384:
            raise ValueError("chunk_frames must be between 128 and 16384")
        if not isinstance(executable, str) or not executable:
            raise ValueError("arecord executable must be non-empty")
        self.device = device
        self.sample_rate = sample_rate
        self.chunk_frames = chunk_frames
        self.analyzer = Pcm16MonoAnalyzer(sample_rate, sensitivity=sensitivity)
        self.executable = executable
        self._process_factory = process_factory
        self._latest = ManualAudioAnalysisSource()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status = AudioCaptureStatus(message="configured; not started")
        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None

    @property
    def command(self) -> tuple[str, ...]:
        return (
            self.executable,
            "-q",
            "-D",
            self.device,
            "-f",
            "S16_LE",
            "-c",
            "1",
            "-r",
            str(self.sample_rate),
            "-t",
            "raw",
        )

    def sample(self, elapsed: float) -> AudioAnalysis:
        return self._latest.sample(elapsed)

    def status(self) -> AudioCaptureStatus:
        with self._lock:
            return self._status

    def _set_status(self, **changes: object) -> None:
        with self._lock:
            current = self._status
            self._status = AudioCaptureStatus(
                running=bool(changes.get("running", current.running)),
                healthy=bool(changes.get("healthy", current.healthy)),
                message=str(changes.get("message", current.message)),
                chunks_processed=int(
                    changes.get("chunks_processed", current.chunks_processed)
                ),
            )

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("audio capture is already started")
        self._stop_event.clear()
        try:
            process = self._process_factory(
                list(self.command),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            self._set_status(message=f"capture failed to start: {exc}")
            raise RuntimeError(f"could not start arecord for {self.device}: {exc}") from exc
        if process.stdout is None:
            process.terminate()
            raise RuntimeError("arecord did not provide a PCM stream")
        self._process = process
        self._set_status(running=True, healthy=True, message="capturing")
        self._thread = threading.Thread(
            target=self._run,
            args=(process, process.stdout),
            name="phreqed-audio",
            daemon=True,
        )
        self._thread.start()

    def _run(self, process: subprocess.Popen[bytes], stream: BinaryIO) -> None:
        chunks = 0
        message = "capture stopped"
        try:
            while not self._stop_event.is_set():
                pcm = stream.read(self.chunk_frames * 2)
                if not pcm:
                    break
                if len(pcm) % 2:
                    pcm = pcm[:-1]
                if pcm:
                    self._latest.update(self.analyzer.process(pcm))
                    chunks += 1
                    self._set_status(
                        running=True,
                        healthy=True,
                        message="capturing",
                        chunks_processed=chunks,
                    )
        except (OSError, ValueError) as exc:
            message = f"capture error: {exc}"
        finally:
            if not self._stop_event.is_set():
                error = b""
                if process.stderr is not None:
                    try:
                        error = process.stderr.read(2_048)
                    except OSError:
                        pass
                detail = error.decode("utf-8", "replace").strip()
                message = detail or message
            self._latest.update(SILENT_AUDIO)
            self._set_status(
                running=False,
                healthy=False,
                message=message,
                chunks_processed=chunks,
            )

    def close(self) -> None:
        process, thread = self._process, self._thread
        if process is None:
            return
        self._stop_event.set()
        if process.poll() is None:
            process.terminate()
        if thread is not None:
            thread.join(timeout=2.0)
        if thread is not None and thread.is_alive() and process.poll() is None:
            process.kill()
            thread.join(timeout=1.0)
        self._latest.update(SILENT_AUDIO)
        self._set_status(running=False, healthy=False, message="stopped")
        self._process = None
        self._thread = None

    def __enter__(self) -> ArecordAudioSource:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
