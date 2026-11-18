from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from phreqed_dmx.studio_catalog import StudioCatalog
from phreqed_dmx.studio_web import StudioController, make_server


class StudioWebTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.source = root / "clip.mp4"
        self.source.write_bytes(b"fake-video-for-catalog-only")
        self.controller = StudioController(StudioCatalog(root / "workspace"))
        self.token = "test-studio-token"
        self.server = make_server(self.controller, port=0, token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def get(self, path: str):
        return urlopen(f"{self.base}{path}", timeout=3)

    def post(self, value: dict, *, token: str | None = None, origin: str | None = None):
        headers = {
            "Content-Type": "application/json",
            "X-Phreqed-Studio-Token": self.token if token is None else token,
        }
        if origin is not None:
            headers["Origin"] = origin
        request = Request(
            f"{self.base}/api/command",
            data=json.dumps(value).encode(),
            headers=headers,
            method="POST",
        )
        return urlopen(request, timeout=3)

    def test_serves_studio_shell_css_and_empty_state(self) -> None:
        with self.get("/") as response:
            html = response.read().decode()
        self.assertIn("Phreqed Studio", html)
        self.assertIn(self.token, html)
        self.assertIn("Storylets", html)
        with self.get("/studio.css") as response:
            self.assertEqual(response.headers.get_content_type(), "text/css")
        with self.get("/api/state") as response:
            state = json.load(response)
        self.assertEqual(state["assets"], [])
        self.assertEqual(state["graph"]["nodes"], 1)

    def test_import_storylet_and_graph_export_through_api(self) -> None:
        with self.post(
            {
                "action": "import_asset",
                "path": str(self.source),
                "title": "Reference clip",
                "family": "primary-clip",
            },
            origin=self.base,
        ) as response:
            imported = json.load(response)
        asset_id = imported["asset"]["asset_id"]
        with self.post(
            {
                "action": "create_storylet",
                "storylet_id": "storylet-reference-v1",
                "asset_id": asset_id,
                "title": "Reference",
                "duration_seconds": 12.0,
                "loop": False,
                "markers": [
                    {"name": "reveal", "at_seconds": 1.0},
                    {"name": "black", "at_seconds": 12.0},
                ],
            },
            origin=self.base,
        ) as response:
            created = json.load(response)
        self.assertEqual(created["storylet"]["asset_id"], asset_id)
        with self.post({"action": "export_graph"}, origin=self.base) as response:
            exported = json.load(response)
        self.assertTrue(Path(exported["path"]).is_file())
        self.assertGreater(exported["state"]["graph"]["relationships"], 0)

    def test_rejects_bad_token_origin_remote_binding_and_unknown_action(self) -> None:
        with self.assertRaises(HTTPError) as bad_token:
            self.post({"action": "export_graph"}, token="wrong")
        self.assertEqual(bad_token.exception.code, 403)
        with self.assertRaises(HTTPError) as bad_origin:
            self.post({"action": "export_graph"}, origin="https://example.com")
        self.assertEqual(bad_origin.exception.code, 403)
        with self.assertRaisesRegex(ValueError, "loopback"):
            make_server(self.controller, host="0.0.0.0", port=0)
        with self.assertRaises(HTTPError) as unknown:
            self.post({"action": "shell"}, origin=self.base)
        self.assertEqual(unknown.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
