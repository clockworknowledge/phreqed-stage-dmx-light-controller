"""Local browser control. HTTP preview sockets never imply Art-Net output."""
from __future__ import annotations

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import math
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
from .foot_control import RawMidiFootController
from .library import UserLibrary, number, object_fields, parse_preset, preset_data
from .presets import PRESETS
from .render import compose_dmx
from .white_output import (
    DEFAULT_WHITE_OUTPUT_LEVEL,
    MAX_WHITE_FLASH_HZ,
    MAX_WHITE_OUTPUT_CEILING,
    WHITE_OUTPUT_CEILING,
    WhitePeakLimiter,
    commissioned_white_levels,
)

ASSETS = Path(__file__).with_name('web')


class BrowserFootCommands:
    """Route pedal events through the browser controller's serialized commands."""

    def __init__(self, control: BrowserControl) -> None:
        self.control = control

    def previous_scene(self) -> None:
        self.control.command({'action': 'previous_scene'})

    def next_scene(self) -> None:
        self.control.command({'action': 'next_scene'})

    def tap_tempo(self, timestamp: float | None = None) -> float:
        self.control.command({'action': 'tap'})
        return self.control.controller.show.context().tempo_bpm

    def blackout(self, enabled: bool = True) -> None:
        self.control.command({'action': 'blackout' if enabled else 'resume'})


class BrowserControl:
    """One serialized engine and one optional sender shared by every browser."""
    def __init__(
        self,
        controller: Controller,
        library_path: Path,
        *,
        allow_live: bool = False,
        white_output_ceiling: float = WHITE_OUTPUT_CEILING,
    ) -> None:
        if (
            isinstance(white_output_ceiling, bool)
            or not isinstance(white_output_ceiling, (int, float))
            or not math.isfinite(white_output_ceiling)
            or not 0.0 < white_output_ceiling <= MAX_WHITE_OUTPUT_CEILING
        ):
            raise ValueError('white output ceiling must be above zero and at most 1.0')
        if white_output_ceiling > WHITE_OUTPUT_CEILING and not allow_live:
            raise ValueError('high-output whites require explicit live browser mode')
        self.controller = controller
        self.engine = controller.engine
        self.library = UserLibrary(library_path, tuple(self.engine.geometry))
        self.engine.presets = self.library.all_presets
        self.engine.preset_order = tuple(self.engine.presets)
        self.controller.scenes.replace(self.library.cues)
        # Never raise an explicit lower CLI limit when browser control starts.
        self.engine.set_global_brightness(
            min(
                0.25,
                self.engine.compositor.global_brightness,
                self.engine.compositor.maximum_brightness,
            )
        )
        self.allow_live = allow_live
        self.white_output_ceiling = float(white_output_ceiling)
        self.sender: ArtNetSender | None = None
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.started = time.monotonic()
        self.lease_deadline = 0.0
        self.error = ''
        self.notice = ''
        self.white_peak_preview = False
        self.white_preview_threshold = 0.65
        self.white_preview_level = 0.8
        self.white_preview_active_level = 0.0
        self.white_output_enabled = False
        self.white_output_level = DEFAULT_WHITE_OUTPUT_LEVEL
        self.white_output_active_level = 0.0
        self.white_peak_limiter = WhitePeakLimiter()
        self.foot_controller: RawMidiFootController | None = None
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
            source = self.controller.audio_source
            analysis = None
            if source is None:
                audio = dict(
                    enabled=False, running=False, healthy=False,
                    message='Audio input disabled', loudness=0.0, onset=0.0,
                    bass=0.0, mid=0.0, treble=0.0,
                )
            else:
                analysis = source.sample(self.elapsed())
                status_method = getattr(source, 'status', None)
                status = status_method() if callable(status_method) else None
                audio = dict(
                    enabled=True,
                    running=getattr(status, 'running', True),
                    healthy=getattr(status, 'healthy', True),
                    message=getattr(status, 'message', 'Analysis source active'),
                    loudness=analysis.loudness,
                    onset=analysis.onset,
                    bass=analysis.bands.bass,
                    mid=analysis.bands.mid,
                    treble=analysis.bands.treble,
                )
            audio['motion_multiplier'] = self.controller.audio_motion_multiplier
            audio['brightness_multiplier'] = (
                self.controller.audio_brightness_multiplier
            )
            audio['deep_dim_enabled'] = self.controller.audio_clock.deep_dim_enabled
            audio['quiet_floor'] = self.controller.audio_clock.quiet_brightness_floor
            foot_status = (
                self.foot_controller.status()
                if self.foot_controller is not None
                else None
            )
            white_commissioned = all(
                fixture.white_commissioned and fixture.white_rows_together
                for fixture in self.controller.config.fixtures
            )
            return dict(live_allowed=self.allow_live, live=self.sender is not None,
                        blackout=self.engine.blackout_enabled, error=self.error, notice=self.notice,
                        preset_id=self.engine.active_preset_id, playing=scenes.playing,
                        active_name=self.engine.presets[self.engine.active_preset_id].name,
                        scene_index=scenes.index, tempo=self.controller.show.context().tempo_bpm,
                        brightness=min(
                            self.engine.compositor.global_brightness,
                            self.engine.compositor.maximum_brightness,
                        ),
                        brightness_ceiling=self.engine.compositor.maximum_brightness,
                        audio=audio,
                        white_preview=dict(
                            enabled=self.white_peak_preview,
                            threshold=self.white_preview_threshold,
                            level=self.white_preview_level,
                            active_level=self.white_preview_active_level,
                            commissioned=white_commissioned,
                            mapping='Parts 1-8 right-to-left; both rows together',
                            output_available=(
                                self.allow_live
                                and self.sender is not None
                                and white_commissioned
                                and source is not None
                                and not self.engine.blackout_enabled
                            ),
                            output_enabled=self.white_output_enabled,
                            output_level=self.white_output_level,
                            output_active_level=self.white_output_active_level,
                            output_ceiling=self.white_output_ceiling,
                            high_output=(
                                self.white_output_ceiling > WHITE_OUTPUT_CEILING
                            ),
                            flash_rate_limit_hz=MAX_WHITE_FLASH_HZ,
                        ),
                        foot_control=(
                            dict(
                                enabled=True,
                                running=foot_status.running,
                                connected=foot_status.connected,
                                message=foot_status.message,
                                messages_received=foot_status.messages_received,
                                reconnects=foot_status.reconnects,
                            )
                            if foot_status is not None
                            else dict(
                                enabled=False,
                                running=False,
                                connected=False,
                                message='Foot control disabled',
                                messages_received=0,
                                reconnects=0,
                            )
                        ),
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
        self._disable_white_output()
        sender, self.sender = self.sender, None
        if sender is not None:
            sender.close()

    def _disable_white_output(self) -> None:
        self.white_output_enabled = False
        self.white_preview_active_level = 0.0
        self.white_output_active_level = 0.0
        self.white_peak_limiter.reset()

    def command(self, raw: object) -> None:
        data = object_fields(
            raw,
            {'action'},
            {
                'value', 'preset', 'scenes', 'index', 'enabled', 'floor',
                'threshold', 'level',
            },
        )
        action = data['action']
        with self.lock:
            elapsed = self.elapsed()
            scenes = self.controller.scenes
            if action == 'heartbeat':
                self.lease_deadline = time.monotonic() + 5
            elif action == 'blackout':
                self.engine.set_blackout(True)
                self._disable_white_output()
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
                    self.engine.set_global_brightness(min(
                        0.25,
                        self.engine.compositor.global_brightness,
                        self.engine.compositor.maximum_brightness,
                    ))
                    config = self.controller.config
                    self.sender = ArtNetSender(config.artnet_host, config.artnet_port, config.universe)
                    self.lease_deadline = time.monotonic() + 5
                    self.notice = ''
            elif action == 'stop_live':
                self.engine.set_blackout(True)
                scenes.playing = False
                self._stop_live()
            elif action == 'brightness':
                self.engine.set_global_brightness(number(
                    data.get('value'), 'brightness', 0,
                    self.engine.compositor.maximum_brightness,
                ))
            elif action == 'audio_dimming':
                enabled = data.get('enabled')
                if not isinstance(enabled, bool):
                    raise ValueError('audio deep dim enabled must be boolean')
                floor = number(data.get('floor'), 'audio quiet floor', 0, 0.25)
                self.controller.configure_audio_dimming(
                    enabled=enabled, quiet_floor=floor
                )
            elif action == 'white_preview':
                enabled = data.get('enabled')
                if not isinstance(enabled, bool):
                    raise ValueError('white preview enabled must be boolean')
                threshold = number(
                    data.get('threshold'), 'white preview threshold', 0.1, 1.0
                )
                level = number(
                    data.get('level'), 'white preview level', 0.05, 1.0
                )
                self.white_peak_preview = enabled
                self.white_preview_threshold = threshold
                self.white_preview_level = level
            elif action == 'white_output':
                enabled = data.get('enabled')
                if not isinstance(enabled, bool):
                    raise ValueError('white output enabled must be boolean')
                level = number(
                    data.get('level'), 'white output level', 0.01,
                    self.white_output_ceiling,
                )
                if enabled:
                    if not self.allow_live or self.sender is None:
                        raise ValueError('start explicit browser live output before enabling whites')
                    if self.engine.blackout_enabled:
                        raise ValueError('release blackout before enabling whites')
                    if self.controller.audio_source is None:
                        raise ValueError('audio input is required for white peak output')
                    if not all(
                        fixture.white_commissioned and fixture.white_rows_together
                        for fixture in self.controller.config.fixtures
                    ):
                        raise ValueError('white output requires commissioned fixtures')
                self.white_output_level = level
                self.white_output_enabled = enabled
                if not enabled:
                    self._disable_white_output()
            elif action == 'preset':
                preset_id = data.get('value')
                if not isinstance(preset_id, str) or preset_id not in self.engine.presets:
                    raise ValueError('unknown preset')
                self.controller.begin_transition(elapsed, duration=0.8)
                scenes.playing = False
                scenes.index = None
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
            source = self.controller.audio_source
            analysis = source.sample(now - self.started) if source is not None else None
            onset = analysis.onset if analysis is not None else 0.0
            white_requested = self.white_peak_preview or self.white_output_enabled
            strength = self.white_peak_limiter.update(
                now,
                onset,
                enabled=white_requested and not self.engine.blackout_enabled,
                threshold=self.white_preview_threshold,
            )
            self.white_preview_active_level = (
                self.white_preview_level * strength
                if self.white_peak_preview
                else 0.0
            )
            self.white_output_active_level = (
                self.white_output_level * strength
                if self.white_output_enabled and self.sender is not None
                else 0.0
            )
            if self.sender is not None:
                white_zones = (
                    commissioned_white_levels(
                        self.controller.config.fixtures,
                        self.white_output_active_level,
                        maximum=self.white_output_ceiling,
                    )
                    if self.white_output_enabled
                    else None
                )
                self.sender.send(compose_dmx(
                    self.controller.config.fixtures,
                    self.frames,
                    white_zones=white_zones,
                ))

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
        elif path in (
            '/', '/app.js', '/style.css', '/fixture.css', '/audio.css',
            '/safety.css',
        ):
            name = 'index.html' if path == '/' else path[1:]
            content_type = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8',
                            'style.css': 'text/css; charset=utf-8',
                            'fixture.css': 'text/css; charset=utf-8',
                            'audio.css': 'text/css; charset=utf-8',
                            'safety.css': 'text/css; charset=utf-8'}[name]
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
          allow_network: str = '192.168.1.0/24', allow_live: bool = False,
          foot_midi_device: Path | None = None, foot_midi_channel: int = 1,
          white_output_ceiling: float = WHITE_OUTPUT_CEILING) -> None:
    if not 1 <= port <= 65535:
        raise ValueError('browser port must be between 1 and 65535')
    if controller.config.fps > 25:
        raise ValueError('browser control requires an output rate at or below 25 FPS')
    control = BrowserControl(
        controller,
        library_path,
        allow_live=allow_live,
        white_output_ceiling=white_output_ceiling,
    )
    foot_controller = (
        RawMidiFootController(
            foot_midi_device,
            BrowserFootCommands(control),
            channel=foot_midi_channel,
        )
        if foot_midi_device is not None
        else None
    )
    control.foot_controller = foot_controller
    server = ControlServer((host, port), control, allow_network)
    previous_term = signal.getsignal(signal.SIGTERM)
    def interrupted(signum: int, frame: object) -> None:
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    print(f'Phreqed browser: http://{host}:{port} — simulation active; output stopped', flush=True)
    if white_output_ceiling > WHITE_OUTPUT_CEILING:
        print(
            'WARNING: HIGH-OUTPUT CENTER WHITES ENABLED FOR THIS PROCESS; '
            f'operator ceiling {white_output_ceiling:.0%}',
            flush=True,
        )
    control.start()
    try:
        if foot_controller is not None:
            foot_controller.start()
            print(
                f'FOOT CONTROL: {foot_midi_device} on MIDI channel {foot_midi_channel}',
                flush=True,
            )
        server.serve_forever(poll_interval=0.2)
    finally:
        if foot_controller is not None:
            foot_controller.close()
        control.close()
        server.server_close()
        signal.signal(signal.SIGTERM, previous_term)
