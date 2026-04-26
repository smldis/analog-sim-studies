# Traced Edit API

Status: Implemented in the prototype.

`edits.py` defines how a base simulation directory is turned into one or more
rendered run directories. Edit operations are written as Python helper calls
under the `sidecar_edits.edit` namespace.

The helpers return typed edit objects. Each object records the source location
where it was created, so renderer errors can point users back to the relevant
line in `edits.py` or in a helper module.

## Authoring Edits

Use `from sidecar_edits import edit` and place edit objects in `EDITS`.

```python
from sidecar_edits import edit

BASE_DIR = "base"

COMMON_PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}

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
    edit.write_file(
        path="generated/pwl_sources.inc",
        content="Vstim in 0 PWL(0 0 1n {vdd})\n",
        description="generate PWL source include",
    ),
    edit.append_file(
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

The `edit` namespace is part of the user interface. It keeps supported
operations discoverable through editor autocomplete and gives each operation a
normal Python signature and docstring.

Descriptions are optional. Use them for human intent, not for restating the
operation name. For example, `description="select corner netlist"` is more useful
than `description="replace include line"`.

## Parameter Formatting

Edit fields are templates. They are formatted for each selected parameter set and
matrix case when the edit is applied.

```python
edit.replace(
    path="input.scs",
    old="parameters corner=seed",
    new="parameters corner={corner}",
)
```

Different fields have different formatting rules:

- Path-like fields use parameter formatting and environment-variable expansion.
- Replacement text, generated file content, and patch text use parameter formatting without
  environment-variable expansion.
- Descriptions are static text and are not parameter-formatted.

`edit.append_file` appends exactly the text passed in `content`; it does not add
newlines automatically. It fails if the target file does not already exist.

## Dynamic Generation

`edits.py` is normal Python. Users can generate edit lists directly.

```python
EDITS = [
    edit.replace(
        path=f"runs/{corner}/input.scs",
        old="corner=seed",
        new=f"corner={corner}",
    )
    for corner in ["tt", "ss", "ff"]
]
```

Generated edits may share the same source line. Error messages still include the
`EDITS` index, operation, description when present, target context, and reason so
the failed generated edit can be identified.

## Error Reporting

When an edit fails, the renderer reports the failing entry and the source
location captured when the edit object was created.

Example:

```text
error: EDITS[3] replace "select corner netlist" failed
created at edits.py:18 in <module>
reason: replace target not found in /tmp/run/input_main.scs
```

If an edit is created through a helper function, the renderer may show a short
call chain:

```text
error: EDITS[1] replace failed
created at helpers/netlist.py:7 in model_include
called from edits.py:15 in <module>
reason: replace target not found in /tmp/run/input.scs
```

Paths under the config directory tree are displayed relative to the config
directory. Paths outside that tree are displayed as absolute paths.

This is not intended to be a full Python traceback. The renderer should show only
the small amount of source context needed to find the edit.

## Implementation Model

Each edit helper returns a frozen, operation-specific edit object. For example, a
replace operation has typed attributes such as `path`, `old`, `new`,
`allow_no_match`, `description`, and `source_stack`.

Edit objects execute through `apply(context)`. The render context provides the
target run directory, config directory, config path, and current parameters.

Operation implementations should read typed attributes from the edit object. Do
not use generic dictionary field bags for the public edit model.

## Maintainer Rules

- Keep edit helpers in the `sidecar_edits.edit` namespace.
- Give each helper a typed keyword-only signature and a concise docstring.
- Keep `description` optional.
- Capture source locations when edit objects are created, not when they are
  applied.
- Keep ordinary edit failures as `EditError` and let the renderer add the common
  `EDITS[index]` and source-location envelope.
- Prefer construction-time tracing over AST parsing. The config file is Python,
  and dynamic generation is a supported workflow.
- Do not accept raw dictionary entries in `EDITS`.
