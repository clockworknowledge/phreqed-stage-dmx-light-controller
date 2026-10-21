from email.message import Message
from importlib.resources import files
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from phreqed_dmx.app import Controller, main
from phreqed_dmx.audio_analysis import AudioAnalysis, FrequencyBands, ManualAudioAnalysisSource
from phreqed_dmx.compositor import Compositor
from phreqed_dmx.config import load_config
from phreqed_dmx.engine import SceneEngine
from phreqed_dmx.library import Cue, preset_data
from phreqed_dmx.presets import PRESETS
from phreqed_dmx.web_control import BrowserControl, BrowserFootCommands, ControlHandler


class BrowserControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'library.json'
        self.controller = Controller(load_config())
        self.control = BrowserControl(self.controller, self.path)
        self.addCleanup(self.control.close)

    def preset(self):
        p = preset_data(PRESETS['molten-motion'])
        p.update(preset_id='user-test', name='Test')
        return p

    def test_simulation_actions_never_construct_sender(self):
        with patch('phreqed_dmx.web_control.ArtNetSender') as sender:
            for command in (
                dict(action='preset', value='molten-motion'),
                dict(action='save_preset', preset=self.preset()),
                dict(action='preview', preset=self.preset()),
                dict(action='play'), dict(action='next_scene'), dict(action='blackout'),
                dict(action='resume'), dict(action='tap'),
            ):
                self.control.command(command)
                self.control.step()
            with self.assertRaises(ValueError):
                self.control.command(dict(action='start_live'))
            sender.assert_not_called()

        frames = self.control.state()['frames']
        self.assertEqual(set(frames), {'Cube A', 'Cube B'})
        for frame in frames.values():
            self.assertEqual(len(frame), 4)
            self.assertTrue(all(len(row) == 12 for row in frame))

    def test_browser_preview_documents_disabled_center_strobes(self):
        html = files('phreqed_dmx').joinpath('web/index.html').read_text(encoding='utf-8')
        script = files('phreqed_dmx').joinpath('web/app.js').read_text(encoding='utf-8')
        self.assertIn('12 by 4 RGB grid and two center white preview lines', html)
        self.assertIn('whites preview-only', html)
        self.assertIn("const white = Math.round", script)
        self.assertIn("white.active_level", script)

    def test_browser_reports_disabled_and_active_audio_analysis(self):
        disabled = self.control.state()['audio']
        self.assertFalse(disabled['enabled'])
        self.assertEqual(disabled['loudness'], 0.0)

        source = ManualAudioAnalysisSource(
            AudioAnalysis(0.6, 0.3, FrequencyBands(0.8, 0.4, 0.2))
        )
        enabled = BrowserControl(
            Controller(load_config(), audio_source=source), self.path
        )
        self.addCleanup(enabled.close)
        audio = enabled.state()['audio']
        self.assertTrue(audio['enabled'])
        self.assertTrue(audio['healthy'])
        self.assertEqual(
            (audio['loudness'], audio['onset'], audio['bass'], audio['mid'], audio['treble']),
            (0.6, 0.3, 0.8, 0.4, 0.2),
        )
        enabled.step(enabled.started + 0.5)
        reactive = enabled.state()['audio']
        self.assertGreater(reactive['motion_multiplier'], 1.0)
        self.assertLessEqual(reactive['brightness_multiplier'], 1.0)

        html = files('phreqed_dmx').joinpath('web/index.html').read_text(encoding='utf-8')
        for meter in ('audio-loudness', 'audio-onset', 'audio-bass', 'audio-mid', 'audio-treble'):
            self.assertIn(f'id="{meter}"', html)
        self.assertIn('id="audio-motion"', html)
        self.assertIn('id="audio-brightness"', html)

    def test_preset_and_scene_storage_survives_new_controller_without_autoplay(self):
        self.control.command(dict(action='save_preset', preset=self.preset()))
        cues = [dict(name='Night', preset_id='user-test', hold_seconds=7, fade_seconds=1)]
        self.control.command(dict(action='save_scenes', scenes=cues))
        self.control.command(dict(action='play'))
        restored = BrowserControl(Controller(load_config()), self.path)
        self.addCleanup(restored.close)
        self.assertEqual(restored.library.document()['scenes'], cues)
        self.assertIn('user-test', restored.engine.presets)
        self.assertFalse(restored.controller.scenes.playing)
        self.assertIsNone(restored.sender)
        self.assertIsNone(restored.controller.scenes.index)

    def test_deletion_rejects_referenced_presets_and_builtins(self):
        self.control.command(dict(action='save_preset', preset=self.preset()))
        self.control.command(dict(action='save_scenes', scenes=[dict(
            name='Test', preset_id='user-test', hold_seconds=3, fade_seconds=1)]))
        before = self.path.read_bytes()
        for preset_id in ('user-test', 'molten-motion'):
            with self.assertRaises(ValueError):
                self.control.command(dict(action='delete_preset', value=preset_id))
        self.assertEqual(before, self.path.read_bytes())

    def test_draft_does_not_modify_saved_preset_or_catalog(self):
        self.control.command(dict(action='save_preset', preset=self.preset()))
        changed = self.preset()
        changed['name'] = 'Unsaved draft'
        self.control.command(dict(action='preview', preset=changed))
        self.assertEqual(self.control.state()['active_name'], 'Unsaved draft')
        self.assertEqual(self.control.library.presets['user-test'].name, 'Test')
        self.assertEqual(next(p for p in self.control.catalog()['presets'] if p['preset_id']=='user-test')['name'], 'Test')

    def test_bad_commands_do_not_mutate_scene_or_brightness(self):
        before = self.control.engine.active_preset_id
        for command in (dict(action='brightness', value=0.7), dict(action='brightness', value=float('inf')),
                        dict(action='preset', value=[]), dict(action='save_scenes', scenes=[{}]),
                        dict(action='select_scene', index=True),
                        dict(action='audio_dimming', enabled='yes', floor=0.02),
                        dict(action='audio_dimming', enabled=True, floor=0.5),
                        dict(action='white_preview', enabled=True, threshold=0.0, level=0.8),
                        dict(action='white_preview', enabled=True, threshold=0.65, level=2.0),
                        dict(action='anything')):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.control.command(command)
        self.assertEqual(self.control.engine.active_preset_id, before)
        self.assertEqual(self.control.engine.compositor.global_brightness, 0.25)
        self.assertFalse(self.control.controller.audio_clock.deep_dim_enabled)
        self.assertFalse(self.control.white_peak_preview)

    def test_browser_brightness_uses_explicit_controller_ceiling(self):
        config = load_config()
        engine = SceneEngine(
            config.fixtures, compositor=Compositor(maximum_brightness=0.9)
        )
        control = BrowserControl(Controller(config, engine), self.path)
        self.addCleanup(control.close)

        self.assertEqual(control.state()['brightness_ceiling'], 0.9)
        control.command(dict(action='brightness', value=0.8))
        self.assertEqual(control.engine.compositor.global_brightness, 0.8)
        with self.assertRaises(ValueError):
            control.command(dict(action='brightness', value=0.91))

        html = files('phreqed_dmx').joinpath('web/index.html').read_text(encoding='utf-8')
        script = files('phreqed_dmx').joinpath('web/app.js').read_text(encoding='utf-8')
        self.assertIn('id="brightness-ceiling"', html)
        self.assertIn("$('master').max = s.brightness_ceiling", script)
        self.assertIn('HIGH-OUTPUT MODE', script)

    def test_master_brightness_survives_preset_and_scene_changes(self):
        self.control.command(dict(action='brightness', value=0.41))
        self.control.command(dict(action='preset', value='molten-motion'))
        self.control.step()
        self.assertEqual(self.control.state()['brightness'], 0.41)

        self.control.controller.scenes.replace((
            Cue('Matrix', 'matrix-rain', 5, 0),
            Cue('VU', 'inside-out-vu', 5, 0),
        ))
        self.control.command(dict(action='next_scene'))
        self.control.step()
        self.control.command(dict(action='next_scene'))
        self.control.step()
        self.assertEqual(self.control.state()['brightness'], 0.41)

    def test_deep_dim_and_center_white_peak_preview_are_bounded_and_preview_only(self):
        source = ManualAudioAnalysisSource(
            AudioAnalysis(0.1, 0.9, FrequencyBands(0.2, 0.1, 0.1))
        )
        control = BrowserControl(
            Controller(load_config(), audio_source=source), self.path, allow_live=True
        )
        self.addCleanup(control.close)
        control.command(dict(action='audio_dimming', enabled=True, floor=0.02))
        control.command(dict(
            action='white_preview', enabled=True, threshold=0.65, level=0.8
        ))
        control.step(control.started + 1.0)
        state = control.state()
        self.assertTrue(state['audio']['deep_dim_enabled'])
        self.assertEqual(state['audio']['quiet_floor'], 0.02)
        self.assertGreater(state['white_preview']['active_level'], 0.0)
        self.assertFalse(state['white_preview']['output_enabled'])

        with patch('phreqed_dmx.web_control.ArtNetSender') as sender:
            control.command(dict(action='start_live'))
            control.step()
            payload = sender.return_value.send.call_args.args[0]
        self.assertEqual(payload[144:152], bytes(8))
        self.assertEqual(payload[296:304], bytes(8))

        html = files('phreqed_dmx').joinpath('web/index.html').read_text(encoding='utf-8')
        self.assertIn('id="deep-dim"', html)
        self.assertIn('id="white-preview"', html)
        self.assertIn('Physical output locked', html)

    def test_live_requires_two_steps_and_watchdog_closes_with_blackout(self):
        control = BrowserControl(Controller(load_config()), self.path, allow_live=True)
        self.addCleanup(control.close)
        with patch('phreqed_dmx.web_control.ArtNetSender') as sender:
            control.step()
            sender.assert_not_called()
            control.command(dict(action='start_live'))
            sender.assert_called_once()
            self.assertLessEqual(control.engine.compositor.global_brightness, 0.25)
            control.step(control.lease_deadline + 0.1)
            sender.return_value.close.assert_called_once_with()
            self.assertIsNone(control.sender)
            self.assertTrue(control.engine.blackout_enabled)
            self.assertFalse(control.controller.scenes.playing)
            control.command(dict(action='heartbeat'))
            self.assertIsNone(control.sender)

    def test_browser_startup_preserves_lower_explicit_brightness(self):
        controller = Controller(load_config())
        controller.engine.set_global_brightness(0.15)
        control = BrowserControl(controller, self.path, allow_live=True)
        self.addCleanup(control.close)
        self.assertEqual(control.engine.compositor.global_brightness, 0.15)
        with patch('phreqed_dmx.web_control.ArtNetSender'):
            control.command(dict(action='start_live'))
        self.assertEqual(control.engine.compositor.global_brightness, 0.15)

    def test_live_frames_reserved_channels_and_blackout_override(self):
        control = BrowserControl(Controller(load_config()), self.path, allow_live=True)
        self.addCleanup(control.close)
        with patch('phreqed_dmx.web_control.ArtNetSender') as sender:
            control.command(dict(action='start_live'))
            control.command(dict(action='next_scene'))
            control.step()
            payload = sender.return_value.send.call_args.args[0]
            self.assertEqual(len(payload), 512)
            self.assertEqual(payload[144:152], bytes(8))
            self.assertEqual(payload[296:304], bytes(8))
            self.assertLessEqual(max(payload), round(0.65*255))
            control.command(dict(action='blackout'))
            sender.return_value.blackout.assert_called_once()
            control.step()
            self.assertEqual(sender.return_value.send.call_args.args[0], bytes(512))
            control.command(dict(action='stop_live'))
            sender.return_value.close.assert_called_once()

    def test_cli_browser_simulation_cannot_enable_live(self):
        with patch('phreqed_dmx.web_control.serve') as serve:
            self.assertEqual(main(['web']), 0)
            self.assertFalse(serve.call_args.kwargs['allow_live'])
            self.assertEqual(main(['live', '--web']), 0)
            self.assertTrue(serve.call_args.kwargs['allow_live'])
        with self.assertRaises(SystemExit):
            main(['simulate', '--web'])

    def test_browser_foot_commands_use_serialized_browser_actions(self):
        control = Mock()
        control.controller.show.context.return_value.tempo_bpm = 123.0
        commands = BrowserFootCommands(control)
        commands.previous_scene()
        commands.next_scene()
        self.assertEqual(commands.tap_tempo(), 123.0)
        commands.blackout(True)
        commands.blackout(False)
        self.assertEqual(
            [call.args[0] for call in control.command.call_args_list],
            [
                {'action': 'previous_scene'},
                {'action': 'next_scene'},
                {'action': 'tap'},
                {'action': 'blackout'},
                {'action': 'resume'},
            ],
        )

    def test_cli_passes_explicit_foot_device_to_browser_server(self):
        with (
            patch('phreqed_dmx.web_control.serve') as serve,
            patch('phreqed_dmx.app.RawMidiFootController') as raw_midi,
        ):
            self.assertEqual(
                main(['web', '--foot-midi-device', '/dev/snd/midiC2D0']), 0
            )
        raw_midi.assert_not_called()
        self.assertEqual(
            serve.call_args.kwargs['foot_midi_device'], Path('/dev/snd/midiC2D0')
        )
        self.assertEqual(serve.call_args.kwargs['foot_midi_channel'], 1)


class HttpBoundaryTests(unittest.TestCase):
    def handler(self, body, *, token='expected', origin='http://127.0.0.1:8080', host='127.0.0.1:8080'):
        handler = object.__new__(ControlHandler)
        handler.server = SimpleNamespace(token='expected', control=Mock())
        handler.headers = Message()
        for key, value in {'Host':host, 'Origin':origin, 'X-Control-Token':token,
                           'Content-Type':'application/json', 'Content-Length':str(len(body))}.items():
            handler.headers[key] = value
        handler.path = '/api/command'
        handler.connection = Mock()
        handler.connection.getsockname.return_value = ('127.0.0.1',8080)
        handler.rfile = io.BytesIO(body)
        handler.reply = Mock()
        return handler

    def test_cross_origin_unknown_host_and_missing_token_rejected(self):
        for kwargs in (dict(origin='http://evil.test'),dict(token=''),dict(host='evil.test'),dict(host='[')):
            with self.subTest(kwargs=kwargs):
                handler = self.handler(b'{"action":"start_live"}', **kwargs)
                handler.do_POST()
                self.assertEqual(handler.reply.call_args.args[0], 403)
                handler.server.control.command.assert_not_called()

    def test_malformed_or_oversized_body_rejected_before_dispatch(self):
        for body, length in ((b'{broken',7),(b'{}',1000001),(b'{}',-1)):
            handler = self.handler(body)
            handler.headers.replace_header('Content-Length', str(length))
            handler.do_POST()
            self.assertEqual(handler.reply.call_args.args[0],400)
            handler.server.control.command.assert_not_called()

    def test_valid_same_origin_command_dispatched(self):
        handler = self.handler(b'{"action":"blackout"}')
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0],200)
        handler.server.control.command.assert_called_once_with({'action':'blackout'})
