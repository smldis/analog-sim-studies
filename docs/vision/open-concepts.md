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
| Concurrency in the driver | `ass-run` executes one invocation at a time. Measured 2026-08-04: a waiting invocation costs ~16 KiB of thread plus one client process, so this is a **safety rail with an arbitrary high default**, not a scheduler feature to tune. The real limiter is the site's MAX JOB policy, per-user process limits, and the licence count. Ask for those numbers rather than inventing one. |
| Per-job status: a `bjobs` watcher and a sweep view | **Wanted, user direction 2026-08-04: a live view of a long sweep matters, and it should show the status of each `bsub -I`.** Nothing provides it today: with `-I` the transport blocks from submission to terminal, so the record cannot distinguish a corner pending in the queue from one simulating. `discover()` and `_state_from_bjobs` already read `PEND/RUN/DONE/EXIT`; nothing calls them while a direct submission is in flight. Shape proposed: one `bjobs` call per refresh for all live identities (job names are `ass-<digest>`), appending `observed` events to each attempt's record, with the view as a reader over journals. Two by-products: it measures **per-job queue latency**, which is the number the pooled-versus-direct question has always lacked, and being a reader rather than a driver feature it works unchanged whoever owns readiness. Site facts to check first, in preflight: whether `bjobs -o` is available and whether `-J` accepts a wildcard. |
| One-scheduler mixed topology (labelled local, direct-gateway, pooled workers) | Requires pooled mode first; must be demonstrated, not assumed, since `LSFCluster` normally owns its own scheduler. See "What \"both slots\" must not be allowed to mean" below for why mixed, rather than wholly pooled, is the preferred shape. |
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

### Measured rather than argued (2026-08-04)

`prototypes/dask_secede_spike.py` runs the question instead of reasoning about
it: a `LocalCluster` of 2 workers x 2 threads, 8 tasks each holding a child
process for 3s, which is the shape of a transport waiting on `bsub -I`.

| | result |
| --- | --- |
| 8 blocking tasks, 4 slots | **6.1s** — serialises at 4, exactly as the old argument claimed |
| the same after `secede()` | **3.1s** — all 8 at once |
| 64 waiters, measured while blocked | 63 threads held, **8.1 MiB** PSS of client processes, **1.0 MiB** of our own growth (~16 KiB per waiting thread) |
| one Dask worker process | **51 MiB** PSS |

Two things follow, and the second matters more than the first.

### Retracted: the worker-occupancy argument

The strongest argument this register made against Dask in slot A was that a
task whose placement is `lsf-direct` would block a Dask worker slot for the
whole external job, so ten workers and fifty direct corners serialise at ten.
**It is retracted**, rather than quietly edited, because it was cited as
reasoning elsewhere.

The measurement above shows the claim *does* describe Dask's default behaviour
— 6.1s is real serialisation. What it gets wrong is the significance. The cap
is `nthreads`, a configuration value chosen for tasks that *compute*; our tasks
wait. And a waiter costs 16 KiB of thread plus one client process. Nothing is
scarce, so the cap is arbitrary, and any of three settings removes it:
`threads_per_worker=200` (~3 MiB), `secede()` (~3 MiB), or one worker process
per job (~10-20 GB for 200 — it works, and it spends the entire memory budget
on idle interpreters).

So the honest correction is not "`secede()` rescues Dask". It is that **the
concurrency question was never about cost**, and neither candidate for slot A
has an advantage in it. That argument is closed in both directions.

### `secede()`: understood, and deliberately not used

Its real purpose is keeping *one* pool honest when it serves both kinds of
work: `nthreads` stays a truthful limit on CPU-bound measurements while waiters
escape the count. If waiters and compute live on different workers, or if the
pool only ever waits, configuration replaces it entirely.

We do not want it here, for an observability reason rather than a technical
one. Measured with 6 tasks against 4 slots:

| | worker `task_counts` | scheduler `processing` |
| --- | --- | --- |
| no secede | `{'executing': 2, 'ready': 1}` per worker | 6 tasks, by name |
| seceded | `{'long-running': 3}` per worker | 6 tasks, by name |

Graph-level tooling is identical either way — futures, progress, task stream,
and named keys all survive seceding, and every worker stays visible. The one
difference is that `long-running` is excluded from the parallelism count, so
the Workers table reads `executing = 0` while jobs are in flight. **User
direction (2026-08-04): a submit worker holding at least one live `bsub -I`
should read as running.** Not seceding gives exactly that, so raise the thread
count and leave `secede()` alone.

### What is left against Dask in slot A

- **Locality is gone.** Steps exchange file addresses on a shared store, so
  there are no in-memory values to keep warm and nothing to schedule around.
  This is still true, but note its shape: it says Dask *adds nothing* here, not
  that it costs something.
- **Defaults that are wrong for us.** `nthreads` sized for cores, and a nanny
  that may restart a worker under memory pressure. Under owner-bound lifetime a
  restarted worker kills every `bsub -I` client it held, and with it that many
  running farm jobs. The waiters themselves are far too small to cause this;
  it only bites if memory-hungry in-process work shares their worker.
- **It does not deliver the view that was asked for.** Dask can show tasks; it
  cannot show `PEND` versus `RUN`, or a corner waiting on a licence. That is
  LSF state, and something has to poll for it whoever owns readiness.
- **Concurrency limits are a site question, not an architecture one.** The real
  ceiling is the site's MAX JOB policy, per-user process limits, and the licence
  count — none of which either candidate knows.

### The case for Dask in both slots, as it now stands

Recorded because it was asked for, and because it is stronger than this file
previously implied. "Both slots" means one library serving two distinct roles —
**not** the slots merging, and emphatically not routing every invocation through
a pool.

1. **The case against slot A has largely dissolved.** One argument was
   retracted outright; the rest reduce to "Dask adds nothing here", which is a
   reason not to *need* it, not a reason to refuse it.
2. **The requirements that have arrived are a scheduler's feature list.**
   Bounded concurrency, a live view, retries, cancellation. Building them into
   `ass-run` one reasonable increment at a time is precisely the accretion the
   inquiry warned against; adopting a mature scheduler is the compliant
   alternative, not the transgression.
3. **Slot B already points at `dask-jobqueue`.** `DECISIONS.md` records that
   pooled mode should adopt `LSFCluster` for owner-bound worker lifetime
   (`death_timeout` plus `bkill` on close) rather than rebuild it. If the
   dependency is in the stack for B, using it for A costs an import, not a
   dependency.
4. **One mechanism instead of three.** Otherwise readiness lives in `ass-run`,
   pooling in a transport, and progress in a watcher, each with its own
   failure modes.
5. **Data-parallel post-processing** over many raw files is Dask's home ground.
   If a study needs it, Dask is present anyway.

### What "both slots" must not be allowed to mean

- **Not wholly pooled.** Routing every invocation through pooled workers gives
  up one visible LSF job per invocation, forces a single worker shape on
  heterogeneous work, and removes simulator licences from the scheduler that
  arbitrates them — LSF would see workers, not corners. Per-invocation
  `-R rusage[...]`, `bkill`, accounting and failure isolation all depend on the
  one-job-per-corner shape. Per-invocation placement is what prevents this,
  provided placements are actually authored.
- **Not pooled workers for slot A.** The cluster that owns readiness should be
  local to the submit host. A worker that dies takes its blocked clients, and
  therefore its running farm jobs, with it.
- **Not inside `ass-exec`.** The durable protocol, identity, and journal stay
  executor-neutral; Dask enters as a driver or adapter that is a peer of
  `ass-run`. That neutrality is what makes this decision reversible, and it has
  already survived two reversals.
- **Not as a replacement for per-job status.** The `bjobs` watcher is needed
  either way.

### What would still make it the wrong choice

- **Scale.** If the OTA/PVT study turns out to be a few dozen corners of several
  minutes each, a thread pool and a watcher are enough, and the dependency buys
  ceremony. This is the observation that decides, and it does not exist yet.
- **Mixed topology proving awkward.** A local cluster for readiness plus a
  separate `LSFCluster` used as a transport is two clusters in one process; that
  it composes cleanly is assumed, not demonstrated.

### The tripwire, revised

The accretion list — concurrency, limits, backpressure, priorities,
cancellation, progress reporting — had two items live at once, which read as
the moment to reopen the engine question. The measurement deflates one of them:
with waiters this cheap, concurrency in `ass-run` is not a scheduler feature but
a safety rail with an arbitrary high default, because the real limiter is the
site's MAX JOB policy and the licence count. And progress reporting belongs in a
watcher that reads journals and calls `bjobs`, which is a client of existing
contracts rather than a driver feature — it works unchanged whoever owns
readiness.

So one wire, not two, and the driver stays small either way. The decision is
still open, and it is still the study that should settle it.

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
