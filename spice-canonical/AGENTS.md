# SPICE Canonical agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`, and
local `unit.toml`, then inspect the relevant implementation and tests.

This unit owns deterministic extraction of circuits, devices, nets, hierarchy,
and diagnostics from supported netlist syntax while the simulator deck remains
authoritative. Keep functional classification, simulation-input editing, and
project policy outside this boundary. Update the local ontology when this being
changes; place a changed contract with another unit, including the canonical
data consumed by decomposition, in the closest containing ontology.
