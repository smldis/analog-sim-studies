# User Guide

An edit file defines how a base simulation directory is transformed into rendered
run directories. The suggested filename is `edits.py`.

## Authoring Edits

Use `from sidecar_edits import edit` and place edit objects in `EDITS`.

```python
from sidecar_edits import edit

BASE_DIR = "base"

COMMON_PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
    "vdd": "1.2",
}

EDITS = [
    edit.extract_subckts(
        description="split reusable subcircuits from main netlist",
        input="input.scs",
        output_main="input_main.scs",
        output_subckts="subckts.inc",
    ),
    edit.write_file(
        path="generated/pwl_sources.inc",
        content="Vstim in 0 PWL(0 0 1n {vdd})\n",
        description="generate PWL source include",
    ),
    edit.append_to_file(
        path="input_main.scs",
        content='include "generated/pwl_sources.inc"\n',
        description="append generated PWL include",
    ),
    edit.replace(
        path="input_main.scs",
        old='include "/seed/netlists/rc_filter.scs"',
        new='include "{netlist_path}"',
        description="select corner netlist",
    ),
]
```

The `edit` namespace keeps supported operations discoverable through editor
autocomplete and normal Python help.

## Parameter Formatting

Edit fields are templates. They are formatted for each selected parameter set
and matrix case when the edit is applied.

```python
edit.replace(
    path="input.scs",
    old="parameters corner=seed",
    new="parameters corner={corner}",
)
```

Formatting rules:

- Path-like fields use parameter formatting and environment-variable expansion.
- Replacement text, generated file content, source lines, and patch text use
  parameter formatting without environment-variable expansion.
- Descriptions are static text and are not parameter-formatted.

## Series Source Injection

Use `insert_series_source_at_instance_net` when a netlist has a uniquely named
X instance and you want to detach one connected net and reattach it through a
source.

```python
edit.insert_series_source_at_instance_net(
    path="input_main.scs",
    instance="X_SIDE_INJECT_001",
    net="in",
    internal_net="in__sidecar_inj",
    source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
    description="inject pulse on unique instance input",
)
```

This transforms:

```spice
X_SIDE_INJECT_001 in out vss vdd amp
```

into:

```spice
Vinj in in__sidecar_inj PULSE(0 1.2 0 10p 10p 4n 8n)
X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp
```

The edit fails if the instance is missing, ambiguous, commented, or if the
selected net is missing or appears more than once on that instance.

## Error Reporting

When an edit fails, the renderer reports the failing `EDITS` entry and the
source location captured when the edit object was created.

```text
error: EDITS[3] replace "select corner netlist" failed
created at edit.py:18 in <module>
reason: replace target not found in /tmp/run/input_main.scs
```

If an edit is created through a helper function, the renderer may show a short
call chain.

## Local Documentation

The repository includes prebuilt HTML documentation under `docs/_build/html/`.
Open `docs/_build/html/index.html` directly to read it without installing the
documentation toolchain.

Regenerating the HTML is an optional maintainer step:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html docs docs/_build/html
```

Preview it with:

```bash
python -m http.server --directory docs/_build/html 8000
```
