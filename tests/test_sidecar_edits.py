from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BASIC_EXAMPLE_DIR = REPO_ROOT / "examples" / "basic"
BASIC_EDITS = BASIC_EXAMPLE_DIR / "edit.py"
APPLY_PATCH_EXAMPLE_DIR = REPO_ROOT / "examples" / "apply_patch"
APPLY_PATCH_EDITS = APPLY_PATCH_EXAMPLE_DIR / "edit.py"
PARAM_MATRIX_EXAMPLE_DIR = REPO_ROOT / "examples" / "param_matrix"
PARAM_MATRIX_EDITS = PARAM_MATRIX_EXAMPLE_DIR / "edit.py"

sys.path.insert(0, str(REPO_ROOT / "src"))

import sidecar_edits  # noqa: E402
from sidecar_edits import edit  # noqa: E402
from sidecar_edits.render import (  # noqa: E402
    EditError,
    ParamSet,
    apply_copy,
    apply_edit,
    apply_extract_subckts,
    apply_patch_edit,
    apply_regex_replace,
    apply_replace,
    copy_base_tree,
    load_editfile,
    run_command,
    select_param_sets,
)


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


def test_tool_path_builds_extract_subckts_for_editable_source_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_root = tmp_path / "sidecar_edits"
    (package_root / "native").mkdir(parents=True)
    (package_root / "native" / "extract_subckts.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    captured = {}

    def fake_files(package: str) -> Path:
        assert package == "sidecar_edits"
        return package_root

    def fake_run(command: list[str], check: bool) -> None:
        captured["command"] = command
        captured["check"] = check
        target = Path(command[command.index("-o") + 1])
        target.write_text("binary\n", encoding="utf-8")

    monkeypatch.setattr(sidecar_edits, "files", fake_files)
    monkeypatch.setattr(sidecar_edits.subprocess, "run", fake_run)

    path = sidecar_edits.tool_path("extract_subckts")

    assert path == package_root / "bin" / "extract_subckts"
    assert path.read_text(encoding="utf-8") == "binary\n"
    assert captured["check"] is True
    assert captured["command"][-1] == str(package_root / "native" / "extract_subckts.c")


def test_tool_path_reports_missing_native_source_for_unbuilt_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_root = tmp_path / "sidecar_edits"
    package_root.mkdir()

    monkeypatch.setattr(sidecar_edits, "files", lambda package: package_root)

    with pytest.raises(RuntimeError, match="Install a built wheel"):
        sidecar_edits.tool_path("extract_subckts")


def test_basic_example_render_applies_declared_edits(tmp_path: Path) -> None:
    build_lib = build_package(tmp_path)
    output_dir = tmp_path / "example_run"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(build_lib)

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(BASIC_EDITS), str(output_dir)],
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
        "simulator lang=spectre\n"
        'include "/work/netlists/rc_filter_corner_tt.scs"\n'
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


def write_fake_apply_patch(bin_dir: Path) -> Path:
    binary = bin_dir / "apply_patch"
    binary.write_text(
        f"""#!{sys.executable}
from pathlib import Path
import sys

patch = sys.stdin.read()
if "*** Add File: APPLY_PATCH_PROOF.txt" not in patch:
    raise SystemExit(2)
Path("APPLY_PATCH_PROOF.txt").write_text("run_label=tt_1v2_27c\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    binary.chmod(0o755)
    return binary


def test_apply_patch_example_uses_installed_apply_patch_binary(tmp_path: Path) -> None:
    build_lib = build_package(tmp_path)
    output_base = tmp_path / "apply_patch_run"
    output_dir = tmp_path / "apply_patch_run_tt_1v2"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_fake_apply_patch(bin_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(build_lib)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(APPLY_PATCH_EDITS), str(output_base)],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "APPLY_PATCH_PROOF.txt").read_text(encoding="utf-8") == (
        "run_label=tt_1v2_27c\n"
    )
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == (
        "base example\n"
        "run_label=tt_1v2_27c\n"
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
    assert not (output_dir / "psf").exists()
    assert not (output_dir / "scratch.tmp").exists()


def test_param_matrix_example_renders_named_matrix_dirs(tmp_path: Path) -> None:
    output_base = tmp_path / "matrix_run"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(PARAM_MATRIX_EDITS), str(output_base)],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    tt_run = tmp_path / "matrix_run_tt" / "vdd_0p90_temp_c_m40" / "input.scs"
    ss_run = tmp_path / "custom_ss_sweep" / "vdd_1p20_temp_c_125" / "input.scs"

    assert tt_run.read_text(encoding="utf-8") == (
        "simulator lang=spectre\n"
        'include "/work/netlists/amp_tt.scs"\n'
        "parameters corner=tt vdd=0.90 temp=-40\n"
        "save V(out)\n"
    )
    assert ss_run.read_text(encoding="utf-8") == (
        "simulator lang=spectre\n"
        'include "/work/netlists/amp_ss.scs"\n'
        "parameters corner=ss vdd=1.20 temp=125\n"
        "save V(out)\n"
    )


def test_apply_patch_missing_binary_fails_in_renderer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_path = tmp_path / "empty_path"
    empty_path.mkdir()
    monkeypatch.setenv("PATH", str(empty_path))

    with pytest.raises(EditError, match="apply_patch executable not found"):
        apply_patch_edit(
            tmp_path,
            {
                "op": "apply_patch",
                "description": "missing binary test",
                "patch": "*** Begin Patch\n*** Add File: out.txt\n+content\n*** End Patch\n",
            },
            {},
        )


def test_apply_patch_can_be_optional_when_binary_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty_path = tmp_path / "empty_path"
    empty_path.mkdir()
    monkeypatch.setenv("PATH", str(empty_path))

    apply_patch_edit(
        tmp_path,
        {
            "op": "apply_patch",
            "description": "optional proof file edit",
            "optional": True,
            "patch": "*** Begin Patch\n*** Add File: out.txt\n+content\n*** End Patch\n",
        },
        {},
    )

    assert "skip optional optional proof file edit" in capsys.readouterr().out
    assert not (tmp_path / "out.txt").exists()


def test_extract_subckts_missing_packaged_tool_fails_as_edit_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sidecar_edits.render as render

    def missing_tool(name: str) -> Path:
        raise RuntimeError(f"packaged tool is not built: {name}")

    monkeypatch.setattr(render, "tool_path", missing_tool)

    with pytest.raises(EditError, match="extract reusable subcircuits failed"):
        apply_extract_subckts(
            tmp_path,
            {
                "op": "extract_subckts",
                "description": "extract reusable subcircuits",
                "input": "input.scs",
                "output_main": "input_main.scs",
                "output_subckts": "subckts.inc",
            },
            {},
        )


def test_replace_failure_uses_edit_description(tmp_path: Path) -> None:
    target = tmp_path / "input.scs"
    target.write_text("parameters vdd=1.2\n", encoding="utf-8")

    with pytest.raises(EditError, match="update supply include failed"):
        apply_replace(
            target,
            {
                "op": "replace",
                "description": "update supply include",
                "old": "missing token",
                "new": "replacement",
            },
            {},
        )


def test_editfile_can_load_params_from_file(tmp_path: Path) -> None:
    (tmp_path / "base").mkdir()
    (tmp_path / "params.json").write_text('{"run_label": "file"}\n', encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
BASE_DIR = "base"
COMMON_PARAMS_FILE = "params.json"
EDITS = []
""",
        encoding="utf-8",
    )

    render_plan = load_editfile(editfile)
    params = render_plan.param_sets[0].params

    assert params["run_label"] == "file"


def test_editfile_expands_env_vars_in_base_dir_and_params_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_root = tmp_path / "env_root"
    (env_root / "base").mkdir(parents=True)
    (env_root / "params.json").write_text('{"run_label": "env-file"}\n', encoding="utf-8")
    monkeypatch.setenv("SIDECAR_TEST_ROOT", str(env_root))
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
BASE_DIR = "$SIDECAR_TEST_ROOT/base"
COMMON_PARAMS_FILE = "$SIDECAR_TEST_ROOT/params.json"
EDITS = []
""",
        encoding="utf-8",
    )

    render_plan = load_editfile(editfile)
    params = render_plan.param_sets[0].params

    assert render_plan.base_dir == env_root / "base"
    assert params["run_label"] == "env-file"


def test_editfile_can_define_params_inline(tmp_path: Path) -> None:
    (tmp_path / "base").mkdir()
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
BASE_DIR = "base"
COMMON_PARAMS = {"simulator_cmd": "aps", "run_label": "inline"}
EDITS = []
""",
        encoding="utf-8",
    )

    params = load_editfile(editfile).param_sets[0].params

    assert params == {"simulator_cmd": "aps", "run_label": "inline"}


def test_named_param_sets_render_all_by_default(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.txt").write_text("corner=seed\nvdd=seed\n", encoding="utf-8")
    (tmp_path / "ss.json").write_text('{"corner": "ss", "vdd": "0.90"}\n', encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
COMMON_PARAMS = {"vdd": "1.20"}
PARAM_SETS = [
    {"name": "tt", "description": "typical", "params": {"corner": "tt"}},
    {"name": "ss", "targetdir": "custom_ss", "params_file": "ss.json"},
]
EDITS = [
    edit.replace(path="input.txt", old="corner=seed", new="corner={corner}"),
    edit.replace(path="input.txt", old="vdd=seed", new="vdd={vdd}"),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile), str(tmp_path / "run")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (tmp_path / "run_tt" / "input.txt").read_text(encoding="utf-8") == "corner=tt\nvdd=1.20\n"
    assert (tmp_path / "custom_ss" / "input.txt").read_text(encoding="utf-8") == "corner=ss\nvdd=0.90\n"


def test_write_file_edit_creates_generated_file_with_params(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
COMMON_PARAMS = {"name": "stim1", "vdd": "1.2"}
EDITS = [
    edit.write_file(
        path="generated/{name}.inc",
        content="V{name} in 0 PWL(0 0 1n {vdd})\\n",
        description="generate PWL source include",
    ),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile), str(tmp_path / "run")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (tmp_path / "run" / "generated" / "stim1.inc").read_text(encoding="utf-8") == (
        "Vstim1 in 0 PWL(0 0 1n 1.2)\n"
    )


def test_append_file_edit_appends_generated_text_with_params(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.scs").write_text("simulator lang=spectre\n", encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
COMMON_PARAMS = {"include_path": "generated/pwl_sources.inc"}
EDITS = [
    edit.append_file(
        path="input.scs",
        content='include "{include_path}"\\n',
        description="append generated PWL include",
    ),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile), str(tmp_path / "run")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (tmp_path / "run" / "input.scs").read_text(encoding="utf-8") == (
        "simulator lang=spectre\n"
        'include "generated/pwl_sources.inc"\n'
    )


def test_append_file_edit_fails_when_target_is_missing(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
EDITS = [
    edit.append_file(
        path="missing.scs",
        content="include generated/pwl_sources.inc\\n",
        description="append generated PWL include",
    ),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile), str(tmp_path / "run")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert 'EDITS[1] append_file "append generated PWL include" failed' in result.stderr
    assert "append target does not exist" in result.stderr


def test_named_param_sets_run_filter(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.txt").write_text("corner=seed\n", encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
PARAM_SETS = [
    {"name": "tt", "params": {"corner": "tt"}},
    {"name": "ff", "params": {"corner": "ff"}},
]
EDITS = [
    edit.replace(path="input.txt", old="corner=seed", new="corner={corner}"),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sidecar_edits.render",
            str(editfile),
            str(tmp_path / "run"),
            "--run",
            "ff",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not (tmp_path / "run_tt").exists()
    assert (tmp_path / "run_ff" / "input.txt").read_text(encoding="utf-8") == "corner=ff\n"


def test_named_param_sets_unknown_run_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.txt").write_text("corner=seed\n", encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
BASE_DIR = "base"
PARAM_SETS = [
    {"name": "tt", "params": {"corner": "tt"}},
]
EDITS = []
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sidecar_edits.render",
            str(editfile),
            str(tmp_path / "run"),
            "--run",
            "missing",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "unknown parameter set" in result.stderr


def test_param_matrix_single_run_renders_under_output_base(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.txt").write_text("vdd=seed\ntemp=seed\n", encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
COMMON_PARAMS = {"vdd": "from_common"}
PARAM_MATRIX = {
    "vdd": ["0.90", "1.20"],
    "temp_c": [27],
}
EDITS = [
    edit.replace(path="input.txt", old="vdd=seed", new="vdd={vdd}"),
    edit.replace(path="input.txt", old="temp=seed", new="temp={temp_c}"),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [sys.executable, "-m", "sidecar_edits.render", str(editfile), str(tmp_path / "run")],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (tmp_path / "run" / "vdd_0p90_temp_c_27" / "input.txt").read_text(encoding="utf-8") == (
        "vdd=0.90\ntemp=27\n"
    )
    assert (tmp_path / "run" / "vdd_1p20_temp_c_27" / "input.txt").read_text(encoding="utf-8") == (
        "vdd=1.20\ntemp=27\n"
    )


def test_param_matrix_named_sets_use_nested_dirs_and_targetdir(tmp_path: Path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "input.txt").write_text("corner=seed\ntemp=seed\n", encoding="utf-8")
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
from sidecar_edits import edit

BASE_DIR = "base"
PARAM_SETS = [
    {"name": "tt", "params": {"corner": "tt"}},
    {"name": "ss", "targetdir": "custom_ss", "params": {"corner": "ss"}},
]
PARAM_MATRIX = {
    "temp_c": [-40, 125],
}
EDITS = [
    edit.replace(path="input.txt", old="corner=seed", new="corner={corner}"),
    edit.replace(path="input.txt", old="temp=seed", new="temp={temp_c}"),
]
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sidecar_edits.render",
            str(editfile),
            str(tmp_path / "run"),
            "--run",
            "ss",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not (tmp_path / "run_tt").exists()
    assert (tmp_path / "custom_ss" / "temp_c_m40" / "input.txt").read_text(encoding="utf-8") == (
        "corner=ss\ntemp=-40\n"
    )
    assert (tmp_path / "custom_ss" / "temp_c_125" / "input.txt").read_text(encoding="utf-8") == (
        "corner=ss\ntemp=125\n"
    )


def test_param_matrix_rejects_empty_axis(tmp_path: Path) -> None:
    (tmp_path / "base").mkdir()
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
BASE_DIR = "base"
PARAM_MATRIX = {"vdd": []}
EDITS = []
""",
        encoding="utf-8",
    )

    with pytest.raises(EditError, match="PARAM_MATRIX entry vdd must not be empty"):
        load_editfile(editfile)


def test_all_is_allowed_for_single_run_editfile() -> None:
    param_set = ParamSet(name=None, params={"corner": "tt"})

    assert select_param_sets([param_set], run_names=None, all_runs=True) == [param_set]


def test_copy_file_expands_env_vars_in_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets_dir = tmp_path / "assets"
    target_dir = tmp_path / "run"
    assets_dir.mkdir()
    target_dir.mkdir()
    (assets_dir / "model.scs").write_text("model\n", encoding="utf-8")
    monkeypatch.setenv("SIDECAR_ASSETS", str(assets_dir))
    monkeypatch.setenv("SIDECAR_COPY_DEST", "include")

    apply_copy(
        target_dir,
        {
            "op": "copy_file",
            "path": "$SIDECAR_ASSETS/model.scs",
            "to": "$SIDECAR_COPY_DEST/copied.scs",
        },
        {},
        tmp_path,
    )

    assert (target_dir / "include" / "copied.scs").read_text(encoding="utf-8") == "model\n"


def test_edit_target_path_expands_env_vars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_dir = tmp_path / "run"
    target_dir.mkdir()
    (target_dir / "input_main.scs").write_text('include "old.scs"\n', encoding="utf-8")
    monkeypatch.setenv("TARGET_FILE", "input_main.scs")

    apply_edit(
        target_dir,
        edit.replace(
            path="$TARGET_FILE",
            old='include "old.scs"',
            new='include "new.scs"',
        ),
        {},
        tmp_path,
    )

    assert (target_dir / "input_main.scs").read_text(encoding="utf-8") == 'include "new.scs"\n'


def test_extract_subckts_requires_output_paths_before_loading_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sidecar_edits.render as render

    def fail_tool_path(name: str) -> Path:
        raise AssertionError("tool_path should not be called when required fields are missing")

    monkeypatch.setattr(render, "tool_path", fail_tool_path)

    with pytest.raises(EditError, match=r"missing required field\(s\): output_main, output_subckts"):
        apply_extract_subckts(
            tmp_path,
            {
                "op": "extract_subckts",
                "input": "input.scs",
            },
            {},
        )


def test_extract_subckts_expands_env_vars_in_file_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sidecar_edits.render as render

    captured = {}

    def fake_run_command_args(target_dir: Path, command: list[str], optional: bool, description: str) -> None:
        captured["command"] = command

    monkeypatch.setattr(render, "tool_path", lambda name: Path(f"/tools/{name}"))
    monkeypatch.setattr(render, "run_command_args", fake_run_command_args)
    monkeypatch.setenv("INPUT_NETLIST", "input.scs")
    monkeypatch.setenv("MAIN_NETLIST", "main.scs")
    monkeypatch.setenv("SUBCKT_OUTPUT", "generated/subckts.inc")
    monkeypatch.setenv("SIDE_INCLUDE", "../generated/subckts.inc")

    apply_extract_subckts(
        tmp_path,
        {
            "op": "extract_subckts",
            "input": "$INPUT_NETLIST",
            "output_main": "$MAIN_NETLIST",
            "output_subckts": "$SUBCKT_OUTPUT",
            "include": "$SIDE_INCLUDE",
        },
        {},
    )

    assert captured["command"] == [
        "/tools/extract_subckts",
        "input.scs",
        "main.scs",
        "generated/subckts.inc",
        "../generated/subckts.inc",
    ]


def test_extract_subckts_defaults_include_to_output_subckts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sidecar_edits.render as render

    captured = {}

    def fake_run_command_args(target_dir: Path, command: list[str], optional: bool, description: str) -> None:
        captured["command"] = command

    monkeypatch.setattr(render, "tool_path", lambda name: Path(f"/tools/{name}"))
    monkeypatch.setattr(render, "run_command_args", fake_run_command_args)

    apply_extract_subckts(
        tmp_path,
        {
            "op": "extract_subckts",
            "input": "input.scs",
            "output_main": "main.scs",
            "output_subckts": "generated/subckts.inc",
        },
        {},
    )

    assert captured["command"] == [
        "/tools/extract_subckts",
        "input.scs",
        "main.scs",
        "generated/subckts.inc",
        "generated/subckts.inc",
    ]


def test_run_command_expands_env_vars_in_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sidecar_edits.render as render

    captured = {}

    def fake_run_command_args(target_dir: Path, command: list[str], optional: bool, description: str) -> None:
        captured["command"] = command

    monkeypatch.setattr(render, "run_command_args", fake_run_command_args)
    monkeypatch.setenv("TOOL_ROOT", "/opt/tools")

    run_command(
        tmp_path,
        {
            "op": "run",
            "command": ["$TOOL_ROOT/bin/tool", "--input", "{INPUT_PATH}"],
        },
        {"INPUT_PATH": "netlists/input.scs"},
    )

    assert captured["command"] == ["/opt/tools/bin/tool", "--input", "netlists/input.scs"]


def test_editfile_rejects_ambiguous_param_sources(tmp_path: Path) -> None:
    (tmp_path / "base").mkdir()
    editfile = tmp_path / "edit.py"
    editfile.write_text(
        """
BASE_DIR = "base"
COMMON_PARAMS = {"run_label": "inline"}
COMMON_PARAMS_FILE = "params.json"
EDITS = []
""",
        encoding="utf-8",
    )

    with pytest.raises(EditError, match="defines both COMMON_PARAMS and COMMON_PARAMS_FILE"):
        load_editfile(editfile)


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
