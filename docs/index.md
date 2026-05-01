# Analog Sim Studies

Prototype tooling for building repeatable analog simulation runs from a base
directory and a small Python sidecar.

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

The renderer copies the base tree, applies typed edit operations, and writes one
or more concrete run directories.

<div class="grid cards" markdown>

-   :material-pencil-ruler:{ .lg .middle } **Author Edits**

    ---

    Write normal Python in `edits.py`. Use typed helpers under
    `sidecar_edits.edit` for discoverable operations and better errors.

    [:octicons-arrow-right-24: User guide](user-guide.md)

-   :material-source-branch:{ .lg .middle } **Generate Runs**

    ---

    Combine common parameters, named parameter sets, and parameter matrices to
    render multiple simulation directories from one base.

    [:octicons-arrow-right-24: User guide](user-guide.md#parameter-formatting)

-   :material-flash-outline:{ .lg .middle } **Inject Sources**

    ---

    Insert a series source at a uniquely named instance net without introducing
    a wrapper subckt or parsing the full netlist.

    [:octicons-arrow-right-24: Series source injection](user-guide.md#series-source-injection)

-   :material-code-json:{ .lg .middle } **API Reference**

    ---

    Browse generated documentation for every edit helper, including signatures,
    formatting behavior, and failure modes.

    [:octicons-arrow-right-24: API reference](api/edit.md)

</div>

## Quick Start

=== "Install"

    ```bash
    python -m pip install -e .
    ```

=== "Render"

    ```bash
    sidecar-render examples/basic/edits.py /tmp/sidecar_example_run
    ```

=== "Docs"

    ```bash
    python -m mkdocs serve
    ```

!!! note "Prototype status"
    This project is intentionally small and text-first. It favors explicit,
    reviewable edits over a full simulator netlist model.
