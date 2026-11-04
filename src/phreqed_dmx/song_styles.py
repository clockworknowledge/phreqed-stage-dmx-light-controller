"""Deterministic, editable baseline cue templates for operator-selected styles."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .songs import MAX_SONG_SECONDS, SongCue, SongStyle


@dataclass(frozen=True, slots=True)
class StyleCue:
    position: float
    preset_id: str
    transition_seconds: float


@dataclass(frozen=True, slots=True)
class StyleTemplate:
    name: str
    description: str
    cues: tuple[StyleCue, ...]


STYLE_TEMPLATES: dict[SongStyle, StyleTemplate] = {
    SongStyle.PUNK: StyleTemplate(
        'Punk', 'Fast cuts, aggressive motion, and short contrasting breaks.',
        (
            StyleCue(0.00, 'blaster-sweep', 0.20),
            StyleCue(0.10, 'crossfire', 0.20),
            StyleCue(0.22, 'neon-blades', 0.15),
            StyleCue(0.34, 'inferno-rise', 0.25),
            StyleCue(0.46, 'inside-out-vu', 0.20),
            StyleCue(0.58, 'flame-thrower', 0.20),
            StyleCue(0.70, 'pacman-chase', 0.15),
            StyleCue(0.82, 'crossfire', 0.15),
            StyleCue(0.92, 'energy-bridge', 0.30),
        ),
    ),
    SongStyle.ROCK: StyleTemplate(
        'Rock', 'Strong section changes with driving motion and a broad finale.',
        (
            StyleCue(0.00, 'psychedelic-bloom', 0.60),
            StyleCue(0.14, 'wave-rider', 0.60),
            StyleCue(0.28, 'crossfire', 0.35),
            StyleCue(0.43, 'inferno-rise', 0.50),
            StyleCue(0.58, 'hypnotic-drive', 0.55),
            StyleCue(0.72, 'neon-blades', 0.40),
            StyleCue(0.86, 'blaster-sweep', 0.30),
            StyleCue(0.94, 'energy-bridge', 0.50),
        ),
    ),
    SongStyle.MELLOW: StyleTemplate(
        'Mellow', 'Long, smooth sections with restrained movement and soft fades.',
        (
            StyleCue(0.00, 'midnight-current', 1.80),
            StyleCue(0.20, 'molten-motion', 1.80),
            StyleCue(0.40, 'wave-rider', 1.50),
            StyleCue(0.60, 'watchful-eyes', 1.80),
            StyleCue(0.78, 'midnight-current', 1.80),
            StyleCue(0.92, 'psychedelic-bloom', 1.20),
        ),
    ),
    SongStyle.FUNK: StyleTemplate(
        'Funk', 'Rhythmic colour changes, VU motion, and playful syncopated looks.',
        (
            StyleCue(0.00, 'inside-out-vu', 0.45),
            StyleCue(0.13, 'hypnotic-drive', 0.40),
            StyleCue(0.26, 'pacman-chase', 0.30),
            StyleCue(0.39, 'acid-mirrors', 0.45),
            StyleCue(0.52, 'wave-rider', 0.40),
            StyleCue(0.65, 'inside-out-vu', 0.30),
            StyleCue(0.78, 'phase-collider', 0.45),
            StyleCue(0.90, 'neon-blades', 0.30),
        ),
    ),
}


def generate_style_cues(
    style: SongStyle | str,
    duration_seconds: float,
    preset_ids: set[str],
) -> tuple[SongCue, ...]:
    """Scale one style template to a song duration without publishing it."""

    try:
        selected = style if isinstance(style, SongStyle) else SongStyle(style)
    except (TypeError, ValueError) as exc:
        raise ValueError('song style is invalid') from exc
    template = STYLE_TEMPLATES.get(selected)
    if template is None:
        raise ValueError('choose punk, rock, mellow, or funk before applying a default')
    if (isinstance(duration_seconds, bool)
            or not isinstance(duration_seconds, (int, float))
            or not math.isfinite(duration_seconds)
            or not 1 <= duration_seconds <= MAX_SONG_SECONDS):
        raise ValueError('song duration is invalid')
    missing = {cue.preset_id for cue in template.cues} - preset_ids
    if missing:
        raise ValueError(f'style template requires missing preset: {sorted(missing)[0]}')
    return tuple(
        SongCue(
            round(float(duration_seconds) * cue.position, 3),
            cue.preset_id,
            cue.transition_seconds,
        )
        for cue in template.cues
    )
