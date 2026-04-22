from sidecar_edits import tool_path


BASE_DIR = "base"

COPY_IGNORE = [
    "psf/",
    "*.tmp",
]

DEFAULTS = {
    "simulator_cmd": "spectre",
}

PARAMS_FILE = "params.json"

PRE_EDITS = [
    {
        "op": "run",
        "description": "extract subcircuits before applying main-file edits",
        "command": [
            str(tool_path("extract_subckts")),
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
        "description": "installed apply_patch hook",
        "patch": """*** Begin Patch
*** Add File: APPLY_PATCH_PROOF.txt
+run_label={run_label}
*** End Patch
""",
    },
]
