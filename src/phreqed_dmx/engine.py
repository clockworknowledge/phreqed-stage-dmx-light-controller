"""Fixture-independent scene rendering over the standardized effect catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .color import NormalizedGrid
from .compositor import BlendMode, Compositor, Layer, Scene, black_scene
from .effect_api import EffectParameters, EffectRegistry, FixtureIdentity, ParameterValue, PerformanceContext
from .effect_library import EFFECT_REGISTRY
from .fixtures import FixtureConfig
from .presets import EXAMPLE_PRESETS, EffectLayerSpec, VisualPreset


@dataclass(slots=True)
class FixtureSelection:
    effect_id: str
    parameters: dict[str, ParameterValue] = field(default_factory=dict)


class SceneEngine:
    def __init__(
        self,
        fixtures: tuple[FixtureConfig, ...],
        *,
        registry: EffectRegistry = EFFECT_REGISTRY,
        compositor: Compositor | None = None,
        presets: tuple[VisualPreset, ...] = EXAMPLE_PRESETS,
    ) -> None:
        if not fixtures:
            raise ValueError("scene engine requires fixtures")
        self.fixtures = fixtures
        self.registry = registry
        self.compositor = compositor or Compositor()
        self.presets = {preset.preset_id: preset for preset in presets}
        self.preset_order = tuple(self.presets)
        self.active_preset_id = self.preset_order[0] if self.preset_order else None
        self.global_brightness_override: float | None = None
        self.manual_mode = False
        self.blackout_enabled = False
        self.fixture_selections = {
            fixture.name: FixtureSelection("plasma" if index == 0 else "tunnel")
            for index, fixture in enumerate(fixtures)
        }
        if self.active_preset_id is not None:
            self.compositor.set_global_brightness(
                self.presets[self.active_preset_id].global_brightness
            )

    @property
    def geometry(self) -> dict[str, tuple[int, int]]:
        return {
            fixture.name: (fixture.width, fixture.height) for fixture in self.fixtures
        }

    def render(
        self, animation_time: float, context: PerformanceContext | None = None
    ) -> Scene:
        if self.blackout_enabled:
            return black_scene(self.geometry)
        if self.manual_mode:
            layer_specs = tuple(
                EffectLayerSpec(
                    selection.effect_id,
                    fixtures=(fixture_name,),
                    parameters=selection.parameters,
                )
                for fixture_name, selection in self.fixture_selections.items()
            )
        else:
            if self.active_preset_id is None:
                raise RuntimeError("no active preset")
            preset = self.presets[self.active_preset_id]
            level = (
                preset.global_brightness
                if self.global_brightness_override is None
                else self.global_brightness_override
            )
            self.compositor.set_global_brightness(level)
            layer_specs = preset.layers
        layers = tuple(
            self._render_layer(layer_spec, animation_time, context)
            for layer_spec in layer_specs
        )
        return self.compositor.compose(self.geometry, layers)

    def render_preset(
        self,
        preset_id: str,
        animation_time: float,
        context: PerformanceContext | None = None,
    ) -> Scene:
        try:
            preset = self.presets[preset_id]
        except KeyError as exc:
            raise ValueError(f"unknown preset: {preset_id}") from exc
        previous = self.compositor.global_brightness
        try:
            self.compositor.set_global_brightness(preset.global_brightness)
            layers = tuple(
                self._render_layer(layer, animation_time, context) for layer in preset.layers
            )
            return self.compositor.compose(self.geometry, layers)
        finally:
            self.compositor.set_global_brightness(previous)

    def transition_presets(
        self,
        first_id: str,
        second_id: str,
        animation_time: float,
        progress: float,
        context: PerformanceContext | None = None,
    ) -> Scene:
        first = self.render_preset(first_id, animation_time, context)
        second = self.render_preset(second_id, animation_time, context)
        return self.compositor.transition(first, second, progress)

    def select_effect(self, fixture_name: str, effect_id: str) -> None:
        self.registry.get(effect_id)
        selection = self._selection(fixture_name)
        selection.effect_id = effect_id
        selection.parameters.clear()
        self.manual_mode = True

    def update_parameter(
        self, fixture_name: str, key: str, value: ParameterValue
    ) -> None:
        selection = self._selection(fixture_name)
        proposed = {**selection.parameters, key: value}
        self.registry.parameters(selection.effect_id, proposed)
        selection.parameters = proposed
        self.manual_mode = True

    def activate_preset(self, preset_id: str) -> None:
        if preset_id not in self.presets:
            raise ValueError(f"unknown preset: {preset_id}")
        self.active_preset_id = preset_id
        self.manual_mode = False

    def set_blackout(self, enabled: bool) -> None:
        self.blackout_enabled = bool(enabled)

    def set_global_brightness(self, value: float) -> None:
        self.compositor.set_global_brightness(value)
        self.global_brightness_override = value

    def _selection(self, fixture_name: str) -> FixtureSelection:
        try:
            return self.fixture_selections[fixture_name]
        except KeyError as exc:
            raise ValueError(f"unknown fixture: {fixture_name}") from exc

    def _render_layer(
        self,
        layer_spec: EffectLayerSpec,
        animation_time: float,
        context: PerformanceContext | None,
    ) -> Layer:
        effect = self.registry.get(layer_spec.effect_id)
        parameters = self.registry.parameters(layer_spec.effect_id, layer_spec.parameters)
        target_names = (
            frozenset(fixture.name for fixture in self.fixtures)
            if layer_spec.fixtures is None
            else frozenset(layer_spec.fixtures)
        )
        unknown = target_names.difference(self.geometry)
        if unknown:
            raise ValueError(f"layer targets unknown fixtures: {sorted(unknown)}")
        frames: dict[str, NormalizedGrid] = {}
        for index, fixture in enumerate(self.fixtures):
            if fixture.name not in target_names:
                continue
            identity = FixtureIdentity(fixture.name, index, len(self.fixtures))
            frames[fixture.name] = self._render_effect_frame(
                effect, parameters, identity, fixture, animation_time, context
            )
        return Layer(
            frames,
            opacity=layer_spec.opacity,
            blend_mode=layer_spec.blend_mode,
            fixtures=target_names,
        )

    @staticmethod
    def _render_effect_frame(
        effect: object,
        parameters: EffectParameters,
        identity: FixtureIdentity,
        fixture: FixtureConfig,
        animation_time: float,
        context: PerformanceContext | None,
    ) -> NormalizedGrid:
        grid = NormalizedGrid(fixture.width, fixture.height)
        for y in range(fixture.height):
            for x in range(fixture.width):
                grid[x, y] = effect.sample(
                    x,
                    y,
                    fixture.width,
                    fixture.height,
                    animation_time,
                    identity,
                    parameters,
                    context,
                )
        return grid
