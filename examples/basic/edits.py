from sidecar_edits import edit


BASE_DIR = "base"

COMMON_PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}

# Other supported operations: run, extract_subckts, regex_replace, patch, apply_patch.

EDITS = [
    edit.extract_subckts(
        description="split reusable subcircuits from main netlist",
        input="input.scs",
        output_main="input_main.scs",
        output_subckts="subckts.inc",
    ),
    edit.copy_file(
        path="assets/model_override.scs",
        to="include/model_override.scs",
    ),
    edit.replace(
        path="input_main.scs",
        old='include "/seed/netlists/rc_filter.scs"',
        new='include "{netlist_path}"',
    ),
]
