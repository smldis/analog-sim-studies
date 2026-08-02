# Study Flow agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`, and
local `unit.toml`, then inspect the relevant implementation and tests.

This unit owns a bounded, domain-neutral execution experiment: one recorded
controller-side preparation, a chain of operations mapped over two work items,
one reduction, durable attempt/artifact records, and local or Dask Jobqueue
cluster setup. Keep domain operation semantics, production orchestration,
durable recovery, evidence authority, and project-wide policy outside this
boundary. Dask Futures and LSF identifiers are operational handles, never the
only representation of flow meaning. Update the local ontology whenever the
experiment changes what this unit is.
