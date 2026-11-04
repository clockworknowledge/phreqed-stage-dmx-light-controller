import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phreqed_dmx.presets import PRESETS
from phreqed_dmx.songs import SongLibrary


class SongLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'songs.json'
        self.library = SongLibrary(self.path, set(PRESETS))

    @staticmethod
    def document():
        return {
            'version': 1,
            'songs': [
                {
                    'song_id': 'song-first', 'title': 'First Song', 'artist': 'Phreqed',
                    'duration_seconds': 120.0, 'notes': 'Open the set',
                    'source': 'mp3_upload', 'active_cue_sheet_id': 'cue-first-v1',
                    'style': 'punk',
                },
                {
                    'song_id': 'song-second', 'title': 'Second Song', 'artist': 'Phreqed',
                    'duration_seconds': 90.0, 'notes': '',
                    'source': 'rehearsal_capture', 'active_cue_sheet_id': 'cue-second-v1',
                    'style': 'mellow',
                },
            ],
            'cue_sheets': [
                {
                    'cue_sheet_id': 'cue-first-v1', 'song_id': 'song-first',
                    'revision': 1, 'published': True,
                    'cues': [
                        {'at_seconds': 0.0, 'preset_id': 'psychedelic-bloom',
                         'transition_seconds': 0.0},
                        {'at_seconds': 30.0, 'preset_id': 'molten-motion',
                         'transition_seconds': 1.5},
                    ],
                },
                {
                    'cue_sheet_id': 'cue-second-v1', 'song_id': 'song-second',
                    'revision': 1, 'published': True,
                    'cues': [
                        {'at_seconds': 0.0, 'preset_id': 'digital-storm',
                         'transition_seconds': 0.5},
                    ],
                },
            ],
            'setlists': [{
                'setlist_id': 'setlist-show', 'name': 'Show',
                'song_ids': ['song-first', 'song-second'], 'notes': 'Main set',
            }],
        }

    def test_round_trip_preserves_song_sources_cues_and_setlist_order(self):
        document = self.document()
        self.library.save(document)
        restored = SongLibrary(self.path, set(PRESETS))
        self.assertEqual(restored.document(), document)
        self.assertEqual(restored.songs['song-first'].source.value, 'mp3_upload')
        self.assertEqual(restored.songs['song-first'].style.value, 'punk')
        self.assertEqual(restored.setlists['setlist-show'].song_ids,
                         ('song-first', 'song-second'))

    def test_rejects_invalid_document_without_changing_memory_or_disk(self):
        original = self.document()
        self.library.save(original)
        before = self.path.read_bytes()
        mutations = (
            lambda d: d.update(version=2),
            lambda d: d.update(extra=True),
            lambda d: d['songs'][0].update(song_id='../../escape'),
            lambda d: d['songs'][0].update(source='streaming_link'),
            lambda d: d['songs'][0].update(style='classical'),
            lambda d: d['songs'][0].update(duration_seconds=float('nan')),
            lambda d: d['songs'][0].update(active_cue_sheet_id='cue-missing'),
            lambda d: d['songs'].append(copy.deepcopy(d['songs'][0])),
            lambda d: d['cue_sheets'][0].update(published=False),
            lambda d: d['cue_sheets'][0]['cues'][0].update(at_seconds=1),
            lambda d: d['cue_sheets'][0]['cues'][1].update(at_seconds=0),
            lambda d: d['cue_sheets'][0]['cues'][1].update(at_seconds=120),
            lambda d: d['cue_sheets'][0]['cues'][0].update(preset_id='missing'),
            lambda d: d['setlists'][0]['song_ids'].append('song-missing'),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                proposed = copy.deepcopy(original)
                mutate(proposed)
                with self.assertRaises(ValueError):
                    self.library.save(proposed)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self.library.document(), original)

    def test_legacy_song_without_style_loads_as_unspecified(self):
        document = self.document()
        for song in document['songs']:
            song.pop('style')
        self.path.write_text(json.dumps(document), encoding='utf-8')

        restored = SongLibrary(self.path, set(PRESETS))

        self.assertEqual(restored.songs['song-first'].style.value, 'unspecified')
        self.assertEqual(restored.document(), document)

    def test_unpublished_draft_is_allowed_until_made_active(self):
        document = self.document()
        document['songs'][0]['active_cue_sheet_id'] = None
        document['cue_sheets'][0]['published'] = False
        self.library.save(document)
        self.assertFalse(self.library.cue_sheets['cue-first-v1'].published)

    def test_published_cue_sheet_is_immutable_but_new_revision_is_allowed(self):
        document = self.document()
        self.library.save(document)
        changed = copy.deepcopy(document)
        changed['cue_sheets'][0]['cues'][0]['preset_id'] = 'energy-bridge'
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.library.save(changed)

        revised = copy.deepcopy(document)
        revised['songs'][0]['active_cue_sheet_id'] = 'cue-first-v2'
        revised['cue_sheets'].append({
            'cue_sheet_id': 'cue-first-v2', 'song_id': 'song-first',
            'revision': 2, 'published': True,
            'cues': [{
                'at_seconds': 0.0, 'preset_id': 'energy-bridge',
                'transition_seconds': 0.5,
            }],
        })
        self.library.save(revised)
        self.assertEqual(self.library.songs['song-first'].active_cue_sheet_id,
                         'cue-first-v2')

    def test_setlist_may_repeat_a_song_for_an_encore(self):
        document = self.document()
        document['setlists'][0]['song_ids'].append('song-first')
        self.library.save(document)
        self.assertEqual(self.library.setlists['setlist-show'].song_ids[-1], 'song-first')

    def test_failed_atomic_replace_preserves_previous_file_and_state(self):
        original = self.document()
        self.library.save(original)
        before = self.path.read_bytes()
        changed = copy.deepcopy(original)
        changed['songs'][0]['title'] = 'Changed'
        with patch('phreqed_dmx.songs.os.replace', side_effect=OSError('disk failed')):
            with self.assertRaises(OSError):
                self.library.save(changed)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.library.songs['song-first'].title, 'First Song')
        self.assertEqual(list(self.path.parent.glob('.songs-*')), [])

    def test_corrupt_library_is_not_silently_overwritten(self):
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'cannot load song library'):
            SongLibrary(self.path, set(PRESETS))
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{broken')

    def test_library_contains_metadata_only_and_opens_no_network(self):
        document = self.document()
        self.assertNotIn('media', json.dumps(document))
        self.library.save(document)
        with patch('socket.socket', side_effect=AssertionError('no socket')):
            SongLibrary(self.path, set(PRESETS))


if __name__ == '__main__':
    unittest.main()
