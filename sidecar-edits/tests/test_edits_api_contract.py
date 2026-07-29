from __future__ import annotations

import inspect
import runpy
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

def test_edit_namespace_exposes_typed_documented_helpers() -> None:
    from sidecar_edits import edits

    signature = inspect.signature(edits.replace)

    assert edits.replace.__doc__
    assert edits.extract_subckts.__doc__
    assert edits.write_file.__doc__
    assert edits.append_to_file.__doc__
    assert signature.parameters["path"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["old"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["new"].kind is inspect.Parameter.KEYWORD_ONLY


def test_replace_helper_returns_typed_edit_object_with_source_location() -> None:
    from sidecar_edits import edits

    spec = edits.replace(
        path="input.scs",
        old="corner=seed",
        new="corner=tt",
        description="select corner",
    )

    assert spec.op == "replace"
    assert spec.description == "select corner"
    assert spec.path == "input.scs"
    assert spec.old == "corner=seed"
    assert spec.new == "corner=tt"
    assert spec.allow_no_match is False
    assert not hasattr(spec, "fields")
    assert spec.source_stack[0].path == Path(__file__).resolve()
    assert spec.source_stack[0].function == (
        "test_replace_helper_returns_typed_edit_object_with_source_location"
    )


def test_extract_subckts_requires_named_outputs_and_defaults_include_to_output_subckts() -> None:
    from sidecar_edits import edits

    spec = edits.extract_subckts(
        input="input.scs",
        output_main="input_main.scs",
        output_subckts="subckts.inc",
    )

    assert spec.op == "extract_subckts"
    assert spec.input == "input.scs"
    assert spec.output_main == "input_main.scs"
    assert spec.output_subckts == "subckts.inc"
    assert spec.include is None

    with pytest.raises(TypeError):
        edits.extract_subckts(input="input.scs", output="input_main.scs", subckts="subckts.inc")


def test_write_file_helper_returns_typed_edit_object() -> None:
    from sidecar_edits import edits

    spec = edits.write_file(
        path="generated/pwl_sources.inc",
        content="Vstim in 0 PWL(0 0 1n {vdd})\n",
        description="generate PWL source include",
    )

    assert spec.op == "write_file"
    assert spec.path == "generated/pwl_sources.inc"
    assert spec.content == "Vstim in 0 PWL(0 0 1n {vdd})\n"
    assert spec.description == "generate PWL source include"
    assert not hasattr(spec, "fields")
    assert spec.source_stack[0].path == Path(__file__).resolve()


def test_append_to_file_helper_returns_typed_edit_object() -> None:
    from sidecar_edits import edits

    spec = edits.append_to_file(
        path="input_main.scs",
        content='\ninclude "generated/pwl_sources.inc"\n',
        description="append generated PWL include",
    )

    assert spec.op == "append_to_file"
    assert spec.path == "input_main.scs"
    assert spec.content == '\ninclude "generated/pwl_sources.inc"\n'
    assert spec.description == "append generated PWL include"
    assert not hasattr(spec, "fields")
    assert spec.source_stack[0].path == Path(__file__).resolve()


def test_helper_signatures_reject_unknown_fields_by_normal_python_call_behavior() -> None:
    from sidecar_edits import edits

    with pytest.raises(TypeError):
        edits.replace(path="input.scs", old="a", new="b", typo=True)


def test_source_frames_format_paths_relative_to_config_tree(tmp_path: Path) -> None:
    from sidecar_edits import edits

    editfile_path = tmp_path / "study" / "edits.py"
    in_tree = tmp_path / "study" / "helpers" / "factory.py"
    outside_tree = tmp_path / "shared" / "factory.py"

    assert edits.SourceFrame(in_tree, 12, "make_edit").format(editfile_path) == (
        "helpers/factory.py:12 in make_edit"
    )
    assert edits.SourceFrame(outside_tree, 7, "make_edit").format(editfile_path) == (
        f"{outside_tree}:7 in make_edit"
    )


def test_wrapped_edit_captures_creation_and_caller_locations(tmp_path: Path) -> None:
    editfile_path = tmp_path / "study" / "edits.py"
    editfile_path.parent.mkdir()
    editfile_path.write_text(
        """
from sidecar_edits import edits

def model_include(path):
    return edits.replace(
        path="input.scs",
        old="MODEL_PATH",
        new=path,
    )

EDITS = [
    model_include("/work/model.scs"),
]
""",
        encoding="utf-8",
    )

    loaded = runpy.run_path(str(editfile_path))
    spec = loaded["EDITS"][0]

    assert spec.source_stack[0].format(editfile_path) == "edits.py:5 in model_include"
    assert spec.source_stack[1].format(editfile_path) == "edits.py:12 in <module>"


def test_editfile_executes_before_edit_operations(tmp_path: Path) -> None:
    editfile_path = tmp_path / "study" / "edits.py"
    editfile_path.parent.mkdir()
    editfile_path.write_text(
        """
from sidecar_edits import edits

corner = "tt"

EDITS = [
    edits.replace(
        path="input.scs",
        old="corner=seed",
        new=f"corner={corner}",
    )
]
""",
        encoding="utf-8",
    )

    loaded = runpy.run_path(str(editfile_path))
    spec = loaded["EDITS"][0]

    assert spec.new == "corner=tt"
    assert spec.source_stack[0].format(editfile_path) == "edits.py:7 in <module>"


def test_renderer_rejects_raw_dictionary_edits(tmp_path: Path) -> None:
    editfile_path = tmp_path / "edits.py"
    output_dir = tmp_path / "run"
    (tmp_path / "base").mkdir()
    editfile_path.write_text(
        """
BASE_DIR = "base"
EDITS = [
    {"op": "replace", "path": "input.scs", "old": "a", "new": "b"},
]
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile_path), str(output_dir)],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "raw dictionary edits are not supported" in result.stderr


def test_renderer_reports_failing_edit_source_location(tmp_path: Path) -> None:
    editfile_path = tmp_path / "edits.py"
    output_dir = tmp_path / "run"
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.scs").write_text("corner=tt\n", encoding="utf-8")
    editfile_path.write_text(
        """
from sidecar_edits import edits

BASE_DIR = "base"
EDITS = [
    edits.replace(
        path="input.scs",
        old="corner=missing",
        new="corner=ss",
        description="select corner",
    ),
]
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile_path), str(output_dir)],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert 'EDITS[1] replace "select corner" failed' in result.stderr
    assert "created at edits.py:6" in result.stderr
    assert "replace target not found" in result.stderr
