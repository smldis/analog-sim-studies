# ASS Flow

ASS Flow is the independently installable prototype for Python-native static
operation and flow planning described in [`PLANNING.md`](PLANNING.md). It
captures immutable definitions, explicit dependencies, nested flow boundaries,
ordered collection fan-in, scoped authored keys, and deterministic,
JSON-inspectable Plan IR without executing operation bodies.

Use `artifacts(kind)` for a required, non-empty ordered collection input. The
normalized binding preserves member order and emits one positioned dependency
edge per member. Use `.options(key="...")` on operation and flow calls when a
call needs explicit identity within its containing flow boundary. Keys may be
reused in distinct scopes, but operation and flow calls share one key namespace
inside any one scope.

Keys identify Plan nodes only. They are not cache or scheduler keys, attempt or
runtime identities, or sequential slots. Cross-edit stability requires every
relevant enclosing boundary and endpoint to be keyed: unkeyed boundaries and
calls, external sources, and fallback edges retain deterministic authored-order
IDs that can change when earlier work is inserted.

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
local execution, Dask/LSF lowering, retries, persistence, recovery, plugins,
dynamic replanning, production hardening, and result-dependent replanning are
outside this unit. The archived sequential-flow convenience is inactive
historical material, not an active API or backlog.

See [`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary,
[`docs/architecture.md`](docs/architecture.md) for the graduated architecture
adapted to current development status, [`docs/index.md`](docs/index.md) for the
component documentation entry point, and
[`IMPLEMENTATION.md`](IMPLEMENTATION.md) for current evidence and limitations.
