# Brainstorming

## Named Parameter Sets

The prototype supports multiple named parameter configurations in one `edits.py`,
then lets the CLI select one or more runs to prepare.

Current prototype shape:

```python
COMMON_PARAMS = {
    "simulator_cmd": "spectre",
    "temp_c": "27",
}

PARAM_SETS = [
    {
        "name": "tt_1v2",
        "description": "typical corner at 1.2 V",
        "params": {
            "netlist_path": "/work/netlists/rc_filter_tt.scs",
            "vdd": "1.20",
        },
    },
    {
        "name": "ss_0v9",
        "targetdir": "custom_ss_run",
        "params": {
            "netlist_path": "/work/netlists/rc_filter_ss.scs",
            "vdd": "0.90",
        },
    },
    {
        "name": "ff_1v3",
        "params_file": "ff_1v3.json",
    },
]
```

A parameter set has a required identifier `name`, optional `description`,
optional `targetdir`, and either inline `params` or `params_file`. `COMMON_PARAMS`
are merged into every set, with the set-specific values taking precedence.

CLI:

```bash
sidecar-render examples/basic/edits.py /tmp/run
sidecar-render examples/basic/edits.py /tmp/run --run tt_1v2
sidecar-render examples/basic/edits.py /tmp/run --run tt_1v2 --run ss_0v9
sidecar-render examples/basic/edits.py /tmp/run --all
```

Default output layout:

```text
/tmp/run_tt_1v2/
/tmp/custom_ss_run/
/tmp/run_ff_1v3/
```

The command renders all named groups by default. `--all` is accepted mostly for
readability; `--run` selects one or more groups.

Design notes:

- Keep `edits.py` as the study definition.
- Let the CLI select which named parameter sets to render.
- Keep single-run examples simple by using only `COMMON_PARAMS`.
- For named parameter sets, treat the output argument as a base output path.
- Merge `COMMON_PARAMS | PARAM_SETS[i]["params"]` per run.
- Avoid putting loops or orchestration logic inside `edits.py` for now.
- Keep tests around selected runs, all runs by default, explicit target directories, and unknown run names.

This adds multi-run preparation without turning the prototype into a full
scheduler or dependency graph yet.
