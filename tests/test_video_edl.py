import json
import tempfile
import unittest
from pathlib import Path

from phreqed_dmx.video_edl import (
    VideoComposition,
    load_asset_map,
    load_video_edl,
    parse_asset_map,
    parse_video_edl,
)


def edl_document(
    *, rotation: str = "none", horizontal_flip: bool = False
) -> dict:
    document = {
        "version": 1,
        "edl_id": "video-edl-test",
        "title": "Test projection",
        "projection": {
            "profile_id": "portrait-test",
            "canvas_width": 1080,
            "canvas_height": 1920,
            "output_rotation": rotation,
            "frame_rate": 30.0,
        },
        "clips": [
            {
                "clip_id": "clip-opening",
                "asset_id": "asset-master",
                "source_in_seconds": 2.0,
                "source_out_seconds": 7.0,
                "fit_mode": "cover",
                "focal_x": 0.4,
                "focal_y": 0.6,
                "fade_in_seconds": 0.25,
                "fade_out_seconds": 0.5,
            }
        ],
    }
    if horizontal_flip:
        document["projection"]["horizontal_flip"] = True
    return document


def composition_document() -> dict:
    return {
        "version": 2,
        "edl_id": "video-composition-test",
        "title": "Sparse hybrid projection",
        "projection": {
            "profile_id": "portrait-test",
            "canvas_width": 720,
            "canvas_height": 1280,
            "output_rotation": "clockwise",
            "frame_rate": 30.0,
            "horizontal_flip": True,
        },
        "duration_seconds": 30.0,
        "layers": [
            {
                "layer_id": "master-fragment",
                "asset_id": "asset-master",
                "at_seconds": 4.0,
                "source_in_seconds": 2.0,
                "source_out_seconds": 9.0,
                "fit_mode": "cover",
                "focal_x": 0.4,
                "focal_y": 0.6,
                "opacity": 1.0,
                "blend_mode": "normal",
                "fade_in_seconds": 0.5,
                "fade_out_seconds": 0.5,
            },
            {
                "layer_id": "energy-overlay",
                "asset_id": "asset-energy",
                "at_seconds": 6.0,
                "source_in_seconds": 0.0,
                "source_out_seconds": 4.0,
                "fit_mode": "cover",
                "focal_x": 0.5,
                "focal_y": 0.5,
                "opacity": 0.7,
                "blend_mode": "screen",
                "fade_in_seconds": 0.25,
                "fade_out_seconds": 0.75,
            },
        ],
    }


class VideoEdlTests(unittest.TestCase):
    def test_round_trips_sparse_layered_composition(self) -> None:
        composition = parse_video_edl(composition_document())
        self.assertIsInstance(composition, VideoComposition)
        self.assertEqual(composition.as_dict(), composition_document())
        self.assertEqual(composition.duration_seconds, 30.0)
        self.assertEqual(composition.layers[0].end_seconds, 11.0)

    def test_stage_layout_profiles_keep_layout_and_projection_side_separate(self):
        examples = Path(__file__).parents[1] / "examples" / "video"
        portrait = load_video_edl(
            examples / "travelling-fifteen-second-stage-portrait-rear.edl.json"
        )
        landscape = load_video_edl(
            examples / "travelling-fifteen-second-stage-landscape-front.edl.json"
        )
        self.assertEqual(portrait.projection.output_dimensions, (1280, 720))
        self.assertEqual(landscape.projection.output_dimensions, (1280, 720))
        self.assertEqual(
            (portrait.projection.canvas_width, portrait.projection.canvas_height),
            (720, 1280),
        )
        self.assertEqual(
            (landscape.projection.canvas_width, landscape.projection.canvas_height),
            (1280, 720),
        )
        self.assertTrue(portrait.projection.horizontal_flip)
        self.assertFalse(landscape.projection.horizontal_flip)
        self.assertEqual(portrait.clips[0].fit_mode, "cover")
        self.assertEqual(landscape.clips[0].fit_mode, "cover")

    def test_travelling_hybrid_is_sparse_and_song_length(self) -> None:
        examples = Path(__file__).parents[1] / "examples" / "video"
        composition = load_video_edl(
            examples / "travelling-on-a-floating-rock-hybrid-v1.edl.json"
        )
        self.assertIsInstance(composition, VideoComposition)
        self.assertEqual(composition.duration_seconds, 180.0)
        self.assertEqual(composition.projection.output_dimensions, (1280, 720))
        intervals = sorted(
            (layer.at_seconds, layer.end_seconds) for layer in composition.layers
        )
        merged: list[list[float]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        visible_seconds = sum(end - start for start, end in merged)
        self.assertGreaterEqual(visible_seconds, 60.0)
        self.assertLessEqual(visible_seconds, 75.0)
        self.assertTrue(any(
            right[0] - left[1] >= 15.0
            for left, right in zip(merged, merged[1:])
        ))

    def test_round_trips_versioned_non_destructive_edl(self) -> None:
        edl = parse_video_edl(edl_document())
        self.assertEqual(edl.as_dict(), edl_document())
        self.assertEqual(edl.duration_seconds, 5.0)
        self.assertEqual(edl.projection.output_dimensions, (1080, 1920))
        self.assertFalse(edl.projection.horizontal_flip)
        self.assertNotIn("horizontal_flip", edl.as_dict()["projection"])
        rotated = parse_video_edl(edl_document(rotation="clockwise"))
        self.assertEqual(rotated.projection.output_dimensions, (1920, 1080))
        mirrored = parse_video_edl(edl_document(horizontal_flip=True))
        self.assertTrue(mirrored.projection.horizontal_flip)
        self.assertTrue(mirrored.as_dict()["projection"]["horizontal_flip"])
        self.assertNotIn(b"filesystem", edl.canonical_bytes())

    def test_loads_edl_and_local_asset_map_without_embedding_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            edl_path = root / "test.edl.json"
            assets_path = root / "assets.json"
            source = root / "source.mov"
            source.write_bytes(b"source")
            edl_path.write_text(json.dumps(edl_document()), encoding="utf-8")
            assets_path.write_text(json.dumps({
                "version": 1,
                "assets": {"asset-master": str(source)},
            }), encoding="utf-8")
            self.assertEqual(load_video_edl(edl_path).edl_id, "video-edl-test")
            self.assertEqual(load_asset_map(assets_path), {"asset-master": source})

    def test_rejects_unsafe_or_invalid_edit_decisions(self) -> None:
        invalid = edl_document()
        invalid["clips"][0]["source_out_seconds"] = 1.0
        with self.assertRaisesRegex(ValueError, "source out"):
            parse_video_edl(invalid)
        invalid = edl_document()
        invalid["clips"][0]["fade_in_seconds"] = 4.8
        invalid["clips"][0]["fade_out_seconds"] = 0.5
        with self.assertRaisesRegex(ValueError, "fades"):
            parse_video_edl(invalid)
        invalid = edl_document()
        invalid["projection"]["canvas_width"] = 1079
        with self.assertRaisesRegex(ValueError, "canvas width"):
            parse_video_edl(invalid)
        invalid = edl_document()
        invalid["projection"]["frame_rate"] = 60.0
        with self.assertRaisesRegex(ValueError, "frame rate"):
            parse_video_edl(invalid)
        invalid = edl_document()
        invalid["projection"]["canvas_width"] = 1920
        invalid["projection"]["canvas_height"] = 1920
        with self.assertRaisesRegex(ValueError, "1080p target"):
            parse_video_edl(invalid)
        invalid = edl_document()
        invalid["projection"]["horizontal_flip"] = "yes"
        with self.assertRaisesRegex(ValueError, "horizontal flip"):
            parse_video_edl(invalid)
        with self.assertRaisesRegex(ValueError, "local filesystem"):
            parse_asset_map({
                "version": 1,
                "assets": {"asset-master": "https://example.com/video.mp4"},
            })

    def test_rejects_invalid_layer_timing_and_blend(self) -> None:
        invalid = composition_document()
        invalid["layers"][0]["at_seconds"] = 28.0
        with self.assertRaisesRegex(ValueError, "exceeds its duration"):
            parse_video_edl(invalid)
        invalid = composition_document()
        invalid["layers"][0]["blend_mode"] = "multiply"
        with self.assertRaisesRegex(ValueError, "blend mode"):
            parse_video_edl(invalid)
        invalid = composition_document()
        invalid["layers"][0]["opacity"] = 1.5
        with self.assertRaisesRegex(ValueError, "layer opacity"):
            parse_video_edl(invalid)


if __name__ == "__main__":
    unittest.main()
