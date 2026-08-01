# Netlist Decomposition agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`, and
local `unit.toml`, then inspect the relevant implementation and tests.

This unit owns explainable structural-to-functional rules, composition passes,
tagging sets, and dependency metadata over the `spice-canonical` circuit
contract. Keep raw syntax parsing, simulation-input editing, and behavioral
claims unsupported by structural evidence outside this boundary. Update the
local ontology when this being changes; place a changed cross-unit canonical
contract in the closest containing ontology.
