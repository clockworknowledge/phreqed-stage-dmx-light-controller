#!/usr/bin/env python3
"""Steady, low-output LF4808 white-zone check; offline unless `live` is explicit."""

from __future__ import annotations

import argparse
import math
import time

from phreqed_dmx.artnet import ArtNetSender
from phreqed_dmx.config import load_config
from phreqed_dmx.render import compose_dmx, create_grids


def validated_steps(level: float = 0.05) -> list[tuple[str, bytes]]:
    if not math.isfinite(level) or not 0 < level <= 0.10:
        raise ValueError("white check level must be above zero and at most 0.10")
    config = load_config()
    actual = tuple(
        (fixture.name, fixture.start_address, fixture.channel_count,
         fixture.white_zone_count)
        for fixture in config.fixtures
    )
    if actual != (("Cube A", 1, 152, 8), ("Cube B", 153, 152, 8)):
        raise ValueError("white check requires confirmed A001/A153 LF4808 fixtures")
    if (config.artnet_host, config.artnet_port, config.universe, config.fps) != (
        "127.0.0.1", 6454, 0, 25
    ):
        raise ValueError("white check requires localhost universe 0 at 25 FPS")

    grids = create_grids(config.fixtures)
    steps: list[tuple[str, bytes]] = []
    for fixture in config.fixtures:
        for zone_number in range(1, fixture.white_zone_count + 1):
            levels = [0.0] * fixture.white_zone_count
            levels[zone_number - 1] = level
            payload = compose_dmx(
                config.fixtures,
                grids,
                white_zones={fixture.name: levels},
            )
            expected = bytearray(512)
            expected[fixture.white_offset(zone_number)] = round(level * 255)
            if payload != bytes(expected):
                raise ValueError("white-zone address, isolation, or level check failed")
            steps.append(
                (
                    f"{fixture.name}: white Part {zone_number}; all RGB and other white zones DARK",
                    payload,
                )
            )
    return steps


def _send_for(sender: ArtNetSender, payload: bytes, seconds: float) -> None:
    frames = math.ceil(seconds * 25)
    started = time.monotonic()
    for index in range(frames):
        sender.send(payload)
        time.sleep(max(0, started + (index + 1) / 25 - time.monotonic()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("simulate", "live"), default="simulate")
    parser.add_argument("--level", type=float, default=0.05, help="steady level, maximum 0.10")
    parser.add_argument("--hold", type=float, default=3.0, help="seconds per white zone")
    parser.add_argument("--blackout", type=float, default=0.75, help="dark seconds between zones")
    args = parser.parse_args()
    if not math.isfinite(args.hold) or args.hold < 0.5:
        parser.error("--hold must be finite and at least 0.5 seconds")
    if not math.isfinite(args.blackout) or args.blackout < 0.5:
        parser.error("--blackout must be finite and at least 0.5 seconds")
    try:
        steps = validated_steps(args.level)
    except ValueError as exc:
        parser.error(str(exc))

    if args.command == "simulate":
        for label, payload in steps:
            active = [(index + 1, value) for index, value in enumerate(payload) if value]
            print(f"OFFLINE: {label}; DMX {active}")
        print("All 16 steady frames verified. No socket created.")
        return

    print(
        "LIVE WHITE-ZONE COMMISSIONING: steady output only; maximum 10%; no flashing",
        flush=True,
    )
    try:
        with ArtNetSender("127.0.0.1", 6454, 0) as sender:
            for label, payload in steps:
                print(f"LIVE: {label}", flush=True)
                _send_for(sender, payload, args.hold)
                print("BLACKOUT", flush=True)
                _send_for(sender, bytes(512), args.blackout)
    except KeyboardInterrupt:
        print("Interrupted; sender shutdown requested blackout.", flush=True)
        return
    print("Complete; sender shutdown requested final blackout.", flush=True)


if __name__ == "__main__":
    main()
