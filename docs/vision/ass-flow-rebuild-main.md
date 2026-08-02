# ASS Flow rebuild inquiry

**Status:** dialecticH seed; no architecture in this document is accepted yet

**Prior implementation:** retired prototype, recoverable from Git at `528c02f`

## Why reopen the design

The first `study-flow` prototype was useful evidence but the wrong foundation
to extend. It replaced a simulation-shaped demonstration with neutral names,
yet retained a fixed preparation/map-chain/reduction graph and a large authored
`FlowSpec`. That made ordinary graph authoring uncomfortable and confused a
single demonstration shape with a general execution contract.

The prototype also treated local Dask and Dask Jobqueue as whole-run backend
choices. The actual requirement is finer grained: an invocation should be able
to run locally by default, as one independently visible LSF job when requested,
or on reusable Dask workers allocated through LSF. Recording attempts and
artifacts separately from temporary Dask handles remained a useful result, but
the old Python types, CLI, schemas, graph shape, and package layout are not
compatibility constraints.

Rebuild from the problem and the evidence rather than refactoring the retired
code. Keep the project manifesto protected. This inquiry may revise the
conceptual flow foundation and the future component ontology, but it does not
silently revise the project vision.

## Scope of the inquiry

Find the smallest coherent, runnable foundation for Python-authored arbitrary
task graphs with per-invocation execution policy. It must support a useful
local path and make direct LSF submission the primary remote path. A reusable
LSF worker pool is also required for workloads that benefit from warm workers
and Dask-managed data locality.

The result must remain generic within ASS. Simulation, CACE integration,
measurements, evidence promotion, adaptive study strategy, and the complete
study lifecycle belong outside this initial execution slice. A successful task
attempt is not automatically engineering evidence.

Do not build an ASS graph scheduler merely to connect these modes. If the
preferred Dask extension cannot express direct LSF soundly, expose that result
and compare an existing engine or a narrower boundary before proposing a new
scheduler.

## Preferred hypothesis: Dask remains the kernel

Treat Dask as the initial graph and scheduling kernel, not as one replaceable
plugin behind a new ASS workflow engine. Dask should continue to own graph
dependencies, readiness, priorities, retries, ordinary result propagation,
and its diagnostics. ASS should add domain-neutral authoring ergonomics,
execution-policy resolution, direct-LSF integration, and durable records at
the boundary where Dask's transient state is insufficient.

This is a hypothesis to test, not a conclusion to protect. In particular,
verify rather than assume that Dask's named worker executor hook, annotations,
resource accounting, cancellation, retry behavior, and worker lifecycle can
represent external jobs that may remain queued or running after a gateway
worker fails.

## Authoring hypothesis

Both Dask Futures and Delayed should be exercised. Arbitrary branching and
fan-in are core; map/reduce is only one demonstration constructed from them.
The ordinary ASS-facing surface should be compact and hide raw
`dask.annotate()` contexts:

```python
@task
def prepare(source):
    ...

@task(policy=lsf_direct("normal"))
def evaluate(prepared):
    ...

@task(policy=lsf_pool("standard"))
def summarize(result):
    ...

a = prepare(source)
b = evaluate(a)
c = summarize(b)

# One invocation may override the operation's default without mutating it.
d = evaluate.options(policy=local())(a)
```

Determine how one task definition supports Delayed graph construction and
Futures-style immediate submission without surprising mode-dependent
semantics. An invocation override should outrank a decorator default, which
should outrank a flow/run default, with local as the final default. Resolution
must be deterministic and inspectable. Unsupported placement must fail rather
than silently fall back elsewhere.

Task-policy boundaries must survive Dask graph optimization. Investigate
fusion, callable annotations, key stability, serialization, and whether policy
belongs in the callable wrapper, Dask annotations, or both.

## Execution modes

### Local

Local is the default and should require no LSF installation. It uses ordinary
Dask execution and supplies the fast feedback path for development. Decide
whether externally executable operations should use the same invocation runner
and file contract locally as they do under LSF, while allowing ordinary
in-memory Python tasks to remain inexpensive.

### Direct LSF

Direct LSF is the primary remote mode: one selected logical invocation should
correspond to one `bsub` job with its own job identifier, resource request,
logs, status, and cancellation.

The leading integration hypothesis is a resource-labelled Dask gateway worker
with a named `concurrent.futures.Executor` selected internally by task
annotation. The executor would materialize an invocation bundle on shared
storage, render a structured LSF profile into a job script, submit it, monitor
it, map cancellation to `bkill`, and complete the Dask task with a small result
or artifact manifest.

Do not accept this hook merely because it can submit a command. Establish:

- how executor capacity and Dask worker occupancy correspond to outstanding
  and queued LSF jobs;
- how dependencies are materialized without serializing large worker-memory
  values into batch submissions;
- how job IDs survive controller or gateway loss;
- how cancellation, timeout, retry, and resubmission avoid orphaned or
  duplicate jobs;
- how a restarted controller reconciles durable invocation identity with
  `bjobs` and completed result manifests;
- how remote Python/code/environment identity is selected and recorded; and
- whether the public Dask extension surface is stable enough for this role.

A thin gateway task that submits and waits, a named executor, and a
scheduler/worker plugin are distinct designs with different failure modes.
Compare them through a small spike before selecting one. If all require
reimplementing Dask's state machine or relying on unstable internals, stop and
reconsider the engine boundary rather than hiding a second scheduler inside an
adapter.

### Pooled LSF

Pooled LSF uses Dask Jobqueue to allocate reusable Dask workers through LSF.
It is intended for many compatible tasks, warm-worker latency, and useful
in-memory reuse. It does not promise one LSF job per logical task.

The desired topology is one Dask scheduler coordinating explicitly labelled
local workers, pooled LSF workers, and the direct-LSF gateway. Validate how a
Jobqueue-managed `LSFCluster` can own or join that topology rather than
assuming several separately scheduled Dask clusters can exchange Futures.
Begin with one homogeneous pool profile; multiple differently shaped pools
are deferred until a real workload requires them. Static scaling and adaptive
scaling should remain available.

## Policy and placement

Execution policy belongs to an invocation, with convenient defaults on an
operation. Use named, site-owned profiles rather than embedding arbitrary
`bsub` fragments in workflow code. A resolved policy may include:

- mode: `local`, `lsf-direct`, or `lsf-pool`;
- profile, queue, project/account, cores, memory, wall time, and environment;
- logical scarce resources such as licences;
- priority, retry and timeout bounds; and
- an explicit fallback rule, absent by default.

Persist requested, resolved, and observed placement separately. Dask resource
labels may enforce routing, but arbitrary ASS metadata has no scheduling effect
unless the ASS layer or a deliberate plugin interprets it.

## Durable boundary

Dask Futures, scheduler task state, worker addresses, and Jobqueue cluster
objects are operational handles rather than the only history. Retain a small,
file-first sidecar that can explain each invocation and attempt without
becoming a competing workflow database. At minimum record:

- stable flow/run, task, invocation, and attempt identities;
- operation/code and resolved-input identity;
- requested, resolved, and observed execution policy;
- timestamps, status, retry lineage, executor kind and scheduler job ID;
- stdout, stderr, diagnostic and result-manifest locations; and
- produced artifact references and enough environment identity to interpret
  them.

Use append-only attempts and atomic result publication. Large or cross-backend
values should cross the direct-LSF boundary as artifact references on shared
or otherwise addressable storage. Decide what may remain an in-memory Dask
value and make every automatic materialization boundary visible.

This slice does not yet need global provenance queries, cache correctness for
all ASS inputs, evidence promotion, a workflow server, or a complete durable
study projection. Preserve seams for those responsibilities without
pretending to implement them.

## First falsifiable vertical slice

The first implementation plan should build evidence in this order:

1. A small arbitrary DAG with branching and fan-in runs locally through both
   the compact Delayed surface and a Futures-style submission surface.
2. Invocation defaults and immutable call-site overrides resolve to explicit
   policies, and policy boundaries remain intact after graph optimization.
3. A fake, command-compatible LSF adapter proves job-script rendering, job-ID
   capture, status transitions, cancellation, failure, idempotent retry, and
   result-manifest publication without requiring farm access.
4. A real direct-LSF smoke test proves that one selected invocation becomes
   one LSF job while predecessor and successor tasks may remain local.
5. One Jobqueue pool proves reusable LSF workers, then a mixed graph exercises
   local, direct, and pooled placement under one Dask scheduler.
6. Interruption or gateway loss is injected to expose whether durable
   reconciliation is credible or whether the Dask integration hypothesis must
   be rejected.

The demonstration may use one locally prepared dependency and a two-item
map/reduce fan-out and fan-in, but those operations must be expressed through
the same arbitrary graph primitives available to users.

## Questions the dialectic must resolve

- Is a named Dask worker executor a sound public boundary for independently
  scheduled LSF jobs, or merely a clever prototype that violates Dask's worker
  assumptions?
- What is the smallest direct-LSF lifecycle contract that remains recoverable
  without building another workflow engine?
- How should local, direct, and pooled work share one scheduler, resource
  model, and security boundary?
- Which dependency values require artifact materialization, and who owns it?
- Can one compact task decorator honestly serve both Futures and Delayed?
- What durable plan projection is useful without duplicating the Dask graph as
  a second source of truth?
- Does this unit implement a flow, a resolved task runtime, or an executor
  substrate? Its eventual name and ontology should match what it actually is.
- Which existing engine should be reconsidered if direct per-task batch
  execution makes Dask an unsound kernel?

The immediate deliverable is a reviewed architecture, explicit contracts,
falsification criteria, and a staged implementation plan. Do not implement the
new component until that proposal has been reviewed and graduated.
