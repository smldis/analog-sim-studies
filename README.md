# Analog Sim Studies Manifesto

The design note for this package lives in [design/manifesto.md](design/manifesto.md).

## Layout

- `src/sidecar_edits/` contains the package implementation
- `examples/basic/` contains a small runnable sidecar-edit example
- `tests/` contains the pytest coverage for the current behavior
- `design/` contains the project note and high-level intent

## Install From A Fresh Workspace

Requirements:

- Python 3.10 or newer
- a C compiler available as `cc`

Clone the repository, activate any virtual environment you want to use, then
install the package:

```bash
git clone git@github.com:smldis/analog-sim-studies-manifesto.git
cd analog-sim-studies-manifesto
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

The example copies `examples/basic/base/` into the output directory, then applies
the configured edit steps. The basic example only uses `copy_file` and
`replace`; other operations are listed as a comment in `examples/basic/edits.py`.

Parameters are selected inside `edits.py`, not on the command line. Use
`PARAMS_FILE = "params.json"` to load a JSON file next to the edit spec, or use
inline Python values:

```python
PARAMS = {
    "netlist_path": "/work/netlists/rc_filter_corner_tt.scs",
}
```

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
