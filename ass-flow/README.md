# ASS Flow

ASS Flow is the independently installable prototype for Python-native static
operation and flow planning described in [`PLANNING.md`](PLANNING.md). It
captures immutable definitions, explicit dependencies, nested flow boundaries,
and deterministic, JSON-inspectable Plan IR without executing operation bodies.

Install and test it from this directory with:

```console
python -m pip install -e .
python -m pytest -q
```

The simulator-free example prints the normalized plan it authors:

```console
PYTHONPATH=src python examples/characterization.py | python -m json.tool
```

Flow bodies are ordinary authored Python used to construct a static plan;
their freedom from side effects is an authoring discipline. ASS Flow has no
executor or runtime authority: `submit(...)` refuses execution, and scheduling,
transport, persistence, recovery, and result-dependent replanning are outside
this unit.

See [`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary,
[`docs/index.md`](docs/index.md) for component documentation, and
[`IMPLEMENTATION.md`](IMPLEMENTATION.md) for current evidence and limitations.
