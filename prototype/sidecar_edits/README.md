# Sidecar Edits Prototype

This prototype keeps simulation source files mostly untouched.

The model is:

- `base/` contains raw files copied into a run directory
- `edits.py` contains the parameterized modifications
- `params.json` contains one run's values
- `render.py` copies the tree and applies edits in order

Supported edit kinds:

- `replace`
- `regex_replace`
- `patch` using the system `patch` command
- `apply_patch` as an optional external hook

The `apply_patch` step is intentionally optional in this prototype. If no compatible executable is present, the render still succeeds and prints a skip message.

Example:

```bash
python3 prototype/sidecar_edits/render.py \
  prototype/sidecar_edits/example/edits.py \
  prototype/sidecar_edits/example/params.json \
  prototype/sidecar_edits/out/example_run
```
