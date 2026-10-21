"""Bounded audio dynamics for the shared animation clock and visual intensity."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .audio_analysis import AudioAnalysis


@dataclass(frozen=True, slots=True)
class AudioReactiveState:
    animation_time: float
    motion_multiplier: float
    brightness_multiplier: float


class AudioReactiveClock:
    """Integrate tempo and smoothed audio dynamics without changing safety limits."""

    def __init__(
        self,
        *,
        deep_dim_enabled: bool = False,
        quiet_brightness_floor: float = 0.03,
    ) -> None:
        self.animation_time = 0.0
        self.motion_multiplier = 1.0
        self.brightness_multiplier = 1.0
        self._last_elapsed = 0.0
        self.configure_dimming(
            enabled=deep_dim_enabled, quiet_floor=quiet_brightness_floor
        )

    def configure_dimming(self, *, enabled: bool, quiet_floor: float) -> None:
        if not isinstance(enabled, bool):
            raise TypeError("deep dim enabled must be boolean")
        if (
            isinstance(quiet_floor, bool)
            or not isinstance(quiet_floor, (int, float))
            or not math.isfinite(quiet_floor)
            or not 0.0 <= quiet_floor <= 0.25
        ):
            raise ValueError("quiet brightness floor must be between 0.0 and 0.25")
        self.deep_dim_enabled = enabled
        self.quiet_brightness_floor = float(quiet_floor)

    def advance(
        self,
        elapsed: float,
        *,
        tempo_bpm: float,
        speed: float,
        audio: AudioAnalysis | None,
    ) -> AudioReactiveState:
        for name, value in (("elapsed", elapsed), ("tempo_bpm", tempo_bpm), ("speed", speed)):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if elapsed < 0.0:
            raise ValueError("elapsed must be nonnegative")
        if tempo_bpm <= 0.0 or speed <= 0.0:
            raise ValueError("tempo and speed must be positive")

        if elapsed < self._last_elapsed:
            self.animation_time = 0.0
            self.motion_multiplier = 1.0
            self.brightness_multiplier = 1.0
            self._last_elapsed = 0.0
        delta = elapsed - self._last_elapsed
        self._last_elapsed = elapsed

        motion_target, brightness_target = self._targets(audio)
        self.motion_multiplier = self._smooth(
            self.motion_multiplier, motion_target, delta, attack=0.10, release=0.32
        )
        self.brightness_multiplier = self._smooth(
            self.brightness_multiplier, brightness_target, delta, attack=0.07, release=0.28
        )
        self.animation_time += (
            delta * speed * (tempo_bpm / 120.0) * self.motion_multiplier
        )
        return AudioReactiveState(
            self.animation_time,
            self.motion_multiplier,
            self.brightness_multiplier,
        )

    def _targets(self, audio: AudioAnalysis | None) -> tuple[float, float]:
        if audio is None:
            return 1.0, 1.0
        energy = min(
            1.0,
            audio.loudness * 0.50
            + audio.bands.bass * 0.30
            + audio.bands.mid * 0.12
            + audio.bands.treble * 0.08,
        )
        motion = min(2.0, 1.0 + energy * 0.75 + audio.onset * 0.25)
        intensity = min(
            1.0,
            audio.loudness * 0.65
            + audio.bands.bass * 0.15
            + audio.bands.mid * 0.10
            + audio.bands.treble * 0.10
            + audio.onset * 0.20,
        )
        # The operator's master remains the peak. Deep dim is explicit and
        # retains an adjustable near-black floor; the default floor stays 55%.
        floor = self.quiet_brightness_floor if self.deep_dim_enabled else 0.55
        brightness = floor + intensity * (1.0 - floor)
        return motion, brightness

    @staticmethod
    def _smooth(
        current: float,
        target: float,
        delta: float,
        *,
        attack: float,
        release: float,
    ) -> float:
        if delta <= 0.0:
            return current
        time_constant = attack if target > current else release
        amount = 1.0 - math.exp(-delta / time_constant)
        return current + (target - current) * amount
