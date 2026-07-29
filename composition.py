#!/usr/bin/env python3
"""Compose declared unit workflows for an Analog Sim Studies ontology node."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


MANIFEST_NAME = "unit.toml"
SCHEMA_VERSION = 1
UNIT_ID = re.compile(r"^[a-z][a-z0-9-]*$")


class CompositionError(ValueError):
    """A unit declaration cannot be composed safely."""


@dataclass(frozen=True)
class DocsContract:
    source: Path
    index: Path
    resources: tuple[Path, ...]


@dataclass(frozen=True)
class Unit:
    root: Path
    unit_id: str
    name: str
    ontology: Path
    test_command: tuple[str, ...] | None
    docs: DocsContract | None
    children: tuple["Unit", ...]


def _table(value: Any, label: str, manifest: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CompositionError(f"{manifest}: {label} must be a TOML table")
    return value


def _relative_path(value: Any, label: str, manifest: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise CompositionError(f"{manifest}: {label} must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CompositionError(f"{manifest}: {label} must stay within its unit")
    return path


def _command(value: Any, label: str, manifest: Path) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(part, str) or not part for part in value)
    ):
        raise CompositionError(
            f"{manifest}: {label} must be a non-empty array of strings"
        )
    return tuple(value)


def load_unit(root: Path) -> Unit:
    """Load a unit and its declared descendants in deterministic ID order."""

    root = root.resolve()
    manifest = root / MANIFEST_NAME
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompositionError(f"missing unit declaration: {manifest}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise CompositionError(f"malformed unit declaration {manifest}: {exc}") from exc

    if data.get("schema_version") != SCHEMA_VERSION:
        raise CompositionError(
            f"{manifest}: schema_version must be {SCHEMA_VERSION}"
        )

    unit_data = _table(data.get("unit"), "[unit]", manifest)
    unit_id = unit_data.get("id")
    name = unit_data.get("name")
    if not isinstance(unit_id, str) or not UNIT_ID.fullmatch(unit_id):
        raise CompositionError(f"{manifest}: unit.id is not a stable kebab-case ID")
    if not isinstance(name, str) or not name.strip():
        raise CompositionError(f"{manifest}: unit.name must be a non-empty string")

    ontology_rel = _relative_path(
        unit_data.get("ontology", "ONTOLOGY.md"), "unit.ontology", manifest
    )
    ontology = root / ontology_rel
    if not ontology.is_file():
        raise CompositionError(f"{manifest}: missing ontology: {ontology_rel}")

    workflows = _table(data.get("workflows", {}), "[workflows]", manifest)
    test_value = workflows.get("test")
    test_command = (
        None if test_value is None else _command(test_value, "workflows.test", manifest)
    )

    docs_data = data.get("docs")
    docs = None
    if docs_data is not None:
        docs_table = _table(docs_data, "[docs]", manifest)
        source_rel = _relative_path(docs_table.get("source"), "docs.source", manifest)
        index_rel = _relative_path(docs_table.get("index"), "docs.index", manifest)
        source = root / source_rel
        index = source / index_rel
        if not source.is_dir():
            raise CompositionError(f"{manifest}: missing docs source: {source_rel}")
        if not index.is_file():
            raise CompositionError(
                f"{manifest}: missing docs index: {source_rel / index_rel}"
            )
        resource_values = docs_table.get("resources", [])
        if not isinstance(resource_values, list):
            raise CompositionError(
                f"{manifest}: docs.resources must be an array of paths"
            )
        resources: list[Path] = []
        for value in resource_values:
            resource_rel = _relative_path(value, "docs.resources entry", manifest)
            resource = root / resource_rel
            if not resource.exists():
                raise CompositionError(
                    f"{manifest}: missing docs resource: {resource_rel}"
                )
            resources.append(resource)
        docs = DocsContract(
            source=source, index=index, resources=tuple(resources)
        )

    child_values = unit_data.get("children", [])
    if not isinstance(child_values, list) or any(
        not isinstance(value, str) for value in child_values
    ):
        raise CompositionError(f"{manifest}: unit.children must be an array of paths")
    if len(child_values) != len(set(child_values)):
        raise CompositionError(f"{manifest}: duplicate child path")

    children: list[Unit] = []
    for value in child_values:
        child_rel = _relative_path(value, "unit.children entry", manifest)
        if len(child_rel.parts) != 1:
            raise CompositionError(
                f"{manifest}: children must be immediate child directories"
            )
        child_root = root / child_rel
        if not child_root.is_dir():
            raise CompositionError(f"{manifest}: missing child directory: {child_rel}")
        children.append(load_unit(child_root))

    child_ids = [child.unit_id for child in children]
    if len(child_ids) != len(set(child_ids)):
        raise CompositionError(f"{manifest}: duplicate child unit ID")

    return Unit(
        root=root,
        unit_id=unit_id,
        name=name,
        ontology=ontology,
        test_command=test_command,
        docs=docs,
        children=tuple(sorted(children, key=lambda child: child.unit_id)),
    )


def ontology_lines(unit: Unit, prefix: str = "") -> list[str]:
    """Return a deterministic composition tree without assigning precedence."""

    lines = [f"{prefix}{unit.unit_id}: {unit.ontology.relative_to(unit.root)}"]
    for child in unit.children:
        lines.extend(ontology_lines(child, prefix + "  "))
    return lines


def run_tests(unit: Unit) -> int:
    """Run descendant tests postorder, then this node's integration tests."""

    for child in unit.children:
        result = run_tests(child)
        if result:
            return result
    if unit.test_command is None:
        return 0
    print(f"==> test {unit.unit_id}: {' '.join(unit.test_command)}", flush=True)
    return subprocess.run(unit.test_command, cwd=unit.root, check=False).returncode


def _copy_path(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("_build"))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def stage_docs(unit: Unit, stage: Path) -> None:
    """Create a generated Sphinx source view from authored unit documentation."""

    if unit.docs is None:
        raise CompositionError(f"{unit.root / MANIFEST_NAME}: no [docs] contract")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    for source in sorted(unit.docs.source.iterdir(), key=lambda path: path.name):
        if source.name in {"_build", "conf.py"}:
            continue
        _copy_path(source, stage / source.name)
    for resource in unit.docs.resources:
        _copy_path(resource, stage.parent / resource.name)

    child_entries: list[tuple[str, str]] = []
    for child in unit.children:
        if child.docs is None:
            raise CompositionError(
                f"{child.root / MANIFEST_NAME}: child has no [docs] contract"
            )
        child_stage = stage / "children" / child.unit_id
        _copy_path(child.docs.source, child_stage / child.docs.source.name)
        for resource in child.docs.resources:
            _copy_path(resource, child_stage / resource.name)
        child_index = child.docs.index.relative_to(child.root).as_posix()
        child_entries.append((child.name, f"children/{child.unit_id}/{child_index}"))

    generated = [
        "# Composed child documentation",
        "",
        "This page is generated from the immediate child declarations in `unit.toml`.",
        "The linked sources remain owned by their child units.",
        "",
        "```{toctree}",
        ":maxdepth: 2",
        ":caption: Child units",
        "",
    ]
    generated.extend(f"{name} <{target}>" for name, target in child_entries)
    generated.extend(["```", ""])
    (stage / "_composed-children.md").write_text(
        "\n".join(generated), encoding="utf-8"
    )


def build_docs(unit: Unit, output: Path) -> int:
    """Build this node's docs from root glue and declared child sources."""

    work = unit.root / "build" / "composed-docs"
    stage = work / "source"
    stage_docs(unit, stage)
    if output.exists():
        shutil.rmtree(output)
    command = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        "html",
        "-E",
        "-c",
        str(unit.docs.source),
        str(stage),
        str(output),
    ]
    print(f"==> docs {unit.unit_id}: {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=unit.root, check=False).returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    subparsers.add_parser("tree", help="print the deterministic ontology tree")
    subparsers.add_parser("test", help="run child tests and parent integration tests")
    docs_parser = subparsers.add_parser("docs", help="build composed documentation")
    docs_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        unit = load_unit(args.root)
        if args.operation == "tree":
            print("\n".join(ontology_lines(unit)))
            return 0
        if args.operation == "test":
            return run_tests(unit)
        output = args.output or unit.root / "build" / "docs" / "html"
        return build_docs(unit, output.resolve())
    except CompositionError as exc:
        print(f"composition error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
