"""Application controller and explicit simulation/live command-line modes."""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

from .artnet import ArtNetSender
from .compositor import FrameSafetyLimiter, Scene
from .config import DEFAULT_CONFIG_PATH, ControllerConfig, load_config
from .effect_api import PerformanceContext
from .effect_library import EFFECT_REGISTRY
from .engine import SceneEngine
from .presets import PRESETS
from .render import compose_dmx
from .show_control import ShowController
from .scenes import SceneSequencer


class Controller:
    """Owns visual state; network output remains outside this class."""

    def __init__(
        self,
        config: ControllerConfig,
        engine: SceneEngine | None = None,
        *,
        speed: float = 1.0,
        safety_limiter: FrameSafetyLimiter | None = None,
    ) -> None:
        if speed <= 0:
            raise ValueError("speed must be positive")
        self.config = config
        self.engine = engine or SceneEngine(config.fixtures)
        self.show = ShowController(self.engine)
        self.speed = speed
        self.safety_limiter = safety_limiter or FrameSafetyLimiter()
        self._last_scene: Scene | None = None
        self._transition_from: Scene | None = None
        self._transition_started = 0.0
        self._transition_duration = 0.0
        self.scenes = SceneSequencer(self.engine, self.begin_transition)

    def begin_transition(self, elapsed: float, *, duration: float = 0.45) -> None:
        if not math.isfinite(duration) or duration < 0.0:
            raise ValueError("transition duration must be finite and nonnegative")
        if duration == 0.0:
            self._transition_from = None
            return
        if self._last_scene is None:
            return
        self._transition_from = {
            name: grid.copy() for name, grid in self._last_scene.items()
        }
        self._transition_started = elapsed
        self._transition_duration = duration

    def render_scene(
        self,
        elapsed: float,
        *,
        context: PerformanceContext | None = None,
        apply_safety: bool = True,
    ) -> Scene:
        context = self.show.context() if context is None else context
        self.scenes.update(elapsed)
        if self.engine.blackout_enabled:
            self._transition_from = None
        scene = self.engine.render(elapsed * self.speed, context)
        if self._transition_from is not None:
            progress = (elapsed - self._transition_started) / self._transition_duration
            if progress >= 1.0:
                self._transition_from = None
            else:
                scene = self.engine.compositor.transition(
                    self._transition_from, scene, max(0.0, progress)
                )
        result = self.safety_limiter.apply(scene, elapsed) if apply_safety else scene
        self._last_scene = {name: grid.copy() for name, grid in result.items()}
        return result

    def render_dmx(
        self, elapsed: float, *, context: PerformanceContext | None = None
    ) -> bytes:
        return compose_dmx(
            self.config.fixtures,
            self.render_scene(elapsed, context=context, apply_safety=True),
        )


def _brightness(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 0.65:
        raise argparse.ArgumentTypeError("brightness must be between 0.0 and 0.65")
    return parsed


def _positive(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    effect_ids = tuple(metadata.effect_id for metadata in EFFECT_REGISTRY.metadata())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("simulate", "live", "web"),
        default="simulate",
        help="output mode; defaults to safe local simulation",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH, help="fixture TOML path"
    )
    parser.add_argument(
        "--preset", choices=tuple(PRESETS), default="psychedelic-bloom", help="initial preset"
    )
    parser.add_argument(
        "--effect",
        choices=effect_ids,
        help="optional manual Cube A effect; overrides the preset",
    )
    parser.add_argument(
        "--mode",
        choices=("mirror", "complementary", "independent"),
        default="mirror",
        help="manual two-cube relationship when --effect is supplied",
    )
    parser.add_argument(
        "--second-effect",
        choices=effect_ids,
        default="tunnel",
        help="Cube B effect in independent mode",
    )
    parser.add_argument(
        "--palette",
        choices=("spectrum", "magma", "ocean", "neon", "ember", "monochrome"),
        default="spectrum",
        help="manual effect palette",
    )
    parser.add_argument(
        "--brightness",
        type=_brightness,
        help="optional global output level from 0.0 to the safety ceiling of 0.65",
    )
    parser.add_argument(
        "--speed", type=_positive, default=1.0, help="global animation speed multiplier"
    )
    parser.add_argument(
        "--duration", type=_positive, help="optional live-mode run time in seconds"
    )
    parser.add_argument("--web", action="store_true", help="browser control for explicit live mode")
    parser.add_argument("--host", default="127.0.0.1", help="browser listen address")
    parser.add_argument("--port", type=int, default=8080, help="browser port (default 8080)")
    parser.add_argument("--allow-network", default="192.168.1.0/24", help="trusted IPv4 browser network")
    parser.add_argument("--library", type=Path, default=Path.home() / ".local/share/phreqed-dmx/library.json",
                        help="user preset and scene JSON file")
    return parser


def _configure_engine(args: argparse.Namespace, config: ControllerConfig) -> SceneEngine:
    engine = SceneEngine(config.fixtures)
    engine.activate_preset(args.preset)
    if args.brightness is not None:
        engine.set_global_brightness(args.brightness)
    if args.effect is None:
        return engine

    fixture_names = [fixture.name for fixture in config.fixtures]
    engine.select_effect(fixture_names[0], args.effect)
    engine.update_parameter(fixture_names[0], "palette", args.palette)
    if args.mode == "independent":
        second_effect = args.second_effect
        second_palette = args.palette
    elif args.mode == "complementary":
        second_effect = args.effect
        second_palette = "neon" if args.palette == "spectrum" else "spectrum"
    else:
        second_effect = args.effect
        second_palette = args.palette
    engine.select_effect(fixture_names[1], second_effect)
    engine.update_parameter(fixture_names[1], "palette", second_palette)
    if args.brightness is not None:
        engine.set_global_brightness(args.brightness)
    return engine


def _run_live(controller: Controller, duration: float | None) -> None:
    config = controller.config
    interval = 1.0 / config.fps
    started = time.monotonic()
    next_frame = started
    print(
        f"LIVE: Art-Net universe {config.universe} -> "
        f"{config.artnet_host}:{config.artnet_port} at {config.fps} FPS",
        file=sys.stderr,
    )
    with ArtNetSender(config.artnet_host, config.artnet_port, config.universe) as sender:
        while duration is None or time.monotonic() - started < duration:
            now = time.monotonic()
            sender.send(controller.render_dmx(now - started))
            next_frame += interval
            time.sleep(max(0.0, next_frame - time.monotonic()))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.web and args.command != "live":
        parser.error("--web requires the explicit live command; use web for browser simulation")
    if (args.command == "web" or args.web) and args.duration is not None:
        parser.error("--duration is not supported by browser control")
    if args.command == "simulate" and args.duration is not None:
        parser.error("--duration is available only in live mode")

    config = load_config(args.config)
    engine = _configure_engine(args, config)
    controller = Controller(config, engine, speed=args.speed)

    try:
        if args.command == "web" or args.web:
            from .web_control import serve

            serve(controller, args.library, host=args.host, port=args.port,
                  allow_network=args.allow_network, allow_live=args.command == "live")
        elif args.command == "live":
            _run_live(controller, args.duration)
        else:
            from .simulator import TkSimulator

            TkSimulator(controller).run()
    except KeyboardInterrupt:
        message = (
            "Interrupted; live mode requested a blackout before closing."
            if args.command == "live"
            else "Simulation interrupted; no network output was active."
        )
        print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
