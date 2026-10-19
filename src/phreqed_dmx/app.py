"""Application controller and explicit simulation/live command-line modes."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .artnet import ArtNetSender
from .config import DEFAULT_CONFIG_PATH, ControllerConfig, load_config
from .effects import CUBE_MODES, EFFECT_NAMES, STANDARD_EFFECTS, Effect, VisualEngine
from .frame import PixelGrid
from .render import compose_dmx, create_grids


class Controller:
    def __init__(self, config: ControllerConfig, effect: Effect, *, speed: float = 1.0) -> None:
        if speed <= 0:
            raise ValueError("speed must be positive")
        self.config = config
        self.effect = effect
        self.speed = speed
        self.grids: dict[str, PixelGrid] = create_grids(config.fixtures)

    def render(self, elapsed: float) -> bytes:
        ordered_grids = [self.grids[fixture.name] for fixture in self.config.fixtures]
        self.effect.render(elapsed * self.speed, ordered_grids)
        return compose_dmx(self.config.fixtures, self.grids)


def _brightness(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("brightness must be between 0.0 and 1.0")
    return parsed


def _positive(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("simulate", "live"),
        default="simulate",
        help="output mode; defaults to safe local simulation",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG_PATH, help="fixture TOML path"
    )
    parser.add_argument(
        "--effect", choices=EFFECT_NAMES, default="plasma", help="Cube A effect"
    )
    parser.add_argument(
        "--mode", choices=CUBE_MODES, default="mirror", help="two-cube relationship"
    )
    parser.add_argument(
        "--second-effect",
        choices=STANDARD_EFFECTS,
        default="tunnel",
        help="Cube B effect in independent mode",
    )
    parser.add_argument(
        "--brightness", type=_brightness, default=0.35, help="output level from 0.0 to 1.0"
    )
    parser.add_argument(
        "--speed", type=_positive, default=1.0, help="animation speed multiplier"
    )
    parser.add_argument(
        "--duration", type=_positive, help="optional live-mode run time in seconds"
    )
    return parser


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
            sender.send(controller.render(now - started))
            next_frame += interval
            time.sleep(max(0.0, next_frame - time.monotonic()))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "simulate" and args.duration is not None:
        parser.error("--duration is available only in live mode")

    config = load_config(args.config)
    engine = VisualEngine(
        args.effect,
        mode=args.mode,
        second_effect=args.second_effect,
        brightness=args.brightness,
    )
    controller = Controller(config, engine, speed=args.speed)

    try:
        if args.command == "live":
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
