"""Atomic local Studio catalog with content-addressed media storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Iterable


CATALOG_VERSION = 1
MAX_CATALOG_BYTES = 20_000_000
MAX_IMPORT_BYTES = 20_000_000_000
_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,95}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ASSET_FAMILIES = frozenset(
    {
        "primary-clip",
        "storylet-source",
        "character-interaction",
        "transition-bridge",
        "impact-accent",
        "scene-fill",
        "brand-artwork",
        "other",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(value: object, prefix: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _ID_PATTERN.fullmatch(value)
        or not value.startswith(f"{prefix}-")
    ):
        raise ValueError(
            f"{label} must start with {prefix}- and use lowercase letters, "
            "digits, or hyphens"
        )
    return value


def _text(value: object, label: str, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValueError(f"{label} must contain at most {maximum} characters")
    return cleaned


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class StudioAsset:
    asset_id: str
    sha256: str
    size_bytes: int
    media_type: str
    original_name: str
    title: str
    family: str
    created_utc: str

    def __post_init__(self) -> None:
        _identifier(self.asset_id, "asset", "asset ID")
        if not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(
            self.sha256
        ):
            raise ValueError("asset SHA-256 is invalid")
        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or not 0 < self.size_bytes <= MAX_IMPORT_BYTES
        ):
            raise ValueError("asset size is invalid")
        _text(self.media_type, "asset media type", 200)
        if (
            Path(_text(self.original_name, "asset original name", 255)).name
            != self.original_name
        ):
            raise ValueError("asset original name must not contain a path")
        _text(self.title, "asset title")
        if self.family not in ASSET_FAMILIES:
            raise ValueError("asset family is invalid")
        _text(self.created_utc, "asset created time", 80)

    def as_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "original_name": self.original_name,
            "title": self.title,
            "family": self.family,
            "created_utc": self.created_utc,
        }


@dataclass(frozen=True, slots=True)
class StoryletMarker:
    name: str
    at_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _ID_PATTERN.fullmatch(self.name):
            raise ValueError("marker name must use lowercase letters, digits, or hyphens")
        if (
            isinstance(self.at_seconds, bool)
            or not isinstance(self.at_seconds, (int, float))
            or not math.isfinite(float(self.at_seconds))
            or float(self.at_seconds) < 0.0
        ):
            raise ValueError("marker time must be a nonnegative finite number")

    def as_dict(self) -> dict:
        return {"name": self.name, "at_seconds": float(self.at_seconds)}


@dataclass(frozen=True, slots=True)
class StudioStorylet:
    storylet_id: str
    asset_id: str
    title: str
    duration_seconds: float
    loop: bool
    markers: tuple[StoryletMarker, ...]
    created_utc: str

    def __post_init__(self) -> None:
        _identifier(self.storylet_id, "storylet", "storylet ID")
        _identifier(self.asset_id, "asset", "storylet asset ID")
        _text(self.title, "storylet title")
        if (
            isinstance(self.duration_seconds, bool)
            or not isinstance(self.duration_seconds, (int, float))
            or not math.isfinite(float(self.duration_seconds))
            or not 0.1 <= float(self.duration_seconds) <= 3600.0
        ):
            raise ValueError("storylet duration must be between 0.1 and 3600 seconds")
        if not isinstance(self.loop, bool):
            raise ValueError("storylet loop flag must be boolean")
        if not isinstance(self.markers, tuple) or not self.markers:
            raise ValueError("storylet requires at least one marker")
        names = [marker.name for marker in self.markers]
        if len(names) != len(set(names)):
            raise ValueError("storylet marker names must be unique")
        times = [float(marker.at_seconds) for marker in self.markers]
        if times != sorted(times):
            raise ValueError("storylet markers must be ordered by time")
        if times[-1] > float(self.duration_seconds):
            raise ValueError("storylet marker exceeds the duration")
        _text(self.created_utc, "storylet created time", 80)

    def as_dict(self) -> dict:
        return {
            "storylet_id": self.storylet_id,
            "asset_id": self.asset_id,
            "title": self.title,
            "duration_seconds": float(self.duration_seconds),
            "loop": self.loop,
            "markers": [marker.as_dict() for marker in self.markers],
            "created_utc": self.created_utc,
        }


class StudioCatalog:
    """Local authoritative metadata and blob store; no graph dependency."""

    def __init__(self, root: Path, *, workspace_id: str = "workspace-local") -> None:
        self.root = root.expanduser().resolve()
        self.workspace_id = _identifier(workspace_id, "workspace", "workspace ID")
        self.catalog_path = self.root / "catalog.json"
        self.events_path = self.root / "events.jsonl"
        self.graph_path = self.root / "graph-projection.json"
        self.blob_root = self.root / "blobs" / "sha256"
        self.assets: dict[str, StudioAsset] = {}
        self.storylets: dict[str, StudioStorylet] = {}
        if self.catalog_path.exists():
            self._load()

    def _load(self) -> None:
        if self.catalog_path.stat().st_size > MAX_CATALOG_BYTES:
            raise ValueError("Studio catalog exceeds 20 MB")
        try:
            value = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot load Studio catalog: {exc}") from exc
        if not isinstance(value, dict) or set(value) != {
            "version",
            "workspace_id",
            "assets",
            "storylets",
        }:
            raise ValueError("Studio catalog fields are invalid")
        if value["version"] != CATALOG_VERSION:
            raise ValueError("unsupported Studio catalog version")
        if value["workspace_id"] != self.workspace_id:
            raise ValueError("Studio catalog workspace does not match")
        if not isinstance(value["assets"], list) or not isinstance(
            value["storylets"], list
        ):
            raise ValueError("Studio catalog collections are invalid")
        assets = [StudioAsset(**item) for item in value["assets"]]
        storylets = [self._parse_storylet(item) for item in value["storylets"]]
        self.assets = {asset.asset_id: asset for asset in assets}
        self.storylets = {storylet.storylet_id: storylet for storylet in storylets}
        if len(self.assets) != len(assets) or len(self.storylets) != len(storylets):
            raise ValueError("Studio catalog contains duplicate IDs")
        if any(item.asset_id not in self.assets for item in self.storylets.values()):
            raise ValueError("Studio storylet references an unknown asset")

    @staticmethod
    def _parse_storylet(value: object) -> StudioStorylet:
        if not isinstance(value, dict) or set(value) != {
            "storylet_id",
            "asset_id",
            "title",
            "duration_seconds",
            "loop",
            "markers",
            "created_utc",
        }:
            raise ValueError("Studio storylet fields are invalid")
        markers = value["markers"]
        if not isinstance(markers, list):
            raise ValueError("Studio storylet markers are invalid")
        return StudioStorylet(
            storylet_id=value["storylet_id"],
            asset_id=value["asset_id"],
            title=value["title"],
            duration_seconds=value["duration_seconds"],
            loop=value["loop"],
            markers=tuple(StoryletMarker(**marker) for marker in markers),
            created_utc=value["created_utc"],
        )

    def document(self) -> dict:
        return {
            "version": CATALOG_VERSION,
            "workspace_id": self.workspace_id,
            "assets": [item.as_dict() for item in self.assets.values()],
            "storylets": [item.as_dict() for item in self.storylets.values()],
        }

    def _atomic_json(self, path: Path, value: object) -> None:
        encoded = json.dumps(value, indent=2, allow_nan=False) + "\n"
        if len(encoded.encode("utf-8")) > MAX_CATALOG_BYTES:
            raise ValueError("Studio JSON output exceeds 20 MB")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}-",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _save(self) -> None:
        self._atomic_json(self.catalog_path, self.document())

    def _record_event(self, event_type: str, entity_id: str, revision: int = 1) -> None:
        event = {
            "event_id": f"event-{hashlib.sha256(f'{event_type}:{entity_id}:{revision}'.encode()).hexdigest()[:24]}",
            "event_type": event_type,
            "workspace_id": self.workspace_id,
            "entity_id": entity_id,
            "revision": revision,
            "recorded_utc": _utc_now(),
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, allow_nan=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def blob_path(self, sha256: str) -> Path:
        if not _SHA256_PATTERN.fullmatch(sha256):
            raise ValueError("blob SHA-256 is invalid")
        return self.blob_root / sha256[:2] / sha256

    def import_asset(
        self,
        source: Path,
        *,
        title: str | None = None,
        family: str = "other",
    ) -> StudioAsset:
        selected = source.expanduser().resolve()
        if not selected.is_file():
            raise ValueError(f"media source is unavailable: {selected}")
        size = selected.stat().st_size
        if not 0 < size <= MAX_IMPORT_BYTES:
            raise ValueError("media source size is invalid")
        if family not in ASSET_FAMILIES:
            raise ValueError("asset family is invalid")
        digest = _sha256(selected)
        asset_id = f"asset-{digest[:24]}"
        existing = self.assets.get(asset_id)
        if existing is not None:
            return existing
        destination = self.blob_path(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_name(f".{destination.name}.import")
            try:
                with selected.open("rb") as source_stream, temporary.open("xb") as target:
                    shutil.copyfileobj(source_stream, target, length=1024 * 1024)
                    target.flush()
                    os.fsync(target.fileno())
                if _sha256(temporary) != digest or temporary.stat().st_size != size:
                    raise ValueError("imported blob verification failed")
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        media_type = mimetypes.guess_type(selected.name)[0] or "application/octet-stream"
        asset = StudioAsset(
            asset_id=asset_id,
            sha256=digest,
            size_bytes=size,
            media_type=media_type,
            original_name=selected.name,
            title=_text(title or selected.stem, "asset title"),
            family=family,
            created_utc=_utc_now(),
        )
        self.assets[asset.asset_id] = asset
        try:
            self._save()
        except Exception:
            self.assets.pop(asset.asset_id, None)
            raise
        self._record_event("asset-imported", asset.asset_id)
        return asset

    def create_storylet(
        self,
        *,
        storylet_id: str,
        asset_id: str,
        title: str,
        duration_seconds: float,
        loop: bool,
        markers: Iterable[StoryletMarker],
    ) -> StudioStorylet:
        if asset_id not in self.assets:
            raise ValueError("storylet references an unknown asset")
        storylet = StudioStorylet(
            storylet_id=storylet_id,
            asset_id=asset_id,
            title=title,
            duration_seconds=duration_seconds,
            loop=loop,
            markers=tuple(markers),
            created_utc=_utc_now(),
        )
        existing = self.storylets.get(storylet.storylet_id)
        if existing is not None:
            if existing == storylet:
                return existing
            raise ValueError("storylet ID already exists")
        self.storylets[storylet.storylet_id] = storylet
        try:
            self._save()
        except Exception:
            self.storylets.pop(storylet.storylet_id, None)
            raise
        self._record_event("storylet-created", storylet.storylet_id)
        return storylet

    def graph_projection(self) -> dict:
        nodes: list[dict] = []
        relationships: list[dict] = []
        nodes.append(
            {
                "id": self.workspace_id,
                "labels": ["Workspace"],
                "properties": {"workspace_id": self.workspace_id},
            }
        )
        for asset in self.assets.values():
            nodes.append(
                {
                    "id": asset.asset_id,
                    "labels": ["AssetRevision"],
                    "properties": asset.as_dict(),
                }
            )
            relationships.append(
                {
                    "type": "OWNS_ASSET",
                    "from": self.workspace_id,
                    "to": asset.asset_id,
                    "properties": {},
                }
            )
        for storylet in self.storylets.values():
            nodes.append(
                {
                    "id": storylet.storylet_id,
                    "labels": ["StoryletRevision"],
                    "properties": {
                        key: value
                        for key, value in storylet.as_dict().items()
                        if key != "markers"
                    },
                }
            )
            relationships.append(
                {
                    "type": "DERIVED_FROM",
                    "from": storylet.storylet_id,
                    "to": storylet.asset_id,
                    "properties": {},
                }
            )
            for marker in storylet.markers:
                marker_id = f"marker-{storylet.storylet_id[9:]}-{marker.name}"
                nodes.append(
                    {
                        "id": marker_id,
                        "labels": ["Marker"],
                        "properties": {
                            "name": marker.name,
                            "at_seconds": float(marker.at_seconds),
                        },
                    }
                )
                relationships.append(
                    {
                        "type": "HAS_MARKER",
                        "from": storylet.storylet_id,
                        "to": marker_id,
                        "properties": {},
                    }
                )
        return {
            "version": 1,
            "workspace_id": self.workspace_id,
            "generated_utc": _utc_now(),
            "nodes": nodes,
            "relationships": relationships,
        }

    def export_graph(self) -> Path:
        self._atomic_json(self.graph_path, self.graph_projection())
        return self.graph_path

    def state(self) -> dict:
        projection = self.graph_projection()
        return {
            "workspace_id": self.workspace_id,
            "root": str(self.root),
            "asset_families": sorted(ASSET_FAMILIES),
            "assets": [item.as_dict() for item in self.assets.values()],
            "storylets": [item.as_dict() for item in self.storylets.values()],
            "graph": {
                "nodes": len(projection["nodes"]),
                "relationships": len(projection["relationships"]),
                "export_path": str(self.graph_path),
            },
        }
