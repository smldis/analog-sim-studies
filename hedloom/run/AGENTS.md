# Hedloom Run agent guidance

Inherit the project guidance from `../AGENTS.md`. Read `../MANIFESTO.md`, the
root `ONTOLOGY.md`, this unit's `ONTOLOGY.md`, and
`../docs/vision/open-concepts.md` before working here.

This unit owns plan traversal, readiness, value threading, and failure
handling. Keep attempt identity, journals, transports, reuse, and artifact
recording in `hedloom-exec`; keep authoring and Plan IR in `hedloom-flow`.

The standing constraint: do not add result-dependent control here. Branching on
a result, retrying with different inputs, or falling back to another operation
are open architectural questions, and the inquiry explicitly rejected hidden
imperative controllers. If a workload needs one, raise it rather than
implementing it.
