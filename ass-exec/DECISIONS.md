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

## Premise correction (2026-08-03, user direction)

The unit was built on the architecture's lifetime asymmetry: an accepted batch
job outlives the process that submitted it, so a transient handle cannot own
its identity. **The user has stated the opposite as the design intent — a job
is not supposed to outlive its owner, and a caller crash should take the work
down with it.**

This removes the premise of the graduated main's provisional decision that "an
attempt protocol owns LSF." With owner-bound lifetime, the unsafe transition
that argument was built to survive becomes a defect to prevent rather than a
state to reconcile, and Dask owning the lifecycle is no longer unsound on
lifetime grounds.

**What the failure mode becomes.** Duplicate prevention is replaced by orphan
prevention. The indeterminate-submission window still exists and still matters,
but the correct response inverts: from "refuse to guess, wait to attach" to
"discover it and kill it." Lookup by a pre-chosen unique identity is therefore
still a required site capability, used for reaping rather than attaching, and
identity uniqueness matters more than before because the action it enables is
destructive.

**What enforces it.** An expectation is not a mechanism; unenforced owner-bound
lifetime is how orphans happen. `dask-jobqueue` already implements this for
pooled workers via `--death-timeout` plus `bkill` on cluster close, so pooled
mode should adopt it rather than rebuild it. Direct mode should borrow the same
discipline. Enforcement must not depend on `bsub -I`: the manifesto forbids
authority living in an interactive session, and a lease works identically for a
terminal, a script, CI, or an agent.

**What "resume" means here.** Not reattaching to running work, which no longer
exists. The manifesto's actual requirement is to rerun from a clean environment
without repeating results whose inputs remain valid. That is result reuse and
staleness, and it is the durable record's real purpose in this design —
evidence and reuse, not recovery.

**Consequence for this unit.** Attempt identity, the append-only journal, atomic
terminal publication, the refused/indeterminate distinction, and reconciliation
all survive with changed justifications. The attach disposition and
`UnrecoverableAttempt` are demoted: they are correct only for a transport that
declares detached lifetime, and no such transport exists or is currently wanted.
They are retained, unreachable by default, rather than deleted, because the
distinction they encode is what makes the orphan-reaping path expressible.

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

## Settled by user direction

- **Job lifetime is owner-bound.** Work must not outlive the caller that
  launched it. Detached execution is not wanted.
- **`bsub -J` and lookup by job name are available** at the target site.
- **Minimal local invocations must not pay for durability.** Recording is a
  declared property of work that leaves the process, not a tax on every call.
- **Interactive jobs are permitted at the target site**, so `bsub -I` is the
  direct mode.
- **Many similar jobs belong on a pooled `LSFCluster`**, not on many concurrent
  `-I` submissions.

## Open

- **Owner-bound enforcement — lease rejected, three layers proposed.** A
  bespoke lease file was proposed and rejected: it reinvents, badly, what the
  ecosystem already solves. Surveyed alternatives:

  - *Existing control connection.* `dask-jobqueue` workers exit after
    `death_timeout` (default 60s) when the scheduler is unreachable, and
    `cluster.close()` `bkill`s the jobs. Parsl's high-throughput executor does
    the same with manager-to-interchange heartbeats, and treats heartbeat
    timeout — not direct termination by the executor — as the intended way
    workers go away at shutdown. Effectively a lease, but carried on a channel
    that must exist anyway. Only applies when the remote process is our own
    agent, so it covers pooled mode and not one-`bsub`-per-task. Parsl's
    recurring heartbeat defects (managers evicted for missed heartbeats,
    scale-down broken by an over-aggressive result heartbeat) are the strongest
    argument against hand-rolling this: the mechanism is fiddly even for
    projects whose core competence it is.
  - *Plain batch commands.* Parsl's `LSFProvider` is just `bsub` to submit,
    `bjobs` for status, `bkill` to cancel — the same three primitives assumed
    here, with no lease of its own.
  - *Trap and kill.* Nextflow and Snakemake submit detached and cancel on
    signal. Reported failure modes are consistent: cancelling the controller's
    own cluster job orphans its children, SIGTERM frequently never reaches the
    job, and a backgrounded controller leaks its subtree. Best effort only.
  - *Batch walltime.* `bsub -W` lets LSF bound the job itself. Coarse, but
    unconditional, and the only layer that survives the owner losing power.

  **Accepted (2026-08-03, user direction): `bsub -I`, and none of the above.**
  The site permits interactive jobs, so LSF itself binds job lifetime to the
  submitting client and no lease, heartbeat, signal-trap layer, or reaper is
  needed. An earlier objection — that `-I` loses its guarantee outside an
  interactive session — was wrong: `-I` needs no terminal, blocks, and behaves
  identically under a script. The manifesto's rule about authority not living
  in an interactive session was also mis-applied; `-I` is a transport, while
  intent and records stay in files.

  The one real gap is local, not LSF's: `-I` binds the job to the `bsub` client,
  which is our child. If this process is killed outright the child would be
  reparented and keep the job alive. Closed by keeping the child in our process
  group and setting `PR_SET_PDEATHSIG` on Linux. `-W` is still mandatory as the
  one bound that survives everything else failing.

  Known costs, accepted: one process and one connection per concurrent job, no
  requeue, and output streaming rather than landing in job output files. The
  first is why many jobs go to a pool instead.
- **Orphan reaping.** Mostly obviated by `-I`: a job should not survive its
  owner, so a `bjobs -J` match means something already went wrong.
  `LSFInteractiveTransport.discover(...)` reports such a leftover but nothing
  acts on it automatically, and nothing should until a destructive `bkill` path
  has its own failure injection.
- **Pooled mode.** Accepted in principle for many similar invocations, where
  holding one process per job is the wrong shape. `LSFPooledTransport` is a
  refusing boundary; the implementation should adopt
  `dask_jobqueue.LSFCluster`, whose `death_timeout` and close-time `bkill`
  already give owner-bound worker lifetime. Not started; `dask-jobqueue` is not
  installed in this environment.
- **Result reuse and staleness.** The real resume path: rerun a flow and skip
  invocations whose results are already published and whose inputs are
  unchanged. This needs input identity, which needs a bundle contract, which is
  the next real design question in this unit.
- **Bundle contract.** Bundles are plain mappings today. Whether they derive
  from ASS Flow's Plan IR, and who materializes input values across the
  boundary, is undecided — but result reuse now pushes on it, since reuse is
  only sound if input identity is part of the bundle.
- **Who drives readiness.** Dask remains the hypothesis, and the lifetime
  correction removes the main objection to it owning the lifecycle. Nothing in
  this unit depends on that choice, which is worth preserving.
- **Retry lineage.** `sequence` exists in the identity and is otherwise unused.

## Would change our minds

- A workload that genuinely needs detached execution — an overnight sweep that
  should survive closing a laptop. That would reinstate the lifetime asymmetry
  for that mode only, and the demoted attach path exists so the change would be
  a transport capability rather than a redesign.
- A lease mechanism that cannot bound orphan lifetime under realistic network
  or filesystem failure. That would make owner-bound lifetime an unenforceable
  intent, and direct submission would need to be refused rather than trusted.
- Reconciliation needing to know which nodes were ready. That would mean the
  boundary is wrong and the engine question should be reopened.
- Result reuse proving unsound in practice because input identity cannot be
  captured honestly for simulator work. That would make rerun-everything the
  correct default and reduce the record to pure provenance.
