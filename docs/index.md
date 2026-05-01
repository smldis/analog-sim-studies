# Analog Sim Studies

Prototype tooling for building repeatable analog simulation runs from a base
directory and a small Python sidecar.

The renderer executes an edit file, copies the base tree, applies typed edit
operations, and writes one or more concrete run directories. The suggested edit
file name is `edit.py`, and the interface is plain Python while still providing
source-location error reports.

```{toctree}
:maxdepth: 2
:caption: Contents

user-guide
api
design/traced-edit-api
design/manifesto
```

## Minimal Example

```python
from sidecar_edits import edit

BASE_DIR = "base"

EDITS = [
    edit.replace(
        path="input.scs",
        old="parameters corner=seed",
        new="parameters corner=tt",
    ),
]
```

## Quick Start

Install the package in editable mode:

```bash
python -m pip install -e .
```

Render the basic example:

```bash
sidecar-render examples/basic/edit.py /tmp/sidecar_example_run
```

This repository includes prebuilt HTML documentation under `docs/_build/html/`.
Regenerate it only when updating the documentation:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -b html docs docs/_build/html
```

## Main Sections

- [User Guide](user-guide.md): how to author an edit file, format parameters,
  inject generated sources, and read errors.
- [API Reference](api): generated signatures and docstrings for every
  helper in `sidecar_edits.edit`.
- [Design Notes](design/traced-edit-api.md): implementation model and maintainer
  constraints for the traced edit API.

```{note}
This project is intentionally small and text-first. It favors explicit,
reviewable edits over a full simulator netlist model.
```
