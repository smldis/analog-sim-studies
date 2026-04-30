from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


def run_render(config_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(config_path), str(output_dir)],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
    )


def write_config(tmp_path: Path, edits: str, base_text: str) -> Path:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.scs").write_text(base_text, encoding="utf-8")
    config_path = tmp_path / "edits.py"
    config_path.write_text(
        f"""
from sidecar_edits import edit

BASE_DIR = "base"
COMMON_PARAMS = {{"vdd": "1.2"}}
EDITS = [
{edits}
]
""",
        encoding="utf-8",
    )
    return config_path


def test_insert_series_source_helper_returns_typed_edit_object() -> None:
    from sidecar_edits import edit

    spec = edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="X_SIDE_INJECT_001",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
        description="inject pulse on unique instance input",
    )

    assert spec.op == "insert_series_source_at_instance_net"
    assert spec.path == "input.scs"
    assert spec.instance == "X_SIDE_INJECT_001"
    assert spec.net == "in"
    assert spec.internal_net == "in__sidecar_inj"
    assert spec.source_line == "Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)"
    assert spec.description == "inject pulse on unique instance input"
    assert not hasattr(spec, "fields")
    assert spec.source_stack[0].path == Path(__file__).resolve()


def test_insert_series_source_rewrites_unique_instance_net(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
    edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="X_SIDE_INJECT_001",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
    ),
""",
        "simulator lang=spectre\nX_SIDE_INJECT_001 in out vss vdd amp\n",
    )

    result = run_render(config_path, tmp_path / "run")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "run" / "input.scs").read_text(encoding="utf-8") == (
        "simulator lang=spectre\n"
        "Vinj in in__sidecar_inj PULSE(0 1.2 0 10p 10p 4n 8n)\n"
        "X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp\n"
    )


def test_source_line_uses_render_params_and_operation_values(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
    edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="X_SIDE_INJECT_001",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 {vdd} 0 10p 10p 4n 8n)",
    ),
""",
        "X_SIDE_INJECT_001 in out vss vdd amp\n",
    )

    result = run_render(config_path, tmp_path / "run")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "run" / "input.scs").read_text(encoding="utf-8") == (
        "Vinj in in__sidecar_inj PULSE(0 1.2 0 10p 10p 4n 8n)\n"
        "X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp\n"
    )


def test_continuation_lines_and_params_are_preserved_as_text(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
    edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="X_SIDE_INJECT_001",
        net="vss",
        internal_net="vss__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
    ),
""",
        "X_SIDE_INJECT_001 in out\n+ vss vdd amp gain=10 m=2\n",
    )

    result = run_render(config_path, tmp_path / "run")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "run" / "input.scs").read_text(encoding="utf-8") == (
        "Vinj vss vss__sidecar_inj PULSE(0 1.2 0 10p 10p 4n 8n)\n"
        "X_SIDE_INJECT_001 in out\n"
        "+ vss__sidecar_inj vdd amp gain=10 m=2\n"
    )


def test_doubled_second_character_instance_convention_is_accepted(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
    edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="XFOO",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
    ),
""",
        "XFFOO in out vss vdd amp\n",
    )

    result = run_render(config_path, tmp_path / "run")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "run" / "input.scs").read_text(encoding="utf-8") == (
        "Vinj in in__sidecar_inj PULSE(0 1.2 0 10p 10p 4n 8n)\n"
        "XFFOO in__sidecar_inj out vss vdd amp\n"
    )


def test_doubled_second_character_and_exact_instance_match_is_ambiguous(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
    edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="xfoo",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
        description="inject pulse on unique instance input",
    ),
""",
        "XFOO in out vss vdd amp\nXFFOO in out vss vdd amp\n",
    )

    result = run_render(config_path, tmp_path / "run")

    assert result.returncode == 2
    assert "instance is ambiguous" in result.stderr


@pytest.mark.parametrize(
    ("base_text", "expected"),
    [
        ("X_OTHER in out vss vdd amp\n", "instance not found"),
        (
            "X_SIDE_INJECT_001 in out vss vdd amp\nX_SIDE_INJECT_001 in2 out vss vdd amp\n",
            "instance is ambiguous",
        ),
        ("X_SIDE_INJECT_001 in out gnd vdd amp\n", "net not found"),
        ("X_SIDE_INJECT_001 in out vss vss amp\n", "net appears more than once"),
        ("X_SIDE_INJECT_001 in out vss vdd amp $ comment\n", "comments are not supported"),
        ("X_SIDE_INJECT_001 in out vss vdd amp ; comment\n", "comments are not supported"),
        ("X_SIDE_INJECT_001 in out vss vdd amp * comment\n", "comments are not supported"),
    ],
)
def test_insert_series_source_reports_actionable_failures(
    tmp_path: Path,
    base_text: str,
    expected: str,
) -> None:
    config_path = write_config(
        tmp_path,
        """
    edit.insert_series_source_at_instance_net(
        path="input.scs",
        instance="X_SIDE_INJECT_001",
        net="vss",
        internal_net="vss__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
        description="inject pulse on unique instance input",
    ),
""",
        base_text,
    )

    result = run_render(config_path, tmp_path / "run")

    assert result.returncode == 2
    assert 'EDITS[1] insert_series_source_at_instance_net "inject pulse on unique instance input" failed' in result.stderr
    assert expected in result.stderr


def test_non_x_instance_name_is_rejected() -> None:
    from sidecar_edits import edit

    with pytest.raises(ValueError, match="instance must start with X"):
        edit.insert_series_source_at_instance_net(
            path="input.scs",
            instance="M1",
            net="in",
            internal_net="in__sidecar_inj",
            source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
        )
