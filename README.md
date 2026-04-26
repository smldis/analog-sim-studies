# Analog Sim Studies

The design note for this package lives in [design/manifesto.md](design/manifesto.md).

## Layout

- `src/sidecar_edits/` contains the package implementation
- `examples/basic/` contains a small runnable sidecar-edit example
- `examples/apply_patch/` contains the fuller example with `apply_patch`
- `examples/param_matrix/` contains a named parameter-set plus matrix example
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
the configured edit steps. It uses `extract_subckts`, `copy_file`, and
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

The `apply_patch` operation uses the installed `apply_patch` executable from
`PATH` by default. If it is missing, the renderer raises a package-level
`EditError` with an installation/configuration hint; the example does not call
`cargo` or define tool-specific environment variables.

Every edit operation may include an optional `description`. It should describe
the intended edit, for example `add run label to notes`, not the command or tool
used to perform it. Required edits fail by default; set `optional: True` only
when a skipped edit is acceptable.

Edit operations are created through the `sidecar_edits.edit` namespace:

```python
from sidecar_edits import edit

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
    edit.replace(
        path="input_main.scs",
        old='include "/seed/netlists/rc_filter.scs"',
        new='include "{netlist_path}"',
    ),
]
```

These helpers are regular typed Python functions with docstrings, so editor
autocomplete and `help(sidecar_edits.edit.replace)` can show the available
arguments. Raw dictionary edit entries are not supported by the renderer.

Parameters are defined inside `edits.py`, not assembled on the command line. For
a single run, use inline common parameters:

```python
COMMON_PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}
```

For multiple configurations, add `PARAM_SETS`. Rendering all named groups is the
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

## Manual Build Flow

For a build without installing into the environment:

```bash
python setup.py build_py
PYTHONPATH=build/lib python -m sidecar_edits.render \
  examples/basic/edits.py \
  /tmp/sidecar_example_run_manual
```
