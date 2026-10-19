"""Example multi-layer visual presets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .compositor import BlendMode
from .effect_api import ParameterValue


@dataclass(frozen=True, slots=True)
class EffectLayerSpec:
    effect_id: str
    fixtures: tuple[str, ...] | None = None
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.ALPHA
    parameters: Mapping[str, ParameterValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("preset layer opacity must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class VisualPreset:
    preset_id: str
    name: str
    description: str
    layers: tuple[EffectLayerSpec, ...]
    global_brightness: float = 0.5

    def __post_init__(self) -> None:
        if not self.layers:
            raise ValueError("a preset requires at least one layer")
        if not 0.0 <= self.global_brightness <= 0.65:
            raise ValueError("preset brightness must be between 0.0 and 0.65")


EXAMPLE_PRESETS = (
    VisualPreset(
        "psychedelic-bloom",
        "Psychedelic Bloom",
        "Advanced plasma with expanding additive rings.",
        (
            EffectLayerSpec("plasma", parameters={"brightness": 0.72, "palette": "neon"}),
            EffectLayerSpec(
                "rings",
                opacity=0.45,
                blend_mode=BlendMode.ADDITIVE,
                parameters={"brightness": 0.55, "palette": "spectrum", "spacing": 2.1},
            ),
        ),
        global_brightness=0.48,
    ),
    VisualPreset(
        "molten-motion",
        "Molten Motion",
        "Slow lava forms with a restrained spark overlay.",
        (
            EffectLayerSpec(
                "lava-lamp", parameters={"brightness": 0.78, "palette": "magma"}
            ),
            EffectLayerSpec(
                "sparks",
                opacity=0.5,
                blend_mode=BlendMode.LIGHTEN,
                parameters={"brightness": 0.48, "palette": "ember", "count": 9},
            ),
        ),
        global_brightness=0.44,
    ),
    VisualPreset(
        "digital-storm",
        "Digital Storm",
        "Digital rain punctuated by low-level glitch blocks.",
        (
            EffectLayerSpec(
                "digital-rain", parameters={"brightness": 0.72, "palette": "ocean"}
            ),
            EffectLayerSpec(
                "glitch",
                opacity=0.32,
                blend_mode=BlendMode.ADDITIVE,
                parameters={"brightness": 0.35, "palette": "neon", "jitter": 3.0},
            ),
        ),
        global_brightness=0.42,
    ),
    VisualPreset(
        "energy-bridge",
        "Energy Bridge",
        "A continuous energy packet travels between both cubes.",
        (
            EffectLayerSpec(
                "energy-transfer",
                parameters={"brightness": 0.8, "palette": "spectrum", "trail": 3.5},
            ),
            EffectLayerSpec(
                "radial-pulse",
                opacity=0.28,
                blend_mode=BlendMode.LIGHTEN,
                parameters={"brightness": 0.4, "palette": "ocean"},
            ),
        ),
        global_brightness=0.5,
    ),
)

PRESETS = {preset.preset_id: preset for preset in EXAMPLE_PRESETS}
