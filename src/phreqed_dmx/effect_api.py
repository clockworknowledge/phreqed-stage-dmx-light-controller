"""Standard deterministic effect interface, metadata, and parameter validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol

from .color import NormalizedRGB, Palette
from .audio_analysis import AudioAnalysis

ParameterValue = float | int | str


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    key: str
    label: str
    default: ParameterValue
    description: str
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    choices: tuple[str, ...] = ()

    def validate(self, value: ParameterValue) -> ParameterValue:
        if self.choices:
            if not isinstance(value, str) or value not in self.choices:
                raise ValueError(f"{self.key} must be one of {', '.join(self.choices)}")
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{self.key} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"{self.key} must be finite")
        if self.minimum is not None and numeric < self.minimum:
            raise ValueError(f"{self.key} must be at least {self.minimum}")
        if self.maximum is not None and numeric > self.maximum:
            raise ValueError(f"{self.key} must be at most {self.maximum}")
        return numeric


COMMON_PARAMETER_SPECS = (
    ParameterSpec("speed", "Speed", 1.0, "Animation speed multiplier", 0.1, 5.0, 0.1),
    ParameterSpec(
        "brightness", "Effect level", 0.75, "Effect-local brightness", 0.0, 1.0, 0.01
    ),
    ParameterSpec(
        "palette",
        "Palette",
        Palette.SPECTRUM.value,
        "Colour palette",
        choices=tuple(palette.value for palette in Palette),
    ),
)


@dataclass(frozen=True, slots=True)
class EffectMetadata:
    effect_id: str
    name: str
    description: str
    category: str
    parameters: tuple[ParameterSpec, ...]

    def __post_init__(self) -> None:
        keys = [parameter.key for parameter in self.parameters]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate parameter keys for {self.effect_id}")

    def parameter(self, key: str) -> ParameterSpec:
        for parameter in self.parameters:
            if parameter.key == key:
                return parameter
        raise KeyError(key)


class EffectParameters:
    """Immutable, metadata-validated effect parameter values."""

    def __init__(
        self,
        metadata: EffectMetadata,
        overrides: Mapping[str, ParameterValue] | None = None,
    ) -> None:
        overrides = {} if overrides is None else overrides
        specs = {spec.key: spec for spec in metadata.parameters}
        unknown = set(overrides).difference(specs)
        if unknown:
            raise ValueError(f"unknown parameters for {metadata.effect_id}: {sorted(unknown)}")
        values = {
            key: spec.validate(overrides.get(key, spec.default)) for key, spec in specs.items()
        }
        self._values: Mapping[str, ParameterValue] = MappingProxyType(values)

    def __getitem__(self, key: str) -> ParameterValue:
        return self._values[key]

    def number(self, key: str) -> float:
        value = self._values[key]
        if not isinstance(value, (int, float)):
            raise TypeError(f"{key} is not numeric")
        return float(value)

    def choice(self, key: str) -> str:
        value = self._values[key]
        if not isinstance(value, str):
            raise TypeError(f"{key} is not a choice")
        return value

    def as_dict(self) -> dict[str, ParameterValue]:
        return dict(self._values)


@dataclass(frozen=True, slots=True)
class FixtureIdentity:
    name: str
    index: int
    count: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("fixture identity name cannot be empty")
        if self.count <= 0 or not 0 <= self.index < self.count:
            raise ValueError("fixture identity index must be within fixture count")


@dataclass(frozen=True, slots=True)
class PerformanceContext:
    tempo_bpm: float = 120.0
    beat_phase: float = 0.0
    energy: float = 0.5
    event: str | None = None
    seed: int = 0
    audio: AudioAnalysis | None = None

    def __post_init__(self) -> None:
        if not 20.0 <= self.tempo_bpm <= 300.0:
            raise ValueError("tempo_bpm must be between 20 and 300")
        if not 0.0 <= self.beat_phase <= 1.0:
            raise ValueError("beat_phase must be between 0 and 1")
        if not 0.0 <= self.energy <= 1.0:
            raise ValueError("energy must be between 0 and 1")
        if self.audio is not None and not isinstance(self.audio, AudioAnalysis):
            raise TypeError("audio must be AudioAnalysis or None")


class Effect(Protocol):
    metadata: EffectMetadata

    def sample(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        animation_time: float,
        fixture: FixtureIdentity,
        parameters: EffectParameters,
        context: PerformanceContext | None = None,
    ) -> NormalizedRGB: ...


class EffectRegistry:
    def __init__(self, effects: tuple[Effect, ...]) -> None:
        self._effects = {effect.metadata.effect_id: effect for effect in effects}
        if len(self._effects) != len(effects):
            raise ValueError("effect IDs must be unique")

    def get(self, effect_id: str) -> Effect:
        try:
            return self._effects[effect_id]
        except KeyError as exc:
            raise ValueError(f"unknown effect: {effect_id}") from exc

    def metadata(self) -> tuple[EffectMetadata, ...]:
        return tuple(effect.metadata for effect in self._effects.values())

    def parameters(
        self,
        effect_id: str,
        overrides: Mapping[str, ParameterValue] | None = None,
    ) -> EffectParameters:
        return EffectParameters(self.get(effect_id).metadata, overrides)
