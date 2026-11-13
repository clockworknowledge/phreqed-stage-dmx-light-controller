#!/usr/bin/env python3
"""Perform one fixed, root-managed NetworkManager action for the local kiosk."""

from __future__ import annotations

import argparse
import os
import subprocess


ACTIONS = ('stage', 'wifi', 'enable-stage', 'disable-stage')


def nmcli(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ('/usr/bin/nmcli', *arguments),
        check=check,
        timeout=30.0,
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def connection_names() -> set[str]:
    result = nmcli('-t', '-f', 'NAME', 'connection', 'show')
    return {line for line in result.stdout.splitlines() if line}


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    args = parser.parse_args(argv)
    hotspot = os.environ.get('PHREQED_HOTSPOT_CONNECTION', 'phreqed-stage-ap')
    names = connection_names()
    if hotspot not in names:
        raise RuntimeError(f'configured stage hotspot does not exist: {hotspot}')
    if args.action == 'stage':
        nmcli('connection', 'up', hotspot)
    elif args.action == 'wifi':
        wifi = os.environ.get('PHREQED_WIFI_CONNECTION', '').strip()
        if not wifi or wifi == hotspot or wifi not in names:
            raise RuntimeError('PHREQED_WIFI_CONNECTION must name a saved non-hotspot profile')
        nmcli('connection', 'down', hotspot, check=False)
        nmcli('connection', 'up', wifi)
    elif args.action == 'enable-stage':
        nmcli('connection', 'modify', hotspot, 'connection.autoconnect', 'yes')
        nmcli('connection', 'modify', hotspot, 'connection.autoconnect-priority', '100')
    else:
        nmcli('connection', 'modify', hotspot, 'connection.autoconnect', 'no')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
