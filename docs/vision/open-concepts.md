# Open concepts from the Hedloom Flow rebuild inquiry

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
| Static custom-flow composition; one normalized inspectable Plan | `hedloom-flow` | Accepted with the OTA/PVT domain reference. |
| Declarative source handoff: artifact contract and address | `hedloom-flow` | Schema-2 Plan IR. |
| Local Dask Delayed lowering (evidence ladder 3) | `hedloom-flow` experimental | Bounded instrument, not an execution API. |
| Immutable bundle and stable record ID derived before submission | `hedloom-exec` | `attempt_identity(plan, invocation, digest)`, content-addressed; Phase 1 removed the old sequence hash slot and deliberately changed renderings. |
| One record owning numbered try workspaces | `hedloom-exec` | Layout 1: allocation is recorded under the claim before transport, farm operations use `<record>-<try>`, terminal evidence is immutable per try, and `standing.json` selects reusable evidence. No migration from earlier roots. |
| `launch_or_attach` claiming, attaching, or completing | `hedloom-exec` | Exactly three dispositions or a loud failure. |
| Idempotent `request_cancel` recording intent before acting | `hedloom-exec` | Cancellation is intent, never established by return. |
| Success requires observed terminal state *and* atomic publication | `hedloom-exec` | Disagreement publishes `unreconciled`. |
| Both loss windows (evidence ladder 5) | `hedloom-exec` | Failure injections against a fake substrate. |
| File-first sidecar: identities, append-only try events, job ID, timestamps, diagnostics, per-try manifests, artifact references | `hedloom-exec` | Deliberately not a workflow database. |
| Out-of-place execution, declared artifacts, atomic publication | `hedloom-exec` | Per-try workspace; declared outputs only. |
| Materialization before data crosses to an external substrate | `hedloom-exec` | On a shared store this is recording an address, not moving bytes. |
| Operator-run workspace retention and per-try pins | `hedloom-exec`, Hedloom `Site` | A dry-run survey classifies spent tries under strict named Site rules; apply rechecks under the record claim and records removal before deleting bytes. Standing results, aliases, pins, live tries, the global floor, and `unreconciled` evidence remain protected. Terminal-only pins store attributable digest inventories in the record and detect rather than claim to prevent drift. Named automatic rules may run after completion; no study-owned pruning argument exists. |

## Changed by evidence

| Concept | Original stance | Now |
| --- | --- | --- |
| Direct-LSF job lifetime | A job outlives its submitter, so a durable protocol must own its identity | User direction: work is owner-bound. `bsub -I` plus process-group and `PR_SET_PDEATHSIG`. The protocol survives with a changed justification. |
| Dask as the kernel | The main's *preferred hypothesis*: Dask owns graph dependencies, readiness, priorities, retries | **Adopted 2026-08-04 (user direction), after the case against it was measured and largely dissolved.** `hedloom_run.graph` gives readiness to Dask; `hedloom_run.binding` keeps the meaning of a run identical across kernels; `hedloom-exec` remains Dask-free. The route there is worth keeping: the hypothesis was weakened twice — owner-bound lifetime removed the identity objection, and file-based artifacts removed the locality argument for the steps that use them — then the strongest remaining objection was retracted on measurement. What decided it was not new evidence for Dask but the collapse of the evidence against it, plus a stated need for a live view. |
| Component boundary and name | One rebuilt "Hedloom Flow" | Split into `hedloom-flow` (planning), `hedloom-exec` (attempts), and `hedloom-run` (binding a run, with readiness now Dask's), coupled through the Plan document. No unit is named operator-facing "flow"; whether one should be is still open. |
| "Resume" | Reattaching to running work | Result reuse: rerun and skip work whose inputs are unchanged. |

## Deferred, still wanted

| Concept | Trigger to revisit |
| --- | --- |
| Pooled LSF via `dask_jobqueue.LSFCluster` | **Many short invocations**, where per-job queue dispatch costs more than the work. Not "many invocations": one job each is a good fit for long-running corners regardless of count, and it buys per-corner resource requests, `bkill`, accounting, licence arbitration and failure isolation. `LSFPooledTransport` refuses today. |
| ~~Concurrency in the driver~~ **Answered by adopting Dask; placement budgets built 2026-08-16.** | `Site.placements` now owns one in-flight cap per placement. `cluster_for(site)` derives one in-process `SpecCluster` worker per placement, with `nthreads` and `resources={"placement:<name>": cap}` from the same number; `[kernel] threads` is local concurrency only. A waiting invocation still costs ~16 KiB of thread plus one client process, so the farm cap remains a courtesy rail set from the site's MAX JOB policy and submit-host process limits, not a number to invent. |
| ~~Per-job status: a `bjobs` watcher and a sweep view~~ **Built as `hedloom_exec.watch`.** | One `bjobs -o "job_name stat"` per refresh for every live attempt, transitions appended to an `observations.jsonl` beside each record, and `examples/watch_sweep.py` as a terminal view. An observation is evidence about an attempt, never a transition of it, so the observer writes its own file and cannot change an outcome. A journal now records `transport` (who submitted) and `substrate` (where the work lands) separately, fixing 2026-08-16 a defect that made the watcher blind to the supported study path: it matched `"lsf-interactive"` while façade journals recorded only `"bound:lsf-interactive"`, and an empty sweep is indistinguishable from a finished one. **Wired into the façade 2026-08-16:** `submit(watch=True)` now runs the poller on a daemon thread for the duration of a run and prints only transitions — `[watch] invoke:corner-tt pending → running (48s queued)` — so queue latency per job is printed rather than merely derivable. A `TransportError` disables the poller instead of failing the run. What is still unmet is a real farm: the parser has never met one, and default `bjobs` output remains deliberately refused because its columns shift for pending jobs. |
| ~~Unified flow-level `submit()`~~ **Built as the `hedloom` unit (2026-08-04).** | One file authors and runs a study. The operation body is the implementation and receives `out`, a workspace of its declared file outputs; returning `shell(...)` makes it a launcher whose command runs at the invocation's placement; `sweep(points, key=...)` keys every call inside the loop; the Plan (now schema 3) records each operation's entry point and a fingerprint of its source, so an edited body reruns the work it produced and `operation_version` stops being a promise someone has to remember; declared output bindings live on the operation, retiring the run-time `outputs=` dict; `Site` holds placements, roots, address spaces and threads. Evidence: `studies/rc_corners.py` covers local ngspice, identity and reuse, and `examples/farm_smoke.py` has reached a real farm through the sequential kernel. `hedloom-exec` still imports neither `hedloom_flow` nor Dask. **Met 2026-08-16 against the fake farm:** `examples/farm_smoke.py --dask` runs the graph kernel through `bsub -I` and `BoundTransport` with a cluster from `cluster_for(site)`. Still unmet: that same crossing against a real farm. |
| One-scheduler mixed topology (labelled local, direct-gateway, pooled workers) | Requires pooled mode first; must be demonstrated, not assumed, since `LSFCluster` normally owns its own scheduler. See "What \"both slots\" must not be allowed to mean" below for why mixed, rather than wholly pooled, is the preferred shape. |
| Delayed versus Futures comparison (evidence ladder 4) | **Now live, since Dask is the driver.** `hedloom_run.graph` uses Futures — `client.submit` with explicit keys, `pure=False`, and `as_completed` for live events — while `hedloom_flow.experimental.local_dask` lowers to Delayed. Futures were chosen for keys an operator can recognise and for reporting as work completes; whether Delayed would express the graph better is untested. |
| ~~Real direct-LSF smoke test (evidence ladder 6)~~ **Built through the sequential kernel.** | `examples/farm_smoke.py` passed on the real farm, validating `bsub -I`, artifact chaining, failure recording and reuse. It did not exercise Dask, concurrency, or queue-wait observability. **Closed against the fake farm 2026-08-16:** `--dask` covers the crossing, and the test asserts that `max_jobs = 2` holds four jobs to two in flight — removing the placement annotation from the kernel fails it with `assert 4 == 2`, so the cap is demonstrated rather than assumed. Worth recording from building it: Dask keeps a consumer on its producer's worker for locality, which held the *chained* sweep to two on its own, so a test written over the chained jobs would have passed against the broken kernel. Independent jobs are what give it teeth. |
| Plugins and declarative flow configuration | A concrete multi-repository or non-Python authoring need. |
| **NFS is being used as a synchronization mechanism, and it may not be one** | **Raised 2026-08-16 (user), unreviewed.** `AttemptJournal.claim` holds an advisory `flock` on a file in the attempt directory, and the whole single-writer argument rests on that lock being honoured. Over NFS it may silently not be: `local_lock=flock`/`local_lock=all`, or NFSv3 `-o nolock`, make it node-local, and NFSv4 locks are leases a partitioned client can lose while believing it holds one — `flock()` returns success in every case. The consequence is not only duplicate `bsub` jobs for one identity: `events.jsonl` is appended with `O_APPEND`, which NFS does **not** make atomic, so a degraded lock can interleave or overwrite the record every recovery, reuse and identity decision is read back from. Manifest publication is unaffected — `rename()` is atomic on NFS. Not reachable today (one process, in-process cluster, and two opens in one process do contend correctly); reachable the moment two controllers share a root, or pooled placement writes journals from farm nodes. Options, cheapest first: probe `/proc/mounts` at run start and refuse a root whose mount cannot honour the lock; replace `flock` with the `link()`-plus-`st_nlink` idiom that holds on v3 and v4; partition roots per controller (costs cross-run reuse). Full write-up in the `DEVNOTE/TODO` block on `hedloom_exec.journal.AttemptJournal.claim`. Trigger to revisit: **before any second controller, any pooled placement, or any farm run whose study root is on NFS.** |
| Retry policy for indeterminate transport failures | **Delayed (2026-08-16).** `_run_one` catches both `AttemptError` and `TransportError` and returns an outcome, so Dask's own `retries=` can never fire and a transient `bsub` hiccup fails a corner permanently, blocking its dependents, with nothing in the report distinguishing it from a diverged simulation. Dask retries would in fact be *safe* here — identity is chosen before submission and content-addressed, so a re-executed task re-enters `launch_or_attach` and resolves to `attached` rather than duplicating a job — but the policy belongs in `hedloom_exec`, which is the only layer that can tell `SubmissionRefused` (definitely nothing accepted, safe to resubmit) from `TransportError` (indeterminate). Trigger to revisit: the first farm run where a transient submission failure costs a corner. |
| Artifact checksums and provenance | Deliberate: hashing multi-GB raw files every run is a real cost, and mtime plus size is the cheap staleness signal. Revisit if mtime proves unreliable on NFS. |

## Dropped without a decision — recovered here

These fell out during direct development. None was rejected on merit.

- ~~**Requested versus resolved versus observed placement.**~~ **Recovered.**
  A `placement` journal event records requested and resolved before submission;
  observed is published with the manifest. `hedloom-run` selects a transport from
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
  reported as indeterminate rather than refused. Phase 1 removed the executor's
  `max_attempts`: records mechanically allocate unbounded tries, while policy
  about whether to retry remains unmodelled.
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

`hedloom_run.graph.run_plan_graph` is the kernel. What that does and does not mean:

- **Slot A is Dask's.** Readiness, ordering, and concurrency belong to the
  graph. Concurrency is `threads_per_worker` — there is no limit parameter,
  because a waiting invocation costs ~16 KiB and the real ceiling is site
  policy.
- **Slot B is unchanged and still per-invocation.** `local` runs in the worker,
  `lsf-direct` blocks on its own `bsub -I` so per-corner `rusage`, `bkill` and
  accounting survive, and `lsf-pool` still refuses. Adopting Dask for readiness
  did *not* route work through pooled workers, and must not.
- **The recommended cluster is local and threaded** on the submit host, built
  by `cluster_for(site)` as an in-process `SpecCluster` with one `Worker` per
  placement. Each worker's `nthreads` is derived from that placement's cap; no
  nanny may restart a worker holding live clients, and nothing secedes, so a
  worker with jobs in flight reads as running.
- **`hedloom-exec` stays Dask-free**, which is what keeps this reversible. It has
  already been reversed twice.

Two things the adoption did not resolve. Per-job status still needs the `bjobs`
watcher — Dask cannot see `PEND`, and it has still never met a real farm. And
the sequential kernel is retained rather than deleted: it is the reference that keeps the graph kernel
honest, and the test that matters is that the two agree on identity and value.

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

**Slot A — who decides what runs next.** `hedloom-run`'s loop, or a Dask graph.

**Slot B — where one invocation runs.** `local`, `lsf-direct`, or `lsf-pool`,
already resolved per invocation by Hedloom Flow and honoured per invocation by
`hedloom-run`.

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
   `hedloom-run` one reasonable increment at a time is precisely the accretion the
   inquiry warned against; adopting a mature scheduler is the compliant
   alternative, not the transgression.
3. **Slot B already points at `dask-jobqueue`.** `DECISIONS.md` records that
   pooled mode should adopt `LSFCluster` for owner-bound worker lifetime
   (`death_timeout` plus `bkill` on close) rather than rebuild it. If the
   dependency is in the stack for B, using it for A costs an import, not a
   dependency.
4. **One mechanism instead of three.** Otherwise readiness lives in `hedloom-run`,
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
- **Not inside `hedloom-exec`.** The durable protocol, identity, and journal stay
  executor-neutral; Dask enters as a driver or adapter that is a peer of
  `hedloom-run`. That neutrality is what makes this decision reversible, and it has
  already survived two reversals.
- **Not as a replacement for per-job status.** The `bjobs` watcher is needed
  either way.

### What would still make it the wrong choice

- **Scale.** If the OTA/PVT study turns out to be a few dozen corners of several
  minutes each, a thread pool and a watcher are enough, and the dependency buys
  ceremony. This is the observation that decides, and it does not exist yet.
- **Mixed topology proving awkward.** The in-process `SpecCluster` for readiness
  plus a separate `LSFCluster` used as a transport is two clusters in one
  process; that it composes cleanly is assumed, not demonstrated.

### The tripwire, revised

The accretion list — concurrency, limits, backpressure, priorities,
cancellation, progress reporting — had two items live at once, which read as
the moment to reopen the engine question. The measurement deflates one of them:
with waiters this cheap, concurrency in `hedloom-run` is not a scheduler feature but
a safety rail with an arbitrary high default, because the real limiter is the
site's MAX JOB policy and the licence count. And progress reporting belongs in a
watcher that reads journals and calls `bjobs`, which is a client of existing
contracts rather than a driver feature — it works unchanged whoever owns
readiness.

So one wire, not two, and the driver stays small either way. The decision is
still open, and it is still the study that should settle it.

## New ideas raised during development

- **A source's identity is its declared artifact and address, plus an optional
  runtime fingerprint.** Raised running the OTA/PVT reference's real execution
  binding (`docs/reference/ota-pvt-plan/run_study.py`, 2026-08-04). The original
  finding was that declaration-only identity let an in-place fixture edit reuse
  results computed from the old content. That gap is now bounded explicitly:
  `plan_bundles`'s `_source_identity` hashes `{artifact, address, fingerprint}`;
  `hedloom_run` supplies the content fingerprint because it owns address
  resolution. Without one, identity remains declaration-only and an in-place
  edit is invisible; with one, the changed fixture invalidates the attempts
  that read it. The original run's honest workaround was to make config that
  should participate in identity (point_id, process, vdd_v, temp_c) a declared
  Plan config value rather than fixture content. The runtime fingerprint now
  covers the source-content case without conflating it with declared-output
  checks in `hedloom_exec.artifacts.ArtifactRef`.
- **`hedloom_exec`'s `Durability.RECORDED` path requires every in-process return
  value to be JSON-safe, not merely inspectable.** Raised by the same run:
  `reconcile()` appends `{"value": ...}` to the append-only journal via
  `json.dumps` before any output declaration is even consulted, and
  `hedloom_run.run_plan` always executes at `Durability.RECORDED` — there is no
  lighter path for a fast in-process step, unlike `hedloom_exec.durability`'s own
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
  `hedloom_run`'s placement-name lookup.** `ota_pvt_plan.py`'s
  `PLAN_DECLARATION_POLICY`/`SIMULATOR_BOUNDARY_POLICY` are named
  `reference.plan-only`, meant only as a status marker ("declaration-only",
  "unimplemented"). `hedloom_run.binding.select_transport` reads
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

### Already demonstrated: staged plans (2026-08-05)

The "sequence of Plans" shape above is not hypothetical. It runs, in
`studies/ota_pvt_clean_nested.py`, and it arrived from the opposite
direction — not as a way to adapt to results, but as the answer to a limitation
that looked fatal.

Reading a corner set inside the graph makes it a *result*, so the plan holding
that read cannot name one invocation per corner. The conclusion "therefore the
fan-out must collapse into monolithic operations" is wrong, and was recorded
here as wrong. An invocation may **author a Plan and run it**: `jobs` is an
ordinary value inside a body, so authoring over it is ordinary authoring. Stage
two names one prepare, simulate and measure per corner and is complete and
inspectable before it spends anything, exactly like the plan containing it.

This is not result-dependent control and must not be filed as a step toward it.
No plan branches on its own results; each plan is fully determined when
authored, and a later stage is authored after an earlier stage produced its
values. Every property defined against "a graph that exists before execution"
survives, per plan. Measured: changing a spec limit reran the outer invocation,
which re-authored stage two, which then **reused nine of its ten invocations**
and recomputed only the evaluation.

Two things it does not yet have, and both are what `explore(...)` above would
need anyway:

- The stage-two plan is a declared output of the invocation that authored it,
  so it is recorded — but nothing links stage one to stage two as *provenance*.
  Reading the sequence back as an argument is manual.
- The authoring function has no identity of its own. Point 3 above calls that
  the load-bearing part, and it is missing here for the same reason: the body
  that authors stage two is fingerprinted as an operation, which is close, but
  the register should not treat "close" as "done".

### Deferred: declaring part of a source

Found by the same example. A source is fingerprinted whole, so a file carrying
two independent declarations over-invalidates. `pvt_edits.py` says both *which
corners exist* and *how every corner is edited*; every corner's render declares
the file as an input, so adding a corner changes the fingerprint and correctly —
but far too broadly — reruns every corner's simulation.

The system is not wrong; the declaration is too coarse. What is missing is a way
to say "this operation depends on *that part* of that source". Staged plans make
it fixable rather than fixed: stage one already separates the param sets from
the rest of the file, so stage two could depend on the edit recipe instead of
the file that carries it. Nothing does that yet, and it should not be invented
before a workload pays for it.

### What would make it live

A real workload that needs a fallback, and cannot be expressed by rerunning an
edited plan by hand. Until then, editing the plan and rerunning is both the
honest answer and, given content-addressed reuse, a cheap one: only the
affected branch recomputes.

## Two concurrency limits, not one (2026-08-05)

### The defect

`LSFTransport.submit` is documented as *"Submit and wait. With `-I` the call
returns when the job is over."* So one in-flight farm job holds one Dask thread
for its whole life, queue wait included, and `threads_per_worker` **is** the
maximum number of concurrent `bsub -I` jobs.

That welds two unrelated facts together. Local concurrency is a property of the
submit host's CPU. Farm concurrency is the site's LSF MAX JOB policy for this
user. Today you cannot say "two hundred farm jobs, little local parallelism" —
to get the jobs you must declare the threads, which also authorises two hundred
concurrent *local* invocations nobody asked for. `Site.threads` exists, is
parsed from `[kernel] threads`, and is read by nothing, so the number is written
once in the profile and again in the operator's `LocalCluster(...)` call with
nothing comparing them.

**Amended 2026-08-06.** The second half of that sentence no longer holds:
`hedloom_run.cluster.cluster_for(site)` reads `Site.threads` and builds the cluster
from it, so the number is written once. The first half is untouched — one
number still means both limits, and the resolution below is still the way out.

### The resolution: a dedicated in-process worker, bounded by a Dask resource

User direction, and it is better than the alternative this register previously
leaned toward. The secede entry above already predicted it — *"if waiters and
compute live on different workers … configuration replaces it entirely"* — and
measurement confirms it. Two in-process workers, `local` at one thread and
`farm` at many, with farm jobs routed by `resources={"lsf": 1}`:

| farm worker declares | 8 jobs × 0.5 s | expected |
| --- | --- | --- |
| `{"lsf": 2}` | 2.06 s | 2.0 s |
| `{"lsf": 4}` | 1.05 s | 1.0 s |
| `{"lsf": 8}` | 0.53 s | 0.5 s |

The declared resource *is* the MAX JOB limit, enforced by the scheduler,
exactly. It beats `secede()` on the one axis secede was rejected for: the farm
worker genuinely reads as busy while jobs are in flight, so the observability
requirement is met rather than traded away. It also removes a
`threading.Semaphore` that would otherwise have gone into `LSFTransport` — and
with it, a limit that would have been silently wrong across processes. `hedloom_exec`
does not change at all.

Shape:

```toml
[kernel]
threads = 1                    # local concurrency; unrelated to farm jobs

[placement.lsf]
kind = "lsf-interactive"
max_jobs = 200                 # the site's LSF MAX JOB policy for this user
```

Two things to write down rather than discover: the farm worker's `nthreads`
must be **derived** from the total of the declared caps, or the thread count
binds first and silently; and the farm worker must be in-process (`cls=Worker`,
no nanny), because a nanny restarting it under memory pressure would take its
`bsub -I` clients and, under owner-bound lifetime, that many running farm jobs.

**Built 2026-08-16**, with one correction to the resolution above.

`Site.placements` reads `max_jobs` per placement and refuses an uncapped LSF
one; `Site.cluster_spec()` derives one in-process worker per placement, its
`nthreads` taken from that cap; `hedloom_run.cluster.spec_cluster` builds them
through `SpecCluster`, since `LocalCluster` applies one recipe to every worker
and cannot express two that differ. `run_plan_graph` annotates every task with
`resources={"placement:<name>": 1}` and refuses, before submitting anything, a
cluster that declares no capacity for a placement the plan uses.

**The correction: routing only the farm jobs is not enough.** A task carrying no
resource is not weakly preferred anywhere — it is legal on *every* worker
(`valid_workers` returns `None`, scheduler.py:3202), so the scheduler may place
local work on the farm worker, and work stealing will keep moving it there for
the whole run: restrictions are strictly enforced during a steal, and a task
with none has nothing to enforce. The farm worker's threads are the farm's
in-flight budget, so a local invocation holding one is a `bsub -I` that cannot
start while its capacity sits unused. Annotating *every* task, `local` included,
is what makes that unrepresentable — and it is also what makes stealing safe to
leave switched on.

Two smaller things found while building it. Task keys were `corner-digest`, so
every task was its own Dask prefix, no duration average was ever learned, and
every estimate fell back to a flat 500 ms — the number the scheduler uses to
decide which worker is least busy and what is worth stealing; keys are now
`operation-corner-digest`. And a placement the *run* cannot serve is deliberately
left unannotated, because it is refused per invocation by `select_transport`
exactly as under the sequential kernel: annotating it would hang it instead, and
the two kernels must not disagree about a plan.

### Deferred, wanted: an async LSF transport

The cleanest end-state, and explicitly deferred for time (2026-08-05, user
direction: *"i would like to explore the async path, but i dont have time now"*).

A coroutine awaiting `asyncio.create_subprocess_exec` holds **no thread at
all**, so two hundred waiting jobs would cost zero threads and no worker slots,
and the dedicated farm worker above would stop being necessary — the cap would
be the only limit left, which is the honest model. Dask runs coroutine tasks on
the worker's event loop rather than its thread pool, so the kernel already
supports it.

What it costs: `execute()` and the journal are synchronous throughout, and
`hedloom_exec` has no async anywhere. Adding it is not a transport change, it is an
async path through the durable-record machinery — the part of this system with
the strongest correctness requirements. Owner-bound lifetime looks preservable
(`preexec_fn` is available on the asyncio subprocess API) but is unverified.

What would make it live: thread count actually hurting. It does not yet — a
waiter was measured at about 16 KiB, so two hundred jobs is roughly 3 MB. The
dedicated-worker resolution above is enough until the farm says otherwise, and
the async path should be judged against a real MAX JOB number rather than a
hypothetical one.

## How to use this file

Add to it when a concept is raised and not immediately built. Move rows between
sections when status changes, and say why. A concept leaving this file should
leave because it was realized or rejected, never because nobody mentioned it
again.
