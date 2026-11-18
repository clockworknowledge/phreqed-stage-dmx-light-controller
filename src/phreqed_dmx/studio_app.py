"""Command-line entry point for the local-first Phreqed Studio foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .studio_catalog import ASSET_FAMILIES, StoryletMarker, StudioCatalog
from .studio_relate import StudioRelateGraph
from .studio_web import StudioController, run_server


DEFAULT_WORKSPACE = Path.home() / ".local" / "share" / "phreqed-studio"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--workspace-id", default="workspace-local")
    parser.add_argument(
        "--relate-store",
        type=Path,
        help="durable Relate directory store (defaults to WORKSPACE/relate)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the loopback Studio browser")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8090)

    ingest = commands.add_parser("import", help="import one local media asset")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--title")
    ingest.add_argument("--family", choices=sorted(ASSET_FAMILIES), default="other")

    storylet = commands.add_parser("storylet", help="create one storylet revision")
    storylet.add_argument("--id", required=True, dest="storylet_id")
    storylet.add_argument("--asset", required=True, dest="asset_id")
    storylet.add_argument("--title", required=True)
    storylet.add_argument("--duration", type=float, required=True)
    storylet.add_argument("--loop", action="store_true")
    storylet.add_argument(
        "--marker",
        action="append",
        default=[],
        metavar="NAME=SECONDS",
        help="repeat for each ordered semantic marker",
    )

    commands.add_parser("export-graph", help="write the rebuildable graph projection")
    commands.add_parser("relate-sync", help="sync the catalog into durable Relate")
    commands.add_parser("relate-state", help="read durable Relate graph counts")
    lineage = commands.add_parser("relate-lineage", help="query asset Storylet lineage")
    lineage.add_argument("--asset", required=True, dest="asset_id")
    find = commands.add_parser("relate-find", help="find Storylets by bounded duration")
    find.add_argument("--minimum", type=float, default=0.1)
    find.add_argument("--maximum", type=float, default=3600.0)
    loop_group = find.add_mutually_exclusive_group()
    loop_group.add_argument("--loop", action="store_const", const=True, dest="loop")
    loop_group.add_argument(
        "--one-shot", action="store_const", const=False, dest="loop"
    )
    commands.add_parser("state", help="print the local Studio state as JSON")
    return parser


def _markers(values: list[str]) -> tuple[StoryletMarker, ...]:
    markers: list[StoryletMarker] = []
    for value in values:
        name, separator, raw_time = value.partition("=")
        if not separator:
            raise ValueError("markers must use NAME=SECONDS")
        try:
            at_seconds = float(raw_time)
        except ValueError as exc:
            raise ValueError("marker seconds must be numeric") from exc
        markers.append(StoryletMarker(name, at_seconds))
    return tuple(markers)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = StudioCatalog(args.workspace, workspace_id=args.workspace_id)
    relate_graph = StudioRelateGraph(args.relate_store or catalog.root / "relate")
    if args.command == "serve":
        run_server(
            StudioController(catalog, relate_graph=relate_graph),
            host=args.host,
            port=args.port,
        )
        return 0
    if args.command == "import":
        asset = catalog.import_asset(args.path, title=args.title, family=args.family)
        print(json.dumps(asset.as_dict(), indent=2))
        return 0
    if args.command == "storylet":
        try:
            markers = _markers(args.marker)
            item = catalog.create_storylet(
                storylet_id=args.storylet_id,
                asset_id=args.asset_id,
                title=args.title,
                duration_seconds=args.duration,
                loop=args.loop,
                markers=markers,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(item.as_dict(), indent=2))
        return 0
    if args.command == "export-graph":
        print(catalog.export_graph())
        return 0
    if args.command == "relate-sync":
        print(json.dumps(relate_graph.sync_projection(catalog.graph_projection()), indent=2))
        return 0
    if args.command == "relate-state":
        print(json.dumps(relate_graph.state(catalog.workspace_id), indent=2))
        return 0
    if args.command == "relate-lineage":
        print(
            json.dumps(
                relate_graph.asset_lineage(catalog.workspace_id, args.asset_id),
                indent=2,
            )
        )
        return 0
    if args.command == "relate-find":
        print(
            json.dumps(
                relate_graph.find_storylets(
                    catalog.workspace_id,
                    minimum_seconds=args.minimum,
                    maximum_seconds=args.maximum,
                    loop=args.loop,
                ),
                indent=2,
            )
        )
        return 0
    if args.command == "state":
        print(json.dumps(catalog.state(), indent=2))
        return 0
    raise AssertionError("unhandled Studio command")


if __name__ == "__main__":
    raise SystemExit(main())
