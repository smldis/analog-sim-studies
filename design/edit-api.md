# Edit API

Status: Implemented in the prototype.

An edit file defines how a base simulation directory is turned into one or more
rendered run directories. The suggested filename is `edit.py`. Edit operations
are written as Python helper calls under the `sidecar_edits.edit` namespace.

The helpers return typed edit objects. Each object records the source location
where it was created, so renderer errors can point users back to the relevant
line in the edit file or in a helper module.

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
    edit.append_to_file(
        path="input_main.scs",
        content='include "generated/pwl_sources.inc"\n',
        description="append generated PWL include",
    ),
    edit.insert_series_source_at_instance_net(
        path="input_main.scs",
        instance="X_SIDE_INJECT_001",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
        description="inject pulse on unique instance input",
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

`edit.append_to_file` appends exactly the text passed in `content`; it does not add
newlines automatically. It fails if the target file does not already exist.

`edit.insert_series_source_at_instance_net` finds one uniquely named X instance,
inserts `source_line` before it, and rewrites one connected net token in the
instance text. The source line can reference `{net}` and `{internal_net}` in
addition to normal render parameters. The first version rejects commented
instance lines and repeated selected net tokens.

## Edit File Execution

The edit file is a Python file. The renderer executes it first, reads the
resulting `BASE_DIR`, parameter definitions, and `EDITS`, and only then applies
the edit operations for each selected run.

This keeps setup code, imports, local helper functions, and data loading in the
normal Python execution model without introducing a separate compilation step.

## Error Reporting

When an edit fails, the renderer reports the failing entry and the source
location captured when the edit object was created.

Example:

```text
error: EDITS[3] replace "select corner netlist" failed
created at edit.py:18 in <module>
reason: replace target not found in /tmp/run/input_main.scs
```

If an edit is created through a helper function, the renderer may show a short
call chain:

```text
error: EDITS[1] replace failed
created at helpers/netlist.py:7 in model_include
called from edit.py:15 in <module>
reason: replace target not found in /tmp/run/input.scs
```

Paths under the edit file directory tree are displayed relative to that
directory. Paths outside that tree are displayed as absolute paths.

This is not intended to be a full Python traceback. The renderer should show only
the small amount of source context needed to find the edit.

## Implementation Model

Each edit helper returns a frozen, operation-specific edit object. For example, a
replace operation has typed attributes such as `path`, `old`, `new`,
`allow_no_match`, `description`, and `source_stack`.

Edit objects execute through `apply(context)`. The render context provides the
target run directory, edit file directory, edit file path, and current
parameters.

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
- Prefer construction-time tracing over AST parsing. The renderer executes the
  edit file before applying edit operations.
- Do not accept raw dictionary entries in `EDITS`.
