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
| Dask as the kernel | The main's *preferred hypothesis*: Dask owns graph dependencies, readiness, priorities, retries | Weakened twice. Owner-bound lifetime removed the identity objection that made Dask necessary *and* the one that made it unsound. Then the file-based artifact decision removed its strongest remaining argument: when steps exchange paths on a shared store there are no in-memory values to keep warm and no locality to schedule around. What remains is concurrency and scale, and bounded concurrency is a small addition to `ass-run`. Dask stays relevant for *pooled* execution — many short jobs wanting warm workers — which is a different question from readiness. |
| Component boundary and name | One rebuilt "ASS Flow" | Split into `ass-flow` (planning) and `ass-exec` (attempts), coupled through the Plan document. Nothing yet owns "run the plan", so no unit is operator-facing "flow". Open. |
| "Resume" | Reattaching to running work | Result reuse: rerun and skip work whose inputs are unchanged. |

## Deferred, still wanted

| Concept | Trigger to revisit |
| --- | --- |
| Pooled LSF via `dask_jobqueue.LSFCluster` | A workload needing warm workers or data locality. `LSFPooledTransport` refuses today. |
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
- **Logical scarce resources such as licences.** Named in the policy vocabulary
  and conspicuously relevant here — simulator licences are exactly the scarce
  resource an analog sweep contends for. `LSFInteractiveTransport` passes `-R`
  through, and policy options now reach the run, but nothing yet turns a
  declared licence need into a resource request or reasons about contention.
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

### Why Dask should probably not take slot A

- **Worker occupancy under mixed placement.** If Dask owns both readiness and
  the workers, a task whose placement is `lsf-direct` blocks a Dask worker slot
  for the whole external job while doing nothing. Ten pooled workers and fifty
  direct corners serialise at ten. This is the graduated main's unanswered
  question — how executor capacity corresponds to outstanding LSF jobs — and
  per-invocation placement makes it the normal case rather than an edge case.
  With `ass-run` owning readiness a blocked wait is a thread, and there are no
  slots to contend for.
- **Locality is gone.** Steps exchange file addresses on a shared store, so
  there are no in-memory values to keep warm and nothing to schedule around.
  That was Dask's strongest argument for owning readiness.
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

### Preferred shape

Three placements as peers with readiness staying in `ass-run`. Revisit Dask for
slot A only if task counts and priority needs outgrow a thread pool.

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
