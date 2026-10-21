"""Ordered, elapsed-time driven cues. No transport, files, or GUI imports."""
from __future__ import annotations

from collections.abc import Callable
import math

from .engine import SceneEngine
from .library import Cue


class SceneSequencer:
    """Hold time includes the entry fade; timed playback stops at the final cue."""
    def __init__(self, engine: SceneEngine, transition: Callable[..., None]) -> None:
        self.engine = engine
        self.transition = transition
        self.cues: tuple[Cue, ...] = ()
        self.index: int | None = None
        self.started = 0.0
        self.playing = False

    def replace(self, cues: tuple[Cue, ...]) -> None:
        if any(cue.preset_id not in self.engine.presets for cue in cues):
            raise ValueError('scene references an unknown preset')
        self.cues = cues
        self.index = None
        self.playing = False

    def select(self, index: int, elapsed: float) -> None:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self.cues):
            raise ValueError('scene index is out of range')
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('scene time must be finite and nonnegative')
        cue = self.cues[index]
        if cue.preset_id not in self.engine.presets:
            raise ValueError('scene references an unknown preset')
        self.transition(elapsed, duration=cue.fade_seconds)
        self.engine.activate_preset(cue.preset_id)
        self.index = index
        self.started = elapsed

    def move(self, direction: int, elapsed: float) -> None:
        if not self.cues:
            raise ValueError('add a scene first')
        index = 0 if self.index is None else (self.index + direction) % len(self.cues)
        self.select(index, elapsed)

    def play(self, elapsed: float) -> None:
        if not self.cues:
            raise ValueError('add a scene first')
        self.select(0 if self.index is None else self.index, elapsed)
        self.playing = True

    def update(self, elapsed: float) -> None:
        if self.engine.blackout_enabled:
            self.playing = False
        while self.playing and self.index is not None:
            deadline = self.started + self.cues[self.index].hold_seconds
            if elapsed < deadline:
                break
            if self.index == len(self.cues) - 1:
                self.playing = False
                break
            self.select(self.index + 1, deadline)
