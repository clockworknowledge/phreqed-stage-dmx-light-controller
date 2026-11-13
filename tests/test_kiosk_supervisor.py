import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "kiosk-supervisor.py"
SPEC = importlib.util.spec_from_file_location("phreqed_kiosk_supervisor", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
kiosk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kiosk)


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class KioskSupervisorTests(unittest.TestCase):
    def test_native_heartbeat_claims_local_named_lease(self) -> None:
        with patch.object(kiosk, "urlopen", return_value=Response()) as open_url:
            kiosk.renew_lease("http://127.0.0.1:8080", "secret", "local-kiosk")

        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/command")
        self.assertEqual(
            json.loads(request.data),
            {
                "action": "heartbeat",
                "lease_id": "local-kiosk",
                "lease_kind": "local",
            },
        )
        self.assertEqual(request.get_header("X-control-token"), "secret")
        self.assertEqual(request.get_header("Origin"), "http://127.0.0.1:8080")

    def test_supervisor_renews_only_while_chromium_lives(self) -> None:
        child = Mock(returncode=7)
        child.poll.side_effect = [None, 0, 0, 0]
        with (
            patch.object(kiosk, "wait_for_controller", return_value="secret"),
            patch.object(kiosk, "browser_path", return_value="/usr/bin/chromium"),
            patch.object(kiosk.subprocess, "Popen", return_value=child) as popen,
            patch.object(kiosk, "renew_lease") as renew,
            patch.object(kiosk.time, "sleep"),
            patch.object(kiosk.signal, "signal", return_value=None),
        ):
            result = kiosk.run(["--poll-seconds", "1"])

        self.assertEqual(result, 7)
        command = popen.call_args.args[0]
        self.assertIn("--kiosk", command)
        self.assertIn("--app=http://127.0.0.1:8080/?surface=kiosk", command)
        renew.assert_called_once_with(
            "http://127.0.0.1:8080", "secret", "local-kiosk"
        )
        child.terminate.assert_not_called()

    def test_poll_interval_is_bounded(self) -> None:
        for value in ("0.1", "4.1"):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "between 0.5 and 4.0"
            ):
                kiosk.run(["--poll-seconds", value])


if __name__ == "__main__":
    unittest.main()
