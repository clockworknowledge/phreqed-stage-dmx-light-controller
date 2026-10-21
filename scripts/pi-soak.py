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
import threading
import time
from unittest.mock import patch

from phreqed_dmx.app import Controller
from phreqed_dmx.config import load_config
from phreqed_dmx.effect_library import EFFECT_REGISTRY
from phreqed_dmx.engine import SceneEngine
from phreqed_dmx.presets import PRESETS


class FootProbeCommands:
    """Record mapped pedal actions without changing the rendered show."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts = {
            'previous_scene': 0,
            'next_scene': 0,
            'tap_tempo': 0,
            'blackout_on': 0,
            'blackout_off': 0,
        }

    def _record(self, action: str) -> None:
        with self._lock:
            self._counts[action] += 1

    def previous_scene(self) -> None:
        self._record('previous_scene')

    def next_scene(self) -> None:
        self._record('next_scene')

    def tap_tempo(self, timestamp: float | None = None) -> float:
        self._record('tap_tempo')
        return 120.0

    def blackout(self, enabled: bool = True) -> None:
        self._record('blackout_on' if enabled else 'blackout_off')

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


MINIMUM_FOOT_ACTIONS = {
    'previous_scene': 1,
    'next_scene': 1,
    'tap_tempo': 2,
    'blackout_on': 1,
    'blackout_off': 1,
}


def foot_control_passed(
    actions: dict[str, int],
    events: list[str],
    status: object | None,
    *,
    require_actions: bool,
) -> bool:
    """Accept recovered reconnects but reject a lost device or command failure."""

    if status is None:
        return not require_actions
    if not bool(getattr(status, 'running', False)):
        return False
    if not bool(getattr(status, 'connected', False)):
        return False
    if any(event.startswith('Foot action ') for event in events):
        return False
    return not require_actions or all(
        actions.get(action, 0) >= minimum
        for action, minimum in MINIMUM_FOOT_ACTIONS.items()
    )


def foot_status_data(status: object | None) -> dict[str, object] | None:
    if status is None:
        return None
    return {
        key: getattr(status, key)
        for key in (
            'running', 'connected', 'message', 'messages_received', 'reconnects'
        )
    }


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


def run_look(
    kind: str,
    look_id: str,
    seconds: float,
    *,
    audio_source: object | None = None,
) -> dict[str, object]:
    config = load_config()
    if config.fps != 25:
        raise ValueError('Pi commissioning requires the configured 25 FPS')
    engine = SceneEngine(config.fixtures)
    if kind == 'effect':
        for fixture in config.fixtures:
            engine.select_effect(fixture.name, look_id)
    else:
        engine.activate_preset(look_id)
    controller = Controller(config, engine, audio_source=audio_source)
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
    audio_loudness = []
    audio_onset = []
    audio_status = getattr(audio_source, 'status', None)
    audio_chunks_before = (
        audio_status().chunks_processed if callable(audio_status) else None
    )
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
        if audio_source is not None:
            analysis = audio_source.sample(now - started)
            audio_loudness.append(analysis.loudness)
            audio_onset.append(analysis.onset)
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
    result = {
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
    if callable(audio_status):
        status = audio_status()
        result['audio'] = {
            'running': status.running,
            'healthy': status.healthy,
            'message': status.message,
            'chunks_processed': status.chunks_processed - audio_chunks_before,
            'loudness_peak': round(max(audio_loudness, default=0.0), 4),
            'onset_peak': round(max(audio_onset, default=0.0), 4),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds-per-look', type=float, default=30)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audio-device', help='explicit ALSA capture device')
    parser.add_argument('--audio-sensitivity', type=float, default=12.0)
    parser.add_argument('--foot-midi-device', type=Path, help='explicit ALSA raw-MIDI device')
    parser.add_argument('--foot-midi-channel', type=int, default=1)
    parser.add_argument(
        '--require-foot-actions',
        action='store_true',
        help='fail unless FS1/FS2/FS3 twice and both FS4 states are observed',
    )
    args = parser.parse_args()
    if not math.isfinite(args.seconds_per_look) or args.seconds_per_look <= 0:
        parser.error('--seconds-per-look must be finite and positive')
    if not math.isfinite(args.audio_sensitivity) or not 0.1 <= args.audio_sensitivity <= 40:
        parser.error('--audio-sensitivity must be between 0.1 and 40')
    if not 1 <= args.foot_midi_channel <= 16:
        parser.error('--foot-midi-channel must be between 1 and 16')
    if args.require_foot_actions and args.foot_midi_device is None:
        parser.error('--require-foot-actions requires --foot-midi-device')
    report = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'platform': platform.platform(), 'python': platform.python_version(),
        'mode': 'headless rendering; sockets blocked; no GUI or Art-Net transport',
        'fps': 25, 'seconds_per_look': args.seconds_per_look, 'looks': [],
        'audio_device': args.audio_device,
        'foot_midi_device': str(args.foot_midi_device) if args.foot_midi_device else None,
    }
    looks = [('effect', item.effect_id) for item in EFFECT_REGISTRY.metadata()]
    looks += [('preset', preset_id) for preset_id in PRESETS]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio_source = None
    foot_controller = None
    foot_probe = FootProbeCommands()
    foot_events: list[str] = []
    foot_final_status = None
    try:
        if args.audio_device:
            from phreqed_dmx.audio_capture import ArecordAudioSource

            audio_source = ArecordAudioSource(
                args.audio_device, sensitivity=args.audio_sensitivity
            )
            audio_source.start()
        if args.foot_midi_device:
            from phreqed_dmx.foot_control import RawMidiFootController

            foot_controller = RawMidiFootController(
                args.foot_midi_device,
                foot_probe,
                channel=args.foot_midi_channel,
                on_error=foot_events.append,
            )
            foot_controller.start()
        # Guard both the transport constructor and all standard Python sockets.
        with patch('socket.socket', side_effect=RuntimeError('sockets forbidden in soak')):
            with patch('phreqed_dmx.app.ArtNetSender', side_effect=RuntimeError('live forbidden')):
                for kind, look_id in looks:
                    result = run_look(
                        kind,
                        look_id,
                        args.seconds_per_look,
                        audio_source=audio_source,
                    )
                    report['looks'].append(result)
                    args.output.write_text(json.dumps(report, indent=2) + '\n')
                    print(json.dumps(result), flush=True)
    finally:
        if foot_controller is not None:
            foot_final_status = foot_controller.status()
            foot_controller.close()
        report['foot_actions'] = foot_probe.snapshot()
        report['foot_events'] = foot_events
        report['foot_errors'] = [
            event for event in foot_events if event.startswith('Foot action ')
        ]
        report['foot_final_status'] = foot_status_data(foot_final_status)
        if audio_source is not None:
            report['audio_final_status'] = {
                key: getattr(audio_source.status(), key)
                for key in ('running', 'healthy', 'message', 'chunks_processed')
            }
            audio_source.close()
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    render_passed = all(
        item['missed_slots'] == 0 and item['over_budget_frames'] == 0
        for item in report['looks']
    )
    audio_passed = audio_source is None or all(
        item.get('audio', {}).get('running')
        and item.get('audio', {}).get('healthy')
        and item.get('audio', {}).get('chunks_processed', 0) > 0
        for item in report['looks']
    )
    foot_passed = foot_control_passed(
        report['foot_actions'],
        foot_events,
        foot_final_status,
        require_actions=args.require_foot_actions,
    )
    report['checks'] = {
        'render_timing': render_passed,
        'audio_capture': audio_passed,
        'foot_control': foot_passed,
    }
    report['passed'] = all(report['checks'].values())
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    if not report['passed']:
        raise SystemExit(f"soak failed: {report['checks']}")


if __name__ == '__main__':
    main()
