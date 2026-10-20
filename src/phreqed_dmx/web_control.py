"""Local browser control. HTTP preview sockets never imply Art-Net output."""
from __future__ import annotations

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import secrets
import signal
import threading
import time
from urllib.parse import urlsplit

from .artnet import ArtNetSender
from .app import Controller
from .compositor import black_scene
from .effect_library import EFFECT_REGISTRY
from .library import UserLibrary, number, object_fields, parse_preset, preset_data
from .presets import PRESETS
from .render import compose_dmx

ASSETS = Path(__file__).with_name('web')


class BrowserControl:
    """One serialized engine and one optional sender shared by every browser."""
    def __init__(self, controller: Controller, library_path: Path, *, allow_live: bool = False) -> None:
        self.controller = controller
        self.engine = controller.engine
        self.library = UserLibrary(library_path, tuple(self.engine.geometry))
        self.engine.presets = self.library.all_presets
        self.engine.preset_order = tuple(self.engine.presets)
        self.controller.scenes.replace(self.library.cues)
        self.engine.set_global_brightness(0.25)
        self.allow_live = allow_live
        self.sender: ArtNetSender | None = None
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.started = time.monotonic()
        self.lease_deadline = 0.0
        self.error = ''
        self.notice = ''
        self.frames = black_scene(self.engine.geometry)
        self.thread: threading.Thread | None = None

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def catalog(self) -> dict:
        return dict(effects=[asdict(m) for m in EFFECT_REGISTRY.metadata()],
                    presets=[{**preset_data(p), 'builtin': p.preset_id in PRESETS}
                             for p in self.library.all_presets.values()], library=self.library.document())

    def state(self) -> dict:
        with self.lock:
            scenes = self.controller.scenes
            return dict(live_allowed=self.allow_live, live=self.sender is not None,
                        blackout=self.engine.blackout_enabled, error=self.error, notice=self.notice,
                        preset_id=self.engine.active_preset_id, playing=scenes.playing,
                        active_name=self.engine.presets[self.engine.active_preset_id].name,
                        scene_index=scenes.index, tempo=self.controller.show.context().tempo_bpm,
                        brightness=self.engine.compositor.global_brightness,
                        frames={name: [[[round(c.red * 255), round(c.green * 255), round(c.blue * 255)]
                                        for c in row] for row in grid.rows()]
                                for name, grid in self.frames.items()})

    def _sync_library(self) -> None:
        self.engine.presets = self.library.all_presets
        self.engine.preset_order = tuple(self.engine.presets)
        if self.engine.active_preset_id not in self.engine.presets:
            self.engine.activate_preset(next(iter(PRESETS)))
        self.controller.scenes.replace(self.library.cues)

    def _stop_live(self) -> None:
        sender, self.sender = self.sender, None
        if sender is not None:
            sender.close()

    def command(self, raw: object) -> None:
        data = object_fields(raw, {'action'}, {'value', 'preset', 'scenes', 'index'})
        action = data['action']
        with self.lock:
            elapsed = self.elapsed()
            scenes = self.controller.scenes
            if action == 'heartbeat':
                self.lease_deadline = time.monotonic() + 5
            elif action == 'blackout':
                self.engine.set_blackout(True)
                scenes.playing = False
                self.controller._transition_from = None
                self.frames = black_scene(self.engine.geometry)
                if self.sender is not None:
                    try:
                        self.sender.blackout()
                    except OSError:
                        self._stop_live()
                        raise
            elif action == 'resume':
                self.engine.set_blackout(False)
            elif action == 'start_live':
                if not self.allow_live:
                    raise ValueError('simulation cannot start live output; restart with live --web')
                if self.error:
                    raise ValueError('restart the controller after a rendering failure')
                if self.sender is None:
                    self.engine.set_global_brightness(min(0.25, self.engine.compositor.global_brightness))
                    config = self.controller.config
                    self.sender = ArtNetSender(config.artnet_host, config.artnet_port, config.universe)
                    self.lease_deadline = time.monotonic() + 5
                    self.notice = ''
            elif action == 'stop_live':
                self.engine.set_blackout(True)
                scenes.playing = False
                self._stop_live()
            elif action == 'brightness':
                self.engine.set_global_brightness(number(data.get('value'), 'brightness', 0, 0.65))
            elif action == 'preset':
                preset_id = data.get('value')
                if not isinstance(preset_id, str) or preset_id not in self.engine.presets:
                    raise ValueError('unknown preset')
                self.controller.begin_transition(elapsed, duration=0.8)
                scenes.playing = False
                scenes.index = None
                self.engine.global_brightness_override = None
                self.engine.activate_preset(preset_id)
            elif action in ('preview', 'save_preset'):
                preset = parse_preset(data.get('preset'), tuple(self.engine.geometry))
                if action == 'save_preset':
                    document = self.library.document()
                    document['presets'] = [p for p in document['presets'] if p['preset_id'] != preset.preset_id]
                    document['presets'].append(preset_data(preset))
                    self.library.save(document)
                    self._sync_library()
                else:
                    self.controller.begin_transition(elapsed, duration=0.8)
                    # Draft is deliberately excluded from the persistent library.
                    from dataclasses import replace

                    preset = replace(preset, preset_id='user-preview-draft')
                    self.engine.presets[preset.preset_id] = preset
                    self.engine.global_brightness_override = None
                    self.engine.activate_preset(preset.preset_id)
                    scenes.playing = False
                    scenes.index = None
            elif action == 'delete_preset':
                preset_id = data.get('value')
                if not isinstance(preset_id, str) or preset_id not in self.library.presets:
                    raise ValueError('only saved user presets can be deleted')
                document = self.library.document()
                document['presets'] = [p for p in document['presets'] if p['preset_id'] != preset_id]
                self.library.save(document)
                self._sync_library()
            elif action == 'save_scenes':
                document = self.library.document()
                document['scenes'] = data.get('scenes')
                self.library.save(document)
                self._sync_library()
            elif action == 'select_scene':
                scenes.select(data.get('index'), elapsed)
            elif action in ('next_scene', 'previous_scene'):
                scenes.move(1 if action == 'next_scene' else -1, elapsed)
            elif action == 'play':
                if self.engine.blackout_enabled:
                    raise ValueError('release blackout before starting the scene list')
                scenes.play(elapsed)
            elif action == 'pause':
                scenes.playing = False
            elif action == 'tap':
                self.controller.show.tap_tempo()
            else:
                raise ValueError('unknown action')

    def step(self, now: float | None = None) -> None:
        with self.lock:
            now = time.monotonic() if now is None else now
            if self.sender is not None and now >= self.lease_deadline:
                self.engine.set_blackout(True)
                self.controller.scenes.playing = False
                self._stop_live()
                self.notice = 'Browser connection lost. Output stopped with blackout; start it explicitly to resume.'
            self.frames = self.controller.render_scene(now - self.started)
            if self.sender is not None:
                self.sender.send(compose_dmx(self.controller.config.fixtures, self.frames))

    def start(self) -> None:
        def run() -> None:
            interval = 1 / self.controller.config.fps
            deadline = time.monotonic()
            while not self.stop_event.is_set():
                try:
                    self.step()
                except Exception as exc:
                    with self.lock:
                        self.error = f'Output stopped: {exc}'
                        self.engine.set_blackout(True)
                        self.controller.scenes.playing = False
                        self.frames = black_scene(self.engine.geometry)
                        self._stop_live()
                    return
                deadline += interval
                # Skip late slots instead of sending a catch-up burst.
                if deadline < time.monotonic():
                    deadline = time.monotonic() + interval
                self.stop_event.wait(max(0, deadline - time.monotonic()))
        self.thread = threading.Thread(target=run, name='phreqed-render', daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=3)
        with self.lock:
            self._stop_live()


class ControlServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], control: BrowserControl, allow_network: str) -> None:
        self.network = ipaddress.ip_network(allow_network, strict=True)
        if self.network.version != 4 or self.network.prefixlen < 8:
            raise ValueError('allow-network must be a specific trusted IPv4 network')
        self.control = control
        self.token = secrets.token_urlsafe(32)
        super().__init__(address, ControlHandler)

    def verify_request(self, request: object, client_address: tuple) -> bool:
        address = ipaddress.ip_address(client_address[0])
        return address.is_loopback or address in self.network


class ControlHandler(BaseHTTPRequestHandler):
    server: ControlServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format: str, *args: object) -> None:
        pass

    def reply(self, status: int, body: bytes, content_type: str = 'application/json') -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self) -> bool:
        try:
            host = urlsplit('http://' + self.headers.get('Host', '')).hostname
            if host in ('localhost', 'raspberrypi', 'raspberrypi.local'):
                return True
            return ipaddress.ip_address(host) == ipaddress.ip_address(self.connection.getsockname()[0])
        except (ValueError, TypeError):
            return False

    def do_GET(self) -> None:
        if not self.valid_host():
            self.reply(403, b'{"error":"unrecognized host"}')
            return
        path = urlsplit(self.path).path
        if path == '/api/state':
            self.reply(200, json.dumps(self.server.control.state()).encode())
        elif path == '/api/catalog':
            with self.server.control.lock:
                self.reply(200, json.dumps(self.server.control.catalog()).encode())
        elif path == '/api/session':
            self.reply(200, json.dumps({'token': self.server.token}).encode())
        elif path in ('/', '/app.js', '/style.css', '/fixture.css'):
            name = 'index.html' if path == '/' else path[1:]
            content_type = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8',
                            'style.css': 'text/css; charset=utf-8',
                            'fixture.css': 'text/css; charset=utf-8'}[name]
            self.reply(200, (ASSETS / name).read_bytes(), content_type)
        elif path == '/favicon.ico':
            self.reply(204, b'', 'image/x-icon')
        else:
            self.reply(404, b'{"error":"not found"}')

    def do_POST(self) -> None:
        origin = self.headers.get('Origin')
        if (not self.valid_host() or self.headers.get('X-Control-Token') != self.server.token
                or (origin is not None and origin != 'http://' + self.headers.get('Host', ''))):
            self.reply(403, b'{"error":"reload this controller page"}')
            return
        if self.path != '/api/command':
            self.reply(404, b'{"error":"not found"}')
            return
        try:
            if self.headers.get('Content-Type') != 'application/json':
                raise ValueError('expected application/json')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1_000_000:
                raise ValueError('request must be between 1 byte and 1 MB')
            data = json.loads(self.rfile.read(length))
            self.server.control.command(data)
            self.reply(200, b'{"ok":true}')
        except (ValueError, TypeError, KeyError) as exc:
            self.reply(400, json.dumps({'error': str(exc)}).encode())
        except OSError:
            self.reply(500, b'{"error":"storage or output failed; check the Pi"}')


def serve(controller: Controller, library_path: Path, *, host: str = '127.0.0.1', port: int = 8080,
          allow_network: str = '192.168.1.0/24', allow_live: bool = False) -> None:
    if not 1 <= port <= 65535:
        raise ValueError('browser port must be between 1 and 65535')
    if controller.config.fps > 25:
        raise ValueError('browser control requires an output rate at or below 25 FPS')
    control = BrowserControl(controller, library_path, allow_live=allow_live)
    server = ControlServer((host, port), control, allow_network)
    previous_term = signal.getsignal(signal.SIGTERM)
    def interrupted(signum: int, frame: object) -> None:
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    print(f'Phreqed browser: http://{host}:{port} — simulation active; output stopped', flush=True)
    control.start()
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        control.close()
        server.server_close()
        signal.signal(signal.SIGTERM, previous_term)
