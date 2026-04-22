BASE_DIR = "base"

DEFAULTS = {}

PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}

# Other supported operations: run, extract_subckts, regex_replace, patch, apply_patch.

EDITS = [
    {
        "op": "extract_subckts",
        "description": "split reusable subcircuits from main netlist",
        "input": "input.scs",
        "output": "input_main.scs",
        "include": "subckts.inc",
    },
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
]
