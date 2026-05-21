# Examples

The repository includes small runnable examples under `examples/`. Run them
from the repository root after installing the package:

```bash
python -m pip install -e .
```

## Basic Edits

```bash
sidecar-render examples/basic/edits.py /tmp/sidecar_example_run
```

This copies a base simulator input directory, extracts subcircuits, copies an
asset, and replaces one include path.

## Apply Patch

```bash
sidecar-render examples/apply_patch/edits.py /tmp/sidecar_apply_patch_run
```

This exercises `extract_subckts`, literal replacement, regex replacement,
system `patch`, and `apply_patch`.

## Parameter Matrix

```bash
sidecar-render examples/param_matrix/edits.py /tmp/sidecar_matrix_run
```

This renders named parameter sets and explicit voltage/temperature matrix
combinations.

## Excel PWL Sources

```bash
sidecar-render examples/pwl_excel/edits.py /tmp/sidecar_pwl_excel_run
```

This reads `examples/pwl_excel/waveforms/startup.xlsx`, converts the sheet named
`startup` into named `PWL(...)` expressions, writes
`generated/pwl_sources.inc`, and appends an include statement to `input.scs`.

The workbook follows the table convention used by `sidecar_edits.pwl`:

| #time | vin | vclk | ireset |
| --- | --- | --- | --- |
| 0 | 0 | 0 | |
| 1n | 0.2 | 1.2 | |
| 2n | | 0 | 1m |
| 5n | 1.2 | | 0 |

The first column must be `#time`. Each remaining column is a source name. Blank
cells mean "do not emit a point for this source at this time."

```{literalinclude} ../examples/pwl_excel/edits.py
:language: python
```
