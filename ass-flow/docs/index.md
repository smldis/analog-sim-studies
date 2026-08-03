# ASS Flow

ASS Flow provides a Python-native, executor-neutral planning boundary. Authored
operation and flow calls inside `plan(...)` become one immutable normalized
graph whose bindings, artifact dependencies, nested flow boundaries, policies,
outputs, and canonical JSON can be inspected before runtime work exists.

Collection inputs declared with `artifacts(kind)` are required, non-empty, and
ordered. The Plan records their artifact references in authored order and one
positioned dependency edge per member. Optional operation and flow call keys
share one namespace within each containing boundary. A fully keyed subgraph has
stable scoped invocation, boundary, and connecting-edge IDs across unrelated
earlier insertions.

That stability is deliberately precise rather than global. A keyed call inside
an unkeyed boundary depends on the boundary's authored-order ID. External
sources, unkeyed calls and boundaries, and fallback edges involving an external
source or unkeyed endpoint can likewise be renumbered by earlier authored work.
Keys are Plan identity only, never cache keys, scheduler keys, attempts, runtime
identity, or sequential slots.

The planning package deliberately has no executor authority. Operation bodies
are not called during planning; `submit(...)` refuses execution. Flow bodies do
run as ordinary Python to author the static graph, so avoiding external side
effects inside them remains an authoring responsibility rather than an enforced
property.

## Experimental local lowering evidence

The non-reexported `ass_flow.experimental.local_dask` module is a bounded
instrument for testing whether Plan IR lowers to Dask Delayed. Install the
optional dependency with `python -m pip install -e '.[dask]'`, then run
`PYTHONPATH=src python examples/local_dask_characterization.py`. The
[experimental characterization example](../examples/local_dask_characterization.py)
reuses the public [planning example](../examples/characterization.py), injects
decoded source data, binds exact operation identities to explicit callables,
and prints deterministic semantic results without Dask keys. It is runnable
evidence, not a convenience layer or a working `submit(...)` path.

The instrument does not compute, enforce local placement, schedule, persist,
cancel, publish, resolve source addresses, or execute codecs. Public/general
execution, Distributed/Futures, LSF, retries, persistence, recovery, plugins,
dynamic replanning, production hardening, and sequential convenience remain
excluded. The sequential design record below is inactive historical material,
not a backlog.

The focused tests, planning-only characterization, and explicit local Dask
characterization command are the current evidence for this prototype boundary.
The complete development rationale and evidence remain in the component-owned
`PLANNING.md` and `IMPLEMENTATION.md` trackers.

```{toctree}
:maxdepth: 1
:caption: Architecture

architecture
```

```{toctree}
:maxdepth: 1
:caption: Historical material

archive/sequential-flow-convenience
```
