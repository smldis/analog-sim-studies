#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import itertools
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sidecar_edits import tool_path


class EditError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParamSet:
    name: str | None
    params: dict[str, object]
    description: str | None = None
    targetdir: str | None = None


@dataclass(frozen=True)
class RenderConfig:
    config_path: Path
    base_dir: Path
    copy_ignore: list[str]
    edits: list[dict]
    param_sets: list[ParamSet]
    param_matrix: dict[str, list[object]]

    @property
    def config_dir(self) -> Path:
        return self.config_path.parent


@dataclass(frozen=True)
class MatrixCase:
    suffix: str | None
    params: dict[str, object]


PARAM_SET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_config(config_path: Path) -> RenderConfig:
    loaded = runpy.run_path(str(config_path))
    copy_ignore = loaded.get("COPY_IGNORE", [])
    edits = loaded.get("EDITS")
    if edits is None:
        raise EditError(f"{config_path} does not define EDITS")
    common_params = load_common_params(config_path, loaded)
    param_sets = load_param_sets(config_path, loaded, common_params)
    param_matrix = load_param_matrix(config_path, loaded)
    base_dir = resolve_config_path(config_path.parent, str(loaded.get("BASE_DIR", "base")), common_params)
    return RenderConfig(config_path, base_dir, copy_ignore, edits, param_sets, param_matrix)


def load_common_params(config_path: Path, loaded: dict[str, object]) -> dict[str, object]:
    inline_params = loaded.get("COMMON_PARAMS")
    params_file = loaded.get("COMMON_PARAMS_FILE")
    if inline_params is not None and params_file is not None:
        raise EditError(f"{config_path} defines both COMMON_PARAMS and COMMON_PARAMS_FILE")
    if inline_params is not None:
        params = inline_params
    elif params_file is not None:
        params_path = resolve_config_path(config_path.parent, str(params_file), {})
        params = json.loads(params_path.read_text(encoding="utf-8"))
    else:
        params = {}
    if not isinstance(params, dict):
        raise EditError(f"{config_path} COMMON_PARAMS must be a dict")
    return params


def load_param_sets(
    config_path: Path,
    loaded: dict[str, object],
    common_params: dict[str, object],
) -> list[ParamSet]:
    raw_param_sets = loaded.get("PARAM_SETS")
    if raw_param_sets is None:
        return [ParamSet(name=None, params=common_params)]
    if not isinstance(raw_param_sets, list):
        raise EditError(f"{config_path} PARAM_SETS must be a list")

    param_sets = []
    seen_names = set()
    for index, raw_param_set in enumerate(raw_param_sets, start=1):
        if not isinstance(raw_param_set, dict):
            raise EditError(f"{config_path} PARAM_SETS entry {index} must be a dict")
        name = raw_param_set.get("name")
        if not isinstance(name, str) or not PARAM_SET_NAME_RE.match(name):
            raise EditError(
                f"{config_path} PARAM_SETS entry {index} needs a valid identifier name"
            )
        if name in seen_names:
            raise EditError(f"{config_path} defines duplicate PARAM_SETS name: {name}")
        seen_names.add(name)

        inline_params = raw_param_set.get("params")
        params_file = raw_param_set.get("params_file")
        if inline_params is not None and params_file is not None:
            raise EditError(f"{config_path} PARAM_SETS entry {name} defines both params and params_file")
        if inline_params is not None:
            params = inline_params
        elif params_file is not None:
            params_path = resolve_config_path(config_path.parent, str(params_file), common_params)
            params = json.loads(params_path.read_text(encoding="utf-8"))
        else:
            params = {}
        if not isinstance(params, dict):
            raise EditError(f"{config_path} PARAM_SETS entry {name} params must be a dict")
        description = raw_param_set.get("description")
        if description is not None and not isinstance(description, str):
            raise EditError(f"{config_path} PARAM_SETS entry {name} description must be a string")
        targetdir = raw_param_set.get("targetdir")
        if targetdir is not None and not isinstance(targetdir, str):
            raise EditError(f"{config_path} PARAM_SETS entry {name} targetdir must be a string")
        param_sets.append(
            ParamSet(
                name=name,
                description=description,
                targetdir=targetdir,
                params=common_params | params,
            )
        )
    if not param_sets:
        raise EditError(f"{config_path} PARAM_SETS must not be empty")
    return param_sets


def load_param_matrix(config_path: Path, loaded: dict[str, object]) -> dict[str, list[object]]:
    raw_matrix = loaded.get("PARAM_MATRIX", {})
    if not isinstance(raw_matrix, dict):
        raise EditError(f"{config_path} PARAM_MATRIX must be a dict")

    matrix = {}
    for key, values in raw_matrix.items():
        if not isinstance(key, str) or not PARAM_SET_NAME_RE.match(key):
            raise EditError(f"{config_path} PARAM_MATRIX key must be a valid identifier: {key}")
        if not isinstance(values, list):
            raise EditError(f"{config_path} PARAM_MATRIX entry {key} must be a list")
        if not values:
            raise EditError(f"{config_path} PARAM_MATRIX entry {key} must not be empty")
        matrix[key] = values
    return matrix


def format_text(value: str, params: dict[str, object]) -> str:
    try:
        return value.format_map(params)
    except KeyError as exc:
        missing = exc.args[0]
        raise EditError(f"missing parameter: {missing}") from exc


def format_path_text(value: str, params: dict[str, object]) -> str:
    return os.path.expandvars(format_text(value, params))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_config_path(base_dir: Path, value: str, params: dict[str, object]) -> Path:
    path = Path(format_path_text(value, params))
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


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
    return resolve_config_path(config_dir, str(edit["path"]), params)


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
    command = [format_path_text(str(arg), params) for arg in edit["command"]]
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
    include_path = format_path_text(str(edit.get("include", "subckts.inc")), params)
    try:
        binary = str(tool_path("extract_subckts"))
    except RuntimeError as exc:
        if optional:
            print(f"skip optional {description}: {exc}")
            return
        raise EditError(f"{description} failed: {exc}") from exc
    command = [
        binary,
        format_path_text(str(edit.get("input", "input.scs")), params),
        format_path_text(str(edit.get("output", "input_main.scs")), params),
        include_path,
        format_path_text(str(edit.get("subckts", include_path)), params),
    ]
    run_command_args(target_dir, command, optional, description)


def apply_patch_edit(target_dir: Path, edit: dict, params: dict[str, object]) -> None:
    optional = edit.get("optional", False)
    patch_text = format_text(edit["patch"], params)
    description = edit_description(edit)
    command = edit.get("command")
    if command is None:
        binary = format_path_text(str(edit.get("binary", "apply_patch")), params)
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
    else:
        command = [format_path_text(str(arg), params) for arg in command]
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
    dest_name = format_path_text(str(edit.get("to", source.name)), params)
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
        apply_replace(target_dir / format_path_text(str(edit["path"]), params), edit, params)
        return
    if op == "regex_replace":
        apply_regex_replace(target_dir / format_path_text(str(edit["path"]), params), edit, params)
        return
    if op == "apply_patch":
        apply_patch_edit(target_dir, edit, params)
        return
    if op == "patch":
        apply_unified_patch(target_dir, edit, params)
        return
    raise EditError(f"unsupported op: {op}")


def select_param_sets(
    param_sets: list[ParamSet],
    run_names: list[str] | None,
    all_runs: bool,
) -> list[ParamSet]:
    named_sets = {param_set.name: param_set for param_set in param_sets if param_set.name is not None}
    if not named_sets:
        if run_names:
            raise EditError("config does not define PARAM_SETS")
        return param_sets

    if run_names and all_runs:
        raise EditError("use either --run or --all, not both")
    if all_runs or not run_names:
        return param_sets

    selected = []
    missing = []
    for run_name in run_names:
        param_set = named_sets.get(run_name)
        if param_set is None:
            missing.append(run_name)
        else:
            selected.append(param_set)
    if missing:
        available = ", ".join(sorted(named_sets))
        missing_text = ", ".join(missing)
        raise EditError(f"unknown parameter set(s): {missing_text}; available: {available}")
    return selected


def path_slug(value: object) -> str:
    text = str(value).strip()
    if text.startswith("-"):
        text = "m" + text[1:]
    text = text.replace(".", "p")
    text = re.sub(r"[^A-Za-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "value"


def expand_param_matrix(param_matrix: dict[str, list[object]]) -> list[MatrixCase]:
    if not param_matrix:
        return [MatrixCase(suffix=None, params={})]

    keys = list(param_matrix)
    cases = []
    for values in itertools.product(*(param_matrix[key] for key in keys)):
        params = dict(zip(keys, values))
        suffix = "_".join(
            f"{path_slug(key)}_{path_slug(value)}"
            for key, value in params.items()
        )
        cases.append(MatrixCase(suffix=suffix, params=params))
    return cases


def base_output_dir_for_param_set(output_base: Path, param_set: ParamSet) -> Path:
    if param_set.name is None:
        return output_base
    if param_set.targetdir:
        target = Path(format_path_text(param_set.targetdir, param_set.params))
        if target.is_absolute():
            return target
        return (output_base.parent / target).resolve()
    return output_base.parent / f"{output_base.name}_{param_set.name}"


def output_dir_for_job(output_base: Path, param_set: ParamSet, matrix_case: MatrixCase) -> Path:
    base_dir = base_output_dir_for_param_set(output_base, param_set)
    if matrix_case.suffix is None:
        return base_dir
    return base_dir / matrix_case.suffix


def render_job(config: RenderConfig, params: dict[str, object], output_dir: Path, label: str | None) -> None:
    if output_dir.exists():
        raise EditError(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    copy_base_tree(config.base_dir, output_dir, config.copy_ignore)
    for edit in config.edits:
        apply_edit(output_dir, edit, params, config.config_dir)
    if label:
        print(f"rendered {label}: {output_dir}")
    else:
        print(f"rendered {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a run directory from a base tree and sidecar edits.")
    parser.add_argument("config", type=Path, help="Path to edits.py")
    parser.add_argument("output", type=Path, help="Output run directory")
    parser.add_argument(
        "--run",
        action="append",
        dest="run_names",
        help="Named PARAM_SETS entry to render. Repeat to render multiple groups.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render all named PARAM_SETS entries. This is already the default for named configs.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        config = load_config(args.config)
        output_base = Path(os.path.expandvars(str(args.output))).resolve()
        matrix_cases = expand_param_matrix(config.param_matrix)
        for param_set in select_param_sets(config.param_sets, args.run_names, args.all):
            for matrix_case in matrix_cases:
                params = param_set.params | matrix_case.params
                output_dir = output_dir_for_job(output_base, param_set, matrix_case)
                label_parts = [part for part in [param_set.name, matrix_case.suffix] if part]
                render_job(config, params, output_dir, "_".join(label_parts) or None)
        return 0
    except EditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
