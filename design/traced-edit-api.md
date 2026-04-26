# Traced Edit API

Status: Implemented in the prototype.

The sidecar edit prototype previously described edits as raw dictionaries inside
`edits.py`. That was compact, but it made failures harder to fix: after an edit
failed, the renderer could usually say what operation failed, but it could not
reliably point back to the Python call that created the edit.

The prototype replaces raw edit dictionaries with traced edit helper functions.
The goal is better user-facing errors without adding a separate configuration
compilation step.

## User Model

Users keep writing normal Python config files. Dynamic generation remains a
first-class use case.

```python
from sidecar_edits import edit

EDITS = [
    edit.extract_subckts(
        input="input.scs",
        output_main="input_main.scs",
        output_subckts="subckts.inc",
    ),
    edit.copy_file(
        path="assets/model_override.scs",
        to="include/model_override.scs",
    ),
    edit.replace(
        path="input_main.scs",
        old='include "/seed/netlists/rc_filter.scs"',
        new='include "{netlist_path}"',
        description="select corner netlist",
    ),
]
```

The `edit` namespace is intentional. It gives users autocomplete for supported
operations and gives maintainers one obvious place for API documentation.

Each edit function should be a normal typed Python function with a docstring.
That makes documentation reachable from editors, `help(sidecar_edits.edit)`, and
future generated docs.

## Error Reporting

Each helper captures a short user call stack when it creates the edit object.
When the renderer reports a failure, it should include:

- the config path
- the `EDITS` entry index
- the operation name
- the optional description, when present
- the captured source location or small call stack
- the existing exception reason

Example:

```text
error: examples/basic/edits.py: EDITS[3] replace "select corner netlist" failed
created at examples/basic/edits.py:18
reason: replace target not found in /tmp/run/input_main.scs
```

For wrapped or generated edits, the helper may capture more than one user frame:

```text
created at edits.py:7 in model_include
called from edits.py:15 in <module>
```

This is not meant to be a full traceback. Two to four user frames should be
enough to locate the edit without making errors noisy.

## API Shape

The public API should accept traced edit objects, not raw dictionaries and not a
generic wrapper around dictionaries.

Internally, each operation can have a small typed dataclass:

```python
@dataclass(frozen=True)
class ReplaceEdit:
    op: Literal["replace"]
    path: str
    old: str
    new: str
    description: str | None
    allow_no_match: bool
    source_stack: tuple[SourceFrame, ...]
```

Each helper validates its required arguments through its function signature and
returns the operation-specific edit object. Edit objects own their operation
execution through `apply(context)`, and operation implementations should read
typed attributes rather than a dict-like field bag.

Optional `description` should remain optional. The source location is the stable
locator; the description is human intent.

## Dynamic Generation

The API must keep normal Python generation ergonomic:

```python
EDITS = [
    edit.replace(
        path="input.scs",
        old="corner=seed",
        new=f"corner={corner}",
    )
    for corner in ["tt", "ss", "ff"]
]
```

Generated edits may share the same source line. That is acceptable as long as
the failure also reports `EDITS[index]`, operation details, target paths, and the
underlying reason.

## Maintenance Guidance

Do not add AST parsing as the primary location mechanism. AST parsing is useful
only while `edits.py` remains mostly literal. This project explicitly wants to
keep Python generation available, so construction-time tracing is a better fit.

Do not require users to name every edit. Names become another thing to maintain.
Use the source location, `EDITS[index]`, operation name, and optional
description.

Do not emit large tracebacks for ordinary edit failures. Preserve exception-based
control flow internally, but format user-facing `EditError` messages around the
failed edit.

During the prototype phase, it is acceptable to drop raw dictionary support when
this API lands. Keeping one edit representation will make validation and error
reporting easier to reason about.

## Decisions

- Helper functions should validate required fields through their signatures. They
  do not need extra unknown-field rejection beyond normal Python call behavior.
- `source_stack` may store absolute paths internally. User-facing formatting
  should prefer paths relative to the config file directory when the source file
  is in the same directory tree.
- Operation-specific error context should be selected by the renderer. Prefer
  concrete debugging facts such as target paths, formatted old/new text, command
  arguments, and the underlying exception reason.
