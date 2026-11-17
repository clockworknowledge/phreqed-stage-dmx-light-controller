from __future__ import annotations

import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from phreqed_dmx.presets import PRESETS
from phreqed_dmx.songs import SongLibrary
from tests.test_projection import write_package


SCRIPT = runpy.run_path(
    str(
        Path(__file__).parents[1]
        / "scripts"
        / "install-travelling-video-track.py"
    ),
    run_name="install_travelling_video_track",
)
main = SCRIPT["main"]


class InstallTravellingVideoTrackTests(unittest.TestCase):
    def test_binds_real_song_id_without_changing_existing_song_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packages = root / "packages"
            packages.mkdir()
            write_package(packages)
            songs_path = root / "songs.json"
            songs = SongLibrary(songs_path, set(PRESETS))
            songs.save({
                "version": 1,
                "songs": [{
                    "song_id": "song-real-pi-id",
                    "title": "Travelling on a Floating Rock",
                    "artist": "Tori Morley",
                    "duration_seconds": 146.0,
                    "notes": "",
                    "source": "manual",
                    "active_cue_sheet_id": "cue-real-v1",
                }],
                "cue_sheets": [{
                    "cue_sheet_id": "cue-real-v1",
                    "song_id": "song-real-pi-id",
                    "revision": 1,
                    "published": True,
                    "cues": [{
                        "at_seconds": 0.0,
                        "preset_id": "psychedelic-bloom",
                        "transition_seconds": 0.0,
                    }],
                }],
                "setlists": [{
                    "setlist_id": "setlist-current",
                    "name": "Current",
                    "song_ids": ["song-real-pi-id"],
                    "notes": "",
                }],
            })
            songs_before = songs_path.read_bytes()
            template_path = root / "template.json"
            template_path.write_text(json.dumps({
                "version": 1,
                "scenes": [{
                    "scene_id": "vscene-test",
                    "name": "Test",
                    "package_id": "video-edl-test--portrait-test",
                    "surface_id": "portrait-character",
                    "loop": False,
                }],
                "tracks": [{
                    "track_id": "vtrack-test-v1",
                    "song_id": "song-placeholder",
                    "revision": 1,
                    "published": True,
                    "cues": [{"at_seconds": 0.0, "scene_id": "vscene-test"}],
                }],
                "active_tracks": [{
                    "song_id": "song-placeholder",
                    "track_id": "vtrack-test-v1",
                }],
            }), encoding="utf-8")
            output_path = root / "video-show.json"
            arguments = [
                "install-travelling-video-track.py",
                "--songs", str(songs_path),
                "--video-show", str(output_path),
                "--packages", str(packages),
                "--template", str(template_path),
            ]
            with patch("sys.argv", arguments):
                self.assertEqual(main(), 0)
            installed = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(installed["tracks"][0]["song_id"], "song-real-pi-id")
            self.assertEqual(songs_path.read_bytes(), songs_before)
            with patch("sys.argv", arguments):
                self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
