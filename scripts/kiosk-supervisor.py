#!/usr/bin/env python3
"""Own the optional local Chromium kiosk and its native trusted lease."""

from __future__ import annotations

import argparse
import json
import shutil
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument('--url', default='http://127.0.0.1:8080')
    value.add_argument('--browser')
    value.add_argument('--lease-id', default='local-kiosk')
    value.add_argument('--poll-seconds', type=float, default=2.0)
    return value


def browser_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in ('chromium', 'chromium-browser'):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError('Chromium was not found; headless controller remains available')


def session_token(base_url: str) -> str:
    with urlopen(f'{base_url.rstrip("/")}/api/session', timeout=2.0) as response:
        document = json.load(response)
    token = document.get('token')
    if not isinstance(token, str) or not token:
        raise RuntimeError('controller returned no session token')
    return token


def renew_lease(base_url: str, token: str, lease_id: str) -> None:
    body = json.dumps(dict(
        action='heartbeat', lease_id=lease_id, lease_kind='local'
    )).encode()
    request = Request(
        f'{base_url.rstrip("/")}/api/command',
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-Control-Token': token,
            'Origin': base_url.rstrip('/'),
        },
    )
    with urlopen(request, timeout=2.0) as response:
        if response.status != 200:
            raise RuntimeError('controller rejected the local display lease')


def wait_for_controller(base_url: str, stop: list[bool]) -> str:
    while not stop[0]:
        try:
            return session_token(base_url)
        except (OSError, RuntimeError, URLError, json.JSONDecodeError):
            time.sleep(2.0)
    raise KeyboardInterrupt


def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not 0.5 <= args.poll_seconds <= 4.0:
        raise ValueError('poll seconds must be between 0.5 and 4.0')
    stop = [False]

    def stopped(signum: int, frame: object) -> None:
        stop[0] = True

    previous_term = signal.signal(signal.SIGTERM, stopped)
    child: subprocess.Popen[bytes] | None = None
    try:
        token = wait_for_controller(args.url, stop)
        executable = browser_path(args.browser)
        kiosk_url = f'{args.url.rstrip("/")}/?surface=kiosk'
        child = subprocess.Popen(
            (
                executable,
                '--kiosk',
                '--noerrdialogs',
                '--disable-infobars',
                '--disable-session-crashed-bubble',
                f'--app={kiosk_url}',
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        while not stop[0] and child.poll() is None:
            try:
                renew_lease(args.url, token, args.lease_id)
            except HTTPError as exc:
                if exc.code == 403:
                    token = wait_for_controller(args.url, stop)
                else:
                    print(f'KIOSK LEASE WARNING: HTTP {exc.code}', file=sys.stderr)
            except (OSError, RuntimeError, URLError) as exc:
                print(f'KIOSK LEASE WARNING: {exc}', file=sys.stderr)
            time.sleep(args.poll_seconds)
        return child.returncode if child.poll() is not None else 0
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                child.kill()
        signal.signal(signal.SIGTERM, previous_term)


if __name__ == '__main__':
    raise SystemExit(run())
