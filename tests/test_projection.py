import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phreqed_dmx.projection import (
    ProjectionPackageRegistry,
    ProjectionController,
    load_stage_video_package,
)
from phreqed_dmx.video_edl import parse_video_edl
from tests.test_video_edl import edl_document


class FakeProjectionBackend:
    def __init__(self) -> None:
        self.calls = []

    def load(self, path): self.calls.append(("load", path))
    def play(self, position_seconds): self.calls.append(("play", position_seconds))
    def pause(self): self.calls.append(("pause",))
    def seek(self, position_seconds): self.calls.append(("seek", position_seconds))
    def stop(self): self.calls.append(("stop",))
    def set_black(self, enabled): self.calls.append(("black", enabled))
    def close(self): self.calls.append(("close",))


def write_package(root: Path) -> Path:
    video = root / "video.mp4"
    content = b"fake stage rendition"
    video.write_bytes(content)
    edl = parse_video_edl(edl_document())
    manifest = {
        "version": 1,
        "package_id": "video-edl-test--portrait-test",
        "edl_sha256": hashlib.sha256(edl.canonical_bytes()).hexdigest(),
        "edl": edl.as_dict(),
        "duration_seconds": 5.0,
        "sources": [{
            "asset_id": "asset-master",
            "size_bytes": 123,
            "sha256": "1" * 64,
        }],
        "rendition": {
            "file": video.name,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "width": 1080,
            "height": 1920,
            "frame_rate": 30.0,
            "video_codec": "h264-high-4.1",
            "pixel_format": "yuv420p",
            "audio": False,
        },
    }
    path = root / "video.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


class ProjectionTests(unittest.TestCase):
    def test_registry_preflights_and_resolves_only_local_package_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_package(root)
            registry = ProjectionPackageRegistry(root)
            packages = registry.refresh()
            self.assertEqual(list(packages), ["video-edl-test--portrait-test"])
            self.assertEqual(
                registry.resolve("video-edl-test--portrait-test").manifest_path,
                manifest.resolve(),
            )
            with self.assertRaisesRegex(ValueError, "unavailable"):
                registry.resolve("missing--portrait")

            duplicate = root / "duplicate.manifest.json"
            duplicate.write_bytes(manifest.read_bytes())
            with self.assertRaisesRegex(ValueError, "duplicate projection package"):
                registry.refresh()

    def test_projection_is_disabled_and_black_without_a_backend(self) -> None:
        controller = ProjectionController()
        self.assertEqual(controller.status(), {
            "enabled": False,
            "state": "disabled",
            "output_black": True,
            "package_id": None,
            "position_seconds": 0.0,
        })
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            controller.play()

    def test_preflights_then_controls_injected_backend(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_package(Path(directory))
            backend = FakeProjectionBackend()
            controller = ProjectionController(backend)
            package = controller.load(manifest)
            controller.play(1.5)
            controller.pause()
            controller.seek(4.0)
            controller.black()
            controller.stop()
            controller.close()
        self.assertEqual(package.width, 1080)
        self.assertEqual(backend.calls[:4], [
            ("black", True),
            ("load", package.video_path),
            ("play", 1.5),
            ("black", False),
        ])
        self.assertTrue(controller.status()["output_black"])

    def test_tampered_or_escaping_rendition_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = write_package(root)
            (root / "video.mp4").write_bytes(b"tampered")
            backend = FakeProjectionBackend()
            controller = ProjectionController(backend)
            with self.assertRaisesRegex(ValueError, "size does not match"):
                controller.load(manifest_path)
            self.assertEqual(backend.calls, [("black", True)])
            self.assertEqual(controller.status()["state"], "error")
            self.assertTrue(controller.status()["output_black"])
            with self.assertRaisesRegex(ValueError, "size does not match"):
                load_stage_video_package(manifest_path)
            document = json.loads(manifest_path.read_text())
            document["rendition"]["file"] = "../video.mp4"
            manifest_path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "local MP4 filename"):
                load_stage_video_package(manifest_path)


if __name__ == "__main__":
    unittest.main()
