# PWL Table Source Generation

Status: Draft.

## Problem

Analog studies often need many related PWL voltage or current sources. Users may
prefer to author the waveform data graphically in a spreadsheet-like tool, then
export a table that the study can consume.

The package should provide a small reusable library that converts such a table
into named SPICE `PWL(...)` expressions. The edit file can then use those names
and expressions to compose the actual voltage or current source lines, write the
generated source block to an include file, and append or insert an include
statement into the rendered netlist.

This should be a library feature, not a new edit operation. The edit operation
still only writes or appends text; the PWL helper is responsible for turning
table columns into reusable PWL data.

## Input Table

The table has one header row.

The first column header is `#time`. Each row below it is a time point. The
remaining column headers are source names.

Example:

```text
#time,vin,vclk,ireset
0,0,0,
1n,0.2,1.2,
2n,,0,1m
5n,1.2,,0
```

This represents three named PWL waveforms:

- `vin` has points at `0`, `1n`, and `5n`.
- `vclk` has points at `0`, `1n`, and `2n`.
- `ireset` has points at `2n` and `5n`.

Missing cells mean "do not emit a point for this source at this time." They do
not mean zero.

The first draft should treat all non-empty cell values as SPICE text and avoid
unit parsing. That keeps the helper compatible with simulator expressions such
as `1.2`, `vdd`, `VDD/2`, `1m`, or `{vdd}`.

## Proposed Library Shape

The library could live under `sidecar_edits.pwl` or a similar small module. It
should not try to know the instance name, source kind, or connected nodes. Those
belong to the user's netlist context.

Potential user-facing API:

```python
from sidecar_edits import edit
from sidecar_edits import pwl

waveforms = pwl.waveforms_from_csv("waveforms/startup.csv")

source_lines = "\n".join(
    f"V{name} {name} 0 {waveform.render_pwl()}"
    for name, waveform in waveforms.items()
) + "\n"

EDITS = [
    edit.write_file(
        path="generated/startup_pwl.inc",
        content=source_lines,
        description="generate startup PWL sources",
    ),
    edit.append_file(
        path="input_main.scs",
        content='include "generated/startup_pwl.inc"\n',
        description="include startup PWL sources",
    ),
]
```

The minimal object model could be:

```python
@dataclass(frozen=True)
class PwlPoint:
    time: str
    value: str

@dataclass(frozen=True)
class PwlWaveform:
    name: str
    points: tuple[PwlPoint, ...]

    def render_pwl(self) -> str: ...
```

`waveforms_from_csv` could return an ordered mapping from table column name to
`PwlWaveform`. The column name is part of the library output because it is the
only context the table owns. The user decides how that name maps to an instance
name, positive node, negative node, or any other netlist convention.

## Output Format

For the example table above, library output would be named PWL expressions:

```spice
vin -> PWL(0 0 1n 0.2 5n 1.2)
vclk -> PWL(0 0 1n 1.2 2n 0)
ireset -> PWL(2n 1m 5n 0)
```

The user can then compose final SPICE lines in the edit file:

```python
lines = []
for name, waveform in waveforms.items():
    lines.append(f"V{name} {name} 0 {waveform.render_pwl()}")
source_block = "\n".join(lines) + "\n"
```

Open choice: line wrapping.

The first version can emit one `PWL(...)` expression per waveform. If long PWL
entries become unreadable or simulator line limits matter, add a wrapping option
that emits continuation lines or returns a sequence of line fragments for the
user to assemble.

## Edit File Usage

This feature fits the current edit-file model:

1. The edit file is executed.
2. The PWL table is read and converted to named PWL expressions.
3. The rendered run directory is created.
4. User Python composes source lines from the PWL names and expressions.
5. `edit.write_file` writes the generated include.
6. `edit.append_file`, `edit.replace`, or a future netlist-aware edit connects
   the include to the main netlist.

No explicit compilation pipeline is needed. The user still writes ordinary
Python and can load the table from CSV, TSV, or another exported format before
declaring `EDITS`.

## Feasibility

This is feasible as a small pure-Python feature.

CSV support can use the standard library. Spreadsheet-native formats such as
`.xlsx` should not be required in the first version because they add optional
dependencies and format-specific behavior. Users can export CSV from graphical
tools, which is good enough for the prototype.

The implementation risk is mostly validation, not parsing:

- Detect missing or misspelled `#time`.
- Reject duplicate source column names.
- Reject rows with values but empty time.
- Decide whether to allow sources with fewer than two points.
- Decide whether to preserve row order exactly or validate monotonic time.
- Report row/column locations clearly when the table is malformed.

The first version should probably preserve row order and not parse time units.
If users need monotonic validation later, add an optional validator rather than
guessing simulator unit semantics.

## Usability

The table format is easy to review in version control when exported as CSV.
Users can keep authoring waveforms graphically while the rendered netlist remains
text-first and reproducible.

The missing-cell rule is useful because different sources often change at
different times. Requiring every source to have a value at every global time
would make exported tables noisy and harder to review.

The main usability risk is source-to-netlist mapping. A column named `vin` may
mean:

- an instance name suffix,
- a positive node,
- a logical signal name that must map to a net,
- or all of the above.

The library should not guess this. It should preserve the column name and
generate only the `PWL(...)` expression. The edit file remains the right place
to map names onto actual SPICE source lines because that is where the user's
netlist conventions are visible.

## Fit With The Manifesto

This feature is aligned with the manifesto because it improves reusable,
parameterized, text-first study authoring without trying to replace the
simulator or the GUI waveform editor.

It helps with:

- testbench reuse, by turning waveform definitions into reusable generated PWL
  expressions or include files;
- reviewability, because the exported table and generated include are plain
  text;
- automation, because the edit file can regenerate sources for every rendered
  run;
- parameterized studies, because table paths and generated source text can still
  be selected by normal Python and render parameters.

It should stay narrow. The package should not become a waveform editor. It
should provide the bridge from user-authored waveform tables to simulator text.
