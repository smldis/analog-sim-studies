# Hedloom agent guidance

Inherit the project guidance from `../AGENTS.md`. Read `../MANIFESTO.md`, the
root `ONTOLOGY.md`, this unit's `ONTOLOGY.md`, and
`../docs/vision/open-concepts.md` before working here.

This unit owns one thing: the join between an authored study and its execution.
It composes the three beneath it and adds no second notion of anything they
already own. Keep authoring and Plan IR in `hedloom-flow`, attempt identity,
journals, transports, reuse and artifact recording in `hedloom-exec`, and traversal,
readiness and binding in `hedloom-run`. `hedloom-exec` must keep importing neither this
package nor Dask; that independence is what makes the kernel and this façade
separately replaceable.

The invariant every addition here is measured against:

    A body decides what runs; it never decides *whether* it runs.

Reuse, identity, ordering and placement are settled before a body is called.
Anything that would let writing Python acquire scheduling authority belongs
somewhere else, or nowhere.

The standing constraint: do not add result-dependent control. `submit` is the
surface where it would most plausibly arrive disguised as convenience — a
`retry=`, `max_iterations=` or `until=` argument is the tripwire, not a feature.
Planning handles refuse to be read as values for the same reason; if a study
needs to branch on a result, raise it rather than implementing it.

Both examples in `examples/` are evidence, not demonstrations: they run real
ngspice and their numbers are checkable. Keep them runnable, and do not let one
acquire a fixture the other would need.
