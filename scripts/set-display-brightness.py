#!/usr/bin/env python3
"""Set a validated percentage on the first Raspberry Pi backlight device."""

from __future__ import annotations

import argparse
from pathlib import Path


LEVELS = (20, 40, 60, 80, 100)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('percent', type=int, choices=LEVELS)
    args = parser.parse_args(argv)
    devices = sorted(Path('/sys/class/backlight').glob('*'))
    if not devices:
        raise RuntimeError('no Linux backlight device was found')
    device = devices[0]
    maximum = int((device / 'max_brightness').read_text().strip())
    target = max(1, round(maximum * args.percent / 100))
    (device / 'brightness').write_text(f'{target}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
