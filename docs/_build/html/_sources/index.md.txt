# Analog Sim Studies

Prototype tooling for building repeatable analog simulation runs from a base
directory and a small Python sidecar.

The renderer copies the base tree, applies typed edit operations, and writes one
or more concrete run directories. The interface is intentionally plain Python so
studies can generate edits dynamically while still getting source-location error
reports.

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
sidecar-render examples/basic/edits.py /tmp/sidecar_example_run
```

Build these docs locally:

```bash
python -m sphinx -b html docs docs/_build/html
```

## Main Sections

- [User Guide](user-guide.md): how to author `edits.py`, format parameters,
  inject generated sources, and read errors.
- [API Reference](api): generated signatures and docstrings for every
  helper in `sidecar_edits.edit`.
- [Design Notes](design/traced-edit-api.md): implementation model and maintainer
  constraints for the traced edit API.

```{note}
This project is intentionally small and text-first. It favors explicit,
reviewable edits over a full simulator netlist model.
```
