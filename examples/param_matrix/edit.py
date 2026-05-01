from sidecar_edits import edit


BASE_DIR = "base"

COMMON_PARAMS = {
    "simulator_cmd": "spectre",
}

PARAM_SETS = [
    {
        "name": "tt",
        "description": "typical process corner",
        "params": {
            "corner": "tt",
            "netlist_path": "/work/netlists/amp_tt.scs",
        },
    },
    {
        "name": "ss",
        "description": "slow process corner with an explicit output parent",
        "targetdir": "custom_ss_sweep",
        "params": {
            "corner": "ss",
            "netlist_path": "/work/netlists/amp_ss.scs",
        },
    },
]

PARAM_MATRIX = {
    "vdd": ["0.90", "1.20"],
    "temp_c": [-40, 27, 125],
}

EDITS = [
    edit.replace(
        description="select corner netlist",
        path="input.scs",
        old='include "/seed/netlists/amp.scs"',
        new='include "{netlist_path}"',
    ),
    edit.replace(
        description="write simulation parameters",
        path="input.scs",
        old="parameters corner=seed vdd=seed temp=seed",
        new="parameters corner={corner} vdd={vdd} temp={temp_c}",
    ),
]
