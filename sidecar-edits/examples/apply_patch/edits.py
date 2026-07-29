from sidecar_edits import edits


BASE_DIR = "base"

COPY_IGNORE = [
    "psf/",
    "*.tmp",
]

COMMON_PARAMS = {
    "simulator_cmd": "spectre",
}

PARAM_SETS = [
    {
        "name": "tt_1v2",
        "description": "typical corner at 1.2 V",
        "params_file": "params.json",
    },
]

EDITS = [
    edits.extract_subckts(
        description="split reusable subcircuits from main netlist",
        input="input.scs",
        output_main="input_main.scs",
        output_subckts="subckts.inc",
    ),
    edits.copy_file(
        path="assets/model_override.scs",
        to="include/model_override.scs",
    ),
    edits.replace(
        path="input_main.scs",
        old='include "/seed/netlists/rc_filter.scs"',
        new='include "{netlist_path}"',
    ),
    edits.regex_replace(
        path="input_main.scs",
        pattern=r"parameters vdd=\S+ temp=\S+",
        new="parameters vdd={vdd} temp={temp_c}",
    ),
    edits.replace(
        path="run_sim.sh",
        old="spectre input_main.scs -format psfxl -raw ./psf",
        new="{simulator_cmd} input_main.scs -format psfxl -raw ./psf",
    ),
    edits.patch(
        description="add run label to notes",
        optional=True,
        strip=0,
        patch="""--- notes.txt.orig
+++ notes.txt
@@ -1 +1,2 @@
 base example
+run_label={run_label}
""",
    ),
    edits.apply_patch(
        description="add apply_patch proof file",
        patch="""*** Begin Patch
*** Add File: APPLY_PATCH_PROOF.txt
+run_label={run_label}
*** End Patch
""",
    ),
]
