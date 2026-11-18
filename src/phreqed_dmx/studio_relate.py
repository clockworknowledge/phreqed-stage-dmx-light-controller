"""Durable Relate projection and allowlisted Studio graph queries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


PINNED_RELATE_VERSION = "1.0.1"
MAX_QUERY_ROWS = 200


def _relate() -> Any:
    try:
        import relate
    except ImportError as exc:
        raise RuntimeError(
            "Relate support requires the studio-graph extra: "
            "python -m pip install -e .[studio-graph]"
        ) from exc
    if relate.__version__ != PINNED_RELATE_VERSION:
        raise RuntimeError(
            f"Relate {PINNED_RELATE_VERSION} is required; found "
            f"{relate.__version__}"
        )
    return relate


def _records(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"graph projection {label} must be a list of objects")
    return value


def _projection_groups(
    projection: object,
) -> tuple[str, dict[str, list[dict]], dict[str, list[dict]]]:
    if not isinstance(projection, dict):
        raise ValueError("graph projection must be an object")
    workspace_id = projection.get("workspace_id")
    if not isinstance(workspace_id, str) or not workspace_id.startswith("workspace-"):
        raise ValueError("graph projection workspace ID is invalid")
    nodes = _records(projection.get("nodes"), "nodes")
    relationships = _records(projection.get("relationships"), "relationships")
    node_groups = {
        "Workspace": [],
        "AssetRevision": [],
        "StoryletRevision": [],
        "Marker": [],
    }
    for node in nodes:
        labels = node.get("labels")
        node_id = node.get("id")
        properties = node.get("properties")
        if (
            not isinstance(labels, list)
            or len(labels) != 1
            or labels[0] not in node_groups
            or not isinstance(node_id, str)
            or not isinstance(properties, dict)
        ):
            raise ValueError("graph projection node is invalid")
        node_groups[labels[0]].append(
            {**properties, "id": node_id, "workspace_id": workspace_id}
        )
    relationship_groups = {
        "OWNS_ASSET": [],
        "DERIVED_FROM": [],
        "HAS_MARKER": [],
    }
    all_node_ids = [item["id"] for items in node_groups.values() for item in items]
    node_ids = set(all_node_ids)
    if len(node_ids) != len(all_node_ids):
        raise ValueError("graph projection contains duplicate node IDs")
    if (
        len(node_groups["Workspace"]) != 1
        or node_groups["Workspace"][0]["id"] != workspace_id
    ):
        raise ValueError("graph projection requires its workspace node")
    for relationship in relationships:
        kind = relationship.get("type")
        start = relationship.get("from")
        end = relationship.get("to")
        properties = relationship.get("properties")
        if (
            kind not in relationship_groups
            or start not in node_ids
            or end not in node_ids
            or properties != {}
        ):
            raise ValueError("graph projection relationship is invalid")
        relationship_groups[kind].append({"from": start, "to": end})
    return workspace_id, node_groups, relationship_groups


class StudioRelateGraph:
    """One-writer durable Studio graph with bounded, allowlisted reads."""

    def __init__(self, store: Path) -> None:
        selected = store.expanduser().resolve()
        if selected.suffix == ".rl":
            raise ValueError("Studio requires a Relate directory store")
        durability = os.environ.get("RELATE_DURABILITY_MODE", "full").lower()
        if durability != "full":
            raise ValueError("Studio requires Relate full durability")
        self.store = selected

    def _connect(self, *, read_only: bool = False):
        relate = _relate()
        return relate.connect(str(self.store), read_only=read_only)

    @staticmethod
    def _create_schema(connection: Any) -> None:
        connection.execute(
            "CREATE CONSTRAINT studio_entity_id IF NOT EXISTS "
            "FOR (n:StudioEntity) REQUIRE n.id IS UNIQUE"
        )
        connection.execute(
            "CREATE INDEX studio_workspace IF NOT EXISTS "
            "FOR (n:StudioEntity) ON (n.workspace_id)"
        )

    def sync_projection(self, projection: object) -> dict:
        workspace_id, nodes, relationships = _projection_groups(projection)
        connection = self._connect()
        try:
            self._create_schema(connection)
            connection.autocommit = False
            try:
                connection.execute(
                    "UNWIND $items AS item "
                    "MERGE (n:StudioEntity:Workspace {id: item.id}) "
                    "SET n.workspace_id = item.workspace_id",
                    {"items": nodes["Workspace"]},
                )
                connection.execute(
                    "UNWIND $items AS item "
                    "MERGE (n:StudioEntity:AssetRevision {id: item.id}) "
                    "SET n.workspace_id = item.workspace_id, "
                    "n.asset_id = item.asset_id, n.sha256 = item.sha256, "
                    "n.size_bytes = item.size_bytes, n.media_type = item.media_type, "
                    "n.original_name = item.original_name, n.title = item.title, "
                    "n.family = item.family, n.created_utc = item.created_utc",
                    {"items": nodes["AssetRevision"]},
                )
                connection.execute(
                    "UNWIND $items AS item "
                    "MERGE (n:StudioEntity:StoryletRevision {id: item.id}) "
                    "SET n.workspace_id = item.workspace_id, "
                    "n.storylet_id = item.storylet_id, n.asset_id = item.asset_id, "
                    "n.title = item.title, n.duration_seconds = item.duration_seconds, "
                    "n.loop = item.loop, n.created_utc = item.created_utc",
                    {"items": nodes["StoryletRevision"]},
                )
                connection.execute(
                    "UNWIND $items AS item "
                    "MERGE (n:StudioEntity:Marker {id: item.id}) "
                    "SET n.workspace_id = item.workspace_id, n.name = item.name, "
                    "n.at_seconds = item.at_seconds",
                    {"items": nodes["Marker"]},
                )
                for kind in ("OWNS_ASSET", "DERIVED_FROM", "HAS_MARKER"):
                    connection.execute(
                        f"UNWIND $items AS item "
                        "MATCH (a:StudioEntity {id: item.from}) "
                        "MATCH (b:StudioEntity {id: item.to}) "
                        f"MERGE (a)-[:{kind}]->(b)",
                        {"items": relationships[kind]},
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            connection.flush()
        finally:
            connection.close()
        return self.state(workspace_id)

    def state(self, workspace_id: str) -> dict:
        connection = self._connect(read_only=True)
        try:
            node_row = connection.execute(
                "MATCH (n:StudioEntity {workspace_id: $workspace_id}) "
                "RETURN count(n) AS total",
                {"workspace_id": workspace_id},
            ).single()
            relationship_row = connection.execute(
                "MATCH (a:StudioEntity {workspace_id: $workspace_id})-[r]->"
                "(b:StudioEntity {workspace_id: $workspace_id}) "
                "RETURN count(r) AS total",
                {"workspace_id": workspace_id},
            ).single()
        finally:
            connection.close()
        return {
            "workspace_id": workspace_id,
            "store": str(self.store),
            "relate_version": PINNED_RELATE_VERSION,
            "nodes": node_row["total"],
            "relationships": relationship_row["total"],
            "durability": "full",
        }

    def asset_lineage(self, workspace_id: str, asset_id: str) -> list[dict]:
        connection = self._connect(read_only=True)
        try:
            cursor = connection.execute(
                "MATCH (a:AssetRevision {workspace_id: $workspace_id, "
                "asset_id: $asset_id})<-[:DERIVED_FROM]-(s:StoryletRevision) "
                "MATCH (s)-[:HAS_MARKER]->(m:Marker) "
                "RETURN s.storylet_id AS storylet_id, s.title AS storylet_title, "
                "s.duration_seconds AS duration_seconds, s.loop AS loop, "
                "m.name AS marker_name, m.at_seconds AS marker_seconds "
                f"ORDER BY s.storylet_id, m.at_seconds LIMIT {MAX_QUERY_ROWS}",
                {"workspace_id": workspace_id, "asset_id": asset_id},
            )
            return [dict(row) for row in cursor]
        finally:
            connection.close()

    def find_storylets(
        self,
        workspace_id: str,
        *,
        minimum_seconds: float = 0.1,
        maximum_seconds: float = 3600.0,
        loop: bool | None = None,
    ) -> list[dict]:
        if not 0.1 <= minimum_seconds <= maximum_seconds <= 3600.0:
            raise ValueError("storylet duration search range is invalid")
        connection = self._connect(read_only=True)
        try:
            cursor = connection.execute(
                "MATCH (s:StoryletRevision {workspace_id: $workspace_id}) "
                "WHERE s.duration_seconds >= $minimum_seconds "
                "AND s.duration_seconds <= $maximum_seconds "
                "AND ($loop IS NULL OR s.loop = $loop) "
                "RETURN s.storylet_id AS storylet_id, s.title AS title, "
                "s.duration_seconds AS duration_seconds, s.loop AS loop, "
                "s.asset_id AS asset_id "
                f"ORDER BY s.duration_seconds, s.storylet_id LIMIT {MAX_QUERY_ROWS}",
                {
                    "workspace_id": workspace_id,
                    "minimum_seconds": minimum_seconds,
                    "maximum_seconds": maximum_seconds,
                    "loop": loop,
                },
            )
            return [dict(row) for row in cursor]
        finally:
            connection.close()
