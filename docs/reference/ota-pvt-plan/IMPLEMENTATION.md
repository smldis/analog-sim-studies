# OTA PVT Plan Reference implementation tracker

## Status

**Phase:** implementation queued

**Authorized slice:** one root-owned, plan-only OTA/PVT reference

**Runtime status:** explicitly unimplemented

**Component impact:** none; the repository retains four direct children

## Work items

| ID | Work | State | Evidence |
| --- | --- | --- | --- |
| R1 | Freeze ownership, graph, acceptance criteria, and stop conditions | complete | `PLANNING.md`; independent Codex high architecture review |
| R2 | Add six refusing operation declarations, two keyed flows, three ordered points, and `build_plan()` | queued | Must match the authorized normalized shape |
| R3 | Add small versioned input fixtures without executing them | queued | Source paths and PVT values checked structurally |
| R4 | Add root integration evidence for shape, branching, fan-in, determinism, validation, and non-execution | queued | Focused test plus full four-child composition |
| R5 | Link the implemented reference from root documentation and record its narrow ontology evidence | queued | Root README, docs index, and ontology only |
| R6 | Independent source and boundary review | queued | Fresh Codex high review after implementation |
| R7 | Decide whether this evidence is sufficient to design executor lowering | blocked on R2-R6 | Decision must use observed seams, not assume adapters |

## Required implementation constraints

- Every operation body raises `NotImplementedError` with plan-declaration-only
  wording.
- Planning imports no simulator and calls no sibling public API.
- Names corresponding to existing tools are documented as proposed adapter
  boundaries, not working integration.
- Every operation and flow call has an explicit scoped key.
- The final operation uses two ordered collection artifact inputs.
- Fixture paths are versioned external-source URIs; Plan construction performs
  no file I/O.
- No child source, ontology, packaging, or active examples change.
- The inactive sequential-flow convenience remains archived.

## Verification log

No implementation verification has run yet. Add exact commands and results as
work is completed; do not turn a passing static plan into an execution claim.

## Open evidence questions

- Does the current IR retain all point configuration and both ordered fan-ins
  without special domain support?
- Can every meaningful authored identity be keyed while keeping external-source
  identity limitations explicit?
- Does the real reference expose a necessary planner defect, or only future
  adapter/runtime work?
- After this graph exists, is an executor-lowering interface the next smallest
  core experiment, or must the artifact/adapter contracts be resolved first?

## Explicitly deferred

- sibling ASS Flow adapters;
- simulator and waveform integration;
- materialized artifacts and serialization;
- execution, lowering, scheduling, retries, attempts, recovery, and caching;
- provenance, evidence promotion, decisions, and durable study lifecycle;
- production hardening and generalized OTA-study APIs.
