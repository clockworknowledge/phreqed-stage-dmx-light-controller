#!/usr/bin/env python3
"""Fixed, low-brightness corner check; defaults to offline validation."""

from __future__ import annotations

import argparse
import time

from phreqed_dmx.artnet import ArtNetSender
from phreqed_dmx.color import NormalizedRGB
from phreqed_dmx.compositor import Compositor, FrameSafetyLimiter, Layer, black_scene
from phreqed_dmx.config import load_config
from phreqed_dmx.render import compose_dmx


def validated_steps() -> list[tuple[str, bytes]]:
    config = load_config()
    actual = tuple(
        (f.name, f.start_address, f.channel_count, f.width, f.height)
        for f in config.fixtures
    )
    if actual != (('Cube A', 1, 152, 8, 6), ('Cube B', 153, 152, 8, 6)):
        raise ValueError('corner check requires confirmed A001/A153 8x6 fixtures')
    if (config.artnet_host, config.artnet_port, config.universe, config.fps) != (
        '127.0.0.1', 6454, 0, 25
    ):
        raise ValueError('corner check requires localhost universe 0 at 25 FPS')
    geometry = {f.name: (f.width, f.height) for f in config.fixtures}
    compositor = Compositor(global_brightness=0.25)
    limiter = FrameSafetyLimiter()
    steps = []
    for name, base in (('Cube A', 0), ('Cube B', 152)):
        for label, coordinate, color, expected_offset in (
            ('RED top-left', (0, 0), NormalizedRGB(1, 0, 0), base + 141),
            ('BLUE bottom-right', (7, 5), NormalizedRGB(0, 0, 1), base + 2),
        ):
            scene = black_scene(geometry)
            scene[name][coordinate] = color
            scene = compositor.compose(geometry, (Layer(scene),))
            scene = limiter.apply(scene, len(steps) * 6.0)
            payload = compose_dmx(config.fixtures, scene)
            # Independent expected offsets verify orientation and isolation.
            expected = bytearray(512)
            expected[expected_offset] = 64
            if payload != bytes(expected):
                raise ValueError('corner mapping, isolation, or brightness check failed')
            steps.append((f'{name}: {label}; other cube DARK', payload))
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=('simulate', 'live'), default='simulate')
    args = parser.parse_args()
    steps = validated_steps()
    if args.command == 'simulate':
        for label, payload in steps:
            print(f'OFFLINE: {label}; channel {[i + 1 for i, v in enumerate(payload) if v]} = 64')
        print('All four frames verified. No socket created.')
        return
    try:
        with ArtNetSender('127.0.0.1', 6454, 0) as sender:
            for label, payload in steps:
                print(f'LIVE, 5 seconds: {label}', flush=True)
                started = time.monotonic()
                for index in range(125):
                    sender.send(payload)
                    time.sleep(max(0, started + (index + 1) / 25 - time.monotonic()))
                print('BLACKOUT, 1 second', flush=True)
                started = time.monotonic()
                for index in range(25):
                    sender.blackout()
                    time.sleep(max(0, started + (index + 1) / 25 - time.monotonic()))
    except KeyboardInterrupt:
        print('Interrupted; sender shutdown requested blackout.', flush=True)
        return
    print('Complete; sender shutdown requested final blackout.', flush=True)


if __name__ == '__main__':
    main()
