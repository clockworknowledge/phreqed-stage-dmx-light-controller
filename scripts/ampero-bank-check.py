#!/usr/bin/env python3
"""Verify one Ampero performance bank without DMX or network output."""

from __future__ import annotations

import argparse
import sys
import threading
import time

from phreqed_dmx.foot_control import RawMidiFootController


REQUIRED = {
    "previous_scene": 1,
    "next_scene": 1,
    "tap_tempo": 1,
    "blackout_on": 1,
    "blackout_off": 1,
}


class Probe:
    def __init__(self) -> None:
        self.counts = {name: 0 for name in REQUIRED}
        self.lock = threading.Lock()

    def record(self, name: str) -> None:
        with self.lock:
            self.counts[name] += 1
        print(f"received: {name}", flush=True)

    def previous_scene(self) -> None:
        self.record("previous_scene")

    def next_scene(self) -> None:
        self.record("next_scene")

    def tap_tempo(self, timestamp: float | None = None) -> float:
        self.record("tap_tempo")
        return 120.0

    def blackout(self, enabled: bool = True) -> None:
        self.record("blackout_on" if enabled else "blackout_off")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/snd/phreqed-ampero-midi")
    parser.add_argument("--channel", type=int, default=1)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--bank", default="current")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.seconds <= 0:
        raise SystemExit("--seconds must be positive")
    probe = Probe()
    events: list[str] = []
    controller = RawMidiFootController(
        args.device, probe, channel=args.channel, on_error=events.append
    )
    print(f"Checking Ampero bank {args.bank!r}; no Art-Net sender will be created.")
    print("Press FS1, FS2, FS3, then toggle FS4 on and off.")
    controller.start()
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline:
            if all(probe.counts[name] >= count for name, count in REQUIRED.items()):
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    status = controller.status()
    controller.close()
    missing = [name for name, count in REQUIRED.items() if probe.counts[name] < count]
    for event in events:
        print(f"device: {event}")
    print(f"counts: {probe.counts}")
    if missing or not status.connected:
        print(f"FAIL: bank {args.bank!r}; missing={missing}; status={status}")
        return 1
    print(f"PASS: bank {args.bank!r} emits the complete Phreqed mapping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
