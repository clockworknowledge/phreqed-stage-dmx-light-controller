from pathlib import Path
import tempfile
import unittest

from phreqed_dmx.performance import PerformanceController, PerformanceMode
from phreqed_dmx.presets import PRESETS
from phreqed_dmx.song_timeline import SongTimelineRunner, TimelineState
from phreqed_dmx.songs import SongLibrary


class PerformanceControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        library = SongLibrary(Path(self.temp.name) / 'songs.json', set(PRESETS))
        library.save({
            'version': 1,
            'songs': [{
                'song_id': 'song-one', 'title': 'One', 'artist': 'Phreqed',
                'duration_seconds': 30.0, 'notes': '', 'source': 'manual',
                'active_cue_sheet_id': 'cue-one-v1',
            }],
            'cue_sheets': [{
                'cue_sheet_id': 'cue-one-v1', 'song_id': 'song-one',
                'revision': 1, 'published': True,
                'cues': [{
                    'at_seconds': 0.0, 'preset_id': 'psychedelic-bloom',
                    'transition_seconds': 0.5,
                }],
            }],
            'setlists': [{
                'setlist_id': 'setlist-main', 'name': 'Main',
                'song_ids': ['song-one'], 'notes': '',
            }],
        })
        self.now = 0.0
        self.activations = []
        runner = SongTimelineRunner(
            library,
            lambda cue, scheduled: self.activations.append((cue.preset_id, scheduled)),
            clock=lambda: self.now,
        )
        self.performance = PerformanceController(runner)

    def test_mode_and_setlist_selection_never_activate_a_cue(self):
        self.performance.set_mode('setlist')
        self.performance.load_setlist('setlist-main')
        self.assertEqual(self.performance.mode, PerformanceMode.SETLIST)
        self.assertEqual(self.performance.timeline.state, TimelineState.ARMED)
        self.assertEqual(self.activations, [])

    def test_primary_is_explicit_start_stop_and_manual_deactivates(self):
        self.performance.set_mode('setlist')
        self.performance.load_setlist('setlist-main')
        self.performance.toggle()
        self.assertEqual(self.performance.timeline.state, TimelineState.RUNNING)
        self.assertEqual(self.activations, [('psychedelic-bloom', 0.0)])
        self.performance.toggle()
        self.assertEqual(self.performance.timeline.state, TimelineState.STOPPED)
        self.performance.set_mode('manual')
        self.assertEqual(self.performance.timeline.state, TimelineState.INACTIVE)

    def test_blackout_stops_without_resume(self):
        self.performance.set_mode('setlist')
        self.performance.load_setlist('setlist-main')
        self.performance.start()
        self.performance.blackout()
        self.assertEqual(self.performance.timeline.state, TimelineState.STOPPED)
        self.now = 10.0
        self.performance.update()
        self.assertEqual(len(self.activations), 1)

    def test_setlist_commands_require_setlist_mode(self):
        for command in (
            lambda: self.performance.load_setlist('setlist-main'),
            lambda: self.performance.move(1),
            self.performance.start,
            self.performance.toggle,
        ):
            with self.subTest(command=command), self.assertRaisesRegex(
                ValueError, 'Setlist mode'
            ):
                command()


if __name__ == '__main__':
    unittest.main()
