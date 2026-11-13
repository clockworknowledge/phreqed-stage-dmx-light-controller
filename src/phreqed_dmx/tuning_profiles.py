"""Persistent, bounded operator tuning profiles with immutable safe defaults."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import tempfile


MAX_SAVED_MASTER = 0.65
MAX_SAVED_WHITE = 0.10


def _number(value: object, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be numeric')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be between {low} and {high}')
    return float(value)


def _text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{label} must contain 1–{maximum} characters')
    return value.strip()


def _fields(value: object, required: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f'expected fields: {", ".join(sorted(required))}')
    return value


@dataclass(frozen=True, slots=True)
class TuningProfile:
    profile_id: str
    name: str
    description: str
    master_level: float
    contrast: float
    audio_auto_level: bool
    deep_dim_enabled: bool
    quiet_floor: float
    white_preview_enabled: bool
    white_threshold: float
    white_preview_level: float
    white_output_level: float

    def as_dict(self) -> dict:
        return dict(
            profile_id=self.profile_id,
            name=self.name,
            description=self.description,
            master_level=self.master_level,
            contrast=self.contrast,
            audio_auto_level=self.audio_auto_level,
            deep_dim_enabled=self.deep_dim_enabled,
            quiet_floor=self.quiet_floor,
            white_preview_enabled=self.white_preview_enabled,
            white_threshold=self.white_threshold,
            white_preview_level=self.white_preview_level,
            white_output_level=self.white_output_level,
        )


PROFILE_FIELDS = {
    'profile_id', 'name', 'description', 'master_level', 'contrast',
    'audio_auto_level', 'deep_dim_enabled', 'quiet_floor',
    'white_preview_enabled', 'white_threshold', 'white_preview_level',
    'white_output_level',
}
LEGACY_PROFILE_FIELDS = PROFILE_FIELDS - {'white_preview_enabled'}


def _parse_profile(value: object, *, builtin: bool) -> TuningProfile:
    if isinstance(value, dict) and set(value) == LEGACY_PROFILE_FIELDS:
        data = dict(value)
        data['white_preview_enabled'] = False
    else:
        data = _fields(value, PROFILE_FIELDS)
    profile_id = data['profile_id']
    pattern = r'[a-z][a-z0-9-]{0,63}' if builtin else r'user-tune-[a-z0-9-]{1,64}'
    if not isinstance(profile_id, str) or not re.fullmatch(pattern, profile_id):
        if builtin:
            raise ValueError(
                'built-in tuning profile ID must use lowercase letters, '
                'digits, or hyphens'
            )
        raise ValueError(
            'user tuning profile ID must start with user-tune- and use '
            'lowercase letters, digits, or hyphens'
        )
    description = data['description']
    if not isinstance(description, str) or len(description) > 500:
        raise ValueError('description must be text of at most 500 characters')
    for key in (
        'audio_auto_level', 'deep_dim_enabled', 'white_preview_enabled'
    ):
        if not isinstance(data[key], bool):
            raise ValueError(f'{key.replace("_", " ")} must be boolean')
    return TuningProfile(
        profile_id=profile_id,
        name=_text(data['name'], 'name', 100),
        description=description.strip(),
        master_level=_number(
            data['master_level'], 'master level', 0.0, MAX_SAVED_MASTER
        ),
        contrast=_number(data['contrast'], 'contrast', 1.0, 3.0),
        audio_auto_level=data['audio_auto_level'],
        deep_dim_enabled=data['deep_dim_enabled'],
        quiet_floor=_number(data['quiet_floor'], 'quiet floor', 0.0, 0.25),
        white_preview_enabled=data['white_preview_enabled'],
        white_threshold=_number(
            data['white_threshold'], 'white threshold', 0.1, 1.0
        ),
        white_preview_level=_number(
            data['white_preview_level'], 'white preview level', 0.05, 1.0
        ),
        white_output_level=_number(
            data['white_output_level'], 'white output level',
            0.01, MAX_SAVED_WHITE,
        ),
    )


def parse_tuning_profile(value: object) -> TuningProfile:
    return _parse_profile(value, builtin=False)


def _load_builtin_profiles(path: Path) -> dict[str, TuningProfile]:
    try:
        data = _fields(json.loads(path.read_text(encoding='utf-8')), {'version', 'profiles'})
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'cannot load built-in tuning profiles {path}: {exc}') from exc
    if type(data['version']) is not int or data['version'] != 1:
        raise RuntimeError('unsupported built-in tuning profile version; expected 1')
    if not isinstance(data['profiles'], list):
        raise RuntimeError('built-in tuning profiles must be a list')
    profiles = [_parse_profile(item, builtin=True) for item in data['profiles']]
    result = {profile.profile_id: profile for profile in profiles}
    if len(result) != len(profiles):
        raise RuntimeError('duplicate built-in tuning profile IDs')
    if tuple(result) != ('rehearsal', 'small-stage', 'large-stage'):
        raise RuntimeError(
            'built-in tuning profiles must be rehearsal, small-stage, and large-stage'
        )
    return result


BUILTIN_TUNING_PROFILES = _load_builtin_profiles(
    Path(__file__).with_name('tuning_profiles.defaults.json')
)


class TuningProfileLibrary:
    """Validate all profiles before atomically replacing persistent state."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.profiles: dict[str, TuningProfile] = {}
        if path.exists():
            try:
                if path.stat().st_size > 100_000:
                    raise ValueError('tuning profile library exceeds 100 KB')
                self.profiles = self.validate(
                    json.loads(path.read_text(encoding='utf-8'))
                )
            except (OSError, ValueError) as exc:
                raise ValueError(
                    f'cannot load tuning profile library {path}: {exc}'
                ) from exc

    @property
    def all_profiles(self) -> dict[str, TuningProfile]:
        return {**BUILTIN_TUNING_PROFILES, **self.profiles}

    def document(self) -> dict:
        return dict(
            version=1,
            profiles=[profile.as_dict() for profile in self.profiles.values()],
        )

    def validate(self, value: object) -> dict[str, TuningProfile]:
        data = _fields(value, {'version', 'profiles'})
        if type(data['version']) is not int or data['version'] != 1:
            raise ValueError('unsupported tuning profile version; expected 1')
        if not isinstance(data['profiles'], list) or len(data['profiles']) > 20:
            raise ValueError('tuning library must contain at most 20 profiles')
        parsed = [parse_tuning_profile(item) for item in data['profiles']]
        profiles = {profile.profile_id: profile for profile in parsed}
        if len(profiles) != len(parsed):
            raise ValueError('duplicate user tuning profile IDs')
        return profiles

    def save(self, value: object) -> None:
        profiles = self.validate(value)
        canonical = dict(
            version=1,
            profiles=[profile.as_dict() for profile in profiles.values()],
        )
        encoded = json.dumps(canonical, indent=2, allow_nan=False) + '\n'
        if len(encoded.encode('utf-8')) > 100_000:
            raise ValueError('tuning profile library exceeds 100 KB')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=self.path.parent,
                prefix='.tuning-', delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.profiles = profiles
