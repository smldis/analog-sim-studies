# Sequential-flow convenience (archived)

- **Status:** inactive historical material
- **Archived by:** user direction
- **Archive date:** 2026-08-03

## Origin

The human-graduated dialecticH baseline recorded in `PLANNING.md` proposed a
sequential-flow editing convenience as one possible acceptance example. The
proposal concerned an authoring layer with ordered slots and editing operations
over them; it was separate from the tested static graph-planning core.

## Why it is not active

The user first deferred this convenience during the bounded planning spike and,
when authorizing promotion to `hedloom-flow/` on 2026-08-03, explicitly archived
it. The promoted evidence does not require sequential editing: arbitrary Python
flow bodies already author the tested static graph, while ordered editing would
introduce a separate identity and mutation design question.

This record is provenance, not a work item, acceptance requirement, stub,
roadmap commitment, or implied backlog.

## Excluded APIs

No public or private API is reserved for sequential flows, ordered slots,
insertion, removal, substitution, or post-definition flow editing. No placeholder
for those operations belongs in `hedloom_flow`.

## Reactivation trigger

Reactivation requires both (1) a new explicit user authorization for a bounded
design slice and (2) observed workflow evidence that users must edit an already
authored ordered flow in ways that ordinary Python composition cannot express
inspectably. If both occur, the idea must be reconsidered as a fresh contract
and ontology decision rather than resumed from an implied backlog.
