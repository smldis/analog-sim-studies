# ASS Run

ASS Run is the step that was missing between authoring a Plan and executing one
invocation: the loop that walks the graph.

It executes invocations in the order the Plan already determines, threads each
one's outputs into the inputs that reference them, reuses work whose inputs have
not changed, and stops on failure with successors reported as `blocked` rather
than run against inputs that do not exist.

It is deliberately a plain sequential driver. There is no concurrency and no
scheduling policy, because the open question is whether a scheduler is needed at
all — and if it is, Dask should replace this unit rather than be absorbed into
it.

Result-dependent control is not here and is not an oversight: whether to reapply
a flow to committed state or to add a visible conditional node is an unresolved
architectural question, recorded in `docs/vision/open-concepts.md`.
