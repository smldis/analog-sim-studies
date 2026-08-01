# Sidecar Edits agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`, and
local `unit.toml`, then inspect the relevant implementation and tests.

This unit owns typed edit declarations and their reviewable materialization
from an authoritative base into simulation run directories, including its
parameter, file/text, PWL, and native-helper behavior. Keep simulator execution,
canonical parsing, functional decomposition, and project policy outside this
boundary. Update the local ontology when this being changes; place a changed
contract with another unit in the closest containing ontology.
