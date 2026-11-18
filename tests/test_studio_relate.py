from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from phreqed_dmx.studio_catalog import StoryletMarker, StudioCatalog
from phreqed_dmx.studio_relate import StudioRelateGraph
from phreqed_dmx.studio_web import StudioController


RELATE_AVAILABLE = importlib.util.find_spec("relate") is not None


@unittest.skipUnless(RELATE_AVAILABLE, "relate-db optional dependency is unavailable")
class StudioRelateGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        source = root / "heart-zones.png"
        source.write_bytes(b"heart-zones-reference")
        self.catalog = StudioCatalog(root / "catalog")
        self.asset = self.catalog.import_asset(
            source, title="Heart Zones", family="brand-artwork"
        )
        self.storylet = self.catalog.create_storylet(
            storylet_id="storylet-heart-zones-v1",
            asset_id=self.asset.asset_id,
            title="Heart Zones pulse",
            duration_seconds=20.0,
            loop=True,
            markers=(
                StoryletMarker("pulse", 2.0),
                StoryletMarker("discharge", 14.0),
                StoryletMarker("recover", 20.0),
            ),
        )
        self.graph = StudioRelateGraph(root / "relate")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_sync_is_idempotent_durable_and_queryable(self) -> None:
        expected = self.catalog.graph_projection()
        first = self.graph.sync_projection(expected)
        second = self.graph.sync_projection(expected)
        self.assertEqual(first["nodes"], len(expected["nodes"]))
        self.assertEqual(first["relationships"], len(expected["relationships"]))
        self.assertEqual(second["nodes"], first["nodes"])
        self.assertEqual(second["relationships"], first["relationships"])
        self.assertEqual(second["durability"], "full")

        reopened = StudioRelateGraph(self.graph.store)
        state = reopened.state(self.catalog.workspace_id)
        self.assertEqual(state["nodes"], first["nodes"])
        lineage = reopened.asset_lineage(
            self.catalog.workspace_id, self.asset.asset_id
        )
        self.assertEqual(
            [row["marker_name"] for row in lineage],
            ["pulse", "discharge", "recover"],
        )
        matches = reopened.find_storylets(
            self.catalog.workspace_id,
            minimum_seconds=15.0,
            maximum_seconds=30.0,
            loop=True,
        )
        self.assertEqual(
            [row["storylet_id"] for row in matches],
            [self.storylet.storylet_id],
        )

        browser = StudioController(self.catalog, relate_graph=reopened)
        browser_result = browser.command({"action": "sync_relate"})
        self.assertEqual(browser_result["state"]["relate"]["status"], "ready")
        self.assertEqual(browser_result["relate"]["nodes"], first["nodes"])

    def test_rejects_single_file_store_and_invalid_projection(self) -> None:
        with self.assertRaisesRegex(ValueError, "directory store"):
            StudioRelateGraph(self.graph.store.with_suffix(".rl"))
        with self.assertRaisesRegex(ValueError, "workspace ID"):
            self.graph.sync_projection(
                {"workspace_id": "bad", "nodes": [], "relationships": []}
            )
        with patch.dict(os.environ, {"RELATE_DURABILITY_MODE": "snapshot"}):
            with self.assertRaisesRegex(ValueError, "full durability"):
                StudioRelateGraph(self.graph.store)


if __name__ == "__main__":
    unittest.main()
