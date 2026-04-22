BASE_DIR = "base"

DEFAULTS = {}

PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}

# Other supported operations: run, regex_replace, patch, apply_patch.

EDITS = [
    {
        "op": "copy_file",
        "path": "assets/model_override.scs",
        "to": "include/model_override.scs",
    },
    {
        "op": "replace",
        "path": "input.scs",
        "old": 'include "/seed/netlists/rc_filter.scs"',
        "new": 'include "{netlist_path}"',
    },
]
