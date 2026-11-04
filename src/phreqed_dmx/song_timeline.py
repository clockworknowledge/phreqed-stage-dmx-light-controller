"""Deterministic setlist playback independent of rendering, transport, and UI."""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import math
import time

from .songs import Setlist, Song, SongCue, SongCueSheet, SongLibrary


class TimelineState(str, Enum):
    INACTIVE = 'inactive'
    ARMED = 'armed'
    RUNNING = 'running'
    STOPPED = 'stopped'
    COMPLETE = 'complete'


class SongTimelineRunner:
    """Run published song cues against an injected monotonic clock."""

    def __init__(
        self,
        library: SongLibrary,
        activate: Callable[[SongCue, float], None],
        *,
        clock: Callable[[], float] = time.monotonic,
        blackout_active: Callable[[], bool] = lambda: False,
    ) -> None:
        self.library = library
        self.activate = activate
        self.clock = clock
        self.blackout_active = blackout_active
        self.setlist_id: str | None = None
        self.song_index: int | None = None
        self.state = TimelineState.INACTIVE
        self.started_at: float | None = None
        self.next_cue_index = 0

    @property
    def setlist(self) -> Setlist | None:
        return None if self.setlist_id is None else self.library.setlists.get(self.setlist_id)

    @property
    def song(self) -> Song | None:
        setlist = self.setlist
        if setlist is None or self.song_index is None:
            return None
        return self.library.songs[setlist.song_ids[self.song_index]]

    @property
    def cue_sheet(self) -> SongCueSheet | None:
        song = self.song
        if song is None or song.active_cue_sheet_id is None:
            return None
        return self.library.cue_sheets.get(song.active_cue_sheet_id)

    @property
    def position_seconds(self) -> float:
        """Current deterministic position; stopped and armed songs are at zero."""

        song = self.song
        if song is None:
            return 0.0
        if self.state is TimelineState.COMPLETE:
            return song.duration_seconds
        if self.state is not TimelineState.RUNNING or self.started_at is None:
            return 0.0
        return min(song.duration_seconds, max(0.0, self._time() - self.started_at))

    def _time(self) -> float:
        now = self.clock()
        if (isinstance(now, bool) or not isinstance(now, (int, float))
                or not math.isfinite(now) or now < 0):
            raise ValueError('timeline clock must return a finite nonnegative number')
        return float(now)

    def load(self, setlist_id: str) -> None:
        if not isinstance(setlist_id, str) or setlist_id not in self.library.setlists:
            raise ValueError('unknown setlist')
        self.setlist_id = setlist_id
        self.song_index = 0
        self.state = TimelineState.ARMED
        self.started_at = None
        self.next_cue_index = 0

    def deactivate(self) -> None:
        self.setlist_id = None
        self.song_index = None
        self.state = TimelineState.INACTIVE
        self.started_at = None
        self.next_cue_index = 0

    def select(self, index: int) -> None:
        setlist = self.setlist
        if setlist is None:
            raise ValueError('load a setlist first')
        if (isinstance(index, bool) or not isinstance(index, int)
                or not 0 <= index < len(setlist.song_ids)):
            raise ValueError('song index is out of range')
        self.song_index = index
        self.state = TimelineState.ARMED
        self.started_at = None
        self.next_cue_index = 0

    def move(self, direction: int) -> None:
        setlist = self.setlist
        if setlist is None or self.song_index is None:
            raise ValueError('load a setlist first')
        if (isinstance(direction, bool) or not isinstance(direction, int)
                or direction not in (-1, 1)):
            raise ValueError('song direction must be -1 or 1')
        self.select((self.song_index + direction) % len(setlist.song_ids))

    def _published_sheet(self) -> SongCueSheet:
        sheet = self.cue_sheet
        if sheet is None:
            raise ValueError('selected song has no active cue sheet')
        if not sheet.published:
            raise ValueError('selected song cue sheet is not published')
        return sheet

    def start(self) -> None:
        if self.song is None:
            raise ValueError('load a setlist first')
        if self.blackout_active():
            raise ValueError('cannot start a song while blackout is active')
        self._published_sheet()
        self.started_at = self._time()
        self.next_cue_index = 0
        self.state = TimelineState.RUNNING
        self.update()

    def stop(self) -> None:
        if self.song is None:
            return
        self.state = TimelineState.STOPPED
        self.started_at = None
        self.next_cue_index = 0

    def restart(self) -> None:
        self.start()

    def update(self) -> None:
        if self.state is not TimelineState.RUNNING:
            return
        if self.blackout_active():
            self.stop()
            return
        now = self._time()
        if self.started_at is None or now < self.started_at:
            self.stop()
            raise ValueError('timeline clock moved backwards')
        song = self.song
        sheet = self._published_sheet()
        if song is None:
            self.stop()
            raise ValueError('selected song is unavailable')
        elapsed = now - self.started_at
        try:
            while (self.next_cue_index < len(sheet.cues)
                   and sheet.cues[self.next_cue_index].at_seconds <= elapsed):
                cue = sheet.cues[self.next_cue_index]
                self.activate(cue, self.started_at + cue.at_seconds)
                self.next_cue_index += 1
        except Exception:
            self.stop()
            raise
        if elapsed >= song.duration_seconds:
            setlist = self.setlist
            has_next = (setlist is not None and self.song_index is not None
                        and self.song_index + 1 < len(setlist.song_ids))
            if has_next:
                self.song_index += 1
                self.state = TimelineState.ARMED
            else:
                self.state = TimelineState.COMPLETE
            self.started_at = None
            self.next_cue_index = 0
