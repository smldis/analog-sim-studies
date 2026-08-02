# Objective

Refine the current main into a coherent and falsifiable architecture for
rebuilding ASS Flow from scratch. Concentrate on the boundary between Dask as
the graph/scheduling kernel, direct per-task LSF submission, reusable
Dask-Jobqueue LSF workers, compact task authoring, and minimal durable attempt
records.

Challenge the preferred design rather than merely elaborating it. In
particular, determine whether Dask's named executor and worker lifecycle can
soundly own external LSF jobs without ASS recreating a workflow scheduler. If
the hypothesis is unsound, explain the failure precisely and compare the
smallest credible existing-engine or boundary alternative.

Produce architectural contracts, decision points, falsification criteria, and
a staged prototype plan. Preserve arbitrary graph support, local-by-default
execution, direct LSF as the primary remote path, pooled LSF as a complementary
path, and the distinction between transient execution handles and durable
records. Do not implement code during this run and do not propose changes to
the protected project manifesto.

Preserve everything in the current main before
`## Active development inquiry: rebuild ASS Flow` byte-for-byte. Proposals
may modify only that section and its descendants.
