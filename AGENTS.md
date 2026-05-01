# AGENTS.md

This file is for coding agents contributing to this prototype. Keep changes small,
reviewable, and aligned with the text-first sidecar-edit model.

“Text-first” means edits operate on ordinary files in a copied input directory,
using explicit Python edit objects whose effects can be reviewed and inspected
before simulation.

## Project Intent

`sidecar_edits` prepares simulator input directories from an existing base
directory.

A user starts with a base directory that already contains netlists, scripts,
includes, and other simulator inputs. The tool copies that directory to a new
target directory, then applies a list of explicit Python edit objects to the
copied files. After that, the target directory is ready for the user to inspect
and run with their simulator.

The project is not trying to be a full simulator frontend or full SPICE netlist
model. It is trying to provide a small, reviewable, Python-driven preparation
step for simulation studies where users need to generate variants of an existing
input deck.

This repository currently implements only the preparation layer of the broader
analog-study idea: copy an existing simulator input deck and apply explicit
text/file edits. Do not add simulator launching, waveform parsing, measurement
evaluation, or workflow orchestration unless explicitly requested.

The user-facing edit API lives in `sidecar_edits.edit`. Edit configs should use:

```python
from sidecar_edits import edit
```

Raw dictionary edit entries are intentionally unsupported. Do not reintroduce
them for compatibility unless the API direction is explicitly changed.

When choosing between a narrow file-editing feature and a broader
simulation-management feature, prefer the narrow file-editing feature and
document any broader need in `design/` instead of implementing it.

## Repository Map

- `src/sidecar_edits/edit.py`: typed edit objects and user-facing edit helpers.
- `src/sidecar_edits/render.py`: directory copy, parameter expansion, error
  reporting, and concrete edit application.
- `src/sidecar_edits/native/`: C helper source for subckt extraction.
- `examples/`: runnable edit configuration examples.
- `tests/`: pytest coverage for renderer behavior and API contracts.
- `design/`: human design notes.
- `docs/`: Sphinx/MyST documentation source.
- `docs/_build/html/`: committed static HTML docs for users.

## Normal Verification

Run the Python tests after behavior changes:

```bash
python -m pytest -q
```

For manual smoke testing:

```bash
sidecar-render examples/basic/edits.py /tmp/sidecar_example_run
```

If `sidecar-render` is not installed, use a virtual environment and install the
package in editable mode:

```bash
python -m pip install -e .
```

## Documentation Policy

Normal users should not need documentation build dependencies. Static HTML is
committed under `docs/_build/html/`.

Only install docs extras when regenerating docs:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html docs docs/_build/html
```

Sphinx autodoc imports project modules. Treat docs generation as a trusted-source
maintainer action, not something users must do to run the prototype.

Do not commit Sphinx doctree caches or source maps. The ignore rules intentionally
track distributable HTML while excluding build/debug artifacts.

## Edit API Invariants

When changing `edit.py` or `render.py`, preserve these expectations unless the
user explicitly chooses a new API:

- Edit helpers return typed edit objects with an `apply(context)` method.
- User configs define `EDITS` as a list of edit helper results.
- Each edit captures a source stack so failures can report where the edit was
  created.
- `description` is optional and should explain user intent, not internal
  mechanics.
- Path-like fields may use render parameters and environment variables where the
  existing API already supports them.
- Replacement text is normal text; do not expand environment variables there
  unless explicitly changing the contract.
- Required edits fail by default. Optional behavior should be opt-in and explicit.

## Testing Guidance

For new edit helpers, add tests that cover:

- successful application,
- failure message and source-location reporting,
- parameter formatting behavior,
- ambiguity or no-match cases,
- backwards-compatible behavior of existing helpers.

Prefer real tests over skipped catalog entries. If a test describes an
implementation choice that is not selected, do not keep it as skipped noise.

## Security Notes

The runtime package should not depend on Sphinx/Furo/MyST. Keep documentation
dependencies under the `docs` optional extra.

Avoid import-time side effects in modules used by autodoc, especially filesystem,
network, subprocess, or environment-modifying behavior.

Generated static documentation may include JavaScript and CSS from the Sphinx
theme. Do not add custom remote assets or browser-side data collection.

## Git Workflow

Before editing, check:

```bash
git status --short --branch
```

Do not overwrite unrelated local changes. Keep commits focused and use clear
messages. If pushing is requested:

```bash
git push origin main
```
