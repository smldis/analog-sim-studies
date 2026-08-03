# ASS Exec

ASS Exec owns the durable lifecycle of one attempt at one planned invocation.
It is the first unit in this repository to own any part of *execute*, and it
deliberately owns only the part that must survive a crash.

The design follows from one asymmetry. After a batch system accepts a job, that
job outlives the worker, executor, scheduler, and client that submitted it. A
transient handle therefore cannot be the authority for it. Attempt identity is
chosen from planning facts *before* submission, written durably before the
substrate is touched, and used afterwards to find work whose receipt was lost.

## What the record guarantees

Each attempt is a plain directory containing an append-only `events.jsonl` and,
once terminal, an atomically published `manifest.json`. State is always derived
by folding that record. Two orderings carry the recovery argument: submission
intent is flushed before any transport call, and the terminal record is written
only after the manifest is visible.

`launch_or_attach(...)` resolves to `claimed`, `attached`, or `completed` — or
raises `UnrecoverableAttempt`, which reports a substrate that cannot say
whether it accepted work. That exception is a supported result. Guessing in its
place is what produces duplicate farm jobs.

## Transports declare what they can answer

A transport moves one attempt to a substrate and reports observations. It never
decides readiness or releases successors. Its `discovery_is_authoritative` flag
governs the *negative* answer only: a positive match is always usable, because
the identity predates the submission that created it.

The only working substrate today is in-process execution — the honest
degenerate case, where accepted work cannot outlive its caller and discovery is
therefore trivially authoritative. LSF and Dask transports do not exist yet.

## Evidence

`tests/test_failure_injection.py` reproduces the two failure injections the
architecture named as decisive, locally, against a fake substrate whose state
outlives its caller. Both must resolve to exactly one job and no rerun. A third
test holds the boundary: reconciliation succeeds from a bundle carrying no
dependency information, so this unit has not absorbed graph scheduling
authority.

See [`DECISIONS.md`](../DECISIONS.md) for what is settled, what is open, and
what would change our minds.
