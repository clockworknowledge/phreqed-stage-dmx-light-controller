"""Transport-independent show-control command interface and state."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import replace
from typing import Protocol

from .effect_api import ParameterValue, PerformanceContext
from .engine import SceneEngine


class ShowCommands(Protocol):
    def select_effect(self, fixture_name: str, effect_id: str) -> None: ...
    def update_parameter(self, fixture_name: str, key: str, value: ParameterValue) -> None: ...
    def activate_preset(self, preset_id: str) -> None: ...
    def trigger_event(self, event: str) -> None: ...
    def blackout(self, enabled: bool = True) -> None: ...
    def tap_tempo(self, timestamp: float | None = None) -> float: ...
    def next_scene(self) -> str: ...
    def previous_scene(self) -> str: ...


class ShowController:
    def __init__(self, engine: SceneEngine) -> None:
        self.engine = engine
        self._context = PerformanceContext()
        self._taps: deque[float] = deque(maxlen=5)
        self._last_tap: float | None = None

    def select_effect(self, fixture_name: str, effect_id: str) -> None:
        self.engine.select_effect(fixture_name, effect_id)

    def update_parameter(
        self, fixture_name: str, key: str, value: ParameterValue
    ) -> None:
        self.engine.update_parameter(fixture_name, key, value)

    def activate_preset(self, preset_id: str) -> None:
        self.engine.activate_preset(preset_id)

    def trigger_event(self, event: str) -> None:
        if not event:
            raise ValueError("event name cannot be empty")
        self._context = replace(self._context, event=event)

    def blackout(self, enabled: bool = True) -> None:
        self.engine.set_blackout(enabled)

    def tap_tempo(self, timestamp: float | None = None) -> float:
        timestamp = time.monotonic() if timestamp is None else timestamp
        if self._taps and timestamp <= self._taps[-1]:
            raise ValueError("tap timestamps must increase")
        self._taps.append(timestamp)
        self._last_tap = timestamp
        if len(self._taps) >= 2:
            intervals = [
                right - left for left, right in zip(self._taps, tuple(self._taps)[1:])
            ]
            average = sum(intervals) / len(intervals)
            bpm = max(20.0, min(300.0, 60.0 / average))
            self._context = replace(self._context, tempo_bpm=bpm)
        return self._context.tempo_bpm

    def next_scene(self) -> str:
        return self._move_scene(1)

    def previous_scene(self) -> str:
        return self._move_scene(-1)

    def context(self, timestamp: float | None = None) -> PerformanceContext:
        timestamp = time.monotonic() if timestamp is None else timestamp
        if self._last_tap is None:
            phase = 0.0
        else:
            seconds_per_beat = 60.0 / self._context.tempo_bpm
            phase = ((timestamp - self._last_tap) / seconds_per_beat) % 1.0
        return replace(self._context, beat_phase=phase)

    def _move_scene(self, direction: int) -> str:
        order = self.engine.preset_order
        if not order:
            raise RuntimeError("no presets are available")
        current = self.engine.active_preset_id
        index = order.index(current) if current in order else 0
        selected = order[(index + direction) % len(order)]
        self.activate_preset(selected)
        return selected
