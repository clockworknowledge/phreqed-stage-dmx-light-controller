import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from phreqed_dmx.video_edl import parse_video_edl
from phreqed_dmx.video_render import build_ffmpeg_command, render_video_edl
from tests.test_video_edl import composition_document, edl_document


class VideoRenderTests(unittest.TestCase):
    def test_builds_sparse_layered_composition_over_black(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            master = root / "master.mov"
            energy = root / "energy.mp4"
            master.write_bytes(b"master")
            energy.write_bytes(b"energy")
            command = build_ffmpeg_command(
                parse_video_edl(composition_document()),
                {"asset-master": master, "asset-energy": energy},
                root / "stage.mp4",
                ffmpeg_executable="fixed-ffmpeg",
            )
        self.assertIn("lavfi", command)
        self.assertEqual(
            command[command.index("-filter_complex_threads") + 1], "1"
        )
        self.assertIn("color=c=black:s=720x1280:r=30", command)
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("start_duration=4", filters)
        self.assertIn("color=black@0", filters)
        self.assertIn("overlay=shortest=0:eof_action=pass", filters)
        self.assertIn("enable='between(t,4,11)'", filters)
        self.assertIn(
            "blend=all_expr=A+B-A*B/255:all_opacity=0.7", filters
        )
        self.assertIn("hflip,transpose=clock", filters)
        self.assertNotIn("concat=", filters)

    def test_layered_composition_decodes_each_asset_once(self) -> None:
        document = composition_document()
        document["layers"][1]["asset_id"] = "asset-master"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            master = root / "master.mov"
            master.write_bytes(b"master")
            command = build_ffmpeg_command(
                parse_video_edl(document),
                {"asset-master": master},
                root / "stage.mp4",
            )
        self.assertEqual(command.count(str(master.resolve())), 1)
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("split=2[source0][source1]", filters)
        self.assertIn("[source0]trim=start=2:end=9", filters)
        self.assertIn("[source1]trim=start=0:end=4", filters)

    def test_filter_worker_limit_is_explicit_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mov"
            source.write_bytes(b"source")
            command = build_ffmpeg_command(
                parse_video_edl(edl_document()),
                {"asset-master": source},
                root / "stage.mp4",
                filter_threads=4,
            )
            self.assertEqual(
                command[command.index("-filter_complex_threads") + 1], "4"
            )
            with self.assertRaisesRegex(ValueError, "filter threads"):
                build_ffmpeg_command(
                    parse_video_edl(edl_document()),
                    {"asset-master": source},
                    root / "stage.mp4",
                    filter_threads=0,
                )

    def test_builds_shell_free_portrait_ffmpeg_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source video.mov"
            source.write_bytes(b"source")
            output = root / "stage.mp4"
            edl = parse_video_edl(
                edl_document(rotation="clockwise", horizontal_flip=True)
            )
            command = build_ffmpeg_command(
                edl,
                {"asset-master": source},
                output,
                ffmpeg_executable="fixed-ffmpeg",
            )
        self.assertEqual(command[0], "fixed-ffmpeg")
        self.assertIn(str(source.resolve()), command)
        self.assertIn("-filter_complex", command)
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("crop=1080:1920", filters)
        self.assertIn("hflip,transpose=clock", filters)
        self.assertIn("concat=n=1:v=1:a=0", filters)
        self.assertIn("-an", command)
        self.assertNotIn("shell", command)

    def test_renders_checksums_and_prevents_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mov"
            source.write_bytes(b"immutable source")
            edl = parse_video_edl(edl_document())
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                Path(command[-1]).write_bytes(b"rendered h264 bytes")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = render_video_edl(
                edl,
                {"asset-master": source},
                root / "output",
                runner=fake_runner,
            )
            manifest = json.loads(result.manifest_path.read_text())
            self.assertEqual(manifest, result.manifest)
            self.assertFalse(manifest["rendition"]["audio"])
            self.assertEqual(manifest["rendition"]["width"], 1080)
            self.assertEqual(manifest["sources"][0]["asset_id"], "asset-master")
            self.assertTrue(result.video_path.is_file())
            self.assertFalse(calls[0][1]["shell"])
            with self.assertRaises(FileExistsError):
                render_video_edl(
                    edl,
                    {"asset-master": source},
                    root / "output",
                    runner=fake_runner,
                )

    def test_rejects_missing_assets_before_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "missing IDs"):
                build_ffmpeg_command(
                    parse_video_edl(edl_document()), {}, root / "out.mp4"
                )


if __name__ == "__main__":
    unittest.main()
