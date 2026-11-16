#!/usr/bin/env python3
"""Soak preflighted VLC projection beside the hardware-free 25 FPS renderer."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from typing import Callable
from unittest.mock import patch

from phreqed_dmx.app import Controller
from phreqed_dmx.config import load_config
from phreqed_dmx.engine import SceneEngine
from phreqed_dmx.presets import PRESETS
from phreqed_dmx.projection import load_stage_video_package
from phreqed_dmx.thermal import cpu_temperature_band, read_cpu_temperature_c
from phreqed_dmx.vlc_player import (
    active_user_id,
    build_display_environment,
    build_vlc_command,
)


def process_sample(pid: int) -> dict[str, float | int | None]:
    """Read bounded Linux process metrics without adding a runtime dependency."""

    rss_kib = None
    cpu_seconds = None
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                rss_kib = int(line.split()[1])
                break
    except (OSError, ValueError, IndexError):
        pass
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat[stat.rfind(")") + 2 :].split()
        ticks = int(fields[11]) + int(fields[12])
        ticks_per_second = int(os.sysconf("SC_CLK_TCK"))
        if ticks_per_second > 0:
            cpu_seconds = ticks / ticks_per_second
    except (OSError, ValueError, IndexError, AttributeError):
        pass
    return {"rss_kib": rss_kib, "cpu_seconds": cpu_seconds}


def _mapped_channel_indexes(config: object) -> tuple[set[int], tuple[int, ...]]:
    mapped: set[int] = set()
    for fixture in config.fixtures:
        start = fixture.start_address - 1
        mapped.update(range(start, start + fixture.width * fixture.height * 3))
    unmapped = tuple(index for index in range(512) if index not in mapped)
    return mapped, unmapped


def run_render_probe(
    process: subprocess.Popen,
    *,
    maximum_seconds: float,
    preset_id: str = "phase-collider",
    temperature_reader: Callable[[], float | None] = read_cpu_temperature_c,
    player_sampler: Callable[[int], dict[str, float | int | None]] = process_sample,
) -> dict[str, object]:
    """Render at 25 FPS until VLC exits while collecting independent evidence."""

    if not math.isfinite(maximum_seconds) or maximum_seconds <= 0:
        raise ValueError("projection soak maximum must be finite and positive")
    if preset_id not in PRESETS:
        raise ValueError("projection soak preset is unknown")
    config = load_config()
    if config.fps != 25:
        raise ValueError("Pi projection soak requires the configured 25 FPS")
    engine = SceneEngine(config.fixtures)
    engine.activate_preset(preset_id)
    controller = Controller(config, engine)
    _, unmapped = _mapped_channel_indexes(config)
    interval = 1.0 / config.fps
    timings: list[float] = []
    temperatures: list[float] = []
    player_rss: list[int] = []
    player_cpu: list[float] = []
    missed = 0
    over_budget = 0
    slots = 0
    timed_out = False
    process_cpu_started = time.process_time()
    started = time.monotonic()
    next_sample = started
    while process.poll() is None:
        deadline = started + slots * interval
        if deadline - started >= maximum_seconds:
            timed_out = True
            break
        time.sleep(max(0.0, deadline - time.monotonic()))
        now = time.monotonic()
        skipped = max(0, int((now - deadline) / interval))
        missed += skipped
        slots += skipped
        if now - started >= maximum_seconds:
            timed_out = True
            break
        before = time.perf_counter()
        payload = controller.render_dmx(now - started)
        render_seconds = time.perf_counter() - before
        if len(payload) != 512 or any(payload[index] for index in unmapped):
            raise RuntimeError("projection soak produced an unsafe render frame")
        timings.append(render_seconds * 1000.0)
        over_budget += render_seconds > interval
        if now >= next_sample:
            temperature = temperature_reader()
            if temperature is not None:
                temperatures.append(float(temperature))
            sample = player_sampler(process.pid)
            rss = sample.get("rss_kib")
            cpu = sample.get("cpu_seconds")
            if isinstance(rss, int):
                player_rss.append(rss)
            if isinstance(cpu, (int, float)):
                player_cpu.append(float(cpu))
            next_sample = now + 1.0
        slots += 1
    duration = time.monotonic() - started
    controller.engine.set_blackout(True)
    blackout_zero = not any(controller.render_dmx(duration))
    if not timings:
        raise RuntimeError("projection soak completed without rendering a frame")
    ordered = sorted(timings)
    player_cpu_percent = None
    if len(player_cpu) >= 2 and duration > 0:
        player_cpu_percent = round(
            max(0.0, player_cpu[-1] - player_cpu[0]) / duration * 100.0,
            2,
        )
    temperature_max = max(temperatures) if temperatures else None
    return {
        "preset_id": preset_id,
        "duration_seconds": round(duration, 3),
        "frames": len(timings),
        "achieved_fps": round(len(timings) / duration, 3),
        "missed_slots": missed,
        "over_budget_frames": over_budget,
        "render_mean_ms": round(statistics.mean(timings), 3),
        "render_p95_ms": round(
            ordered[math.ceil(len(ordered) * 0.95) - 1], 3
        ),
        "render_max_ms": round(max(timings), 3),
        "render_process_cpu_percent_one_core": round(
            (time.process_time() - process_cpu_started) / duration * 100.0, 2
        ),
        "player_cpu_percent_one_core": player_cpu_percent,
        "player_rss_max_kib": max(player_rss) if player_rss else None,
        "temperature_max_c": temperature_max,
        "temperature_band": cpu_temperature_band(temperature_max),
        "unmapped_channels_zero": True,
        "blackout_zero": blackout_zero,
        "timed_out": timed_out,
    }


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)


def _log_diagnostics(value: str) -> dict[str, object]:
    lowered = value.casefold()
    return {
        "v4l2_h264_fallback_observed": (
            "v4l2m2m" in lowered and "cannot start codec" in lowered
        ),
        "wayland_dmabuf_output_observed": (
            "wl_dmabuf" in lowered and "open:" in lowered
        ),
        "global_hotkeys_unavailable": "globalhotkeys" in lowered,
        "video_dropped_frames": None,
        "video_drop_note": (
            "VLC 3 CLI does not expose a reliable per-run dropped-frame count; "
            "visual review and later backend telemetry remain required."
        ),
        "stderr_tail": value[-20000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screen", type=int, default=1)
    parser.add_argument("--vlc", default="vlc")
    parser.add_argument("--preset", choices=tuple(PRESETS), default="phase-collider")
    parser.add_argument(
        "--confirm-projector-output",
        action="store_true",
        help="required acknowledgment that sustained visible output is intended",
    )
    args = parser.parse_args()
    if not args.confirm_projector_output:
        parser.error("--confirm-projector-output is required")
    executable = (
        shutil.which(args.vlc) if Path(args.vlc).name == args.vlc else args.vlc
    )
    if not executable or not Path(executable).is_file():
        raise SystemExit(f"VLC executable is unavailable: {args.vlc}")
    package = load_stage_video_package(args.manifest)
    command = build_vlc_command(
        package,
        vlc_executable=executable,
        screen_number=args.screen,
    )
    environment = build_display_environment(
        os.environ,
        user_id=active_user_id(),
    )
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "mode": (
            "confirmed VLC projector output plus hardware-free 25 FPS render; "
            "no Art-Net transport"
        ),
        "package_id": package.package_id,
        "package_duration_seconds": package.duration_seconds,
        "screen": args.screen,
        "fps": 25,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix(args.output.suffix + ".vlc.log")
    process = None
    try:
        with log_path.open("w", encoding="utf-8") as log_stream:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=log_stream,
                env=environment,
                shell=False,
            )
            with patch(
                "socket.socket",
                side_effect=RuntimeError("Art-Net sockets forbidden in projection soak"),
            ):
                with patch(
                    "phreqed_dmx.app.ArtNetSender",
                    side_effect=RuntimeError("live output forbidden in projection soak"),
                ):
                    report["render"] = run_render_probe(
                        process,
                        maximum_seconds=package.duration_seconds + 30.0,
                        preset_id=args.preset,
                    )
        if process is not None:
            _stop_process(process)
            report["player_returncode"] = process.returncode
    finally:
        if process is not None:
            _stop_process(process)
        log_value = ""
        try:
            log_value = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        report["player_diagnostics"] = _log_diagnostics(log_value)
        report["completed_utc"] = datetime.now(timezone.utc).isoformat()
        render = report.get("render", {})
        minimum_runtime = max(1.0, package.duration_seconds * 0.9)
        report["checks"] = {
            "player_exit": report.get("player_returncode") == 0,
            "playback_duration": (
                float(render.get("duration_seconds", 0.0)) >= minimum_runtime
                and not bool(render.get("timed_out", True))
            ),
            "render_timing": (
                render.get("missed_slots") == 0
                and render.get("over_budget_frames") == 0
            ),
            "reserved_channels": render.get("unmapped_channels_zero") is True,
            "render_blackout": render.get("blackout_zero") is True,
            "temperature": render.get("temperature_band") in {"normal", "warm"},
        }
        report["passed"] = all(report["checks"].values())
        write_json_atomic(args.output, report)
        try:
            log_path.unlink()
        except OSError:
            pass
    print(f"Projection soak report: {args.output.resolve()}")
    if not report["passed"]:
        raise SystemExit(f"projection soak failed: {report['checks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
