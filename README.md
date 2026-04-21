# Analog Sim Studies Manifesto

The design note for this package lives in [design/manifesto.md](design/manifesto.md).

## Prototype

A tiny sidecar-edits prototype lives in [`prototype/sidecar_edits/`](prototype/sidecar_edits/).

## Build And Run From A Fresh Workspace

Requirements:

- Python 3.10 or newer
- a C compiler available as `cc`
- `patch` for standard unified-diff edit steps
- `cargo` only if you want to exercise the optional `apply_patch` hook

Clone the repository and create a local environment:

```bash
git clone git@github.com:smldis/analog-sim-studies-manifesto.git
cd analog-sim-studies-manifesto
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel pytest
```

Build the package:

```bash
python setup.py build_py
```

This compiles the packaged native helper into `build/lib/sidecar_edits/bin/`.
Run the sidecar example with the built package on `PYTHONPATH`:

```bash
PYTHONPATH=build/lib python -m sidecar_edits.render \
  prototype/sidecar_edits/example/edits.py \
  prototype/sidecar_edits/example/params.json \
  /tmp/sidecar_example_run
```

The example copies `base/`, applies `COPY_IGNORE`, runs `PRE_EDITS`, then
applies the configured edit steps. The optional `apply_patch` hook is skipped if
the local Rust `apply_patch` workspace is not available.

Run the tests:

```bash
python -m pytest -q
```

The package also exposes a console entrypoint after installation:

```bash
python -m pip install .
sidecar-render prototype/sidecar_edits/example/edits.py \
  prototype/sidecar_edits/example/params.json \
  /tmp/sidecar_example_run_installed
```
