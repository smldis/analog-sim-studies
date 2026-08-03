# ASS Flow

ASS Flow provides a Python-native, executor-neutral planning boundary. Authored
operation and flow calls inside `plan(...)` become one immutable normalized
graph whose bindings, artifact dependencies, nested flow boundaries, policies,
outputs, and canonical JSON can be inspected before runtime work exists.

The package deliberately has no executor authority. Operation bodies are not
called during planning; `submit(...)` refuses execution. Flow bodies do run as
ordinary Python to author the static graph, so avoiding external side effects
inside them remains an authoring responsibility rather than an enforced
property.

The focused tests and simulator-free characterization example are the current
evidence for this prototype boundary. The complete development rationale and
evidence remain in the component-owned `PLANNING.md` and `IMPLEMENTATION.md`
trackers.

```{toctree}
:maxdepth: 1
:caption: Historical material

archive/sequential-flow-convenience
```
