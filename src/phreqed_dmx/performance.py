"""Transport-independent Manual/Setlist performance-mode coordination."""
from __future__ import annotations

from enum import Enum

from .song_timeline import SongTimelineRunner, TimelineState


class PerformanceMode(str, Enum):
    MANUAL = 'manual'
    SETLIST = 'setlist'


class PerformanceController:
    """Coordinate explicit setlist transport without knowing about HTTP or DMX."""

    def __init__(self, timeline: SongTimelineRunner) -> None:
        self.timeline = timeline
        self.mode = PerformanceMode.MANUAL

    def set_mode(self, mode: PerformanceMode | str) -> None:
        try:
            selected = mode if isinstance(mode, PerformanceMode) else PerformanceMode(mode)
        except (TypeError, ValueError) as exc:
            raise ValueError('performance mode must be manual or setlist') from exc
        if selected is PerformanceMode.MANUAL:
            self.timeline.deactivate()
        elif self.mode is PerformanceMode.MANUAL:
            # Entering Setlist mode only changes control routing. Loading and
            # starting a song remain separate, explicit actions.
            self.timeline.deactivate()
        self.mode = selected

    def load_setlist(self, setlist_id: str) -> None:
        self._require_setlist_mode()
        self.timeline.load(setlist_id)

    def select(self, index: int) -> None:
        self._require_setlist_mode()
        self.timeline.select(index)

    def move(self, direction: int) -> None:
        self._require_setlist_mode()
        self.timeline.move(direction)

    def start(self) -> None:
        self._require_setlist_mode()
        self.timeline.start()

    def stop(self) -> None:
        self.timeline.stop()

    def toggle(self) -> None:
        self._require_setlist_mode()
        if self.timeline.state is TimelineState.RUNNING:
            self.timeline.stop()
        else:
            self.timeline.start()

    def blackout(self) -> None:
        self.timeline.stop()

    def update(self) -> None:
        if self.mode is PerformanceMode.SETLIST:
            self.timeline.update()

    def reconcile_library(self) -> None:
        """Re-arm a loaded setlist after a stopped authoring update."""

        if self.mode is not PerformanceMode.SETLIST:
            return
        setlist_id = self.timeline.setlist_id
        song_index = self.timeline.song_index
        if setlist_id is None:
            return
        setlist = self.timeline.library.setlists.get(setlist_id)
        if setlist is None:
            self.timeline.deactivate()
            return
        self.timeline.load(setlist_id)
        if song_index is not None:
            self.timeline.select(min(song_index, len(setlist.song_ids) - 1))

    def _require_setlist_mode(self) -> None:
        if self.mode is not PerformanceMode.SETLIST:
            raise ValueError('switch to Setlist mode first')
