# ASS Exec decision ledger

This file replaces the per-phase work-order sequence used through ASS Flow
Phases 1–5. It is a living ledger, not an authorization record: it says what is
settled, what is open, and what observation would change each answer. The code
and its tests are the evidence.

## Recorded process revision (2026-08-03)

The graduated main adopted allocation policy 3, "a reviewed evidence work
order," as the default while the architecture was provisional, and explicitly
made that policy falsifiable: *"Reassess it when repeated reviews add ceremony
without changing scope."*

**Observation.** Across ASS Flow Phases 1–5 the policy produced roughly 1,700
lines of governance around 3,171 lines of source, a paired plan commit and
feature commit per phase, and an independent reviewer pass per phase, while the
component still could not execute a single operation. The ceremony grew; the
scope per slice did not.

**Revision.** Direct human-reviewed development against this ledger, with
review at natural boundaries rather than per phase. What is retained from the
prior policy, because it was the part that worked: falsifiable framing, named
discriminating observations, honest ontologies, and the refusal to let passing
tests silently graduate architecture. What is dropped: work-order identities,
authorization records, stop-condition recitals, and delegated review panes.

This revision is recorded rather than drifted into, as the main requires.

## Settled by evidence in this unit

| Question | Answer | Evidence |
| --- | --- | --- |
| Can a durable record own external attempt identity? | Yes, if identity is chosen before submission. | `test_acceptance_to_receipt_loss_attaches_and_never_duplicates` — one job, one run, after a lost receipt across a restart. |
| What must a site provide for recoverable execution? | Either atomic acceptance-to-receipt, or lookup by an identity chosen beforehand. | `test_acceptance_to_receipt_loss_fails_loudly_without_discovery` — absent both, `UnrecoverableAttempt`. |
| Is a non-authoritative discovery useless? | No. Only the negative answer needs authority. | `test_a_positive_discovery_is_usable_even_without_authority`. |
| Does a transport exception mean the work was refused? | No. Only `SubmissionRefused` establishes that; everything else holds the attempt in the crash window. | `test_indeterminate_submission_blocks_a_blind_resubmission`. |
| Does recovery require graph topology? | No. | `test_recovery_needs_no_knowledge_of_the_graph` — recovery succeeds from a bundle carrying no dependency information. |
| Can cancellation be known? | No, only intended and later reconciled. | `test_success_after_requested_cancellation_is_not_normalized`. |

The fourth row is the boundary result: because reconciliation reads no
topology, this unit has not absorbed graph scheduling authority, and the
architecture's rejection line 1 has not been crossed.

## Open

- **Real batch transport.** Everything above is evidence against a fake
  substrate. It establishes that the protocol is sound, not that any site
  satisfies its precondition. The next question is empirical: are `bsub -J` and
  lookup by job name available and authoritative at the target site?
- **Bundle contract.** Bundles are plain mappings today. Whether they should be
  derived from ASS Flow's Plan IR, and who materializes input values across the
  boundary, is undecided. Deciding it early would couple two units before
  either has earned the coupling.
- **Which invocations pay for durability.** An in-memory Python task should not
  need an attempt directory. The proposal on the table is that an operation
  *declares* whether it is externally executable, so the distinction is
  authored and visible rather than inferred from placement.
- **Who drives readiness.** Dask remains the hypothesis for graph readiness,
  but nothing in this unit depends on it. That is deliberate: the attempt
  protocol should survive replacing the kernel.
- **Retry lineage.** `sequence` exists in the identity and is otherwise unused.
  A retry creating a new attempt only after the prior one is terminal is the
  intended rule; it is not yet implemented or tested.

## Would change our minds

- A site where neither atomicity nor discovery is available, making the whole
  direct-execution line unsupported there rather than merely unimplemented.
- Reconciliation needing to know which nodes were ready, or needing a live
  worker to prevent duplicates. Either would mean the boundary is wrong and the
  engine question should be reopened.
- Repeated real workflows in which the durable record is pure overhead because
  nothing ever crashes. That would be evidence for narrowing the protocol to
  externally executed work only, not for deleting it.
