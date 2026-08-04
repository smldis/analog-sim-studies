# Open concepts from the ASS Flow rebuild inquiry

The graduated inquiry raised more concepts than the units have implemented.
Development since has been direct rather than work-order driven, which is
faster but loses things quietly — this register exists so that nothing from
the original study is dropped by silence rather than by decision.

Status vocabulary: **realized** (built and evidenced), **changed** (carried but
altered by evidence), **deferred** (still wanted, not started), **dropped**
(fell out without a decision — the category this file exists to expose), and
**rejected** (deliberately abandoned).

## Realized

| Concept | Where | Note |
| --- | --- | --- |
| Static custom-flow composition; one normalized inspectable Plan | `ass-flow` | Accepted with the OTA/PVT domain reference. |
| Declarative source handoff: address, codec, access scope | `ass-flow` | Schema-2 Plan IR. |
| Local Dask Delayed lowering (evidence ladder 3) | `ass-flow` experimental | Bounded instrument, not an execution API. |
| Immutable bundle and stable attempt ID chosen before submission | `ass-exec` | `attempt_identity`, content-addressed. |
| `launch_or_attach` claiming, attaching, or completing | `ass-exec` | Exactly three dispositions or a loud failure. |
| Idempotent `request_cancel` recording intent before acting | `ass-exec` | Cancellation is intent, never established by return. |
| Success requires observed terminal state *and* atomic publication | `ass-exec` | Disagreement publishes `unreconciled`. |
| Both loss windows (evidence ladder 5) | `ass-exec` | Failure injections against a fake substrate. |
| File-first sidecar: identities, append-only attempts, job ID, timestamps, diagnostics, manifest, artifact references | `ass-exec` | Deliberately not a workflow database. |
| Out-of-place execution, declared artifacts, atomic publication | `ass-exec` | Per-attempt workspace; declared outputs only. |
| Materialization before data crosses to an external substrate | `ass-exec` | On a shared store this is recording an address, not moving bytes. |

## Changed by evidence

| Concept | Original stance | Now |
| --- | --- | --- |
| Direct-LSF job lifetime | A job outlives its submitter, so a durable protocol must own its identity | User direction: work is owner-bound. `bsub -I` plus process-group and `PR_SET_PDEATHSIG`. The protocol survives with a changed justification. |
| Dask as the kernel | The main's *preferred hypothesis*: Dask owns graph dependencies, readiness, priorities, retries | Weakened twice. Owner-bound lifetime removed the identity objection that made Dask necessary *and* the one that made it unsound. Then the file-based artifact decision removed its strongest remaining argument: when steps exchange paths on a shared store there are no in-memory values to keep warm and no locality to schedule around. What remains is concurrency and scale, and bounded concurrency is a small addition to `ass-run`. Dask stays relevant for *pooled* execution — many short jobs wanting warm workers — which is a different question from readiness. A third argument, worker occupancy under mixed placement, was **retracted** on 2026-08-04; see below. |
| Component boundary and name | One rebuilt "ASS Flow" | Split into `ass-flow` (planning) and `ass-exec` (attempts), coupled through the Plan document. Nothing yet owns "run the plan", so no unit is operator-facing "flow". Open. |
| "Resume" | Reattaching to running work | Result reuse: rerun and skip work whose inputs are unchanged. |

## Deferred, still wanted

| Concept | Trigger to revisit |
| --- | --- |
| Pooled LSF via `dask_jobqueue.LSFCluster` | **Many short invocations**, where per-job queue dispatch costs more than the work. Not "many invocations": one job each is a good fit for long-running corners regardless of count, and it buys per-corner resource requests, `bkill`, accounting, licence arbitration and failure isolation. `LSFPooledTransport` refuses today. |
| Concurrency in the driver | `ass-run` executes one invocation at a time. Current preference is bounded concurrency here rather than adopting a scheduler, since file-based artifacts removed Dask's locality argument. Revisit if task counts or priority needs outgrow a thread pool. Note that with `bsub -I`, concurrency means one held client process per running job. |
| One-scheduler mixed topology (labelled local, direct-gateway, pooled workers) | Requires pooled mode first; must be demonstrated, not assumed, since `LSFCluster` normally owns its own scheduler. See "Using Dask for both slots" below for why mixed, rather than wholly pooled, is the preferred shape. |
| Delayed versus Futures comparison (evidence ladder 4) | Was to precede accepting `submit(...)`. Partly overtaken: `ass-exec` executes without Dask, so this now only matters if Dask becomes the driver. |
| Real direct-LSF smoke test (evidence ladder 6) | Site access. `examples/lsf_preflight.py` is ready; not runnable now. |
| Plugins and declarative flow configuration | A concrete multi-repository or non-Python authoring need. |
| Artifact checksums and provenance | Deliberate: hashing multi-GB raw files every run is a real cost, and mtime plus size is the cheap staleness signal. Revisit if mtime proves unreliable on NFS. |

## Dropped without a decision — recovered here

These fell out during direct development. None was rejected on merit.

- ~~**Requested versus resolved versus observed placement.**~~ **Recovered.**
  A `placement` journal event records requested and resolved before submission;
  observed is published with the manifest. `ass-run` selects a transport from
  the policy the Plan already resolved, and a placement no transport provides
  is fatal rather than a silent fallback. Moving work between placements
  provably does not invalidate its result.
- ~~**Logical scarce resources such as licences.**~~ **Recovered.**
  A placement may declare `licences={"<name>": n}`, and that becomes a `rusage`
  term on the one job that needs it, alongside `queue`, `cores`, `memory_mb`
  and a raw `resources` escape hatch — all resolved per invocation over the
  transport's site defaults. Contention is deliberately *not* reasoned about
  here: LSF knows the licence count and who holds it, so arbitration is handed
  to the scheduler rather than modelled. Three things this does not settle:
  whether the site's resource names match what a plan authors (ask, do not
  guess — `lsf_preflight.py --licence <name>` checks it), what a licence
  declaration should mean at a placement that cannot arbitrate it (`local` and
  the in-process transport ignore placement entirely today), and whether a
  study wants to *see* contention rather than merely wait inside it.
- ~~**Retry and timeout bounds.**~~ **Recovered.**
  `LSFInteractiveTransport(timeout=...)` now bounds our own wait; a client that
  exceeds it is killed, which with `-I` takes the job too, and the result is
  reported as indeterminate rather than refused. Retry policy beyond
  `max_attempts` remains unmodelled.
- **Explicit fallback rule, absent by default.** Named in the policy model,
  never modelled. Related to result-dependent control below.
- **Result-dependent control and recovery.** Whether to reapply a flow to
  committed explicit state and produce a new versioned plan, or to add a
  visible conditional/recovery node — hidden imperative controllers rejected
  either way. Still open, and now bounded rather than looming: `ass-run` runs
  only fully determined plans and its guidance forbids adding branching
  quietly. The question arrives when a workload needs a fallback.
- **The typed transition contract.** `Operation(validated_config,
  explicit_state, declared_artifacts) -> StepResult` was adopted as a research
  invariant. Three of its four parts now exist in some form; **`explicit_state`
  has never been revisited**, and the question of whether an operation has
  durable state distinct from its artifacts remains unexamined.

## Dask: which slot, and should the slots merge?

Two independent questions were being asked with one word.

**Slot A — who decides what runs next.** `ass-run`'s loop, or a Dask graph.

**Slot B — where one invocation runs.** `local`, `lsf-direct`, or `lsf-pool`,
already resolved per invocation by ASS Flow and honoured per invocation by
`ass-run`.

They do not need merging, and `lsf-pool` is not a merge in any case: it is a
third peer alongside the other two placements.

### Using the pool does not require giving Dask the graph

`dask-jobqueue` can serve as a *transport*. `LSFPooledTransport` would hold a
client to an `LSFCluster`, submit one invocation, wait for its future, and
return. Dask never sees the plan — it sees independent submissions. The pool's
real benefit, avoiding per-task `bsub` latency for many short steps, is
available without handing over graph authority.

### Retracted: the worker-occupancy argument (2026-08-04)

The strongest argument this register made against Dask in slot A was that a
task whose placement is `lsf-direct` would block a Dask worker slot for the
whole external job, so ten pooled workers and fifty direct corners serialise at
ten. **That is wrong, and it was recorded without checking.** It is retracted
rather than quietly edited, because it was cited as reasoning elsewhere.

`distributed.secede()` exists for exactly this case: called from inside a task,
the thread leaves the worker's thread pool, the pool refills the slot, and the
task changes to the `long-running` state which explicitly does not count
against the worker's parallelism limit. `rejoin()` blocks to re-acquire a slot
afterwards, and `worker_client()` is the documented wrapper that does both
safely. The failure mode that would have vindicated the argument — seceded
tasks driving scheduler occupancy negative so those workers hoarded all new
work — was real in 2022.1.0–2022.3.0 and was fixed (dask/distributed#5975, PR
#6351). Evidence is documentary; no spike was run, because `distributed` is not
installed here.

What survives is smaller and worth stating exactly, because it is *neutral*
rather than anti-Dask: a seceded task still holds a real OS thread and a worker
process for the life of the external job, which is the same cost as a blocked
thread in an `ass-run` pool. Dask does not make an outstanding `bsub -I` cheap;
it makes it *no more expensive than doing it ourselves*. And `secede()` has to
be called from within the task, so a blocking transport would need a
Dask-aware wrapper — a small integration cost `ass-run` does not currently pay.

### Why Dask might still not take slot A

- **Locality is gone.** Steps exchange file addresses on a shared store, so
  there are no in-memory values to keep warm and nothing to schedule around.
  That was Dask's strongest argument for owning readiness.
- **Concurrency limits are a site question, not an architecture one.** Each
  simultaneously running `bsub -I` holds a blocked client on the submit host,
  bounded by the concurrency limit rather than the job count. The real ceiling
  is per-user process and pending-job policy at the site, which has not been
  measured; earlier claims of a threshold here were guesses.
- **What remains** is concurrency, priorities, and backpressure. Bounded
  concurrency is a small addition to `ass-run`; the other two are worth
  revisiting only at task counts this project has not reached.

### What a wholly pooled arrangement would cost

Recorded because it is the arrangement to avoid drifting into, not because
anything proposes it. Routing *every* invocation through a pool would give up
one visible LSF job per invocation, force a single worker shape on
heterogeneous work, and remove simulator licences from the scheduler that could
arbitrate them — LSF would see workers, not corners. Per-invocation placement is
precisely what prevents this, provided placements are actually authored.

### The counter-case, which this register had underweighted

Recorded so the next reader argues both sides rather than inheriting one.

- **`ass-run` accreting into a scheduler.** It already owns ordering,
  readiness, failure handling, and placement selection. Concurrency, then
  limits, backpressure, priorities, cancellation, progress reporting — each
  increment is individually reasonable and collectively the workflow engine the
  inquiry warned against building. **Treat the next scheduler-shaped feature
  request as a tripwire, not a task**: if two arrive together, that is the
  signal to reopen this section rather than implement them.
- **Diagnostics.** Dask's dashboard is real operational value on a long sweep.
  `ass-run` has nothing equivalent and no plan for one.
- **Graph-level retries and error propagation** come free with Dask; both are
  currently unmodelled here (`sequence` exists and is unused).
- **Data-parallel post-processing** over many raw files is Dask's home ground.
  If a study needs it, Dask is in the stack anyway and slot A costs less.
- **The graduated main preferred Dask as the kernel**, formed with a
  whole-system view. The arguments against it were assembled incrementally, and
  one of them has now been retracted outright.

### Where this stands, and what would settle it

Provisionally unchanged: readiness stays in `ass-run`, three placements as
peers, bounded concurrency added here rather than adopting a scheduler. But the
justification is now narrower and should be stated as it actually is — not "a
Dask kernel would serialise mixed placement", which was false, but "Dask's
locality advantage does not apply to file artifacts, and its remaining benefits
are ones no workload here has yet asked for." That is a default to challenge.

Discriminating observations, none of which exist yet:

- Real numbers from the OTA/PVT study: how many invocations, how long each, how
  heterogeneous their resource needs. This is the reason to run it first.
- Whether an operator wants a live dashboard for a long sweep. **Ask; do not
  assume.**
- Whether `ass-run` starts needing priorities or backpressure (the tripwire).
- A spike, if the question turns live: `secede()` around a blocking `bsub -I`
  under `LSFCluster`, which also answers whether `dask_jobqueue` tolerates being
  used as a plain submit-and-wait transport for slot B.

Deciding before the study exists would be choosing on aesthetics.

## New ideas raised during development

- **Workspace garbage collection.** Every attempt keeps its own workspace, and
  failed attempts are retained deliberately. Nothing reclaims them. A study
  with many corners and several reruns will accumulate directories that no
  current plan references. Wants a policy — age, superseded-ness, or explicit
  operator action — and must never delete an attempt a live plan still resolves
  to. Recorded as an idea, not scheduled.

## How to use this file

Add to it when a concept is raised and not immediately built. Move rows between
sections when status changes, and say why. A concept leaving this file should
leave because it was realized or rejected, never because nobody mentioned it
again.
