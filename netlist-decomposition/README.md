# Netlist Decomposition

This unit recognizes transistor stacks, bias structures, differential pairs,
stages, and related functional blocks over the canonical circuit contract owned
by the sibling `spice-canonical` distribution.

For a source checkout, install the dependency and this unit explicitly:

```bash
python -m pip install -e ../spice-canonical -e .
python -m pytest -q tests
python scripts/generate_decomposition_dependencies.py --check
```

The optional OTA verifier consumes a sibling SKY130 workspace:

```bash
python scripts/verify_ota_decomposition.py [workspace-dir]
```

See
[`docs/design/functional-decomposition-abel2021.md`](docs/design/functional-decomposition-abel2021.md)
for implemented paper alignment and [ONTOLOGY.md](ONTOLOGY.md) for exclusions.
