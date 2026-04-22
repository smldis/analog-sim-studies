# Analog Sim Studies

The design note for this package lives in [design/manifesto.md](design/manifesto.md).

## Layout

- `src/sidecar_edits/` contains the package implementation
- `examples/basic/` contains a small runnable sidecar-edit example
- `examples/apply_patch/` contains the fuller example with `apply_patch`
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
install rebuilds the native helper if needed and points the CLI at the source
under `src/sidecar_edits/`, so Python source changes are picked up without
reinstalling. If you change the C helper in `src/sidecar_edits/native/`, rerun
`python -m pip install -e .`.

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

The `apply_patch` operation uses the installed `apply_patch` executable from
`PATH` by default. If it is missing, the renderer raises a package-level
`EditError` with an installation/configuration hint; the example does not call
`cargo` or define tool-specific environment variables.

Every edit operation may include an optional `description`. It should describe
the intended edit, for example `add run label to notes`, not the command or tool
used to perform it. Required edits fail by default; set `optional: True` only
when a skipped edit is acceptable.

Parameters are selected inside `edits.py`, not on the command line. Use
`PARAMS_FILE = "params.json"` to load a JSON file next to the edit spec, or use
inline Python values:

```python
PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}
```

Path-like fields expand environment variables such as `$PDK_ROOT` and
`${RUN_ROOT}`. This applies to `BASE_DIR`, `PARAMS_FILE`, the CLI output path,
edit target paths, `copy_file` source/destination paths, `extract_subckts` file
fields, and command arguments. Replacement text is left as normal text, so
simulator-side environment variables can still be preserved intentionally.

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
