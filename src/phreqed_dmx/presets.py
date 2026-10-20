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
    VisualPreset(
        "midnight-current",
        "Midnight Current",
        "A slow ocean current crossed by faint neon shafts for intros and quiet sections.",
        (
            EffectLayerSpec(
                "flow-noise",
                parameters={
                    "speed": 0.35,
                    "brightness": 0.68,
                    "palette": "ocean",
                    "scale": 4.8,
                    "drift": 0.15,
                },
            ),
            EffectLayerSpec(
                "bars",
                opacity=0.18,
                blend_mode=BlendMode.LIGHTEN,
                parameters={
                    "speed": 0.25,
                    "brightness": 0.35,
                    "palette": "neon",
                    "bar_width": 0.14,
                    "angle": -18.0,
                },
            ),
        ),
        global_brightness=0.34,
    ),
    VisualPreset(
        "acid-mirrors",
        "Acid Mirrors",
        "Contrasting vortex and kaleidoscope motion across the two fixtures.",
        (
            EffectLayerSpec(
                "vortex",
                fixtures=("Cube A",),
                parameters={
                    "speed": 0.85,
                    "brightness": 0.82,
                    "palette": "neon",
                    "arms": 4.0,
                    "twist": 3.4,
                },
            ),
            EffectLayerSpec(
                "kaleidoscope",
                fixtures=("Cube B",),
                parameters={
                    "speed": 0.7,
                    "brightness": 0.82,
                    "palette": "spectrum",
                    "segments": 8.0,
                    "zoom": 2.1,
                },
            ),
            EffectLayerSpec(
                "radial-pulse",
                opacity=0.2,
                blend_mode=BlendMode.ADDITIVE,
                parameters={
                    "speed": 0.5,
                    "brightness": 0.32,
                    "palette": "ocean",
                    "frequency": 1.5,
                    "sharpness": 1.6,
                },
            ),
        ),
        global_brightness=0.44,
    ),
    VisualPreset(
        "phase-collider",
        "Phase Collider",
        "Wave interference and tempo-aware rings collide without hard flashes.",
        (
            EffectLayerSpec(
                "interference",
                parameters={
                    "speed": 0.9,
                    "brightness": 0.76,
                    "palette": "spectrum",
                    "frequency": 8.5,
                    "sources": 4.0,
                },
            ),
            EffectLayerSpec(
                "radial-pulse",
                opacity=0.36,
                blend_mode=BlendMode.ADDITIVE,
                parameters={
                    "speed": 0.8,
                    "brightness": 0.46,
                    "palette": "neon",
                    "frequency": 2.8,
                    "sharpness": 2.4,
                },
            ),
        ),
        global_brightness=0.44,
    ),
    VisualPreset(
        "neon-blades",
        "Neon Blades",
        "Fast diagonal light bars slice through a restrained moving grid.",
        (
            EffectLayerSpec(
                "checkerboard",
                opacity=0.42,
                parameters={
                    "speed": 0.55,
                    "brightness": 0.5,
                    "palette": "ocean",
                    "size": 2.0,
                    "contrast": 0.65,
                    "motion": 0.8,
                },
            ),
            EffectLayerSpec(
                "bars",
                opacity=0.72,
                blend_mode=BlendMode.LIGHTEN,
                parameters={
                    "speed": 1.35,
                    "brightness": 0.78,
                    "palette": "neon",
                    "bar_width": 0.12,
                    "angle": 34.0,
                },
            ),
        ),
        global_brightness=0.46,
    ),
    VisualPreset(
        "inferno-rise",
        "Inferno Rise",
        "Turbulent ember flames climb beneath a dense but smooth spark trail.",
        (
            EffectLayerSpec(
                "fire",
                parameters={
                    "speed": 0.9,
                    "brightness": 0.82,
                    "palette": "ember",
                    "turbulence": 5.2,
                    "cooling": 0.22,
                },
            ),
            EffectLayerSpec(
                "sparks",
                opacity=0.62,
                blend_mode=BlendMode.LIGHTEN,
                parameters={
                    "speed": 1.15,
                    "brightness": 0.62,
                    "palette": "magma",
                    "count": 18.0,
                    "decay": 0.42,
                },
            ),
        ),
        global_brightness=0.48,
    ),
    VisualPreset(
        "split-signal",
        "Split Signal",
        "Digital rain on Cube A answers broken neon blocks on Cube B.",
        (
            EffectLayerSpec(
                "digital-rain",
                fixtures=("Cube A",),
                parameters={
                    "speed": 1.05,
                    "brightness": 0.78,
                    "palette": "ocean",
                    "density": 0.82,
                    "trail": 2.4,
                },
            ),
            EffectLayerSpec(
                "glitch",
                fixtures=("Cube B",),
                parameters={
                    "speed": 0.75,
                    "brightness": 0.62,
                    "palette": "neon",
                    "block_size": 2.0,
                    "jitter": 4.5,
                },
            ),
            EffectLayerSpec(
                "energy-transfer",
                opacity=0.3,
                blend_mode=BlendMode.LIGHTEN,
                parameters={
                    "speed": 0.8,
                    "brightness": 0.5,
                    "palette": "spectrum",
                    "rate": 6.5,
                    "trail": 4.0,
                },
            ),
        ),
        global_brightness=0.43,
    ),
    VisualPreset(
        "hypnotic-drive",
        "Hypnotic Drive",
        "A forward-driving tunnel reinforced by expanding neon rings.",
        (
            EffectLayerSpec(
                "tunnel",
                parameters={
                    "speed": 1.1,
                    "brightness": 0.72,
                    "palette": "neon",
                    "ring_frequency": 3.4,
                    "floor": 0.08,
                },
            ),
            EffectLayerSpec(
                "rings",
                opacity=0.38,
                blend_mode=BlendMode.ADDITIVE,
                parameters={
                    "speed": 0.9,
                    "brightness": 0.48,
                    "palette": "spectrum",
                    "spacing": 1.35,
                    "thickness": 0.28,
                },
            ),
        ),
        global_brightness=0.45,
    ),
    VisualPreset(
        "crossfire",
        "Crossfire",
        "Hot fire and cool noise trade energy between independently rendered cubes.",
        (
            EffectLayerSpec(
                "fire",
                fixtures=("Cube A",),
                parameters={
                    "speed": 0.8,
                    "brightness": 0.8,
                    "palette": "ember",
                    "turbulence": 4.4,
                    "cooling": 0.3,
                },
            ),
            EffectLayerSpec(
                "flow-noise",
                fixtures=("Cube B",),
                parameters={
                    "speed": 0.6,
                    "brightness": 0.76,
                    "palette": "ocean",
                    "scale": 3.8,
                    "drift": 0.42,
                },
            ),
            EffectLayerSpec(
                "energy-transfer",
                opacity=0.48,
                blend_mode=BlendMode.ADDITIVE,
                parameters={
                    "speed": 1.0,
                    "brightness": 0.56,
                    "palette": "neon",
                    "rate": 8.0,
                    "trail": 3.2,
                },
            ),
        ),
        global_brightness=0.46,
    ),
)

PRESETS = {preset.preset_id: preset for preset in EXAMPLE_PRESETS}
