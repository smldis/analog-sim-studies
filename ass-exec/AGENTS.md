# ASS Exec agent guidance

Inherit the project guidance from `../AGENTS.md`. Before work here, read
`../MANIFESTO.md`, `../ONTOLOGY.md`, local `ONTOLOGY.md`, local `README.md`,
local `unit.toml`, and `DECISIONS.md`, then inspect the implementation and
tests.

This unit owns one attempt at one planned invocation: identity chosen before
submission, an append-only durable record, atomic terminal publication, and
reconciliation. Keep graph readiness, successor release, retries, replanning,
policy resolution, artifact storage, and the study lifecycle outside this
boundary.

Two ordering rules carry the recovery argument and must not be weakened:
submission intent is durably flushed before any transport call, and the
terminal record is written only after the manifest is atomically visible. If a
change makes either ordering inconvenient, that is evidence about the design,
not a reason to reorder them.

Prefer failing loudly over guessing. `UnrecoverableAttempt` is a supported
result. Update the local ontology when the unit's being changes.
