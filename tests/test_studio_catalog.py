from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from phreqed_dmx.studio_catalog import StoryletMarker, StudioCatalog


class StudioCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "studio"
        self.source = self.root / "heart-zones.png"
        self.source.write_bytes(b"original-heart-zones-art")
        self.catalog = StudioCatalog(self.workspace)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_import_is_content_addressed_atomic_and_idempotent(self) -> None:
        asset = self.catalog.import_asset(
            self.source,
            title="Heart Zones",
            family="brand-artwork",
        )
        expected_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertEqual(asset.sha256, expected_hash)
        self.assertEqual(
            self.catalog.blob_path(expected_hash).read_bytes(),
            self.source.read_bytes(),
        )
        self.assertIs(
            self.catalog.import_asset(
                self.source,
                title="A title that cannot mutate the immutable import",
                family="other",
            ),
            asset,
        )
        document = json.loads(self.catalog.catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(len(document["assets"]), 1)
        self.assertEqual(document["assets"][0]["title"], "Heart Zones")
        self.assertEqual(
            len(self.catalog.events_path.read_text(encoding="utf-8").splitlines()),
            1,
        )

    def test_storylet_markers_round_trip_and_graph_projection(self) -> None:
        asset = self.catalog.import_asset(self.source, family="brand-artwork")
        storylet = self.catalog.create_storylet(
            storylet_id="storylet-heart-zones-v1",
            asset_id=asset.asset_id,
            title="Heart Zones pulse",
            duration_seconds=20.0,
            loop=True,
            markers=(
                StoryletMarker("pulse-a", 2.0),
                StoryletMarker("discharge", 14.0),
                StoryletMarker("recover", 20.0),
            ),
        )
        restored = StudioCatalog(self.workspace)
        self.assertEqual(restored.storylets[storylet.storylet_id], storylet)
        projection = restored.graph_projection()
        node_ids = {node["id"] for node in projection["nodes"]}
        self.assertIn(asset.asset_id, node_ids)
        self.assertIn(storylet.storylet_id, node_ids)
        self.assertTrue(
            any(
                relationship["type"] == "DERIVED_FROM"
                and relationship["from"] == storylet.storylet_id
                and relationship["to"] == asset.asset_id
                for relationship in projection["relationships"]
            )
        )
        exported = restored.export_graph()
        self.assertEqual(json.loads(exported.read_text())["workspace_id"], "workspace-local")

    def test_rejects_bad_sources_families_and_marker_boundaries(self) -> None:
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.catalog.import_asset(self.root / "missing.mov")
        with self.assertRaisesRegex(ValueError, "family"):
            self.catalog.import_asset(self.source, family="unknown")
        asset = self.catalog.import_asset(self.source)
        with self.assertRaisesRegex(ValueError, "ordered"):
            self.catalog.create_storylet(
                storylet_id="storylet-bad-order",
                asset_id=asset.asset_id,
                title="Bad order",
                duration_seconds=10.0,
                loop=False,
                markers=(StoryletMarker("late", 9.0), StoryletMarker("early", 1.0)),
            )
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.catalog.create_storylet(
                storylet_id="storylet-bad-duration",
                asset_id=asset.asset_id,
                title="Bad duration",
                duration_seconds=5.0,
                loop=False,
                markers=(StoryletMarker("impact", 6.0),),
            )

    def test_loading_rejects_unknown_asset_references(self) -> None:
        self.workspace.mkdir(parents=True)
        self.catalog.catalog_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "workspace_id": "workspace-local",
                    "assets": [],
                    "storylets": [
                        {
                            "storylet_id": "storylet-orphan",
                            "asset_id": "asset-000000000000000000000000",
                            "title": "Orphan",
                            "duration_seconds": 1.0,
                            "loop": False,
                            "markers": [{"name": "black", "at_seconds": 1.0}],
                            "created_utc": "2026-11-18T00:00:00+00:00",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "unknown asset"):
            StudioCatalog(self.workspace)


if __name__ == "__main__":
    unittest.main()
