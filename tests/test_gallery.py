import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phreqed_dmx.config import load_config
from phreqed_dmx.effect_library import EFFECT_REGISTRY
from phreqed_dmx.gallery import generate_effect_gallery
from phreqed_dmx.presets import PRESETS


class EffectGalleryTests(unittest.TestCase):
    def test_generates_deterministic_hardware_free_gallery(self) -> None:
        config = load_config()
        with (
            tempfile.TemporaryDirectory() as first_directory,
            tempfile.TemporaryDirectory() as second_directory,
        ):
            with patch("socket.socket") as socket_constructor:
                first = generate_effect_gallery(
                    config,
                    first_directory,
                    effect_ids=("plasma", "cartoon-bomb"),
                    preset_ids=("psychedelic-bloom", "burning-fuse"),
                    times=(0.0, 1.75),
                    pixel_size=3,
                    gap=2,
                )
            second = generate_effect_gallery(
                config,
                second_directory,
                effect_ids=("plasma", "cartoon-bomb"),
                preset_ids=("psychedelic-bloom", "burning-fuse"),
                times=(0.0, 1.75),
                pixel_size=3,
                gap=2,
            )

            socket_constructor.assert_not_called()
            self.assertEqual(first, second)
            self.assertFalse(first["hardware_output"])
            self.assertEqual(len(first["items"]), 4)
            self.assertEqual(
                json.loads((Path(first_directory) / "manifest.json").read_text()),
                first,
            )
            self.assertIn(
                "Deterministic RGB simulator frames",
                (Path(first_directory) / "index.html").read_text(),
            )
            for item in first["items"]:
                for frame in item["frames"]:
                    content = (Path(first_directory) / frame["file"]).read_bytes()
                    self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_default_catalog_covers_every_builtin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_effect_gallery(
                load_config(), directory, times=(1.0,), pixel_size=1, gap=0
            )
        effects = {
            item["id"] for item in manifest["items"] if item["kind"] == "effect"
        }
        presets = {
            item["id"] for item in manifest["items"] if item["kind"] == "preset"
        }
        self.assertEqual(
            effects,
            {metadata.effect_id for metadata in EFFECT_REGISTRY.metadata()},
        )
        self.assertEqual(presets, set(PRESETS))

    def test_rejects_unknown_ids_and_invalid_times(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unknown effect"):
                generate_effect_gallery(
                    load_config(), directory, effect_ids=("missing",)
                )
            with self.assertRaisesRegex(ValueError, "finite and nonnegative"):
                generate_effect_gallery(load_config(), directory, times=(-1.0,))


if __name__ == "__main__":
    unittest.main()
