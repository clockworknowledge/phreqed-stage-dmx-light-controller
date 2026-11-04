"""Validated song, cue-sheet, and setlist storage with no media or transport I/O."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
import os
from pathlib import Path
import re
import tempfile


MAX_DOCUMENT_BYTES = 2_000_000
MAX_SONG_SECONDS = 4 * 60 * 60
_ID_PATTERN = re.compile(r'[a-z0-9][a-z0-9-]{0,63}')


class SongSource(str, Enum):
    """Authoring input used to create a song analysis."""

    MANUAL = 'manual'
    MP3_UPLOAD = 'mp3_upload'
    REHEARSAL_CAPTURE = 'rehearsal_capture'


class SongStyle(str, Enum):
    """Operator-selected starting point for a baseline cue sheet."""

    UNSPECIFIED = 'unspecified'
    PUNK = 'punk'
    ROCK = 'rock'
    MELLOW = 'mellow'
    FUNK = 'funk'


def _object_fields(value: object, required: set[str]) -> dict:
    if not isinstance(value, dict) or value.keys() != required:
        raise ValueError(f'expected fields: {", ".join(sorted(required))}')
    return value


def _identifier(value: object, prefix: str, label: str) -> str:
    if (not isinstance(value, str) or not _ID_PATTERN.fullmatch(value)
            or not value.startswith(f'{prefix}-')):
        raise ValueError(
            f'{label} must start with {prefix}- and use lowercase letters, digits or hyphens'
        )
    return value


def _text(value: object, label: str, maximum: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f'{label} must be text')
    cleaned = value.strip()
    if (not allow_empty and not cleaned) or len(cleaned) > maximum:
        minimum = 0 if allow_empty else 1
        raise ValueError(f'{label} must contain {minimum}-{maximum} characters')
    return cleaned


def _number(value: object, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be numeric')
    parsed = float(value)
    if not math.isfinite(parsed) or not low <= parsed <= high:
        raise ValueError(f'{label} must be between {low} and {high}')
    return parsed


@dataclass(frozen=True, slots=True)
class Song:
    song_id: str
    title: str
    artist: str
    duration_seconds: float
    notes: str = ''
    source: SongSource = SongSource.MANUAL
    active_cue_sheet_id: str | None = None
    style: SongStyle = SongStyle.UNSPECIFIED

    def __post_init__(self) -> None:
        _identifier(self.song_id, 'song', 'song ID')
        _text(self.title, 'song title', 200)
        _text(self.artist, 'artist', 200)
        _number(self.duration_seconds, 'song duration', 1, MAX_SONG_SECONDS)
        _text(self.notes, 'song notes', 4000, allow_empty=True)
        if not isinstance(self.source, SongSource):
            raise ValueError('song source is invalid')
        if not isinstance(self.style, SongStyle):
            raise ValueError('song style is invalid')
        if self.active_cue_sheet_id is not None:
            _identifier(self.active_cue_sheet_id, 'cue', 'active cue-sheet ID')

    def as_dict(self) -> dict:
        data = {
            'song_id': self.song_id,
            'title': self.title,
            'artist': self.artist,
            'duration_seconds': self.duration_seconds,
            'notes': self.notes,
            'source': self.source.value,
            'active_cue_sheet_id': self.active_cue_sheet_id,
        }
        # Omit the default so existing version-1 song documents round-trip
        # unchanged while styled songs persist the new optional metadata.
        if self.style is not SongStyle.UNSPECIFIED:
            data['style'] = self.style.value
        return data


@dataclass(frozen=True, slots=True)
class SongCue:
    at_seconds: float
    preset_id: str
    transition_seconds: float = 0.5

    def __post_init__(self) -> None:
        _number(self.at_seconds, 'cue time', 0, MAX_SONG_SECONDS)
        _text(self.preset_id, 'preset ID', 100)
        _number(self.transition_seconds, 'transition duration', 0, 60)

    def as_dict(self) -> dict:
        return {
            'at_seconds': self.at_seconds,
            'preset_id': self.preset_id,
            'transition_seconds': self.transition_seconds,
        }


@dataclass(frozen=True, slots=True)
class SongCueSheet:
    cue_sheet_id: str
    song_id: str
    revision: int
    cues: tuple[SongCue, ...]
    published: bool = False

    def __post_init__(self) -> None:
        _identifier(self.cue_sheet_id, 'cue', 'cue-sheet ID')
        _identifier(self.song_id, 'song', 'song ID')
        if (isinstance(self.revision, bool) or not isinstance(self.revision, int)
                or self.revision < 1):
            raise ValueError('cue-sheet revision must be a positive integer')
        if not isinstance(self.published, bool):
            raise ValueError('cue-sheet published flag must be boolean')
        if not isinstance(self.cues, tuple) or not 1 <= len(self.cues) <= 1000:
            raise ValueError('cue sheet must contain 1-1000 cues')
        if any(not isinstance(cue, SongCue) for cue in self.cues):
            raise ValueError('cue sheet contains an invalid cue')
        times = [cue.at_seconds for cue in self.cues]
        if times[0] != 0:
            raise ValueError('the first song cue must start at 0 seconds')
        if any(right <= left for left, right in zip(times, times[1:])):
            raise ValueError('song cue times must be strictly increasing')

    def as_dict(self) -> dict:
        return {
            'cue_sheet_id': self.cue_sheet_id,
            'song_id': self.song_id,
            'revision': self.revision,
            'published': self.published,
            'cues': [cue.as_dict() for cue in self.cues],
        }


@dataclass(frozen=True, slots=True)
class Setlist:
    setlist_id: str
    name: str
    song_ids: tuple[str, ...]
    notes: str = ''

    def __post_init__(self) -> None:
        _identifier(self.setlist_id, 'setlist', 'setlist ID')
        _text(self.name, 'setlist name', 200)
        _text(self.notes, 'setlist notes', 4000, allow_empty=True)
        if not isinstance(self.song_ids, tuple) or not 1 <= len(self.song_ids) <= 200:
            raise ValueError('setlist must contain 1-200 songs')
        for song_id in self.song_ids:
            _identifier(song_id, 'song', 'setlist song ID')

    def as_dict(self) -> dict:
        return {
            'setlist_id': self.setlist_id,
            'name': self.name,
            'song_ids': list(self.song_ids),
            'notes': self.notes,
        }


def _parse_song(value: object) -> Song:
    required = {
        'song_id', 'title', 'artist', 'duration_seconds', 'notes', 'source',
        'active_cue_sheet_id',
    }
    if (not isinstance(value, dict)
            or not required <= value.keys()
            or not value.keys() <= required | {'style'}):
        raise ValueError(f'expected fields: {", ".join(sorted(required))}; optional: style')
    data = value
    try:
        source = SongSource(data['source'])
    except (TypeError, ValueError) as exc:
        raise ValueError('song source is invalid') from exc
    try:
        style = SongStyle(data.get('style', SongStyle.UNSPECIFIED.value))
    except (TypeError, ValueError) as exc:
        raise ValueError('song style is invalid') from exc
    return Song(
        data['song_id'], data['title'], data['artist'],
        _number(data['duration_seconds'], 'song duration', 1, MAX_SONG_SECONDS),
        data['notes'], source, data['active_cue_sheet_id'], style,
    )


def _parse_cue(value: object) -> SongCue:
    data = _object_fields(value, {'at_seconds', 'preset_id', 'transition_seconds'})
    return SongCue(
        _number(data['at_seconds'], 'cue time', 0, MAX_SONG_SECONDS),
        data['preset_id'],
        _number(data['transition_seconds'], 'transition duration', 0, 60),
    )


def _parse_cue_sheet(value: object) -> SongCueSheet:
    data = _object_fields(value, {'cue_sheet_id', 'song_id', 'revision', 'published', 'cues'})
    if not isinstance(data['cues'], list):
        raise ValueError('cue-sheet cues must be a list')
    return SongCueSheet(
        data['cue_sheet_id'], data['song_id'], data['revision'],
        tuple(_parse_cue(cue) for cue in data['cues']), data['published'],
    )


def _parse_setlist(value: object) -> Setlist:
    data = _object_fields(value, {'setlist_id', 'name', 'song_ids', 'notes'})
    if not isinstance(data['song_ids'], list):
        raise ValueError('setlist song IDs must be a list')
    return Setlist(data['setlist_id'], data['name'], tuple(data['song_ids']), data['notes'])


class SongLibrary:
    """Atomically persist validated metadata; MP3 and captured audio never enter this file."""

    def __init__(self, path: Path, preset_ids: set[str]) -> None:
        self.path = path
        self.preset_ids = set(preset_ids)
        if (not self.preset_ids
                or any(not isinstance(item, str) or not item for item in self.preset_ids)):
            raise ValueError('known preset IDs must be nonempty text')
        self.songs: dict[str, Song] = {}
        self.cue_sheets: dict[str, SongCueSheet] = {}
        self.setlists: dict[str, Setlist] = {}
        if path.exists():
            try:
                if path.stat().st_size > MAX_DOCUMENT_BYTES:
                    raise ValueError('song library exceeds 2 MB')
                parsed = json.loads(path.read_text(encoding='utf-8'))
                self.songs, self.cue_sheets, self.setlists = self.validate(parsed)
            except (OSError, ValueError) as exc:
                raise ValueError(f'cannot load song library {path}: {exc}') from exc

    def document(self) -> dict:
        return {
            'version': 1,
            'songs': [song.as_dict() for song in self.songs.values()],
            'cue_sheets': [cue_sheet.as_dict() for cue_sheet in self.cue_sheets.values()],
            'setlists': [setlist.as_dict() for setlist in self.setlists.values()],
        }

    def validate(
        self, data: object,
    ) -> tuple[dict[str, Song], dict[str, SongCueSheet], dict[str, Setlist]]:
        document = _object_fields(data, {'version', 'songs', 'cue_sheets', 'setlists'})
        if type(document['version']) is not int or document['version'] != 1:
            raise ValueError('unsupported song-library version; expected 1')
        limits = (('songs', 1000), ('cue_sheets', 5000), ('setlists', 200))
        for field, maximum in limits:
            if not isinstance(document[field], list) or len(document[field]) > maximum:
                label = field.replace('_', ' ')
                raise ValueError(f'song library must contain at most {maximum} {label}')

        parsed_songs = [_parse_song(value) for value in document['songs']]
        parsed_sheets = [_parse_cue_sheet(value) for value in document['cue_sheets']]
        parsed_setlists = [_parse_setlist(value) for value in document['setlists']]
        songs = {song.song_id: song for song in parsed_songs}
        cue_sheets = {sheet.cue_sheet_id: sheet for sheet in parsed_sheets}
        setlists = {setlist.setlist_id: setlist for setlist in parsed_setlists}
        if len(songs) != len(parsed_songs):
            raise ValueError('duplicate song IDs')
        if len(cue_sheets) != len(parsed_sheets):
            raise ValueError('duplicate cue-sheet IDs')
        if len(setlists) != len(parsed_setlists):
            raise ValueError('duplicate setlist IDs')

        for sheet in cue_sheets.values():
            song = songs.get(sheet.song_id)
            if song is None:
                raise ValueError('cue sheet references an unknown song')
            if sheet.cues[-1].at_seconds >= song.duration_seconds:
                raise ValueError('song cue must occur before the song duration')
            if any(cue.preset_id not in self.preset_ids for cue in sheet.cues):
                raise ValueError('song cue references an unknown preset')

        for song in songs.values():
            if song.active_cue_sheet_id is None:
                continue
            sheet = cue_sheets.get(song.active_cue_sheet_id)
            if sheet is None or sheet.song_id != song.song_id:
                raise ValueError('song references an invalid active cue sheet')
            if not sheet.published:
                raise ValueError('active cue sheet must be published')

        for setlist in setlists.values():
            if any(song_id not in songs for song_id in setlist.song_ids):
                raise ValueError('setlist references an unknown song')
        return songs, cue_sheets, setlists

    def save(self, data: object) -> None:
        songs, cue_sheets, setlists = self.validate(data)
        for cue_sheet_id, existing in self.cue_sheets.items():
            if existing.published:
                replacement = cue_sheets.get(cue_sheet_id)
                if replacement is None or replacement.as_dict() != existing.as_dict():
                    raise ValueError('published cue sheets are immutable')
        encoded = json.dumps(data, indent=2, allow_nan=False) + '\n'
        if len(encoded.encode('utf-8')) > MAX_DOCUMENT_BYTES:
            raise ValueError('song library exceeds 2 MB')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=self.path.parent,
                prefix='.songs-', delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.songs, self.cue_sheets, self.setlists = songs, cue_sheets, setlists
