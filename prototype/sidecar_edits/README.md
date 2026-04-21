# Sidecar Edits Prototype

This prototype keeps simulation source files mostly untouched. The renderer
implementation lives in `src/sidecar_edits/`; this directory is kept as a
small runnable example.

The model is:

- `base/` contains raw files copied into a run directory
- `PRE_EDITS` can run preparation commands after copy and before edits
- `edits.py` contains the parameterized modifications
- `params.json` contains one run's values
- `python -m sidecar_edits.render` copies the tree and applies edits in order

Supported edit kinds:

- `run`
- `copy_file`
- `replace`
- `regex_replace`
- `patch` using the system `patch` command
- `apply_patch` as an optional external hook

`replace` and `regex_replace` are strict by default. Set
`allow_no_match: True` when a missing match should be accepted.

The `apply_patch` step is intentionally optional in this prototype. If no compatible executable is present, the render still succeeds and prints a skip message.

Example:

```bash
python3 setup.py build_py
PYTHONPATH=build/lib python3 -m sidecar_edits.render \
  prototype/sidecar_edits/example/edits.py \
  prototype/sidecar_edits/example/params.json \
  prototype/sidecar_edits/out/example_run
```

The package build compiles the native `extract_subckts` helper once. The render
pipeline then calls the packaged helper instead of rebuilding it per run.

There is also a pytest integration test that runs the example and verifies that
both the standard patch step and the `apply_patch` step take effect.
