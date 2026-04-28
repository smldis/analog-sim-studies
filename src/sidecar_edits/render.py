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

from sidecar_edits import edit as edit_api
from sidecar_edits import tool_path

if __name__ == "__main__":
    sys.modules["sidecar_edits.render"] = sys.modules[__name__]


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
    edits: list[edit_api.EditSpec]
    param_sets: list[ParamSet]
    param_matrix: dict[str, list[object]]

    @property
    def config_dir(self) -> Path:
        return self.config_path.parent


@dataclass(frozen=True)
class MatrixCase:
    suffix: str | None
    params: dict[str, object]


@dataclass(frozen=True)
class RenderContext:
    target_dir: Path
    config_dir: Path
    config_path: Path
    params: dict[str, object]


@dataclass(frozen=True)
class LogicalStatement:
    start: int
    end: int
    text: str


PARAM_SET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_config(config_path: Path) -> RenderConfig:
    loaded = runpy.run_path(str(config_path))
    copy_ignore = loaded.get("COPY_IGNORE", [])
    edits = loaded.get("EDITS")
    if edits is None:
        raise EditError(f"{config_path} does not define EDITS")
    edits = load_edits(config_path, edits)
    common_params = load_common_params(config_path, loaded)
    param_sets = load_param_sets(config_path, loaded, common_params)
    param_matrix = load_param_matrix(config_path, loaded)
    base_dir = resolve_config_path(config_path.parent, str(loaded.get("BASE_DIR", "base")), common_params)
    return RenderConfig(config_path, base_dir, copy_ignore, edits, param_sets, param_matrix)


def load_edits(config_path: Path, raw_edits: object) -> list[edit_api.EditSpec]:
    if not isinstance(raw_edits, list):
        raise EditError(f"{config_path} EDITS must be a list")
    edits = []
    for index, raw_edit in enumerate(raw_edits, start=1):
        if isinstance(raw_edit, dict):
            raise EditError(
                f"{config_path} EDITS[{index}] raw dictionary edits are not supported; "
                "use sidecar_edits.edit helpers"
            )
        if not edit_api.is_edit_spec(raw_edit):
            raise EditError(f"{config_path} EDITS[{index}] must be a sidecar_edits.edit object")
        edits.append(raw_edit)
    return edits


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


def edit_description(edit: dict | edit_api.EditSpec) -> str:
    if isinstance(edit, dict):
        description = edit.get("description")
        if description:
            return str(description)
        op = edit.get("op", "edit")
        return f"{op} edit"

    description = edit.description
    if description:
        return str(description)
    return f"{edit.op} edit"


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
    apply_replace_text(target, old, new, edit.get("allow_no_match", False), description)


def apply_replace_text(
    target: Path,
    old: str,
    new: str,
    allow_no_match: bool,
    description: str,
) -> None:
    content = read_text(target)
    if old not in content:
        if allow_no_match:
            return
        raise EditError(f"{description} failed: replace target not found in {target}")
    write_text(target, content.replace(old, new))


def apply_regex_replace(target: Path, edit: dict, params: dict[str, object]) -> None:
    description = edit_description(edit)
    pattern = edit["pattern"]
    repl = format_text(edit["new"], params)
    count = edit.get("count", 0)
    apply_regex_replace_text(
        target,
        pattern,
        repl,
        count,
        edit.get("allow_no_match", False),
        description,
    )


def apply_regex_replace_text(
    target: Path,
    pattern: str,
    repl: str,
    count: int,
    allow_no_match: bool,
    description: str,
) -> None:
    content = read_text(target)
    updated, replacements = re.subn(pattern, repl, content, count=count, flags=re.MULTILINE)
    if replacements == 0:
        if allow_no_match:
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
    missing = [field for field in ("input", "output_main", "output_subckts") if field not in edit]
    if missing:
        fields = ", ".join(missing)
        raise EditError(f"{description} failed: extract_subckts missing required field(s): {fields}")

    output_subckts = format_path_text(str(edit["output_subckts"]), params)
    include_path = format_path_text(str(edit.get("include", output_subckts)), params)
    run_extract_subckts(
        target_dir,
        format_path_text(str(edit["input"]), params),
        format_path_text(str(edit["output_main"]), params),
        output_subckts,
        include_path,
        optional,
        description,
    )


def run_extract_subckts(
    target_dir: Path,
    input_path: str,
    output_main: str,
    output_subckts: str,
    include_path: str,
    optional: bool,
    description: str,
) -> None:
    try:
        binary = str(tool_path("extract_subckts"))
    except RuntimeError as exc:
        if optional:
            print(f"skip optional {description}: {exc}")
            return
        raise EditError(f"{description} failed: {exc}") from exc
    command = [
        binary,
        input_path,
        output_main,
        output_subckts,
        include_path,
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


def apply_patch_text(
    target_dir: Path,
    patch_text: str,
    binary: str | None,
    command: list[str] | None,
    optional: bool,
    description: str,
) -> None:
    if command is None:
        resolved = shutil.which(binary or "apply_patch")
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
    dest_name = format_path_text(str(edit.get("to", source.name)), params)
    apply_copy_file(target_dir, source, dest_name, description)


def apply_copy_file(target_dir: Path, source: Path, dest_name: str, description: str) -> None:
    if not source.is_file():
        raise EditError(f"{description} failed: copy source does not exist: {source}")
    destination = target_dir / dest_name
    ensure_parent(destination)
    shutil.copy2(source, destination)


def apply_write_file(target_dir: Path, path: str, content: str) -> None:
    destination = target_dir / path
    ensure_parent(destination)
    write_text(destination, content)


def append_text(path: Path, content: str) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(content)


def apply_append_file(target_dir: Path, path: str, content: str, description: str) -> None:
    destination = target_dir / path
    if not destination.is_file():
        raise EditError(f"{description} failed: append target does not exist: {destination}")
    append_text(destination, content)


def apply_insert_series_source_at_instance_net(
    target: Path,
    instance: str,
    net: str,
    internal_net: str,
    source_line: str,
    description: str,
) -> None:
    content = read_text(target)
    updated = insert_series_source_at_instance_net_text(
        content,
        instance,
        net,
        internal_net,
        source_line,
        target,
        description,
    )
    write_text(target, updated)


def insert_series_source_at_instance_net_text(
    content: str,
    instance: str,
    net: str,
    internal_net: str,
    source_line: str,
    target: Path,
    description: str,
) -> str:
    matches = find_instance_statements(content, instance)
    if not matches:
        raise EditError(f"{description} failed: instance not found in {target}: {instance}")
    if len(matches) > 1:
        raise EditError(f"{description} failed: instance is ambiguous in {target}: {instance}")

    statement = matches[0]
    if any(marker in statement.text for marker in ("$", ";", "*")):
        raise EditError(
            f"{description} failed: comments are not supported on instance line: {instance}"
        )

    rewritten_statement = replace_unique_net_token(
        statement.text,
        instance,
        net,
        internal_net,
        target,
        description,
    )
    source = source_line if source_line.endswith("\n") else f"{source_line}\n"
    return content[:statement.start] + source + rewritten_statement + content[statement.end:]


def find_instance_statements(content: str, instance: str) -> list[LogicalStatement]:
    candidates = accepted_instance_names(instance)
    return [
        statement
        for statement in iter_logical_statements(content)
        if first_token_lower(statement.text) in candidates
    ]


def accepted_instance_names(instance: str) -> set[str]:
    lowered = instance.lower()
    names = {lowered}
    if lowered.startswith("x") and (len(lowered) == 1 or lowered[1] != "x"):
        names.add(f"x{lowered}")
    return names


def iter_logical_statements(content: str) -> list[LogicalStatement]:
    lines = content.splitlines(keepends=True)
    statements = []
    offset = 0
    index = 0
    while index < len(lines):
        start = offset
        parts = [lines[index]]
        offset += len(lines[index])
        index += 1
        while index < len(lines) and lines[index].lstrip().startswith("+"):
            parts.append(lines[index])
            offset += len(lines[index])
            index += 1
        statements.append(LogicalStatement(start=start, end=offset, text="".join(parts)))
    return statements


def first_token_lower(text: str) -> str | None:
    match = re.match(r"\s*(\S+)", text)
    if match is None:
        return None
    return match.group(1).lower()


def replace_unique_net_token(
    text: str,
    instance: str,
    net: str,
    internal_net: str,
    target: Path,
    description: str,
) -> str:
    first = re.match(r"\s*\S+", text)
    if first is None:
        raise EditError(f"{description} failed: malformed instance text in {target}: {instance}")

    pattern = re.compile(r"(?<!\S)" + re.escape(net) + r"(?!\S)")
    matches = [match for match in pattern.finditer(text) if match.start() >= first.end()]
    if not matches:
        raise EditError(
            f"{description} failed: net not found on instance {instance} in {target}: {net}"
        )
    if len(matches) > 1:
        raise EditError(
            f"{description} failed: net appears more than once on instance {instance}: {net}"
        )

    match = matches[0]
    return text[:match.start()] + internal_net + text[match.end():]


def apply_edit(
    target_dir: Path,
    edit: edit_api.EditSpec,
    params: dict[str, object],
    config_dir: Path,
    config_path: Path | None = None,
) -> None:
    if isinstance(edit, dict):
        raise EditError("raw dictionary edits are not supported; use sidecar_edits.edit helpers")
    if not edit_api.is_edit_spec(edit):
        raise EditError("edit must be a sidecar_edits.edit object")
    context = RenderContext(
        target_dir=target_dir,
        config_dir=config_dir,
        config_path=config_path or config_dir / "<unknown>",
        params=params,
    )
    edit.apply(context)


def format_edit_failure(config_path: Path, index: int, edit: edit_api.EditSpec, reason: str) -> str:
    label = f'EDITS[{index}] {edit.op}'
    if edit.description:
        label += f' "{edit.description}"'
    lines = [f"{label} failed"]
    if edit.source_stack:
        first, *rest = edit.source_stack[:3]
        lines.append(f"created at {first.format(config_path)}")
        for frame in rest:
            lines.append(f"called from {frame.format(config_path)}")
    lines.append(f"reason: {reason}")
    return "\n".join(lines)


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
    for index, edit in enumerate(config.edits, start=1):
        try:
            apply_edit(output_dir, edit, params, config.config_dir, config.config_path)
        except EditError as exc:
            raise EditError(format_edit_failure(config.config_path, index, edit, str(exc))) from exc
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
