#!/usr/bin/env python3
"""Install the commissioned VLC-to-projector Labwc window rule."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import stat
import tempfile
from xml.etree import ElementTree


TEMPORARY_ERROR_CAPTURE = "phreqed-labwc-config-errors.txt"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _qualified(parent: ElementTree.Element, name: str) -> str:
    if parent.tag.startswith("{"):
        namespace = parent.tag[1:].split("}", 1)[0]
        return f"{{{namespace}}}{name}"
    return name


def _children(
    parent: ElementTree.Element, name: str
) -> list[ElementTree.Element]:
    return [child for child in parent if _local_name(child.tag) == name]


def _remove_temporary_error_capture(root: ElementTree.Element) -> bool:
    changed = False
    for core in list(_children(root, "core")):
        for command in list(_children(core, "errorCommand")):
            if TEMPORARY_ERROR_CAPTURE in (command.text or ""):
                core.remove(command)
                changed = True
        if not list(core) and not core.attrib and not (core.text or "").strip():
            root.remove(core)
            changed = True
    return changed


def configure_tree(
    tree: ElementTree.ElementTree, *, output_name: str
) -> bool:
    """Repair only the VLC projection rule and temporary diagnostic hook."""

    if not output_name.strip():
        raise ValueError("Labwc output name must be nonempty text")
    root = tree.getroot()
    if _local_name(root.tag) != "openbox_config":
        raise ValueError("Labwc configuration root must be openbox_config")

    changed = _remove_temporary_error_capture(root)
    rule_groups = _children(root, "windowRules")
    if rule_groups:
        group = rule_groups[0]
    else:
        group = ElementTree.SubElement(root, _qualified(root, "windowRules"))
        changed = True

    vlc_rules = [
        rule
        for rule in _children(group, "windowRule")
        if rule.get("identifier") == "vlc"
    ]
    if vlc_rules:
        rule = vlc_rules[0]
        for duplicate in vlc_rules[1:]:
            group.remove(duplicate)
            changed = True
    else:
        rule = ElementTree.SubElement(
            group, _qualified(group, "windowRule"), {"identifier": "vlc"}
        )
        changed = True

    managed_names = {"MoveToOutput", "SetFullscreen", "ToggleFullscreen"}
    existing_managed = [
        action
        for action in _children(rule, "action")
        if action.get("name") in managed_names
    ]
    valid = (
        len(existing_managed) == 2
        and existing_managed[0].get("name") == "MoveToOutput"
        and existing_managed[0].get("output") == output_name.strip()
        and existing_managed[1].get("name") == "ToggleFullscreen"
    )
    if not valid:
        for action in existing_managed:
            rule.remove(action)
        ElementTree.SubElement(
            rule,
            _qualified(rule, "action"),
            {"name": "MoveToOutput", "output": output_name.strip()},
        )
        ElementTree.SubElement(
            rule,
            _qualified(rule, "action"),
            {"name": "ToggleFullscreen"},
        )
        changed = True
    return changed


def validate_tree(
    tree: ElementTree.ElementTree, *, output_name: str
) -> None:
    root = tree.getroot()
    for core in _children(root, "core"):
        for command in _children(core, "errorCommand"):
            if TEMPORARY_ERROR_CAPTURE in (command.text or ""):
                raise ValueError("temporary Labwc error capture is still installed")
    groups = _children(root, "windowRules")
    rules = [
        rule
        for group in groups
        for rule in _children(group, "windowRule")
        if rule.get("identifier") == "vlc"
    ]
    if len(rules) != 1:
        raise ValueError("exactly one VLC Labwc window rule is required")
    actions = [
        (action.get("name"), action.get("output"))
        for action in _children(rules[0], "action")
        if action.get("name")
        in {"MoveToOutput", "SetFullscreen", "ToggleFullscreen"}
    ]
    expected = [("MoveToOutput", output_name.strip()), ("ToggleFullscreen", None)]
    if actions != expected:
        raise ValueError(f"VLC Labwc actions are {actions!r}, expected {expected!r}")


def _parse(path: Path) -> ElementTree.ElementTree:
    parser = ElementTree.XMLParser(
        target=ElementTree.TreeBuilder(insert_comments=True)
    )
    return ElementTree.parse(path, parser=parser)


def _write_atomic(path: Path, tree: ElementTree.ElementTree) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.before-phreqed-projection-{timestamp}")
    shutil.copy2(path, backup)
    mode = stat.S_IMODE(path.stat().st_mode)
    namespace = tree.getroot().tag.removeprefix("{").split("}", 1)[0]
    if tree.getroot().tag.startswith("{"):
        ElementTree.register_namespace("", namespace)
    ElementTree.indent(tree, space="  ")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as output:
            tree.write(output, encoding="utf-8", xml_declaration=True)
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return backup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Configure Labwc to route VLC projection to a named output"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".config/labwc/rc.xml",
        help="Labwc rc.xml path",
    )
    parser.add_argument("--output", default="HDMI-A-2", help="Labwc output name")
    parser.add_argument(
        "--check", action="store_true", help="validate without changing the file"
    )
    args = parser.parse_args(argv)
    if not args.config.is_file():
        parser.error(f"Labwc configuration does not exist: {args.config}")

    tree = _parse(args.config)
    if args.check:
        validate_tree(tree, output_name=args.output)
        print(f"Labwc projection rule is valid: vlc -> {args.output}")
        return 0

    changed = configure_tree(tree, output_name=args.output)
    validate_tree(tree, output_name=args.output)
    if not changed:
        print(f"Labwc projection rule already current: vlc -> {args.output}")
        return 0
    backup = _write_atomic(args.config, tree)
    print(f"Configured Labwc projection: vlc -> {args.output}")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
