#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import runpy
import shutil
import subprocess
from pathlib import Path

from sidecar_edits import tool_path


class EditError(RuntimeError):
    pass


def load_config(config_path: Path) -> tuple[Path, list[str], list[dict], dict[str, object]]:
    loaded = runpy.run_path(str(config_path))
    base_dir = loaded.get("BASE_DIR", "base")
    copy_ignore = loaded.get("COPY_IGNORE", [])
    edits = loaded.get("EDITS")
    params = load_params(config_path, loaded)
    if "PRE_EDITS" in loaded:
        raise EditError(f"{config_path} defines PRE_EDITS; put ordered operations in EDITS instead")
    if edits is None:
        raise EditError(f"{config_path} does not define EDITS")
    return (config_path.parent / base_dir).resolve(), copy_ignore, edits, params


def load_params(config_path: Path, loaded: dict[str, object]) -> dict[str, object]:
    defaults = loaded.get("DEFAULTS", {})
    inline_params = loaded.get("PARAMS")
    params_file = loaded.get("PARAMS_FILE")
    if inline_params is not None and params_file is not None:
        raise EditError(f"{config_path} defines both PARAMS and PARAMS_FILE")
    if inline_params is not None:
        params = inline_params
    elif params_file is not None:
        params_path = Path(str(params_file))
        if not params_path.is_absolute():
            params_path = config_path.parent / params_path
        params = json.loads(params_path.read_text(encoding="utf-8"))
    else:
        params = {}
    if not isinstance(defaults, dict):
        raise EditError(f"{config_path} DEFAULTS must be a dict")
    if not isinstance(params, dict):
        raise EditError(f"{config_path} parameters must be a dict")
    return defaults | params


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


def edit_description(edit: dict) -> str:
    description = edit.get("description")
    if description:
        return str(description)
    op = edit.get("op", "edit")
    return f"{op} edit"


def normalize_copy_ignore(patterns: list[str]) -> list[str]:
    normalized = []
    for pattern in patterns:
        stripped = str(pattern).strip()
        if stripped and not stripped.startswith("#"):
            normalized.append(stripped)
    return normalized


def matches_copy_ignore(rel_path: str, name: str, is_dir: bool, pattern: str) -> bool:
    dirs_only = pattern.endswith("/")
    clean_pattern = pattern.strip("/")
    if not clean_pattern:
        return False
    if dirs_only and not is_dir:
        return False
    if "/" in clean_pattern:
        return fnmatch.fnmatchcase(rel_path, clean_pattern)
    return fnmatch.fnmatchcase(name, clean_pattern)


def build_copy_ignore(base_dir: Path, patterns: list[str]):
    ignore_patterns = normalize_copy_ignore(patterns)
    if not ignore_patterns:
        return None

    def ignore(current_dir: str, names: list[str]) -> set[str]:
        ignored = set()
        current_path = Path(current_dir)
        for name in names:
            candidate = current_path / name
            rel_path = candidate.relative_to(base_dir).as_posix()
            is_dir = candidate.is_dir()
            if any(matches_copy_ignore(rel_path, name, is_dir, pattern) for pattern in ignore_patterns):
                ignored.add(name)
        return ignored

    return ignore


def copy_base_tree(base_dir: Path, output_dir: Path, copy_ignore: list[str]) -> None:
    shutil.copytree(base_dir, output_dir, ignore=build_copy_ignore(base_dir, copy_ignore))


def resolve_source_path(edit: dict, params: dict[str, object], config_dir: Path) -> Path:
    source = Path(format_text(edit["path"], params))
    if source.is_absolute():
        return source
    return (config_dir / source).resolve()


def apply_replace(target: Path, edit: dict, params: dict[str, object]) -> None:
    description = edit_description(edit)
    old = format_text(edit["old"], params)
    new = format_text(edit["new"], params)
    content = read_text(target)
    if old not in content:
        if edit.get("allow_no_match", False):
            return
        raise EditError(f"{description} failed: replace target not found in {target}")
    write_text(target, content.replace(old, new))


def apply_regex_replace(target: Path, edit: dict, params: dict[str, object]) -> None:
    description = edit_description(edit)
    pattern = edit["pattern"]
    repl = format_text(edit["new"], params)
    count = edit.get("count", 0)
    content = read_text(target)
    updated, replacements = re.subn(pattern, repl, content, count=count, flags=re.MULTILINE)
    if replacements == 0:
        if edit.get("allow_no_match", False):
            return
        raise EditError(f"{description} failed: regex pattern not found in {target}: {pattern}")
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
        raise EditError(f"{description} failed: required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        details = stderr or stdout or str(exc)
        if optional:
            print(f"skip optional {description}: {details}")
            return
        raise EditError(f"{description} failed: {details}") from exc


def run_command(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    description = edit_description(edit)
    optional = edit.get("optional", False)
    command = [format_text(str(arg), params) for arg in edit["command"]]
    run_command_args(target_dir, command, optional, description)


def run_command_args(target_dir: Path, command: list[str], optional: bool, description: str) -> None:
    try:
        subprocess.run(
            command,
            cwd=target_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        if optional:
            print(f"skip optional {description}: command not found: {command[0]}")
            return
        raise EditError(f"{description} failed: required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        details = stderr or stdout or str(exc)
        if optional:
            print(f"skip optional {description}: {details}")
            return
        raise EditError(f"{description} failed: {details}") from exc


def apply_extract_subckts(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    description = edit_description(edit)
    optional = edit.get("optional", False)
    include_path = format_text(str(edit.get("include", "subckts.inc")), params)
    try:
        binary = str(tool_path("extract_subckts"))
    except RuntimeError as exc:
        if optional:
            print(f"skip optional {description}: {exc}")
            return
        raise EditError(f"{description} failed: {exc}") from exc
    command = [
        binary,
        format_text(str(edit.get("input", "input.scs")), params),
        format_text(str(edit.get("output", "input_main.scs")), params),
        include_path,
        format_text(str(edit.get("subckts", include_path)), params),
    ]
    run_command_args(target_dir, command, optional, description)


def apply_patch_edit(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    optional = edit.get("optional", False)
    patch_text = format_text(edit["patch"], params)
    description = edit_description(edit)
    command = edit.get("command")
    if command is None:
        binary = str(edit.get("binary", "apply_patch"))
        resolved = shutil.which(binary)
        if resolved is None:
            message = (
                f"apply_patch executable not found for {description}. "
                "Install apply_patch on PATH or set the edit's binary/command."
            )
            if optional:
                print(f"skip optional {description}: {message}")
                return
            raise EditError(message)
        command = [resolved]
    run_external_patch(target_dir, patch_text, command, optional, description)


def apply_unified_patch(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    optional = edit.get("optional", False)
    patch_text = format_text(edit["patch"], params)
    strip = str(edit.get("strip", 0))
    description = edit_description(edit)
    command = ["patch", f"-p{strip}"]
    run_external_patch(target_dir, patch_text, command, optional, description)


def apply_copy(target_dir: Path, edit: dict, params: dict[str, object], config_dir: Path) -> None:
    description = edit_description(edit)
    source = resolve_source_path(edit, params, config_dir)
    if not source.is_file():
        raise EditError(f"{description} failed: copy source does not exist: {source}")
    dest_name = format_text(edit.get("to", source.name), params)
    destination = target_dir / dest_name
    ensure_parent(destination)
    shutil.copy2(source, destination)


def apply_edit(target_dir: Path, edit: dict, params: dict[str, object], config_dir: Path) -> None:
    op = edit["op"]
    if op == "run":
        run_command(target_dir, edit, params)
        return
    if op == "extract_subckts":
        apply_extract_subckts(target_dir, edit, params)
        return
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
    parser.add_argument("output", type=Path, help="Output run directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir, copy_ignore, edits, params = load_config(args.config)
    output_dir = args.output.resolve()
    if output_dir.exists():
        raise EditError(f"output directory already exists: {output_dir}")
    copy_base_tree(base_dir, output_dir, copy_ignore)
    for edit in edits:
        apply_edit(output_dir, edit, params, args.config.resolve().parent)
    print(f"rendered {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
