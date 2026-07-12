# Brainstorming

## Named Parameter Sets

Status: Done.

The prototype supports multiple named parameter sets in one edit file,
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

PARAM_MATRIX = {
    "vdd": ["0.90", "1.20"],
    "temp_c": [27, 125],
}
```

A parameter set has a required identifier `name`, optional `description`,
optional `targetdir`, and either inline `params` or `params_file`. `COMMON_PARAMS`
are merged into every set, with the set-specific values taking precedence.
`PARAM_MATRIX` is then applied to every selected set; matrix values override
common and set-specific values for the same key.

CLI:

```bash
sidecar-render examples/basic/edits.py /tmp/run
sidecar-render examples/basic/edits.py /tmp/run --run tt_1v2
sidecar-render examples/basic/edits.py /tmp/run --run tt_1v2 --run ss_0v9
sidecar-render examples/basic/edits.py /tmp/run --all
```

Default output layout:

```text
/tmp/run_tt_1v2/vdd_0p90_temp_c_27/
/tmp/run_tt_1v2/vdd_0p90_temp_c_125/
/tmp/run_tt_1v2/vdd_1p20_temp_c_27/
/tmp/run_tt_1v2/vdd_1p20_temp_c_125/
/tmp/custom_ss_run/vdd_0p90_temp_c_27/
/tmp/custom_ss_run/vdd_0p90_temp_c_125/
```

The command renders all named groups by default. `--all` is accepted mostly for
readability; `--run` selects one or more groups before matrix expansion.

Implementation notes:

- Done: the edit file remains the study definition.
- Done: the CLI selects named parameter sets with `--run`; no selection renders all named sets.
- Done: single-run examples use `COMMON_PARAMS` without requiring `PARAM_SETS`.
- Done: named parameter sets treat the output argument as a base output path.
- Done: per-run parameters merge as `COMMON_PARAMS | PARAM_SETS[i]["params"]`.
- Done: `PARAM_MATRIX` applies after parameter-set selection and renders matrix cases one level deeper.
- Done: matrix values are explicit lists only; users can generate those lists in Python if they want sweep syntax.
- Done: tests cover selected runs, all runs by default, explicit target directories, matrix expansion, and unknown run names.
- Open: avoid putting loops or orchestration logic inside the edit file until a concrete use case requires it.

This adds multi-run preparation without turning the prototype into a full
scheduler or dependency graph yet.

## Render Context Script Interface

Status: Future option.

The current interface treats the edit file as a small Python program that builds
a declarative render plan:

```python
from sidecar_edits import edits

EDITS = [
    edits.replace(path="input.scs", old="corner=seed", new="corner=tt"),
    edits.write_file(path="generated/sources.inc", content=generated_text),
]
```

That model is useful when edits should be reviewable as data: the renderer can
inspect, validate, replay, and report a numbered list of typed operations across
parameter sets and matrix cases.

A complementary interface could make the edit file a normal render script that
receives a renderer-owned context:

```python
def render(ctx):
    ctx.replace(path="input.scs", old="corner=seed", new="corner=tt")
    ctx.write_file(path="generated/sources.inc", content=generated_text)
```

This would not be a raw arbitrary file-mutation script. The context would still
own the run directory, parameter formatting, path handling, optional edit
semantics, and domain-specific errors. The difference is that operations would
execute procedurally instead of first being collected into `EDITS`.

Potential advantages:

- More natural for dynamic generation from spreadsheets, measurements, or other
  Python libraries.
- Normal Python tracebacks point directly into the procedural logic.
- Users do not need to reason about the difference between generating edit
  objects now and applying them later.
- The same helper names could be exposed through `ctx`, preserving autocomplete.

Potential drawbacks:

- The renderer cannot inspect the full edit plan before applying it.
- Dry-run, plan review, and serialization become harder or require recording
  operations as they execute.
- Failure reports would refer to the current operation rather than a stable
  `EDITS[index]` entry.
- Replaying exactly the same plan across runs depends on calling `render(ctx)`
  for every run, so user code must remain deterministic.

Possible coexistence model:

- Keep `EDITS = [...]` as the declarative, reviewable interface.
- Add `def render(ctx): ...` as an optional procedural interface.
- Reject files that define both until there is a concrete reason to combine
  them.
- Share the same operation implementations behind `edits.*` and `ctx.*` to
  avoid maintaining two behavior paths.

This is worth revisiting if dynamic edit generation becomes common enough that
the declarative list feels artificial to users.
