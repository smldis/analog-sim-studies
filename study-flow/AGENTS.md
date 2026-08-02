# Study Flow agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`, and
local `unit.toml`, then inspect the relevant implementation and tests.

This unit owns a bounded execution experiment: an ASS-authored local
preparation, two mapped basic flows, a reduction, durable demonstration
artifacts, and local or Dask-jobqueue cluster setup. Keep simulator-specific
behavior, production orchestration, durable recovery, evidence authority, and
project-wide policy outside this boundary. Dask Futures and LSF job identifiers
are operational handles, never the only representation of study meaning.
Update the local ontology when the experiment changes what this unit is.
