# ASS Exec Ontology

## Purpose and scope

ASS Exec owns the durable lifecycle of one attempt at one planned invocation:
an identity chosen before submission, an append-only record of what was
intended and observed, atomic publication of a terminal result manifest, and
the reconciliation that decides whether an attempt may be claimed, attached to,
or completed from existing evidence.

Launched work is **owner-bound**: it is not meant to outlive the caller that
started it, and a caller crash should take it down. The durable record
therefore exists for evidence and for skipping work already validly done, not
for reattaching to work still running from a previous life. The unit was first
built on the opposite premise; see `DECISIONS.md` for that correction and what
survived it.

## Mode of being

**Development state:** `prototype`

The unit studies whether a durable record can carry attempt evidence and result
reuse without absorbing any graph scheduling authority. Its evidence is the two
failure injections named by the architecture — acceptance without receipt, and
terminal state without a recorded manifest — reproduced locally against a fake
substrate, plus a boundary test showing that reconciliation reads no topology.

Those injections were designed under the superseded detached-lifetime premise.
They remain valid evidence about the protocol's behaviour in the indeterminate
window, which owner-bound lifetime narrows but does not remove: a submission
whose outcome is unknown may still have created work that needs killing.

No real batch system is implemented, and no lease enforces owner-bound lifetime
yet. The only working substrate is in-process execution, which is the honest
degenerate case rather than a simulation of a remote one.

## Current contracts

- Distribution: `ass-exec`, independently installable on Python 3.10 or newer,
  with no dependencies. It does not import `ass_flow`.
- `attempt_identity(...)` derives a stable identity from planning facts alone.
  It is a pure function, chosen before submission, and rendered in a form
  usable as a batch job name and a directory component.
- `AttemptJournal` is an append-only JSONL event log plus a published manifest
  in a plain directory. State is derived by folding the record; nothing is
  inferred from a live object.
- `submit_intent` is durably flushed before any transport call. `terminal` is
  recorded only after the manifest is atomically visible.
- `launch_or_attach(...)` resolves to exactly one of `claimed`, `attached`, or
  `completed`, or raises. `UnrecoverableAttempt` is a supported outcome, not a
  defect: it reports a substrate that cannot answer questions about its own
  accepted work.
- A transport declares `discovery_is_authoritative`. This governs the negative
  answer only; a positive discovery is always usable, because the identity
  predates the submission that created the match.
- `SubmissionRefused` is the only submission failure that permits resubmission
  without discovery. Every other failure is indeterminate and holds the attempt
  in the crash window.
- `request_cancel(...)` records intent before contacting the substrate and is
  idempotent. Cancellation is never established by the call returning.
- `reconcile(...)` publishes disagreement between the record and the substrate
  as the terminal outcome `unreconciled` rather than normalizing it into
  success or failure.
- `Durability` is declared per invocation, never inferred from placement.
  `EPHEMERAL` touches no filesystem, requires no identity or root, and reruns
  on every call. `RECORDED` runs the full protocol and completes from an
  existing manifest without rerunning the payload.

## Contribution to the parent

The unit contributes durable attempt identity, recovery, and terminal evidence
to the repository's author-plan-execute-evaluate vision. It is the first unit
to own any part of *execute*.

## Exclusions

ASS Exec owns no graph. It does not decide readiness, order invocations,
release successors, retry, or replan; those remain outside it, and the boundary
is tested by reconciling an attempt from a record that carries no topology. It
does not own LSF or Dask transports, worker pools, placement enforcement,
policy resolution, artifact storage or addressing, codec execution, evidence
promotion, or the study lifecycle. It does not consume Plan IR yet: bundles are
currently plain mappings supplied by a caller.

It does not yet enforce owner-bound lifetime — no lease, heartbeat, or reaping
exists — and it does not yet implement staleness. `RECORDED` reuse is keyed on
attempt identity alone, so it will happily reuse a result whose inputs have
since changed. Sound reuse needs input identity in the bundle, which is
undecided.

## Child composition

There are currently no child units.
