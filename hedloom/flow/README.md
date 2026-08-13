# Hedloom Flow

Hedloom Flow is the independently installable prototype for Python-native static
operation and flow planning described in [`PLANNING.md`](PLANNING.md). It
captures immutable definitions, explicit dependencies, nested flow boundaries,
ordered collection fan-in, scoped authored keys, and deterministic,
JSON-inspectable Plan IR without executing operation bodies. Schema-2 Plans
can also declare an opaque address, codec contract, and assumed access scope
for an already-materialized external source. Source references are classified
as `artifact`; operation outputs remain `ephemeral`.

Use `address(...)`, `codec(...)`, and `materialization(...)` with the strict
`input_artifact(..., artifact=..., materialized_as=...)` surface to record that
data-only source handoff. Optional output materialization capability is
declaration metadata only: it neither publishes a value nor creates a
materialized output.

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

Install the base planning package and run its planning-only evidence from this
directory with:

```console
python -m pip install -e .
PYTHONPATH=src python examples/characterization.py | python -m json.tool
```

The base distribution keeps `dependencies = []`: `import hedloom_flow` and the
planning-only characterization command do not require Dask. To inspect the
non-reexported local lowering experiment, select the exact optional dependency
and run its simulator-free example explicitly:

```console
python -m pip install -e '.[dask]'
python -m pytest -q
PYTHONPATH=src python examples/local_dask_characterization.py \
  | python -m json.tool
```

That example reuses the public characterization Plan, binds its two operation
identities to explicit callables, injects the one already-decoded source value,
and asks Dask to compute synchronously with optimization disabled. Its canonical
stdout contains semantic results and stable Plan metadata, not the fresh Dask
task namespace. The summary visibly retains the authored `tt`, `ss`, `ff`
collection order.

Flow bodies are ordinary authored Python used to construct a static plan;
their freedom from side effects is an authoring discipline. `submit(...)` still
refuses execution. The explicit `hedloom_flow.experimental.local_dask` instrument
only constructs Dask Delayed values; it does not compute, submit, choose or
enforce a scheduler/placement, or provide a general execution API. Public Dask
execution, Distributed/Futures, LSF, retries, persistence, recovery, plugins,
dynamic replanning, production hardening, and result-dependent replanning are
outside this unit. Address resolution, codec execution, actual access checks,
publication, materialized operation outputs, and runtime artifact values are
also outside it. The archived sequential-flow convenience is inactive
historical material, not an active API or backlog.

See [`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary,
[`docs/architecture.md`](docs/architecture.md) for the graduated architecture
adapted to current development status, [`docs/index.md`](docs/index.md) for the
component documentation entry point, and
[`IMPLEMENTATION.md`](IMPLEMENTATION.md) for current evidence and limitations.
