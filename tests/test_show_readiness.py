from __future__ import annotations

import runpy
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "show-readiness.py"),
    run_name="show_readiness",
)
assess_state = SCRIPT["assess_state"]
stage_lan_check = SCRIPT["stage_lan_check"]


def safe_state() -> dict[str, object]:
    return {
        "live": False,
        "performance": {
            "mode": "manual",
            "state": "inactive",
            "running": False,
        },
        "audio": {"enabled": True, "running": True, "healthy": True},
        "foot_control": {
            "enabled": True,
            "running": True,
            "connected": True,
            "messages_received": 1,
        },
    }


class ShowReadinessTests(unittest.TestCase):
    def test_safe_startup_with_required_peripherals_passes(self) -> None:
        results = assess_state(
            safe_state(), startup_defaults=True,
            require_audio=True, require_foot_event=True,
        )
        self.assertNotIn("FAIL", [level for level, _ in results])

    def test_active_output_and_running_timeline_fail_startup(self) -> None:
        state = safe_state()
        state["live"] = True
        state["performance"] = {
            "mode": "setlist", "state": "running", "running": True,
        }
        results = assess_state(
            state, startup_defaults=True,
            require_audio=False, require_foot_event=False,
        )
        self.assertEqual([level for level, _ in results].count("FAIL"), 2)

    def test_missing_optional_peripherals_warn_but_required_fail(self) -> None:
        state = safe_state()
        state["audio"] = {"enabled": False}
        state["foot_control"] = {"enabled": True, "connected": False}
        optional = assess_state(
            state, startup_defaults=False,
            require_audio=False, require_foot_event=False,
        )
        required = assess_state(
            state, startup_defaults=False,
            require_audio=True, require_foot_event=True,
        )
        self.assertEqual([level for level, _ in optional].count("WARN"), 2)
        self.assertEqual([level for level, _ in required].count("FAIL"), 2)

    def test_stage_lan_accepts_ap_or_router_address(self) -> None:
        for address in ("10.42.0.1/24", "10.42.0.2/24"):
            completed = type("Completed", (), {
                "returncode": 0,
                "stdout": f"2: wlan0 inet {address} scope global wlan0\n",
            })()
            with self.subTest(address=address), patch.dict(
                stage_lan_check.__globals__, {"command": lambda *args: completed}
            ):
                self.assertEqual(stage_lan_check()[0], "PASS")


if __name__ == "__main__":
    unittest.main()
