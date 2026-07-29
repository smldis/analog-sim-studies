# SPICE Canonical

This unit extracts an LLM-oriented canonical connectivity representation from
Eldo or ngspice netlists. It is independently installable:

```bash
python -m pip install -e .
python -m pytest -q tests
spice-canonical input.cir --format ngspice --output canonical.txt
```

The Python API is `spice_canonical.canonical_netlist`. Includes are expanded
recursively; model libraries can remain opaque; strict mode turns unresolved or
unsupported structures into failures. The representation and parser boundaries
are in
[`docs/design/canonical-netlist-representation.md`](docs/design/canonical-netlist-representation.md).

With ngspice installed, the optional network-backed corpus check is:

```bash
python scripts/verify_ngspice_corpus.py
```

It downloads only checksum-pinned upstream examples. Normal tests remain
offline. See [ONTOLOGY.md](ONTOLOGY.md) for this unit's semantic boundary.
