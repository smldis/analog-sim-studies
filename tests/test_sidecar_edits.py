from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "prototype" / "sidecar_edits" / "example"
EDITS = EXAMPLE_DIR / "edits.py"
PARAMS = EXAMPLE_DIR / "params.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

from sidecar_edits.render import EditError, apply_regex_replace, apply_replace, copy_base_tree  # noqa: E402


def build_package(tmp_path: Path) -> Path:
    build_lib = tmp_path / "build_lib"
    subprocess.run(
        [sys.executable, "setup.py", "build_py", "--build-lib", str(build_lib)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return build_lib


def test_example_render_applies_patch_and_apply_patch(tmp_path: Path) -> None:
    build_lib = build_package(tmp_path)
    output_dir = tmp_path / "example_run"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(build_lib)

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(EDITS), str(PARAMS), str(output_dir)],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_dir.exists()
    assert (output_dir / "include" / "model_override.scs").read_text(encoding="utf-8") == (
        "simulator lang=spectre\n"
        "parameters gain_trim=1.05\n"
    )
    assert (output_dir / "input_main.scs").read_text(encoding="utf-8") == (
        'simulator lang=spectre\n'
        'include "/work/netlists/rc_filter_corner_tt.scs"\n\n'
        "parameters vdd=1.20 temp=27\n"
        '.INCLUDE "subckts.inc"\n'
        "X1 in out rc_filter\n"
        "tran tran stop=10u\n"
        "save V(out)\n"
    )
    assert (output_dir / "subckts.inc").read_text(encoding="utf-8") == (
        "\n"
        "*** reusable subcircuit definitions\n"
        ".SUBCKT rc_filter in out\n"
        "R1 in out 1k\n"
        "C1 out 0 1p\n"
        ".ENDS rc_filter\n\n"
    )
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == (
        "base example\n"
        "run_label=tt_1v2_27c\n"
    )
    assert (output_dir / "APPLY_PATCH_PROOF.txt").read_text(encoding="utf-8") == (
        "run_label=tt_1v2_27c\n"
    )
    assert not (output_dir / "psf").exists()
    assert not (output_dir / "scratch.tmp").exists()


def test_copy_base_tree_ignores_directories_basenames_and_relative_paths(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    output_dir = tmp_path / "run"
    (base_dir / "psf").mkdir(parents=True)
    (base_dir / "logs").mkdir()
    (base_dir / "nested").mkdir()
    (base_dir / "input.scs").write_text("netlist\n", encoding="utf-8")
    (base_dir / "psf" / "old.raw").write_text("waveform\n", encoding="utf-8")
    (base_dir / "nested" / "scratch.tmp").write_text("scratch\n", encoding="utf-8")
    (base_dir / "logs" / "run.txt").write_text("log\n", encoding="utf-8")

    copy_base_tree(base_dir, output_dir, ["psf/", "*.tmp", "logs/*.txt"])

    assert (output_dir / "input.scs").is_file()
    assert not (output_dir / "psf").exists()
    assert not (output_dir / "nested" / "scratch.tmp").exists()
    assert not (output_dir / "logs" / "run.txt").exists()


def test_replace_allows_missing_match_when_requested(tmp_path: Path) -> None:
    target = tmp_path / "input.scs"
    target.write_text("parameters vdd=1.2\n", encoding="utf-8")

    apply_replace(
        target,
        {
            "old": "missing token",
            "new": "replacement",
            "allow_no_match": True,
        },
        {},
    )

    assert target.read_text(encoding="utf-8") == "parameters vdd=1.2\n"


def test_replace_remains_strict_by_default(tmp_path: Path) -> None:
    target = tmp_path / "input.scs"
    target.write_text("parameters vdd=1.2\n", encoding="utf-8")

    with pytest.raises(EditError, match="replace target not found"):
        apply_replace(target, {"old": "missing token", "new": "replacement"}, {})


def test_regex_replace_allows_missing_match_when_requested(tmp_path: Path) -> None:
    target = tmp_path / "input.scs"
    target.write_text("parameters vdd=1.2\n", encoding="utf-8")

    apply_regex_replace(
        target,
        {
            "pattern": r"temp=\S+",
            "new": "temp=27",
            "allow_no_match": True,
        },
        {},
    )

    assert target.read_text(encoding="utf-8") == "parameters vdd=1.2\n"
