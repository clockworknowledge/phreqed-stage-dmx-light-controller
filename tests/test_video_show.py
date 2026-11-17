import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phreqed_dmx.presets import PRESETS
from phreqed_dmx.song_timeline import SongTimelineRunner, TimelineState
from phreqed_dmx.songs import SongLibrary
from phreqed_dmx.video_show import (
    ParallelSongTransport,
    SongVideoRunner,
    VideoRunnerState,
    VideoShowLibrary,
    bind_single_song_video_document,
    resolve_song_id_by_title,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeVideoOutput:
    def __init__(self, *, fail_activate: bool = False, fail_check: bool = False) -> None:
        self.calls = []
        self.fail_activate = fail_activate
        self.fail_check = fail_check

    def activate(self, scene, position_seconds, scheduled_at):
        if self.fail_activate:
            raise RuntimeError("player failed")
        self.calls.append(
            ("activate", scene.scene_id, position_seconds, scheduled_at)
        )

    def black(self):
        self.calls.append(("black",))

    def check(self):
        if self.fail_check:
            raise RuntimeError("player exited")


class VideoShowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.song_path = root / "songs.json"
        self.songs = SongLibrary(self.song_path, set(PRESETS))
        self.songs.save(
            {
                "version": 1,
                "songs": [
                    {
                        "song_id": "song-travelling-on-a-floating-rock",
                        "title": "Travelling on a Floating Rock",
                        "artist": "Tori Morley",
                        "duration_seconds": 146.0,
                        "notes": "",
                        "source": "manual",
                        "active_cue_sheet_id": "cue-travelling-v1",
                    },
                    {
                        "song_id": "song-next",
                        "title": "Next",
                        "artist": "Tori Morley",
                        "duration_seconds": 30.0,
                        "notes": "",
                        "source": "manual",
                        "active_cue_sheet_id": "cue-next-v1",
                    },
                ],
                "cue_sheets": [
                    {
                        "cue_sheet_id": "cue-travelling-v1",
                        "song_id": "song-travelling-on-a-floating-rock",
                        "revision": 1,
                        "published": True,
                        "cues": [
                            {
                                "at_seconds": 0.0,
                                "preset_id": "psychedelic-bloom",
                                "transition_seconds": 0.0,
                            },
                            {
                                "at_seconds": 60.0,
                                "preset_id": "molten-motion",
                                "transition_seconds": 1.0,
                            },
                        ],
                    },
                    {
                        "cue_sheet_id": "cue-next-v1",
                        "song_id": "song-next",
                        "revision": 1,
                        "published": True,
                        "cues": [
                            {
                                "at_seconds": 0.0,
                                "preset_id": "digital-storm",
                                "transition_seconds": 0.0,
                            }
                        ],
                    },
                ],
                "setlists": [
                    {
                        "setlist_id": "setlist-show",
                        "name": "Show",
                        "song_ids": [
                            "song-travelling-on-a-floating-rock",
                            "song-next",
                        ],
                        "notes": "",
                    }
                ],
            }
        )
        self.video_path = root / "video-show.json"
        self.video = VideoShowLibrary(self.video_path, self.songs)

    @staticmethod
    def document():
        return {
            "version": 1,
            "scenes": [
                {
                    "scene_id": "vscene-travelling-main",
                    "name": "Travelling portrait characters",
                    "package_id": (
                        "travelling-floating-rock-stage-portrait--"
                        "stage-portrait-hdmi720-clockwise-rear"
                    ),
                    "surface_id": "portrait-character",
                    "loop": False,
                }
            ],
            "tracks": [
                {
                    "track_id": "vtrack-travelling-v1",
                    "song_id": "song-travelling-on-a-floating-rock",
                    "revision": 1,
                    "published": True,
                    "cues": [
                        {"at_seconds": 0.0, "scene_id": "vscene-travelling-main"},
                        {"at_seconds": 4.0, "scene_id": None},
                        {"at_seconds": 6.0, "scene_id": "vscene-travelling-main"},
                    ],
                }
            ],
            "active_tracks": [
                {
                    "song_id": "song-travelling-on-a-floating-rock",
                    "track_id": "vtrack-travelling-v1",
                }
            ],
        }

    def test_sidecar_round_trip_never_changes_existing_song_library(self):
        songs_before = self.song_path.read_bytes()
        document = self.document()
        self.video.save(document)
        restored = VideoShowLibrary(self.video_path, self.songs)
        self.assertEqual(restored.document(), document)
        self.assertEqual(self.song_path.read_bytes(), songs_before)

    def test_travelling_reference_sidecar_is_valid_and_starts_at_zero(self):
        example_path = (
            Path(__file__).parents[1]
            / "examples"
            / "video"
            / "travelling-on-a-floating-rock.video-show.json"
        )
        document = json.loads(example_path.read_text(encoding="utf-8"))
        self.video.save(document)
        track = self.video.active_track("song-travelling-on-a-floating-rock")
        self.assertIsNotNone(track)
        self.assertEqual(track.cues[0].at_seconds, 0.0)
        self.assertEqual(
            self.video.scenes[track.cues[0].scene_id].surface_id,
            "portrait-character",
        )

    def test_reference_binds_exact_title_to_existing_song_id(self):
        document = self.document()
        document["tracks"][0]["song_id"] = "song-template-placeholder"
        document["active_tracks"][0]["song_id"] = "song-template-placeholder"
        bound = bind_single_song_video_document(
            document, self.songs, "  TRAVELLING ON A FLOATING ROCK  "
        )
        self.assertEqual(
            bound["tracks"][0]["song_id"],
            "song-travelling-on-a-floating-rock",
        )
        self.assertEqual(document["tracks"][0]["song_id"], "song-template-placeholder")
        self.assertEqual(
            resolve_song_id_by_title(self.songs, "Travelling on a Floating Rock"),
            "song-travelling-on-a-floating-rock",
        )
        with self.assertRaisesRegex(ValueError, "not present"):
            resolve_song_id_by_title(self.songs, "Missing")

    def test_rejects_bad_references_and_preserves_published_revisions(self):
        document = self.document()
        self.video.save(document)
        invalid = copy.deepcopy(document)
        invalid["tracks"][0]["cues"][0]["scene_id"] = "vscene-missing"
        with self.assertRaisesRegex(ValueError, "unknown Video Scene"):
            self.video.save(invalid)
        changed = copy.deepcopy(document)
        changed["scenes"][0]["package_id"] = "replacement--portrait"
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.video.save(changed)

    def test_parallel_transport_uses_shared_clock_and_skips_stale_video_cues(self):
        self.video.save(self.document())
        clock = FakeClock()
        lighting_calls = []
        lighting = SongTimelineRunner(
            self.songs,
            lambda cue, scheduled: lighting_calls.append(
                (cue.preset_id, scheduled)
            ),
            clock=clock,
        )
        output = FakeVideoOutput()
        video = SongVideoRunner(self.video, output)
        transport = ParallelSongTransport(lighting, video)
        transport.load("setlist-show")
        clock.now = 100.0
        transport.start()
        self.assertEqual(lighting_calls[0], ("psychedelic-bloom", 100.0))
        self.assertEqual(
            output.calls[-1],
            ("activate", "vscene-travelling-main", 0.0, 100.0),
        )
        clock.now = 107.5
        transport.update()
        self.assertEqual(
            output.calls[-1],
            ("activate", "vscene-travelling-main", 1.5, 106.0),
        )
        self.assertEqual(video.state, VideoRunnerState.RUNNING)
        clock.now = 246.0
        transport.update()
        self.assertEqual(lighting.state, TimelineState.ARMED)
        self.assertEqual(output.calls[-1], ("black",))
        self.assertEqual(video.state, VideoRunnerState.BLACK)

    def test_video_failure_blacks_video_without_stopping_lighting(self):
        self.video.save(self.document())
        clock = FakeClock()
        lighting = SongTimelineRunner(
            self.songs, lambda _cue, _scheduled: None, clock=clock
        )
        output = FakeVideoOutput(fail_activate=True)
        video = SongVideoRunner(self.video, output)
        transport = ParallelSongTransport(lighting, video)
        transport.load("setlist-show")
        transport.start()
        self.assertEqual(lighting.state, TimelineState.RUNNING)
        self.assertEqual(video.state, VideoRunnerState.ERROR)
        self.assertEqual(video.last_error, "player failed")
        clock.now = 61.0
        transport.update()
        self.assertEqual(lighting.state, TimelineState.RUNNING)

    def test_unexpected_player_exit_blacks_video_without_stopping_lighting(self):
        self.video.save(self.document())
        clock = FakeClock()
        lighting = SongTimelineRunner(
            self.songs, lambda _cue, _scheduled: None, clock=clock
        )
        output = FakeVideoOutput()
        video = SongVideoRunner(self.video, output)
        transport = ParallelSongTransport(lighting, video)
        transport.load("setlist-show")
        transport.start()
        output.fail_check = True
        clock.now = 1.0
        transport.update()
        self.assertEqual(video.state, VideoRunnerState.ERROR)
        self.assertEqual(video.last_error, "player exited")
        self.assertEqual(lighting.state, TimelineState.RUNNING)
        self.assertEqual(output.calls[-1], ("black",))

    def test_storage_and_parallel_timing_never_open_a_socket(self):
        with patch("socket.socket", side_effect=AssertionError("no socket")):
            self.video.save(self.document())
            output = FakeVideoOutput()
            runner = SongVideoRunner(self.video, output)
            runner.start("song-travelling-on-a-floating-rock", 0.0)
            runner.sync(10.0)
        self.assertEqual(runner.state, VideoRunnerState.RUNNING)


if __name__ == "__main__":
    unittest.main()
