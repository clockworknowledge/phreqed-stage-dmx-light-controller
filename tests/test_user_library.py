import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phreqed_dmx.config import load_config
from phreqed_dmx.library import UserLibrary, parse_preset, preset_data
from phreqed_dmx.presets import PRESETS


class UserLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'library.json'
        self.names = tuple(f.name for f in load_config().fixtures)
        self.library = UserLibrary(self.path, self.names)
        self.preset = preset_data(PRESETS['molten-motion'])
        self.preset.update(preset_id='user-night', name='Night')

    def document(self):
        return dict(version=1, presets=[self.preset], scenes=[dict(
            name='Opening', preset_id='user-night', hold_seconds=10, fade_seconds=2)])

    def test_round_trip_preserves_layer_targets_types_and_brightness(self):
        self.preset['layers'][0]['fixtures'] = ['Cube A']
        self.preset['layers'][1]['fixtures'] = ['Cube B']
        self.library.save(self.document())
        restored = UserLibrary(self.path, self.names)
        self.assertEqual(restored.document(), self.document())
        count = restored.presets['user-night'].layers[1].parameters['count']
        self.assertIs(type(count), int)
        self.assertEqual(restored.presets['user-night'].layers[1].blend_mode.value, 'lighten')

    def test_rejects_bad_schema_without_changing_memory_or_disk(self):
        self.library.save(self.document())
        before = self.path.read_bytes()
        for mutate in (
            lambda d: d.update(version=2), lambda d: d.update(version=True),
            lambda d: d.update(live=True),
            lambda d: d['presets'].append(copy.deepcopy(d['presets'][0])),
            lambda d: d['scenes'][0].update(preset_id='missing'),
            lambda d: d['scenes'][0].update(hold_seconds=0),
            lambda d: d['scenes'][0].update(fade_seconds=11),
            lambda d: d['presets'][0].update(global_brightness=float('nan')),
            lambda d: d['presets'][0].update(global_brightness=0.66),
            lambda d: d['presets'][0].update(preset_id='../../escape'),
            lambda d: d['presets'][0]['layers'][0].update(fixtures=['missing']),
            lambda d: d['presets'][0]['layers'][0].update(opacity=True),
            lambda d: d['presets'][0]['layers'][0].update(effect_id='missing'),
            lambda d: d['presets'][0]['layers'][0].update(blend_mode='missing'),
            lambda d: d['presets'][0]['layers'][0]['parameters'].update(speed=0),
            lambda d: d['presets'][0]['layers'][0]['parameters'].update(fake=1),
        ):
            with self.subTest(mutation=mutate):
                proposed = copy.deepcopy(self.document())
                mutate(proposed)
                with self.assertRaises(ValueError):
                    self.library.save(proposed)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.library.document(), self.document())

    def test_builtin_id_cannot_be_overwritten(self):
        self.preset['preset_id'] = 'molten-motion'
        with self.assertRaises(ValueError):
            parse_preset(self.preset, self.names)

    def test_failed_atomic_replace_preserves_previous_file_and_state(self):
        self.library.save(self.document())
        before = self.path.read_bytes()
        changed = self.document()
        changed['presets'][0]['name'] = 'Changed'
        with patch('phreqed_dmx.library.os.replace', side_effect=OSError('disk failed')):
            with self.assertRaises(OSError):
                self.library.save(changed)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.library.presets['user-night'].name, 'Night')
        self.assertEqual(list(self.path.parent.glob('.library-*')), [])

    def test_corrupt_existing_library_is_not_silently_overwritten(self):
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'cannot load user library'):
            UserLibrary(self.path, self.names)
        self.assertEqual(self.path.read_text(), '{broken')

    def test_loading_does_not_create_network_or_modify_builtins(self):
        original = {key: preset_data(value) for key, value in PRESETS.items()}
        self.library.save(self.document())
        with patch('socket.socket', side_effect=AssertionError('no socket')):
            UserLibrary(self.path, self.names)
        self.assertEqual({key: preset_data(value) for key, value in PRESETS.items()}, original)
