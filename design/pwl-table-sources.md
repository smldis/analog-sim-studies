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

Core support should include plain text inputs that do not require optional
dependencies:

- CSV files.
- TSV files.
- Delimited text strings copied from Excel, LibreOffice, or similar tools.

Spreadsheet-file support should be a design goal too:

- `.xlsx` with sheet selection by name.
- `.ods` if the dependency story is reasonable.
- Other formats that pandas can read without making the core package heavy.

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
from sidecar_edits import edit
from sidecar_edits import pwl

waveforms = pwl.waveforms_from_file("waveforms/startup.xlsx", sheet="startup")

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
    edit.append_to_file(
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
    delimiter="tab",
)
```

The library can also expose explicit helpers such as `waveforms_from_csv`,
`waveforms_from_tsv`, or `waveforms_from_excel` if that reads better than one
generic `waveforms_from_file`.

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
6. `edit.append_to_file`, `edit.replace`, or a future netlist-aware edit connects
   the include to the main netlist.

No explicit compilation pipeline is needed. The user still writes ordinary
Python and can load the table from a workbook, exported text file, or copied
spreadsheet range before declaring `EDITS`.

## Feasibility

This is feasible, but the dependency boundary matters.

CSV, TSV, and copied text ranges can use the standard library. That should be
the always-available core.

Workbook formats are feasible through existing Python readers, probably via
pandas for a broad and familiar interface. The tradeoff is dependency weight:
pandas plus the relevant engines can be large, and support depends on optional
packages such as `openpyxl` for `.xlsx` or `odfpy` for `.ods`. A practical shape
is:

- Keep core text parsing dependency-free.
- Add spreadsheet support behind an optional dependency extra, for example
  `sidecar-edits-prototype[pwl-spreadsheet]`.
- Raise a clear error when a workbook format is requested without the optional
  dependency installed.
- Support `sheet="name"` for workbook readers from the first spreadsheet-capable
  version.

The library does not need to hide pandas if pandas is the right implementation
choice internally, but the user-facing API should stay domain-specific:
`waveforms_from_file(..., sheet="startup")` is clearer than asking users to pass
a DataFrame for the common path.

The implementation risk is mostly validation, not parsing:

- Detect missing or misspelled `#time`.
- Reject duplicate source column names.
- Reject rows with values but empty time.
- Report workbook sheet names clearly when the requested sheet is missing.
- Decide whether to allow sources with fewer than two points.
- Decide whether to preserve row order exactly or validate monotonic time.
- Report row/column locations clearly when the table is malformed.

The first version should probably preserve row order and not parse time units.
If users need monotonic validation later, add an optional validator rather than
guessing simulator unit semantics.

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
