#!/usr/bin/env python3
"""Exercise every look at 25 FPS without creating sockets or opening a GUI."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import statistics
import time
from unittest.mock import patch

from phreqed_dmx.app import Controller
from phreqed_dmx.config import load_config
from phreqed_dmx.effect_library import EFFECT_REGISTRY
from phreqed_dmx.engine import SceneEngine
from phreqed_dmx.presets import PRESETS


def resident_kib() -> int | None:
    """Return current Linux RSS; unsupported platforms report no value."""
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    except OSError:
        pass
    return None


def temperature_c() -> float | None:
    try:
        return float(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
    except (OSError, ValueError):
        return None


def run_look(kind: str, look_id: str, seconds: float) -> dict[str, object]:
    config = load_config()
    if config.fps != 25:
        raise ValueError('Pi commissioning requires the configured 25 FPS')
    engine = SceneEngine(config.fixtures)
    if kind == 'effect':
        for fixture in config.fixtures:
            engine.select_effect(fixture.name, look_id)
    else:
        engine.activate_preset(look_id)
    controller = Controller(config, engine)
    # Build a mask from confirmed RGB pixels; every other channel must be zero.
    mapped = set()
    for fixture in config.fixtures:
        start = fixture.start_address - 1
        mapped.update(range(start, start + fixture.width * fixture.height * 3))
    unmapped = tuple(index for index in range(512) if index not in mapped)
    interval = 1 / config.fps
    slots = math.ceil(seconds * config.fps)
    timings = []
    rss = []
    temperatures = []
    missed = 0
    over_budget = 0
    cpu_started = time.process_time()
    started = time.monotonic()
    slot = 0
    while slot < slots:
        deadline = started + slot * interval
        time.sleep(max(0, deadline - time.monotonic()))
        now = time.monotonic()
        skipped = min(int(max(0, now - deadline) / interval), slots - slot)
        missed += skipped
        slot += skipped
        if slot >= slots:
            break
        before = time.perf_counter()
        payload = controller.render_dmx(now - started)
        elapsed = time.perf_counter() - before
        if len(payload) != 512 or any(payload[index] for index in unmapped):
            raise RuntimeError('invalid frame or nonzero unverified/unmapped channel')
        timings.append(elapsed * 1000)
        over_budget += elapsed > interval
        if slot % config.fps == 0:
            current_rss = resident_kib()
            if current_rss is not None:
                rss.append(current_rss)
            temperature = temperature_c()
            if temperature is not None:
                temperatures.append(temperature)
        slot += 1
    time.sleep(max(0, started + slots * interval - time.monotonic()))
    duration = time.monotonic() - started
    cpu_seconds = time.process_time() - cpu_started
    engine.set_blackout(True)
    if any(controller.render_dmx(duration)):
        raise RuntimeError('blackout did not produce a zero frame')
    ordered = sorted(timings)
    if not ordered:
        raise RuntimeError('no frames rendered')
    return {
        'kind': kind, 'id': look_id, 'frames': len(timings),
        'duration_s': round(duration, 3),
        'achieved_fps': round(len(timings) / duration, 3),
        'missed_slots': missed, 'over_budget_frames': over_budget,
        'render_mean_ms': round(statistics.mean(timings), 3),
        'render_p95_ms': round(ordered[math.ceil(len(ordered) * .95) - 1], 3),
        'render_max_ms': round(max(timings), 3),
        'process_cpu_percent_one_core': round(cpu_seconds / duration * 100, 2),
        'rss_first_kib': rss[0] if rss else None,
        'rss_last_kib': rss[-1] if rss else None,
        'rss_max_kib': max(rss) if rss else None,
        'temperature_max_c': max(temperatures) if temperatures else None,
        'unmapped_channels_zero': True, 'blackout_zero': True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds-per-look', type=float, default=30)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds_per_look) or args.seconds_per_look <= 0:
        parser.error('--seconds-per-look must be finite and positive')
    report = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'platform': platform.platform(), 'python': platform.python_version(),
        'mode': 'headless rendering; sockets blocked; no GUI or transport',
        'fps': 25, 'seconds_per_look': args.seconds_per_look, 'looks': [],
    }
    looks = [('effect', item.effect_id) for item in EFFECT_REGISTRY.metadata()]
    looks += [('preset', preset_id) for preset_id in PRESETS]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Guard both the transport constructor and all standard Python sockets.
    with patch('socket.socket', side_effect=RuntimeError('sockets forbidden in soak')):
        with patch('phreqed_dmx.app.ArtNetSender', side_effect=RuntimeError('live forbidden')):
            for kind, look_id in looks:
                result = run_look(kind, look_id, args.seconds_per_look)
                report['looks'].append(result)
                args.output.write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps(result), flush=True)
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    report['passed'] = all(
        item['missed_slots'] == 0 and item['over_budget_frames'] == 0
        for item in report['looks']
    )
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    if not report['passed']:
        raise SystemExit('soak completed with missed slots or render overruns')


if __name__ == '__main__':
    main()
