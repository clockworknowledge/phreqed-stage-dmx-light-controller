"""Application controller and explicit simulation/live command-line modes."""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import replace
from pathlib import Path

from .artnet import ArtNetSender
from .audio_analysis import AudioAnalysisSource
from .audio_reactivity import AudioReactiveClock
from .compositor import Compositor, FrameSafetyLimiter, Scene
from .config import DEFAULT_CONFIG_PATH, ControllerConfig, load_config
from .effect_api import PerformanceContext
from .effect_library import EFFECT_REGISTRY
from .engine import SceneEngine
from .foot_control import RawMidiFootController
from .presets import PRESETS
from .render import compose_dmx
from .show_control import ShowController
from .scenes import SceneSequencer
from .white_output import MAX_WHITE_OUTPUT_CEILING, WHITE_OUTPUT_CEILING


class Controller:
    """Owns visual state; network output remains outside this class."""

    def __init__(
        self,
        config: ControllerConfig,
        engine: SceneEngine | None = None,
        *,
        speed: float = 1.0,
        safety_limiter: FrameSafetyLimiter | None = None,
        audio_source: AudioAnalysisSource | None = None,
        audio_deep_dim: bool = False,
        audio_quiet_floor: float = 0.03,
    ) -> None:
        if speed <= 0:
            raise ValueError("speed must be positive")
        self.config = config
        self.engine = engine or SceneEngine(config.fixtures)
        self.show = ShowController(self.engine)
        self.speed = speed
        self.safety_limiter = safety_limiter or FrameSafetyLimiter(
            maximum_brightness=self.engine.compositor.maximum_brightness
        )
        self.audio_source = audio_source
        self.audio_clock = AudioReactiveClock(
            deep_dim_enabled=audio_deep_dim,
            quiet_brightness_floor=audio_quiet_floor,
        )
        self.audio_motion_multiplier = 1.0
        self.audio_brightness_multiplier = 1.0
        self._last_scene: Scene | None = None
        self._transition_from: Scene | None = None
        self._transition_started = 0.0
        self._transition_duration = 0.0
        self.scenes = SceneSequencer(self.engine, self.begin_transition)

    def configure_audio_dimming(self, *, enabled: bool, quiet_floor: float) -> None:
        self.audio_clock.configure_dimming(
            enabled=enabled, quiet_floor=quiet_floor
        )

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
        if context is None:
            context = self.show.context()
            if self.audio_source is not None:
                context = replace(context, audio=self.audio_source.sample(elapsed))
        self.scenes.update(elapsed)
        if self.engine.blackout_enabled:
            self._transition_from = None
        reactive = self.audio_clock.advance(
            elapsed,
            tempo_bpm=context.tempo_bpm,
            speed=self.speed,
            audio=context.audio,
        )
        self.audio_motion_multiplier = reactive.motion_multiplier
        self.audio_brightness_multiplier = reactive.brightness_multiplier
        scene = self.engine.render(reactive.animation_time, context)
        if self._transition_from is not None:
            progress = (elapsed - self._transition_started) / self._transition_duration
            if progress >= 1.0:
                self._transition_from = None
            else:
                scene = self.engine.compositor.transition(
                    self._transition_from, scene, max(0.0, progress)
                )
        if reactive.brightness_multiplier < 1.0:
            for grid in scene.values():
                for y in range(grid.height):
                    for x in range(grid.width):
                        grid[x, y] = grid[x, y].scaled(
                            reactive.brightness_multiplier
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
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("brightness must be between 0.0 and 1.0")
    return parsed


def _ceiling(value: str) -> float:
    parsed = _brightness(value)
    if parsed == 0.0:
        raise argparse.ArgumentTypeError("RGB ceiling must be greater than 0.0")
    return parsed


def _white_ceiling(value: str) -> float:
    parsed = _brightness(value)
    if not math.isfinite(parsed) or not 0.0 < parsed <= MAX_WHITE_OUTPUT_CEILING:
        raise argparse.ArgumentTypeError(
            "white ceiling must be above 0.0 and at most 1.0"
        )
    return parsed


def _positive(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _contrast(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or not 1.0 <= parsed <= 3.0:
        raise argparse.ArgumentTypeError("contrast must be between 1.0 and 3.0")
    return parsed


def _audio_sensitivity(value: str) -> float:
    parsed = float(value)
    if not 0.1 <= parsed <= 40.0:
        raise argparse.ArgumentTypeError("audio sensitivity must be between 0.1 and 40.0")
    return parsed


def _quiet_floor(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 0.25:
        raise argparse.ArgumentTypeError(
            "audio quiet floor must be between 0.0 and 0.25"
        )
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
        choices=(
            "spectrum", "magma", "ocean", "neon", "ember", "monochrome",
            "matrix",
        ),
        default="spectrum",
        help="manual effect palette",
    )
    parser.add_argument(
        "--brightness",
        type=_brightness,
        help="optional peak/master output level; it may not exceed --rgb-ceiling",
    )
    parser.add_argument(
        "--rgb-ceiling",
        type=_ceiling,
        default=0.65,
        metavar="0.0-1.0",
        help="hard RGB output ceiling (default 0.65; values above 0.65 are live-only)",
    )
    parser.add_argument(
        "--acknowledge-high-output",
        action="store_true",
        help="required with live mode when --rgb-ceiling is above the safe default",
    )
    parser.add_argument(
        "--white-ceiling",
        type=_white_ceiling,
        default=WHITE_OUTPUT_CEILING,
        metavar="0.0-1.0",
        help=(
            "physical center-white ceiling (default 0.10; higher values require "
            "explicit live --web acknowledgement)"
        ),
    )
    parser.add_argument(
        "--acknowledge-high-output-whites",
        action="store_true",
        help="required with live --web when --white-ceiling is above 0.10",
    )
    parser.add_argument(
        "--speed",
        type=_positive,
        default=1.0,
        help="operator animation trim applied to the tempo and audio-driven clock",
    )
    parser.add_argument(
        "--contrast",
        type=_contrast,
        default=1.0,
        metavar="1.0-3.0",
        help="preserve highlight separation at high master brightness (default 1.0)",
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
    parser.add_argument(
        "--foot-midi-device",
        type=Path,
        help="explicit ALSA raw-MIDI device for Ampero Control (disabled by default)",
    )
    parser.add_argument(
        "--foot-midi-channel",
        type=int,
        choices=range(1, 17),
        default=1,
        metavar="1-16",
        help="Ampero Control MIDI channel (default 1)",
    )
    parser.add_argument(
        "--audio-device",
        help="explicit ALSA capture device, for example plughw:CARD=Snowball,DEV=0",
    )
    parser.add_argument(
        "--audio-sensitivity",
        type=_audio_sensitivity,
        metavar="0.1-40",
        help="microphone analysis gain (default 12.0; requires --audio-device)",
    )
    parser.add_argument(
        "--audio-auto-level",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="adapt microphone gain to avoid sustained pinned analysis (default on)",
    )
    parser.add_argument(
        "--audio-deep-dim",
        action="store_true",
        help="allow quiet audio to dim near black instead of the default 55%% floor",
    )
    parser.add_argument(
        "--audio-quiet-floor",
        type=_quiet_floor,
        default=0.03,
        metavar="0.0-0.25",
        help="brightness floor used by --audio-deep-dim (default 0.03)",
    )
    return parser


def _configure_engine(args: argparse.Namespace, config: ControllerConfig) -> SceneEngine:
    engine = SceneEngine(
        config.fixtures,
        compositor=Compositor(
            maximum_brightness=args.rgb_ceiling,
            contrast=args.contrast,
        ),
    )
    engine.activate_preset(args.preset)
    if args.brightness is not None:
        engine.set_global_brightness(args.brightness)
    elif engine.compositor.global_brightness > args.rgb_ceiling:
        engine.set_global_brightness(args.rgb_ceiling)
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
    if args.audio_sensitivity is not None and args.audio_device is None:
        parser.error("--audio-sensitivity requires --audio-device")
    if args.rgb_ceiling > 0.65:
        if args.command != "live":
            parser.error("--rgb-ceiling above 0.65 is available only in explicit live mode")
        if not args.acknowledge_high_output:
            parser.error(
                "--rgb-ceiling above 0.65 requires --acknowledge-high-output"
            )
    if args.white_ceiling > WHITE_OUTPUT_CEILING:
        if args.command != "live" or not args.web:
            parser.error(
                "--white-ceiling above 0.10 is available only with explicit live --web"
            )
        if not args.acknowledge_high_output_whites:
            parser.error(
                "--white-ceiling above 0.10 requires "
                "--acknowledge-high-output-whites"
            )
    if args.brightness is not None and args.brightness > args.rgb_ceiling:
        parser.error("--brightness may not exceed --rgb-ceiling")

    config = load_config(args.config)
    engine = _configure_engine(args, config)
    audio_source = None
    if args.audio_device is not None:
        # Keep OS capture code out of the default simulation/import path.
        from .audio_capture import ArecordAudioSource

        audio_source = ArecordAudioSource(
            args.audio_device,
            sensitivity=args.audio_sensitivity or 12.0,
            auto_level=args.audio_auto_level,
        )
    controller = Controller(
        config,
        engine,
        speed=args.speed,
        audio_source=audio_source,
        audio_deep_dim=args.audio_deep_dim,
        audio_quiet_floor=args.audio_quiet_floor,
    )
    browser_requested = args.command == "web" or args.web
    foot_controller = (
        RawMidiFootController(
            args.foot_midi_device,
            controller.show,
            channel=args.foot_midi_channel,
        )
        if args.foot_midi_device is not None and not browser_requested
        else None
    )

    try:
        if audio_source is not None:
            try:
                audio_source.start()
            except RuntimeError as exc:
                print(f"AUDIO INPUT ERROR: {exc}", file=sys.stderr)
                return 2
            print(
                f"AUDIO INPUT: {args.audio_device} at 44100 Hz mono",
                file=sys.stderr,
            )
        if foot_controller is not None:
            foot_controller.start()
            print(
                f"FOOT CONTROL: {args.foot_midi_device} on MIDI channel "
                f"{args.foot_midi_channel}",
                file=sys.stderr,
            )
        if browser_requested:
            from .web_control import serve

            serve(controller, args.library, host=args.host, port=args.port,
                  allow_network=args.allow_network, allow_live=args.command == "live",
                  foot_midi_device=args.foot_midi_device,
                  foot_midi_channel=args.foot_midi_channel,
                  white_output_ceiling=args.white_ceiling)
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
    finally:
        if foot_controller is not None:
            foot_controller.close()
        if audio_source is not None:
            audio_source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
