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
| Dask as the kernel | The main's *preferred hypothesis*: Dask owns graph dependencies, readiness, priorities, retries | **Adopted 2026-08-04 (user direction), after the case against it was measured and largely dissolved.** `ass_run.graph` gives readiness to Dask; `ass_run.binding` keeps the meaning of a run identical across kernels; `ass-exec` remains Dask-free. The route there is worth keeping: the hypothesis was weakened twice — owner-bound lifetime removed the identity objection, and file-based artifacts removed the locality argument for the steps that use them — then the strongest remaining objection was retracted on measurement. What decided it was not new evidence for Dask but the collapse of the evidence against it, plus a stated need for a live view. |
| Component boundary and name | One rebuilt "ASS Flow" | Split into `ass-flow` (planning), `ass-exec` (attempts), and `ass-run` (binding a run, with readiness now Dask's), coupled through the Plan document. No unit is named operator-facing "flow"; whether one should be is still open. |
| "Resume" | Reattaching to running work | Result reuse: rerun and skip work whose inputs are unchanged. |

## Deferred, still wanted

| Concept | Trigger to revisit |
| --- | --- |
| Pooled LSF via `dask_jobqueue.LSFCluster` | **Many short invocations**, where per-job queue dispatch costs more than the work. Not "many invocations": one job each is a good fit for long-running corners regardless of count, and it buys per-corner resource requests, `bkill`, accounting, licence arbitration and failure isolation. `LSFPooledTransport` refuses today. |
| ~~Concurrency in the driver~~ **Answered by adopting Dask.** | It is `threads_per_worker` on the cluster, and no code in `ass-run` owns it. Measured 2026-08-04: a waiting invocation costs ~16 KiB of thread plus one client process, so this is a safety rail rather than a scheduler feature, and the real limiter is the site's MAX JOB policy, per-user process limits, and the licence count. Ask for those numbers rather than inventing one. |
| ~~Per-job status: a `bjobs` watcher and a sweep view~~ **Built as `ass_exec.watch`.** | One `bjobs -o "job_name stat"` per refresh for every live attempt, transitions appended to an `observations.jsonl` beside each record, and `examples/watch_sweep.py` as a terminal view. An observation is evidence about an attempt, never a transition of it, so the observer writes its own file and cannot change an outcome. **Queue latency is now derivable** — the gap between `submit_intent` and the first `running` observation is the per-job dispatch cost the pooled-versus-direct question needs. What is still missing is a real farm: the parsing has never met one, `lsf_preflight.py` checks that `-o` exists, and default `bjobs` output is refused rather than parsed because its columns shift for pending jobs. |
| Unified flow-level `submit()` — one file per study | **Wanted (2026-08-04, user direction), designed, not built.** The OTA study currently takes two files: a Plan declaration whose operation bodies raise, and a ~600-line binding supplying implementations, commands, output paths, transports and roots. The proposal collapses them: the operation body *is* the implementation, receiving an `out` namespace of declared output paths in its attempt workspace; a body returning `shell(...)` is a launcher whose command runs at the placement, while a body returning a value ran in process; `sweep(points, key=...)` opens a keyed scope so reuse cannot be lost to renumbering; identity folds a normalized source hash of the body, retiring both the out-of-band `commands=` dict and `operation_version` as a human promise; declared sources are fingerprinted by mtime and size, closing the staleness gap below; durability is inferred from declared outputs with an override. A `Site` holds the only things that are not the study — placements to transports, roots, address spaces, kernel threads — from a file. `study.plan.summary()` stays inspectable before `study.submit(site=...)` spends anything. What it costs: the Plan stops being implementation-neutral and needs its package importable. What it does not cost: `ass-exec` still reads plain dicts and imports neither `ass_flow` nor Dask, so the attempt protocol, reuse, placement and the watcher are untouched and the kernel stays swappable. Estimated 1,200–1,500 lines and a Plan schema bump to 3. |
| One-scheduler mixed topology (labelled local, direct-gateway, pooled workers) | Requires pooled mode first; must be demonstrated, not assumed, since `LSFCluster` normally owns its own scheduler. See "What \"both slots\" must not be allowed to mean" below for why mixed, rather than wholly pooled, is the preferred shape. |
| Delayed versus Futures comparison (evidence ladder 4) | **Now live, since Dask is the driver.** `ass_run.graph` uses Futures — `client.submit` with explicit keys, `pure=False`, and `as_completed` for live events — while `ass_flow.experimental.local_dask` lowers to Delayed. Futures were chosen for keys an operator can recognise and for reporting as work completes; whether Delayed would express the graph better is untested. |
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
- **Result-dependent control and recovery.** Deliberately out of scope
  (2026-08-04, user direction), with the reasoning recorded below rather than
  left as a shrug. See "Future work: result-dependent control".
- **The typed transition contract.** `Operation(validated_config,
  explicit_state, declared_artifacts) -> StepResult` was adopted as a research
  invariant. Three of its four parts now exist in some form; **`explicit_state`
  has never been revisited**, and the question of whether an operation has
  durable state distinct from its artifacts remains unexamined.

## Decided: Dask takes both slots (2026-08-04, user direction)

`ass_run.graph.run_plan_graph` is the kernel. What that does and does not mean:

- **Slot A is Dask's.** Readiness, ordering, and concurrency belong to the
  graph. Concurrency is `threads_per_worker` — there is no limit parameter,
  because a waiting invocation costs ~16 KiB and the real ceiling is site
  policy.
- **Slot B is unchanged and still per-invocation.** `local` runs in the worker,
  `lsf-direct` blocks on its own `bsub -I` so per-corner `rusage`, `bkill` and
  accounting survive, and `lsf-pool` still refuses. Adopting Dask for readiness
  did *not* route work through pooled workers, and must not.
- **The recommended cluster is local and threaded** on the submit host:
  `LocalCluster(processes=False, threads_per_worker=N)`. No nanny to restart a
  worker holding live clients, and nothing secedes, so a worker with jobs in
  flight reads as running.
- **`ass-exec` stays Dask-free**, which is what keeps this reversible. It has
  already been reversed twice.

Two things the adoption did not resolve. Per-job status still needs the `bjobs`
watcher — Dask cannot see `PEND`. And the sequential kernel is retained rather
than deleted: it is the reference that keeps the graph kernel honest, and the
test that matters is that the two agree on identity and value.

**Measured while implementing, and worth recording because it contradicts what
was assumed:** Dask serializes every task even on an in-process cluster, so a
transport travels to a worker as a copy, never as a shared live object. Ours
are stateless per submission, so this is correct today. A pooled transport
holding a client to a second cluster is a singleton and cannot be passed this
way — when `lsf-pool` is built it will need a factory constructed on the
worker, not an instance handed to `run_plan_graph`.

## How that decision was reached, kept in full

Retained rather than summarised: the decision is only trustworthy if the
argument that produced it — including the parts that turned out to be wrong —
remains inspectable.

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

- **Locality is gone — but only for the steps that use artifacts.**
  Corrected 2026-08-04 by user direction: *simple tasks do not use artifacts*.
  The unit already says so — an output may be declared `{"value": True}`, and
  `EPHEMERAL` exists precisely for a step that computes a number from two other
  numbers and writes nothing. So the sweeping form of this claim was wrong.
  What is true, scoped: the *expensive* steps exchange file addresses on a
  shared store, so there is nothing to keep warm where it would matter, and the
  cheap value-passing steps exchange scalars too small for locality to mean
  anything either way. Note the shape of even the corrected claim: it says Dask
  *adds nothing* here, not that it costs something.
  **Trigger:** if steps ever pass in-memory values of real size — a loaded
  waveform array going from a measurement step to an evaluation step rather
  than through a file — locality returns as a live argument, and it is Dask's
  strongest one.
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
- **A source's identity is its declared address and codec, never its
  content.** Raised running the OTA/PVT reference's real execution binding
  (`docs/reference/ota-pvt-plan/run_study.py`, 2026-08-04). `plan_bundles`'s
  `_source_identity` hashes `{artifact, address, materialized_as}` only; there
  is no mtime/size check as there is for a declared *output* file
  (`ass_exec.artifacts.ArtifactRef`). Editing `inputs/base/ota_ac.cir` or
  `inputs/pvt_edits.py` in place, without touching their declared address in
  `ota_pvt_plan.py`, would not invalidate any cached attempt that reads them —
  a rerun would silently reuse a result computed from the old file content.
  This is a different gap from the "Artifact checksums and provenance" row
  below, which is about declared *outputs*: that row's mtime-plus-size
  argument was never extended to sources, and small authored text fixtures
  are exactly the case where hashing content would be cheap. Not scheduled;
  the honest workaround this run used was to make config that should
  participate in identity (point_id, process, vdd_v, temp_c) a declared Plan
  config value rather than fixture content, which is what the edited-corner
  reuse test actually exercised.
- **`ass_exec`'s `Durability.RECORDED` path requires every in-process return
  value to be JSON-safe, not merely inspectable.** Raised by the same run:
  `reconcile()` appends `{"value": ...}` to the append-only journal via
  `json.dumps` before any output declaration is even consulted, and
  `ass_run.run_plan` always executes at `Durability.RECORDED` — there is no
  lighter path for a fast in-process step, unlike `ass_exec.durability`'s own
  stated design ("an ordinary in-memory Python step... has nothing worth
  reconstructing"). Concretely, `spice_canonical.CanonicalNetlist` and
  `netlist_decomposition.BlockTag` are frozen dataclasses with a `frozenset`
  field and are not JSON-serializable; the first real run failed at exactly
  this point. `run_study.py` worked around it by adding a small hand-written
  serialization for both (see its module docstring), which is real forward
  progress on PLANNING.md's recorded "no portable serialization" limitation,
  but it is scoped to what one in-process run needs, not a general artifact
  codec. Whether `run_plan` should offer an `EPHEMERAL` path for invocations
  with no declared outputs, mirroring `execute()`'s own two-tier design, is
  open.
- **A Plan-only reference's documentation-marker policy collides with
  `ass_run`'s placement-name lookup.** `ota_pvt_plan.py`'s
  `PLAN_DECLARATION_POLICY`/`SIMULATOR_BOUNDARY_POLICY` are named
  `reference.plan-only`, meant only as a status marker ("declaration-only",
  "unimplemented"). `ass_run.binding.select_transport` reads
  `(item.policy or {}).get("name")` as the *placement* to route an invocation
  to, falling back to `"local"` only when no name is present at all. Because
  this Plan does author a name, every invocation asks for placement
  `reference.plan-only`, not `local` — a `transports={"local": ...}` mapping
  would raise `UnsupportedPlacement` for all sixteen. `run_study.py` sidesteps
  this by running in single-transport mode (`transport=...`, which answers
  any requested placement name identically), which is honest for a Plan with
  one uniform policy but would not scale to a Plan that actually wanted
  different placements per operation. Whether a plan-only reference should
  eventually author a real placement name distinct from its documentation
  status, once it has a genuine reason to differ per operation, is open.

## Future work: result-dependent control

Deliberately out of scope (2026-08-04, user direction). Recorded in full
because it is the concept most likely to arrive by accident, and because the
two things this project did today — adopting Dask, and designing a flow-level
`submit()` — both lowered the cost of doing it badly.

### What it means

Everything the units run today is *fully determined before it starts*. A flow
body executes at planning time and produces a fixed graph, which is what makes
a Plan inspectable before it spends simulation resources and a rerun
predictable. Result-dependent control breaks that property. Its real forms are
ordinary engineering wishes:

- a corner that will not converge, retried with different solver options;
- a sizing sweep that continues until a specification closes, or gives up;
- corners chosen adaptively, because the interesting ones are near a boundary;
- a fallback placement when a licence never becomes available.

### Why it is not simply a feature

The Plan stops predicting what will run. Reuse, staleness, and "explain which
work is stale and what must run again" are all defined against a graph that
exists before execution. A graph that grows in response to results has no such
object to compare against, so the manifesto's verification path — *inspect
resolved parameters, corners, jobs and dependencies before execution* — has
nothing to inspect.

### The risk is now higher, not lower

Two changes this session made the wrong version cheap:

- **Dask is the kernel.** Tasks launching tasks is a supported pattern
  (`worker_client`, `secede`), so a dynamic graph is now a small code change
  rather than an architectural project. Capability is not permission.
- **A flow-level `submit()` is proposed.** That façade is exactly where
  adaptivity would arrive disguised as convenience — a `retry=` argument, a
  `max_iterations=`, an `until=` predicate. Each is individually reasonable.
  Together they are the hidden imperative controller the inquiry rejected.

Treat any of those three keyword arguments on `submit()` as the tripwire.

### The shape it should take if it is ever built

Not a mutating graph. A second, explicitly named verb — `explore(...)` — that
is honest about producing a **sequence of Plans** rather than one:

1. Each iteration materializes a complete, inspectable, versioned Plan.
2. Provenance links plan *n* to plan *n+1* together with the observation that
   caused the step, so the sequence can be read afterwards as an argument.
3. The decision function itself has an identity — a code fingerprint, like an
   operation — and its inputs are recorded. **This is the load-bearing part:**
   an adaptive study is only reproducible if the controller that adapted it is
   identified and its decisions are durable. Otherwise the study cannot be
   replayed, and "trace a conclusion back to its exact inputs" fails at the
   first branch.
4. Stop conditions and spend limits are declared, not discovered. The
   manifesto already frames autonomy this way: a policy attached to a study,
   bounding operations and resources, not a separate architecture.

Under that shape, reuse and staleness keep working, because every individual
Plan is still fully determined. What changes is that a study becomes a list of
Plans rather than one — which is closer to what an engineering campaign
actually is.

### What would make it live

A real workload that needs a fallback, and cannot be expressed by rerunning an
edited plan by hand. Until then, editing the plan and rerunning is both the
honest answer and, given content-addressed reuse, a cheap one: only the
affected branch recomputes.

## How to use this file

Add to it when a concept is raised and not immediately built. Move rows between
sections when status changes, and say why. A concept leaving this file should
leave because it was realized or rejected, never because nobody mentioned it
again.
