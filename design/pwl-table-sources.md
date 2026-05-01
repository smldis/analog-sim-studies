# PWL Table Source Generation

Status: Draft.

## Problem

Analog studies often need many related PWL voltage or current sources. Users may
prefer to author the waveform data graphically in a spreadsheet-like tool, then
export a table that the study can consume.

The package should provide a small reusable library that converts such a table
into SPICE PWL source entries. The edit file can then write the generated source
block to an include file and append or insert an include statement into the
rendered netlist.

This should be a library feature, not a new edit operation. The edit operation
still only writes or appends text; the PWL helper is responsible for generating
that text.

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

This represents three PWL sources:

- `vin` has points at `0`, `1n`, and `5n`.
- `vclk` has points at `0`, `1n`, and `2n`.
- `ireset` has points at `2n` and `5n`.

Missing cells mean "do not emit a point for this source at this time." They do
not mean zero.

The first draft should treat all non-empty cell values as SPICE text and avoid
unit parsing. That keeps the helper compatible with simulator expressions such
as `1.2`, `vdd`, `VDD/2`, `1m`, or `{vdd}`.

## Proposed Library Shape

The library could live under `sidecar_edits.pwl` or a similar small module.

Potential user-facing API:

```python
from sidecar_edits import edit
from sidecar_edits import pwl

sources = pwl.sources_from_csv(
    path="waveforms/startup.csv",
    kind="V",
    positive_node="{name}",
    negative_node="0",
)

EDITS = [
    edit.write_file(
        path="generated/startup_pwl.inc",
        content=sources.render_spice(),
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
class PwlSource:
    name: str
    kind: Literal["V", "I"]
    positive_node: str
    negative_node: str
    points: tuple[PwlPoint, ...]

@dataclass(frozen=True)
class PwlSourceSet:
    sources: tuple[PwlSource, ...]

    def render_spice(self) -> str: ...
```

`positive_node` and `negative_node` should be templates. At minimum `{name}`
should expand to the table column name. Later versions could accept a callback
for custom per-source node mapping.

## Output Format

For the example table above, voltage output could be:

```spice
Vvin vin 0 PWL(0 0 1n 0.2 5n 1.2)
Vvclk vclk 0 PWL(0 0 1n 1.2 2n 0)
Vireset ireset 0 PWL(2n 1m 5n 0)
```

Open choice: source instance naming.

The simplest convention is `<kind><name>`, for example `Vvin`. This is readable
but can collide if the netlist already contains that instance name. A safer
default is a prefix such as `VPWL_<name>` or `IPWL_<name>`. The helper should
probably expose `instance_name="{kind}PWL_{name}"` so users can adapt it.

Open choice: line wrapping.

The first version can emit one source per line. If long PWL entries become
unreadable or simulator line limits matter, add a wrapping option that emits
continuation lines.

## Edit File Usage

This feature fits the current edit-file model:

1. The edit file is executed.
2. The PWL table is read and converted to text.
3. The rendered run directory is created.
4. `edit.write_file` writes the generated include.
5. `edit.append_file`, `edit.replace`, or a future netlist-aware edit connects
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

The main usability risk is source-to-node mapping. A column named `vin` may mean:

- an instance name suffix,
- a positive node,
- a logical signal name that must map to a net,
- or all of the above.

The first API should make the simple case compact while keeping mapping explicit
enough for real netlists. Template fields such as `positive_node="{name}"`,
`negative_node="0"`, and `instance_name="VPWL_{name}"` are likely a good
starting point.

## Fit With The Manifesto

This feature is aligned with the manifesto because it improves reusable,
parameterized, text-first study authoring without trying to replace the
simulator or the GUI waveform editor.

It helps with:

- testbench reuse, by turning waveform definitions into reusable generated
  include files;
- reviewability, because the exported table and generated include are plain
  text;
- automation, because the edit file can regenerate sources for every rendered
  run;
- parameterized studies, because table paths and generated source text can still
  be selected by normal Python and render parameters.

It should stay narrow. The package should not become a waveform editor. It
should provide the bridge from user-authored waveform tables to simulator text.
