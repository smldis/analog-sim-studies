#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import runpy
import shutil
import subprocess
from pathlib import Path


class EditError(RuntimeError):
    pass


def load_config(config_path: Path) -> tuple[Path, list[dict], dict]:
    loaded = runpy.run_path(str(config_path))
    base_dir = loaded.get("BASE_DIR", "base")
    edits = loaded.get("EDITS")
    defaults = loaded.get("DEFAULTS", {})
    if edits is None:
        raise EditError(f"{config_path} does not define EDITS")
    return (config_path.parent / base_dir).resolve(), edits, defaults


def format_text(value: str, params: dict[str, object]) -> str:
    try:
        return value.format_map(params)
    except KeyError as exc:
        missing = exc.args[0]
        raise EditError(f"missing parameter: {missing}") from exc


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_source_path(edit: dict, params: dict[str, object], config_dir: Path) -> Path:
    source = Path(format_text(edit["path"], params))
    if source.is_absolute():
        return source
    return (config_dir / source).resolve()


def apply_replace(target: Path, edit: dict, params: dict[str, object]) -> None:
    old = format_text(edit["old"], params)
    new = format_text(edit["new"], params)
    content = read_text(target)
    if old not in content:
        raise EditError(f"replace target not found in {target}")
    write_text(target, content.replace(old, new))


def apply_regex_replace(target: Path, edit: dict, params: dict[str, object]) -> None:
    pattern = edit["pattern"]
    repl = format_text(edit["new"], params)
    count = edit.get("count", 0)
    content = read_text(target)
    updated, replacements = re.subn(pattern, repl, content, count=count, flags=re.MULTILINE)
    if replacements == 0:
        raise EditError(f"regex pattern not found in {target}: {pattern}")
    write_text(target, updated)


def run_external_patch(
    target_dir: Path,
    patch_text: str,
    command: list[str],
    optional: bool,
    description: str,
) -> None:
    try:
        subprocess.run(
            command,
            input=patch_text,
            text=True,
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        if optional:
            print(f"skip optional {description}: command not found: {command[0]}")
            return
        raise EditError(f"required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        details = stderr or stdout or str(exc)
        if optional:
            print(f"skip optional {description}: {details}")
            return
        raise EditError(f"{description} failed: {details}") from exc


def apply_patch_edit(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    optional = edit.get("optional", False)
    patch_text = format_text(edit["patch"], params)
    description = edit.get("description", "apply_patch edit")
    command = edit.get("command")
    if command is None:
        binary = edit.get("binary") or shutil.which("apply_patch") or "apply_patch"
        command = [binary]
    run_external_patch(target_dir, patch_text, command, optional, description)


def apply_unified_patch(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    optional = edit.get("optional", False)
    patch_text = format_text(edit["patch"], params)
    strip = str(edit.get("strip", 0))
    description = edit.get("description", "patch edit")
    command = ["patch", f"-p{strip}"]
    run_external_patch(target_dir, patch_text, command, optional, description)


def apply_copy(target_dir: Path, edit: dict, params: dict[str, object], config_dir: Path) -> None:
    source = resolve_source_path(edit, params, config_dir)
    if not source.is_file():
        raise EditError(f"copy source does not exist: {source}")
    dest_name = format_text(edit.get("to", source.name), params)
    destination = target_dir / dest_name
    ensure_parent(destination)
    shutil.copy2(source, destination)


def apply_edit(target_dir: Path, edit: dict, params: dict[str, object], config_dir: Path) -> None:
    op = edit["op"]
    if op == "copy_file":
        apply_copy(target_dir, edit, params, config_dir)
        return
    if op == "replace":
        apply_replace(target_dir / edit["path"], edit, params)
        return
    if op == "regex_replace":
        apply_regex_replace(target_dir / edit["path"], edit, params)
        return
    if op == "apply_patch":
        apply_patch_edit(target_dir, edit, params)
        return
    if op == "patch":
        apply_unified_patch(target_dir, edit, params)
        return
    raise EditError(f"unsupported op: {op}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a run directory from a base tree and sidecar edits.")
    parser.add_argument("config", type=Path, help="Path to edits.py")
    parser.add_argument("params", type=Path, help="Path to params.json")
    parser.add_argument("output", type=Path, help="Output run directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir, edits, defaults = load_config(args.config)
    params = defaults | json.loads(args.params.read_text(encoding="utf-8"))
    output_dir = args.output.resolve()
    if output_dir.exists():
        raise EditError(f"output directory already exists: {output_dir}")
    shutil.copytree(base_dir, output_dir)
    for edit in edits:
        apply_edit(output_dir, edit, params, args.config.resolve().parent)
    print(f"rendered {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
