from email.message import Message
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from phreqed_dmx.app import Controller, main
from phreqed_dmx.config import load_config
from phreqed_dmx.library import preset_data
from phreqed_dmx.presets import PRESETS
from phreqed_dmx.web_control import BrowserControl, ControlHandler


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
                        dict(action='select_scene', index=True), dict(action='anything')):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.control.command(command)
        self.assertEqual(self.control.engine.active_preset_id, before)
        self.assertEqual(self.control.engine.compositor.global_brightness, 0.25)

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
