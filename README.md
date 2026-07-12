# Analog Sim Studies

The design note for this package lives in [design/manifesto.md](design/manifesto.md).
The graph-oriented Eldo/ngspice extraction format is specified in
[design/canonical-netlist-representation.md](design/canonical-netlist-representation.md).

## Layout

- `src/sidecar_edits/` contains the simulation-input preparation package
- `src/netlist_decomposition/` contains structural functional-block tagging
- `examples/basic/` contains a small runnable edit-file example
- `examples/apply_patch/` contains the fuller example with `apply_patch`
- `examples/param_matrix/` contains a named parameter-set plus matrix example
- `examples/pwl_excel/` contains an Excel-backed PWL source generation example
- `tests/` contains the pytest coverage for the current behavior
- `design/` contains the project note and high-level intent

## Install From A Fresh Workspace

Requirements:

- Python 3.10 or newer
- a C compiler available as `cc`
- `patch` and an installed `apply_patch` executable on `PATH` for `examples/apply_patch/`

Clone the repository, activate any virtual environment you want to use, then
install the package:

```bash
git clone git@github.com:smldis/analog-sim-studies.git
cd analog-sim-studies
python3 -m venv ../eda-venv
. ../eda-venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

The virtual environment does not need to live inside this repository. Once it is
activated, use `python`, `pip`, and `sidecar-render` directly. The editable
install points the CLI at the source under `src/sidecar_edits/`, so Python
source changes are picked up without reinstalling. The native `extract_subckts`
helper is compiled into `src/sidecar_edits/bin/` on first use when it is missing.
If you change the C helper in `src/sidecar_edits/native/`, remove the old helper
or reinstall before running again.

If you do not want an editable install, use:

```bash
python -m pip install .
```

## Run The Example

With the virtual environment activated:

```bash
sidecar-render \
  examples/basic/edits.py \
  /tmp/sidecar_example_run
```

The basic example copies `examples/basic/base/` into the output directory, then applies
the declared edit steps. It uses `extract_subckts`, `copy_file`, and
`replace`; other operations are listed as a comment in `examples/basic/edits.py`.

The fuller example also exercises `extract_subckts`, `regex_replace`, `patch`,
and `apply_patch`:

```bash
sidecar-render \
  examples/apply_patch/edits.py \
  /tmp/sidecar_apply_patch_run
```

Because this example defines one named parameter set, it renders
`/tmp/sidecar_apply_patch_run_tt_1v2` by default.

The parameter-set and matrix example renders all named process corners and all
explicit voltage/temperature combinations:

```bash
sidecar-render \
  examples/param_matrix/edits.py \
  /tmp/sidecar_matrix_run
```

That creates paths such as:

```text
/tmp/sidecar_matrix_run_tt/vdd_0p90_temp_c_m40/
/tmp/sidecar_matrix_run_tt/vdd_1p20_temp_c_125/
/tmp/custom_ss_sweep/vdd_0p90_temp_c_m40/
```

The Excel PWL example reads `waveforms/startup.xlsx`, creates
`generated/pwl_sources.inc`, and appends an include statement to `input.scs`:

```bash
sidecar-render \
  examples/pwl_excel/edits.py \
  /tmp/sidecar_pwl_excel_run
```

The `apply_patch` operation uses the installed `apply_patch` executable from
`PATH` by default. If it is missing, the renderer raises a package-level
`EditError` with an installation hint; the example does not call
`cargo` or define tool-specific environment variables.

Every edit operation may include an optional `description`. It should describe
the intended edit, for example `add run label to notes`, not the command or tool
used to perform it. Required edits fail by default; set `optional: True` only
when a skipped edit is acceptable.

Edit operations are created through the `sidecar_edits.edits` namespace:

```python
from sidecar_edits import edits

EDITS = [
    edits.extract_subckts(
        description="split reusable subcircuits from main netlist",
        input="input.scs",
        output_main="input_main.scs",
        output_subckts="subckts.inc",
    ),
    edits.copy_file(
        path="assets/model_override.scs",
        to="include/model_override.scs",
    ),
    edits.write_file(
        path="generated/pwl_sources.inc",
        content="Vstim in 0 PWL(0 0 1n {vdd})\n",
        description="generate PWL source include",
    ),
    edits.append_to_file(
        path="input_main.scs",
        content='include "generated/pwl_sources.inc"\n',
        description="append generated PWL include",
    ),
    edits.insert_series_source_at_instance_net(
        path="input_main.scs",
        instance="X_SIDE_INJECT_001",
        net="in",
        internal_net="in__sidecar_inj",
        source_line="Vinj {net} {internal_net} PULSE(0 1.2 0 10p 10p 4n 8n)",
        description="inject pulse on unique instance input",
    ),
    edits.replace(
        path="input_main.scs",
        old='include "/seed/netlists/rc_filter.scs"',
        new='include "{netlist_path}"',
    ),
]
```

These helpers are regular typed Python functions with docstrings, so editor
autocomplete and `help(sidecar_edits.edits.replace)` can show the available
arguments. Raw dictionary edit entries are not supported by the renderer.

Parameters are defined inside the edit file, not assembled on the command line.
The suggested filename is `edits.py`. For a single run, use inline common
parameters:

```python
COMMON_PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}
```

For multiple named runs, add `PARAM_SETS`. Rendering all named groups is the
default; use `--run <name>` one or more times to render a subset. By default,
`sidecar-render edits.py /tmp/run` writes named groups next to the requested path
as `/tmp/run_<name>`. A group can override that with `targetdir`.

```python
COMMON_PARAMS = {
    "simulator_cmd": "spectre",
}

PARAM_SETS = [
    {
        "name": "tt_1v2",
        "description": "typical corner at 1.2 V",
        "params_file": "params.json",
    },
    {
        "name": "ss_0v9",
        "targetdir": "custom_ss_run",
        "params": {"netlist_path": "/work/netlists/rc_filter_ss.scs", "vdd": "0.90"},
    },
]
```

To render every combination of a few explicit axes, add `PARAM_MATRIX`.
`PARAM_MATRIX` is applied after each selected parameter set, so matrix values
override common or set-specific values with the same key. Matrix combinations are
rendered one level deeper:

```python
PARAM_MATRIX = {
    "vdd": ["0.90", "1.20"],
    "temp_c": [27, 125],
}
```

For `sidecar-render edits.py /tmp/run --run tt_1v2`, the output layout is:

```text
/tmp/run_tt_1v2/vdd_0p90_temp_c_27/
/tmp/run_tt_1v2/vdd_0p90_temp_c_125/
/tmp/run_tt_1v2/vdd_1p20_temp_c_27/
/tmp/run_tt_1v2/vdd_1p20_temp_c_125/
```

If the selected parameter set has `targetdir`, that directory replaces
`/tmp/run_tt_1v2` as the parent directory. The matrix syntax intentionally only
accepts lists; generate sweep lists directly in Python if needed.

Path-like fields expand environment variables such as `$PDK_ROOT` and
`${RUN_ROOT}`. This applies to `BASE_DIR`, `COMMON_PARAMS_FILE`, per-group
`params_file`, the CLI output path, `targetdir`, edit target paths, `copy_file`
source/destination paths, `extract_subckts` file fields, and command arguments.
Replacement text is left as normal text, so simulator-side environment variables
can still be preserved intentionally.

Run the tests:

```bash
python -m pip install pytest
python -m pytest -q
```

## Canonical Netlist Extraction

Convert an Eldo netlist into the canonical net and device tables with:

```bash
spice-canonical input.spi --output canonical.txt
```

Select ngspice explicitly for its title, comment, control-block, and device
syntax:

```bash
spice-canonical input.cir --format ngspice --output canonical.txt
```

Use `--strict` when unresolved subcircuits or unsupported proprietary devices
should make extraction fail. The Python API is available from
`spice_canonical.canonical_netlist`. File extraction recursively expands `.INCLUDE`
and `.INC` directives, resolving relative paths from each including file.
`.LIB` model libraries remain opaque. For model files referenced through
`.INCLUDE`, use repeatable `--stop-include GLOB` boundaries and provide named
pin signatures with `--external-subcircuits interfaces.json`. The JSON file
maps external subcircuit names to pin arrays, for example
`{"vendor_nfet": ["d", "g", "s", "b"]}`.

To verify compatibility against checksum-pinned examples from the official
ngspice repository, with ngspice installed:

```bash
python scripts/verify_ngspice_corpus.py
```

## Local Documentation

The repository includes prebuilt static HTML documentation under
`docs/_build/html/`. Open `docs/_build/html/index.html` directly to read it
without installing documentation dependencies.

Regenerating the documentation is an optional maintainer step. Install the
documentation extras only when you need to rebuild the generated HTML:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html docs docs/_build/html
```

Preview the generated HTML with:

```bash
python -m http.server --directory docs/_build/html 8000
```

The Sphinx build imports project modules for API reference generation, so only
run it from a trusted checkout. Normal package installation and test runs do not
need the documentation extras.

## Manual Build Flow

For a build without installing into the environment:

```bash
python setup.py build_py
PYTHONPATH=build/lib python -m sidecar_edits.render \
  examples/basic/edits.py \
  /tmp/sidecar_example_run_manual
```
