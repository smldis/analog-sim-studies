# Hedloom Flow agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`,
local `unit.toml`, both planning trackers, and `docs/architecture.md`, then
inspect the relevant implementation and tests.

This unit owns executor-neutral operation/flow authoring, early graph
validation, immutable normalized Plan IR, and its simulator-free evidence.
Keep simulation semantics, execution, scheduling and transport, persistence,
recovery, plugins, the complete study lifecycle, and archived sequential
convenience outside this boundary. Update the local ontology when the unit's
being changes; place a changed cross-unit planning contract in the closest
containing ontology.
