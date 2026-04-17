from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
APPLY_PATCH_MANIFEST = REPO_ROOT.parent / "apply-patch" / "Cargo.toml"
APPLY_PATCH_TARGET_DIR = REPO_ROOT / ".cargo-target" / "apply-patch"


BASE_DIR = "base"

DEFAULTS = {
    "simulator_cmd": "spectre",
}

EDITS = [
    {
        "op": "replace",
        "path": "input.scs",
        "old": 'include "/seed/netlists/rc_filter.scs"',
        "new": 'include "{netlist_path}"',
    },
    {
        "op": "regex_replace",
        "path": "input.scs",
        "pattern": r"parameters vdd=\S+ temp=\S+",
        "new": "parameters vdd={vdd} temp={temp_c}",
    },
    {
        "op": "replace",
        "path": "run_sim.sh",
        "old": "spectre input.scs -format psfxl -raw ./psf",
        "new": "{simulator_cmd} input.scs -format psfxl -raw ./psf",
    },
    {
        "op": "patch",
        "description": "optional unified diff hook for structural tweaks",
        "optional": True,
        "strip": 0,
        "patch": """--- notes.txt.orig
+++ notes.txt
@@ -1 +1,2 @@
 base example
+run_label={run_label}
""",
    },
    {
        "op": "apply_patch",
        "description": "workspace apply_patch hook through the local Rust crate",
        "command": [
            "env",
            f"CARGO_TARGET_DIR={APPLY_PATCH_TARGET_DIR}",
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            str(APPLY_PATCH_MANIFEST),
            "--bin",
            "apply_patch",
            "--",
        ],
        "patch": """*** Begin Patch
*** Add File: APPLY_PATCH_PROOF.txt
+run_label={run_label}
*** End Patch
""",
    },
]
