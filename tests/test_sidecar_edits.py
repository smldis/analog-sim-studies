from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER = REPO_ROOT / "prototype" / "sidecar_edits" / "render.py"
EXAMPLE_DIR = REPO_ROOT / "prototype" / "sidecar_edits" / "example"
EDITS = EXAMPLE_DIR / "edits.py"
PARAMS = EXAMPLE_DIR / "params.json"


def test_example_render_applies_patch_and_apply_patch(tmp_path: Path) -> None:
    output_dir = tmp_path / "example_run"

    subprocess.run(
        [sys.executable, str(RENDER), str(EDITS), str(PARAMS), str(output_dir)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_dir.exists()
    assert (output_dir / "include" / "model_override.scs").read_text(encoding="utf-8") == (
        "simulator lang=spectre\n"
        "parameters gain_trim=1.05\n"
    )
    assert (output_dir / "input.scs").read_text(encoding="utf-8") == (
        'simulator lang=spectre\n'
        'include "/work/netlists/rc_filter_corner_tt.scs"\n\n'
        "parameters vdd=1.20 temp=27\n\n"
        "tran tran stop=10u\n"
        "save V(out)\n"
    )
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == (
        "base example\n"
        "run_label=tt_1v2_27c\n"
    )
    assert (output_dir / "APPLY_PATCH_PROOF.txt").read_text(encoding="utf-8") == (
        "run_label=tt_1v2_27c\n"
    )
