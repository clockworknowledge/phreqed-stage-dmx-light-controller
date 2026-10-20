"""Versioned user looks and cues, independent of rendering and transport."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import tempfile

from .compositor import BlendMode
from .effect_library import EFFECT_REGISTRY
from .presets import PRESETS, EffectLayerSpec, VisualPreset


def number(value: object, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be numeric')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be between {low} and {high}')
    return float(value)


def title(value: object, label: str = 'name') -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        raise ValueError(f'{label} must contain 1–100 characters')
    return value.strip()


def object_fields(value: object, required: set[str], optional: set[str] | None = None) -> dict:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ValueError(f'expected fields: {", ".join(sorted(required))}')
    return value


def preset_data(preset: VisualPreset) -> dict:
    return {
        'preset_id': preset.preset_id, 'name': preset.name,
        'description': preset.description, 'global_brightness': preset.global_brightness,
        'layers': [dict(effect_id=layer.effect_id,
                        fixtures=None if layer.fixtures is None else list(layer.fixtures),
                        opacity=layer.opacity, blend_mode=layer.blend_mode.value,
                        parameters=dict(layer.parameters)) for layer in preset.layers],
    }


def parse_preset(data: object, fixture_names: tuple[str, ...]) -> VisualPreset:
    data = object_fields(data, {'preset_id', 'name', 'description', 'global_brightness', 'layers'})
    preset_id = data['preset_id']
    if not isinstance(preset_id, str) or not re.fullmatch(r'user-[a-z0-9-]{1,64}', preset_id):
        raise ValueError('user preset ID must start with user- and use lowercase letters, digits or hyphens')
    if not isinstance(data['description'], str) or len(data['description']) > 500:
        raise ValueError('description must be text of at most 500 characters')
    if not isinstance(data['layers'], list) or not 1 <= len(data['layers']) <= 8:
        raise ValueError('a preset requires 1–8 layers')
    layers = []
    for raw in data['layers']:
        raw = object_fields(raw, {'effect_id', 'fixtures', 'opacity', 'blend_mode', 'parameters'})
        if not isinstance(raw['effect_id'], str):
            raise ValueError('effect ID must be text')
        targets = raw['fixtures']
        if targets is not None:
            if (not isinstance(targets, list) or not targets
                    or any(not isinstance(x, str) or x not in fixture_names for x in targets)
                    or len(set(targets)) != len(targets)):
                raise ValueError('layer targets must be unique known fixture names')
            targets = tuple(targets)
        params = raw['parameters']
        if not isinstance(params, dict):
            raise ValueError('parameters must be an object')
        try:
            EFFECT_REGISTRY.parameters(raw['effect_id'], params)
            blend = BlendMode(raw['blend_mode'])
        except (TypeError, KeyError, ValueError) as exc:
            raise ValueError(f'invalid layer: {exc}') from exc
        layers.append(EffectLayerSpec(raw['effect_id'], targets,
                                     number(raw['opacity'], 'opacity', 0, 1), blend, dict(params)))
    return VisualPreset(preset_id, title(data['name']), data['description'], tuple(layers),
                        number(data['global_brightness'], 'brightness', 0, 0.65))


@dataclass(frozen=True, slots=True)
class Cue:
    name: str
    preset_id: str
    hold_seconds: float = 15.0
    fade_seconds: float = 1.0

    def __post_init__(self) -> None:
        title(self.name, 'scene name')
        title(self.preset_id, 'preset ID')
        number(self.hold_seconds, 'hold seconds', 1, 3600)
        number(self.fade_seconds, 'fade seconds', 0, min(60, self.hold_seconds))

    def as_dict(self) -> dict:
        return dict(name=self.name, preset_id=self.preset_id,
                    hold_seconds=self.hold_seconds, fade_seconds=self.fade_seconds)


def parse_cues(data: object, preset_ids: set[str]) -> tuple[Cue, ...]:
    if not isinstance(data, list) or len(data) > 200:
        raise ValueError('scene list must contain at most 200 scenes')
    cues = []
    for raw in data:
        raw = object_fields(raw, {'name', 'preset_id', 'hold_seconds', 'fade_seconds'})
        if not isinstance(raw['preset_id'], str) or raw['preset_id'] not in preset_ids:
            raise ValueError('scene references an unknown preset')
        hold = number(raw['hold_seconds'], 'hold seconds', 1, 3600)
        fade = number(raw['fade_seconds'], 'fade seconds', 0, min(60, hold))
        cues.append(Cue(title(raw['name'], 'scene name'), raw['preset_id'], hold, fade))
    return tuple(cues)


class UserLibrary:
    """Validate the whole document before an atomic replacement or state change."""
    def __init__(self, path: Path, fixture_names: tuple[str, ...]) -> None:
        self.path = path
        self.fixture_names = fixture_names
        self.presets: dict[str, VisualPreset] = {}
        self.cues: tuple[Cue, ...] = tuple(Cue(p.name, p.preset_id) for p in PRESETS.values())
        if path.exists():
            try:
                if path.stat().st_size > 1_000_000:
                    raise ValueError('library exceeds 1 MB')
                self.presets, self.cues = self.validate(json.loads(path.read_text(encoding='utf-8')))
            except (OSError, ValueError) as exc:
                raise ValueError(f'cannot load user library {path}: {exc}') from exc

    @property
    def all_presets(self) -> dict[str, VisualPreset]:
        return {**PRESETS, **self.presets}

    def document(self) -> dict:
        return dict(version=1, presets=[preset_data(p) for p in self.presets.values()],
                    scenes=[cue.as_dict() for cue in self.cues])

    def validate(self, data: object) -> tuple[dict[str, VisualPreset], tuple[Cue, ...]]:
        data = object_fields(data, {'version', 'presets', 'scenes'})
        if type(data['version']) is not int or data['version'] != 1:
            raise ValueError('unsupported library version; expected 1')
        if not isinstance(data['presets'], list) or len(data['presets']) > 100:
            raise ValueError('library must contain at most 100 user presets')
        parsed = [parse_preset(p, self.fixture_names) for p in data['presets']]
        presets = {p.preset_id: p for p in parsed}
        if len(presets) != len(parsed):
            raise ValueError('duplicate user preset IDs')
        return presets, parse_cues(data['scenes'], set(PRESETS) | set(presets))

    def save(self, data: object) -> None:
        presets, cues = self.validate(data)
        encoded = json.dumps(data, indent=2, allow_nan=False) + '\n'
        if len(encoded.encode('utf-8')) > 1_000_000:
            raise ValueError('library exceeds 1 MB')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.library-', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.presets, self.cues = presets, cues
