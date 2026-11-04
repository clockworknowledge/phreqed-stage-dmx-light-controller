from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phreqed_dmx.presets import PRESETS
from phreqed_dmx.song_timeline import SongTimelineRunner, TimelineState
from phreqed_dmx.songs import SongLibrary


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class SongTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'songs.json'
        self.library = SongLibrary(self.path, set(PRESETS))
        self.library.save({
            'version': 1,
            'songs': [
                {
                    'song_id': 'song-one', 'title': 'One', 'artist': 'Phreqed',
                    'duration_seconds': 10.0, 'notes': '', 'source': 'manual',
                    'active_cue_sheet_id': 'cue-one-v1',
                },
                {
                    'song_id': 'song-two', 'title': 'Two', 'artist': 'Phreqed',
                    'duration_seconds': 8.0, 'notes': '', 'source': 'manual',
                    'active_cue_sheet_id': 'cue-two-v1',
                },
            ],
            'cue_sheets': [
                {
                    'cue_sheet_id': 'cue-one-v1', 'song_id': 'song-one',
                    'revision': 1, 'published': True,
                    'cues': [
                        {'at_seconds': 0.0, 'preset_id': 'psychedelic-bloom',
                         'transition_seconds': 0.0},
                        {'at_seconds': 3.0, 'preset_id': 'molten-motion',
                         'transition_seconds': 1.0},
                        {'at_seconds': 7.0, 'preset_id': 'digital-storm',
                         'transition_seconds': 0.5},
                    ],
                },
                {
                    'cue_sheet_id': 'cue-two-v1', 'song_id': 'song-two',
                    'revision': 1, 'published': True,
                    'cues': [
                        {'at_seconds': 0.0, 'preset_id': 'energy-bridge',
                         'transition_seconds': 0.25},
                    ],
                },
            ],
            'setlists': [{
                'setlist_id': 'setlist-main', 'name': 'Main',
                'song_ids': ['song-one', 'song-two'], 'notes': '',
            }],
        })
        self.clock = FakeClock()
        self.blackout = False
        self.activations = []
        self.runner = SongTimelineRunner(
            self.library,
            lambda cue, scheduled: self.activations.append((cue.preset_id, scheduled)),
            clock=self.clock,
            blackout_active=lambda: self.blackout,
        )
        self.runner.load('setlist-main')

    def test_start_and_skipped_updates_use_scheduled_cue_times(self):
        self.clock.now = 100.0
        self.runner.start()
        self.assertEqual(self.activations, [('psychedelic-bloom', 100.0)])
        self.clock.now = 107.5
        self.runner.update()
        self.assertEqual(self.activations, [
            ('psychedelic-bloom', 100.0),
            ('molten-motion', 103.0),
            ('digital-storm', 107.0),
        ])
        self.assertEqual(self.runner.state, TimelineState.RUNNING)

    def test_completion_arms_next_song_without_starting_it(self):
        self.runner.start()
        self.clock.now = 10.0
        self.runner.update()
        self.assertEqual(self.runner.song.song_id, 'song-two')
        self.assertEqual(self.runner.state, TimelineState.ARMED)
        self.assertIsNone(self.runner.started_at)
        count = len(self.activations)
        self.clock.now = 20.0
        self.runner.update()
        self.assertEqual(len(self.activations), count)

    def test_final_song_completes_without_wrapping_or_autostart(self):
        self.runner.select(1)
        self.runner.start()
        self.clock.now = 8.0
        self.runner.update()
        self.assertEqual(self.runner.song.song_id, 'song-two')
        self.assertEqual(self.runner.state, TimelineState.COMPLETE)
        self.assertIsNone(self.runner.started_at)

    def test_previous_next_selection_wraps_and_stops_playback(self):
        self.runner.move(-1)
        self.assertEqual(self.runner.song.song_id, 'song-two')
        self.runner.start()
        self.runner.move(1)
        self.assertEqual(self.runner.song.song_id, 'song-one')
        self.assertEqual(self.runner.state, TimelineState.ARMED)
        self.assertIsNone(self.runner.started_at)

    def test_stop_and_restart_begin_from_first_cue(self):
        self.runner.start()
        self.clock.now = 4.0
        self.runner.update()
        self.runner.stop()
        self.assertEqual(self.runner.state, TimelineState.STOPPED)
        self.clock.now = 20.0
        self.runner.restart()
        self.assertEqual(self.activations[-1], ('psychedelic-bloom', 20.0))

    def test_blackout_blocks_start_and_stops_without_automatic_resume(self):
        self.blackout = True
        with self.assertRaisesRegex(ValueError, 'blackout'):
            self.runner.start()
        self.blackout = False
        self.runner.start()
        self.blackout = True
        self.runner.update()
        self.assertEqual(self.runner.state, TimelineState.STOPPED)
        self.blackout = False
        self.clock.now = 5.0
        self.runner.update()
        self.assertEqual(len(self.activations), 1)

    def test_deactivate_is_a_mode_change_with_no_output(self):
        self.runner.start()
        count = len(self.activations)
        self.runner.deactivate()
        self.clock.now = 9.0
        self.runner.update()
        self.assertEqual(self.runner.state, TimelineState.INACTIVE)
        self.assertIsNone(self.runner.song)
        self.assertEqual(len(self.activations), count)

    def test_invalid_selection_and_clock_preserve_safe_state(self):
        for value in (-1, 2, True, '1', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.runner.select(value)
        self.assertEqual(self.runner.song.song_id, 'song-one')
        self.clock.now = float('nan')
        with self.assertRaises(ValueError):
            self.runner.start()
        self.assertNotEqual(self.runner.state, TimelineState.RUNNING)

    def test_callback_failure_stops_timeline(self):
        def fail(_cue, _scheduled):
            raise RuntimeError('render failure')

        runner = SongTimelineRunner(self.library, fail, clock=self.clock)
        runner.load('setlist-main')
        with self.assertRaisesRegex(RuntimeError, 'render failure'):
            runner.start()
        self.assertEqual(runner.state, TimelineState.STOPPED)

    def test_persisted_library_runs_after_application_restart(self):
        restored = SongLibrary(self.path, set(PRESETS))
        activations = []
        runner = SongTimelineRunner(
            restored, lambda cue, scheduled: activations.append((cue.preset_id, scheduled)),
            clock=self.clock,
        )
        runner.load('setlist-main')
        runner.start()
        self.assertEqual(activations, [('psychedelic-bloom', 0.0)])

    def test_timeline_playback_never_constructs_a_network_socket(self):
        with patch('socket.socket', side_effect=AssertionError('no socket')):
            self.runner.start()
            self.clock.now = 9.0
            self.runner.update()
        self.assertEqual(self.runner.state, TimelineState.RUNNING)


if __name__ == '__main__':
    unittest.main()
