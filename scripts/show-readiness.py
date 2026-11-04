#!/usr/bin/env python3
"""Read-only readiness checks for the commissioned Raspberry Pi show rig."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen


Result = tuple[str, str]


def command(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments, capture_output=True, text=True, check=False, timeout=10
    )


def get_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=5) as response:  # noqa: S310 - operator-selected local URL
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("state response is not an object")
    return payload


def service_check(name: str) -> Result:
    active = command("systemctl", "is-active", name)
    enabled = command("systemctl", "is-enabled", name)
    if active.returncode != 0:
        return "FAIL", f"{name} is not active ({active.stdout.strip() or active.stderr.strip()})"
    if enabled.returncode != 0:
        return "WARN", f"{name} is active but not enabled at boot"
    return "PASS", f"{name} is active and enabled"


def assess_state(
    state: dict[str, object], *, startup_defaults: bool,
    require_audio: bool, require_foot_event: bool,
) -> list[Result]:
    results: list[Result] = []
    if state.get("live"):
        results.append(("FAIL", "Art-Net output is active during readiness inspection"))
    else:
        results.append(("PASS", "fixture output is stopped"))

    performance = state.get("performance")
    if startup_defaults:
        safe = (
            isinstance(performance, dict)
            and performance.get("mode") == "manual"
            and performance.get("state") == "inactive"
            and performance.get("running") is False
        )
        results.append((
            "PASS" if safe else "FAIL",
            "startup defaults are Manual, inactive, and stopped"
            if safe else f"unsafe/unexpected startup performance state: {performance!r}",
        ))

    audio = state.get("audio")
    audio_ok = (
        isinstance(audio, dict)
        and audio.get("enabled") is True
        and audio.get("running") is True
        and audio.get("healthy") is True
    )
    if audio_ok:
        results.append(("PASS", "audio capture is enabled and healthy"))
    elif require_audio:
        results.append(("FAIL", f"required audio capture is not healthy: {audio!r}"))
    else:
        results.append(("WARN", "audio is unavailable; browser control remains usable"))

    foot = state.get("foot_control")
    foot_connected = (
        isinstance(foot, dict)
        and foot.get("enabled") is True
        and foot.get("running") is True
        and foot.get("connected") is True
    )
    messages_received = foot.get("messages_received", 0) if isinstance(foot, dict) else 0
    foot_event = (
        foot_connected
        and isinstance(messages_received, int)
        and messages_received > 0
    )
    if foot_event:
        results.append(("PASS", "Ampero is connected and has emitted a MIDI event"))
    elif require_foot_event:
        results.append(("FAIL", f"press a mapped Ampero switch before relying on foot control: {foot!r}"))
    elif foot_connected:
        results.append(("WARN", "Ampero is connected but no MIDI event has been observed"))
    else:
        results.append(("WARN", "Ampero is unavailable; use the browser control path"))
    return results


def stage_lan_check() -> Result:
    addresses = command("ip", "-4", "-o", "address", "show")
    if addresses.returncode != 0:
        return "FAIL", "could not inspect IPv4 addresses"
    if "10.42.0.1/24" in addresses.stdout:
        return "PASS", "Pi-hosted stage LAN is active at 10.42.0.1/24"
    if "10.42.0.2/24" in addresses.stdout:
        return "PASS", "dedicated-router stage LAN is active at 10.42.0.2/24"
    return "FAIL", "no commissioned 10.42.0.1/24 or 10.42.0.2/24 stage address found"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller-url", default="http://127.0.0.1:8080")
    parser.add_argument("--require-stage-lan", action="store_true")
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--require-foot-event", action="store_true")
    parser.add_argument("--startup-defaults", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    results = [service_check("qlcplus.service"), service_check("phreqed-dmx.service")]
    try:
        state = get_json(f"{args.controller_url.rstrip('/')}/api/state")
    except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        results.append(("FAIL", f"controller state endpoint is unavailable: {exc}"))
    else:
        results.append(("PASS", "controller state endpoint returned valid JSON"))
        results.extend(assess_state(
            state,
            startup_defaults=args.startup_defaults,
            require_audio=args.require_audio,
            require_foot_event=args.require_foot_event,
        ))
    if args.require_stage_lan:
        results.append(stage_lan_check())

    for level, message in results:
        print(f"{level:4}  {message}")
    failures = sum(level == "FAIL" for level, _ in results)
    warnings = sum(level == "WARN" for level, _ in results)
    print(f"\nReadiness: {len(results) - failures - warnings} passed, "
          f"{warnings} warnings, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
