"""Loopback-only browser shell for the local Phreqed Studio foundation."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse

from .studio_catalog import StoryletMarker, StudioCatalog


MAX_REQUEST_BYTES = 64_000
WEB_ROOT = Path(__file__).with_name("studio_web")
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


class StudioController:
    def __init__(self, catalog: StudioCatalog) -> None:
        self.catalog = catalog

    def state(self) -> dict:
        return self.catalog.state()

    def command(self, value: object) -> dict:
        if not isinstance(value, dict) or not isinstance(value.get("action"), str):
            raise ValueError("Studio command requires an action")
        action = value["action"]
        if action == "import_asset":
            if set(value) != {"action", "path", "title", "family"}:
                raise ValueError("import_asset fields are invalid")
            asset = self.catalog.import_asset(
                Path(value["path"]),
                title=value["title"] or None,
                family=value["family"],
            )
            return {"ok": True, "asset": asset.as_dict(), "state": self.state()}
        if action == "create_storylet":
            if set(value) != {
                "action",
                "storylet_id",
                "asset_id",
                "title",
                "duration_seconds",
                "loop",
                "markers",
            }:
                raise ValueError("create_storylet fields are invalid")
            if not isinstance(value["markers"], list):
                raise ValueError("storylet markers must be a list")
            storylet = self.catalog.create_storylet(
                storylet_id=value["storylet_id"],
                asset_id=value["asset_id"],
                title=value["title"],
                duration_seconds=value["duration_seconds"],
                loop=value["loop"],
                markers=(StoryletMarker(**marker) for marker in value["markers"]),
            )
            return {
                "ok": True,
                "storylet": storylet.as_dict(),
                "state": self.state(),
            }
        if action == "export_graph":
            path = self.catalog.export_graph()
            return {"ok": True, "path": str(path), "state": self.state()}
        raise ValueError("unknown Studio command")


class StudioRequestHandler(BaseHTTPRequestHandler):
    controller: StudioController
    token: str
    expected_host: str

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _host_is_valid(self) -> bool:
        host = self.headers.get("Host", "")
        return host == self.expected_host or host in {
            f"localhost:{self.server.server_port}",
            f"127.0.0.1:{self.server.server_port}",
            f"[::1]:{self.server.server_port}",
        }

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        parsed = urlparse(origin)
        return parsed.scheme == "http" and parsed.netloc in {
            self.expected_host,
            f"localhost:{self.server.server_port}",
            f"127.0.0.1:{self.server.server_port}",
            f"[::1]:{self.server.server_port}",
        }

    def do_GET(self) -> None:
        if not self._host_is_valid():
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid Host header"})
            return
        path = urlparse(self.path).path
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/api/state":
            self._json(HTTPStatus.OK, self.controller.state())
            return
        selected = "index.html" if path == "/" else path.lstrip("/")
        if selected not in {"index.html", "studio.css", "studio.js"}:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        file_path = WEB_ROOT / selected
        try:
            body = file_path.read_bytes()
        except OSError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if selected == "index.html":
            body = body.replace(b"__STUDIO_TOKEN__", self.token.encode("ascii"))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", MIME_TYPES[file_path.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._host_is_valid() or not self._same_origin():
            self._json(HTTPStatus.FORBIDDEN, {"error": "request origin rejected"})
            return
        if self.headers.get("X-Phreqed-Studio-Token") != self.token:
            self._json(HTTPStatus.FORBIDDEN, {"error": "Studio token rejected"})
            return
        if urlparse(self.path).path != "/api/command":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_REQUEST_BYTES:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "request size is invalid"})
            return
        try:
            value = json.loads(self.rfile.read(length))
            result = self.controller.command(value)
        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, result)


def make_server(
    controller: StudioController,
    *,
    host: str = "127.0.0.1",
    port: int = 8090,
    token: str | None = None,
) -> ThreadingHTTPServer:
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("Studio host must be a loopback IP address") from exc
    if not address.is_loopback:
        raise ValueError("Studio currently binds to loopback only")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("Studio port is invalid")
    selected_token = token or secrets.token_urlsafe(32)

    class BoundHandler(StudioRequestHandler):
        pass

    BoundHandler.controller = controller
    BoundHandler.token = selected_token
    server = ThreadingHTTPServer((host, port), BoundHandler)
    BoundHandler.expected_host = f"{host}:{server.server_port}"
    return server


def run_server(
    controller: StudioController,
    *,
    host: str = "127.0.0.1",
    port: int = 8090,
) -> None:
    server = make_server(controller, host=host, port=port)
    print(f"Phreqed Studio: http://{host}:{server.server_port}")
    print(f"Workspace: {controller.catalog.root}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
