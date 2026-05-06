# PWL Table Source Generation

Status: Draft.

## Problem

Analog studies often need many related PWL voltage or current sources. Users may
prefer to author the waveform data graphically in a spreadsheet-like tool, then
export, save, or copy a table that the study can consume.

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

## Input Sources

The table content should be accepted from multiple common spreadsheet workflows.

Support should include the common formats users already get from spreadsheet
tools:

- CSV files.
- TSV files.
- Delimited text strings copied from Excel, LibreOffice, or similar tools.
- `.xlsx` with sheet selection by name.
- `.ods` with sheet selection by name.
- Other tabular formats that pandas can read with a reasonable dependency
  story.

The API should make the source explicit enough that users do not have to learn a
conversion pipeline before using the feature. A user who has data open in a
spreadsheet should be able to either save the workbook, export CSV/TSV, or paste
the selected range into a Python string.

## Proposed Library Shape

The library could live under `sidecar_edits.pwl` or a similar small module. It
should not try to know the instance name, source kind, or connected nodes. Those
belong to the user's netlist context.

Potential user-facing API:

```python
from sidecar_edits import edits
from sidecar_edits import pwl

waveforms = pwl.waveforms_from_file("waveforms/startup.xlsx", sheet="startup")

source_lines = "\n".join(
    f"V{name} {name} 0 {waveform.render_pwl()}"
    for name, waveform in waveforms.items()
) + "\n"

EDITS = [
    edits.write_file(
        path="generated/startup_pwl.inc",
        content=source_lines,
        description="generate startup PWL sources",
    ),
    edits.append_to_file(
        path="input_main.scs",
        content='include "generated/startup_pwl.inc"\n',
        description="include startup PWL sources",
    ),
]
```

For copied spreadsheet ranges:

```python
waveforms = pwl.waveforms_from_text(
    """
    #time	vin	vclk	ireset
    0	0	0	
    1n	0.2	1.2	
    2n		0	1m
    5n	1.2		0
    """,
)
```

The text loader should detect common delimited input automatically. An explicit
delimiter override can still be added if automatic detection proves ambiguous.

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

The table loaders should return an ordered mapping from table column name to
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

`render_pwl()` should wrap long expressions by default using the SPICE `+`
continuation token. A default target line length around 88 characters is a
reasonable starting point: it is short enough to review and long enough to avoid
excessive wrapping. The renderer should also allow wrapping to be disabled for
users or simulators that prefer a single-line `PWL(...)` expression.

## Edit File Usage

This feature fits the current edit-file model:

1. The edit file is executed.
2. The PWL table is read and converted to named PWL expressions.
3. The rendered run directory is created.
4. User Python composes source lines from the PWL names and expressions.
5. `edits.write_file` writes the generated include.
6. `edits.append_to_file`, `edits.replace`, or a future netlist-aware edit connects
   the include to the main netlist.

No explicit compilation pipeline is needed. The user still writes ordinary
Python and can load the table from a workbook, exported text file, or copied
spreadsheet range before declaring `EDITS`.

## Feasibility

This is feasible with pandas as a normal dependency for the PWL table helper.
Common data-science packages are acceptable here because the feature is about
consuming user-authored tabular data, including workbooks.

Pandas gives one familiar implementation path for CSV, TSV, copied delimited
text, `.xlsx`, `.ods`, and sheet selection. The reader should be hidden behind
domain-specific functions: `waveforms_from_file(...)` and
`waveforms_from_text(...)`. Workbook support may still require the normal pandas
reader engines for specific formats, such as `openpyxl` for `.xlsx` or `odfpy`
for `.ods`; missing engines should produce clear install errors.

If a workbook has exactly one sheet, `waveforms_from_file(...)` should use that
sheet by default. If a workbook has multiple sheets, the user should provide
`sheet="..."`; otherwise the error should mention the available sheet names.

The library does not need to hide pandas if pandas is the right implementation
choice internally, but the user-facing API should stay domain-specific:
`waveforms_from_file(..., sheet="startup")` is clearer than asking users to pass
a DataFrame for the common path.

The implementation risk is mostly validation, not parsing:

- Detect missing or misspelled `#time`.
- Reject duplicate source column names.
- Reject rows with values but empty time.
- Report workbook sheet names clearly when the requested sheet is missing.
- Allow sources with fewer than two points. Some users may intentionally use
  single-point expressions or intermediate generated data.
- Discard source columns with no emitted points.
- Preserve row order exactly. Do not validate monotonic time in the first
  version because time values may contain simulator parameters or expressions.
- Report row/column locations clearly when the table is malformed.
- Reject surrounding whitespace around headers, times, or values instead of
  silently rewriting user-authored SPICE text.

The first version should not parse time units. If users need monotonic
validation later, add an optional validator rather than guessing simulator unit
semantics.

## Usability

The table format is easy to review in version control when exported as CSV or
TSV. Users can keep authoring waveforms graphically while the rendered netlist
remains text-first and reproducible.

Copied text input is useful for quick experiments and reviews. It lets a user
select a range in Excel or LibreOffice and paste it directly into the edit file
or a small helper module without creating a separate artifact. For larger or
long-lived studies, a checked-in CSV/TSV or workbook is more reviewable.

The missing-cell rule is useful because different sources often change at
different times. Requiring every source to have a value at every global time
would make exported tables noisy and harder to review.

The library should not guess this. It should preserve the column name and
generate only the `PWL(...)` expression. Users will have their own conventions
for mapping table names onto actual SPICE source lines, and the edit file is the
right place to express those conventions.

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
