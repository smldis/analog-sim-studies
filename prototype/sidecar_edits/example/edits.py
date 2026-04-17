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
        "description": "optional apply_patch hook for future workspace-aware edits",
        "optional": True,
        "patch": """*** Begin Patch
*** Add File: APPLY_PATCH_PROOF.txt
+run_label={run_label}
*** End Patch
""",
    },
]
