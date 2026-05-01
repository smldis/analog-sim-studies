# Analog Sim Studies

Analog Sim Studies is a prototype sidecar edit pipeline for text-first
simulation studies.

The renderer copies a base simulation directory, applies typed edit operations
from `edits.py`, and writes one or more rendered run directories.

## Quick Start

Install the package in editable mode:

```bash
python -m pip install -e .
```

Render the basic example:

```bash
sidecar-render examples/basic/edits.py /tmp/sidecar_example_run
```

Edit operations live under the `sidecar_edits.edit` namespace:

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

Use the [User Guide](user-guide.md) for authoring guidance and the
[API Reference](api/edit.md) for helper signatures and docstrings.
