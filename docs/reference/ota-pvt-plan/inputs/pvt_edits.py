"""Typed Sidecar Edits input for the plan-only OTA/PVT reference fixture."""

from sidecar_edits import edits


REQUIRES = {"base": "base"}

PARAM_SETS = [
    {
        "name": "tt_1v80_27c",
        "description": "typical process at 1.80 V and 27 C",
        "params": {
            "point_id": "tt_1v80_27c",
            "param_set": "tt_1v80_27c",
            "process": "tt",
            "vdd_v": 1.80,
            "temp_c": 27,
        },
    },
    {
        "name": "ss_1v62_125c",
        "description": "slow process at 1.62 V and 125 C",
        "params": {
            "point_id": "ss_1v62_125c",
            "param_set": "ss_1v62_125c",
            "process": "ss",
            "vdd_v": 1.62,
            "temp_c": 125,
        },
    },
    {
        "name": "ff_1v98_m40c",
        "description": "fast process at 1.98 V and -40 C",
        "params": {
            "point_id": "ff_1v98_m40c",
            "param_set": "ff_1v98_m40c",
            "process": "ff",
            "vdd_v": 1.98,
            "temp_c": -40,
        },
    },
]

def edits_for(ctx):
    return [
        edits.replace(
            path="ota_ac.cir",
            old="* PVT point=seed process=seed vdd_v=seed temp_c=seed",
            new=(
                "* PVT point={point_id} process={process} "
                "vdd_v={vdd_v} temp_c={temp_c}"
            ),
            description="record the selected sentinel PVT point",
        ),
        edits.replace(
            path="ota_ac.cir",
            old=".param vdd_v=1.80",
            new=".param vdd_v={vdd_v}",
            description="set the sentinel supply value",
        ),
        edits.replace(
            path="ota_ac.cir",
            old=".temp 27",
            new=".temp {temp_c}",
            description="set the sentinel temperature value",
        ),
    ]
