# Brainstorming

## Named Parameter Sets

A useful next step would be supporting multiple named parameter configurations in
one `edits.py`, then letting the CLI select one or more runs to prepare.

Example shape:

```python
DEFAULTS = {
    "simulator_cmd": "spectre",
    "temp_c": "27",
}

PARAMS = {
    "tt_1v2": {
        "netlist_path": "/work/netlists/rc_filter_tt.scs",
        "vdd": "1.20",
    },
    "ss_0v9": {
        "netlist_path": "/work/netlists/rc_filter_ss.scs",
        "vdd": "0.90",
    },
}
```

Possible CLI:

```bash
sidecar-render examples/basic/edits.py /tmp/runs --run tt_1v2
sidecar-render examples/basic/edits.py /tmp/runs --run tt_1v2 --run ss_0v9
sidecar-render examples/basic/edits.py /tmp/runs --all
```

Possible output layout:

```text
/tmp/runs/
  tt_1v2/
  ss_0v9/
```

Design notes:

- Keep `edits.py` as the study definition.
- Let the CLI select which named parameter sets to render.
- Keep the current single-run `PARAMS = {...}` behavior for simple examples.
- For named parameter sets, treat the output argument as a parent directory.
- Merge `DEFAULTS | PARAMS[name]` per run.
- Avoid putting loops or orchestration logic inside `edits.py` for now.
- Add tests for one selected run, multiple selected runs, all runs, and unknown run names.

This would add multi-run preparation without turning the prototype into a full
scheduler or dependency graph yet.
