from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
APPLY_PATCH_MANIFEST = REPO_ROOT.parent / "apply-patch" / "Cargo.toml"
APPLY_PATCH_TARGET_DIR = REPO_ROOT / ".cargo-target" / "apply-patch"
EXTRACT_SUBCKTS_SOURCE = REPO_ROOT / "prototype" / "sidecar_edits" / "extract_subckts.c"


BASE_DIR = "base"

DEFAULTS = {
    "simulator_cmd": "spectre",
}

PRE_EDITS = [
    {
        "op": "run",
        "description": "build extract_subckts helper",
        "command": [
            "cc",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-std=c11",
            "-o",
            "extract_subckts",
            str(EXTRACT_SUBCKTS_SOURCE),
        ],
    },
    {
        "op": "run",
        "description": "extract subcircuits before applying main-file edits",
        "command": [
            "./extract_subckts",
            "input.scs",
            "input_main.scs",
            "subckts.inc",
            "subckts.inc",
        ],
    },
]

EDITS = [
    {
        "op": "copy_file",
        "path": "assets/model_override.scs",
        "to": "include/model_override.scs",
    },
    {
        "op": "replace",
        "path": "input_main.scs",
        "old": 'include "/seed/netlists/rc_filter.scs"',
        "new": 'include "{netlist_path}"',
    },
    {
        "op": "regex_replace",
        "path": "input_main.scs",
        "pattern": r"parameters vdd=\S+ temp=\S+",
        "new": "parameters vdd={vdd} temp={temp_c}",
    },
    {
        "op": "replace",
        "path": "run_sim.sh",
        "old": "spectre input_main.scs -format psfxl -raw ./psf",
        "new": "{simulator_cmd} input_main.scs -format psfxl -raw ./psf",
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
