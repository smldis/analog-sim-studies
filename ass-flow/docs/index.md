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

The package deliberately has no executor authority. Operation bodies are not
called during planning; `submit(...)` refuses execution. Flow bodies do run as
ordinary Python to author the static graph, so avoiding external side effects
inside them remains an authoring responsibility rather than an enforced
property. Local execution, Dask/LSF lowering, retries, persistence, recovery,
plugins, dynamic replanning, production hardening, and sequential convenience
are excluded. The sequential design record below is inactive historical
material, not a backlog.

The focused tests and simulator-free characterization example are the current
evidence for this prototype boundary. The complete development rationale and
evidence remain in the component-owned `PLANNING.md` and `IMPLEMENTATION.md`
trackers.

```{toctree}
:maxdepth: 1
:caption: Historical material

archive/sequential-flow-convenience
```
