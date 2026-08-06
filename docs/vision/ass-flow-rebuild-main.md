# Analog Sim Studies: A Headless, Python-Native Study System

This manifesto defines the system we aim to build, not the implementation that
exists today. The gap is intentional and will be closed module by module.

## Vision

Build our own headless, Python-native system for analog-design work. To an
operator it should feel like one coherent tool; underneath, it should remain a
composition of narrow, independent modules. We favor composition over
inheritance because explicit boundaries make the system easier to maintain,
test, replace, and extend.

Plain files and CLI-first interfaces make the same capabilities available to
an engineer at a shell, a CI job, a script, or an agent. Operations should be
low-latency, scriptable, and reviewable in version control. Authored intent
must not be owned by GUI state or a proprietary database. Python is the common
authoring and extension language, while materialized files are portable
evidence.

## Core commitments

### Headless authority

Headless describes where authority lives, not which interfaces may exist.
Every essential operation must work without an interactive session, and every
durable piece of authored intent must survive outside a process or user
interface.

Human-facing interfaces may improve exploration and visualization, but they
are replaceable clients of the same public contracts. Closing a client cannot
erase the work, and using one cannot create a second form of intent hidden from
the CLI, CI, or an agent.

This gives every capability a design test. If it depends on private process
state, an unrecorded click sequence, or an opaque database, it is not yet part
of the coherent system. Once it has an explicit operation, inspectable intent,
named outputs, and provenance, human-facing interfaces can be added without
weakening the headless core.

### Python-native composition

Python-native means that engineers can author, compose, inspect, and extend the
system in ordinary Python. It does not require every dependency to be
implemented in Python. Simulators, schedulers, data tools, and adopted
components may use whatever implementation suits them. Explicit adapters
isolate those dependencies, while Python remains the common language for
connecting their capabilities.

### File-based portability

File-based boundaries are visible and transferable. Authored files are
reviewable source. Materialized files are portable evidence, with manifests
and metadata describing derived artifacts. Large or externally stored results
remain addressable through recorded identities and provenance.

Portability does not require committing every raw waveform to Git. It requires
that another permitted operator can discover what exists, determine how it was
produced, and retrieve or reproduce it without reconstructing hidden session
state.

## The unit of work: a “study” (working name)

“Study” is the current umbrella name for a bounded unit of analog-design work.
It may be a characterization or verification campaign, a design change, a
sizing exploration, a comparison between variants, an investigation of a
failure, or the production of an engineering conclusion. It may begin before
the question is fully formed and become more precise as evidence accumulates.
Simulation may be central, secondary, or absent from its earliest stages.

The durable envelope around the work matters more than the noun. It brings
together:

- **Intent:** what the engineer is trying to learn, change, demonstrate, or
  decide.
- **Context:** the designs, testbenches, models, assumptions, constraints, and
  tool configuration on which the work depends.
- **Actions:** the edits, generations, simulations, transformations, and
  evaluations performed.
- **Evidence:** the materialized inputs, outputs, measurements, plots, tables,
  and reports produced.
- **Decisions:** the conclusions, accepted tradeoffs, rejected alternatives,
  and next questions that give the evidence meaning.

The name is deliberately provisional. A future vocabulary may distinguish an
experiment, investigation, campaign, task, or design iteration, or replace
“study” altogether. Renaming it must not require redesigning component
contracts: those contracts depend on intent, context, actions, evidence, and
decisions, not on one favored noun.

## Work capabilities and integration boundaries

Trusted simulators, device models, process data, and other facilities remain
external dependencies reached through narrow adapters. Backend-specific
details stay at that boundary. Authored intent, evaluation logic, provenance,
and results remain inspectable and portable. Changing a backend should require
an adapter or explicit configuration change, never manual rediscovery of the
work.

The system should support these shared responsibilities:

1. **Author.** State questions, inputs, variations, measurements, and
   acceptance criteria in Python and plain files.
2. **Plan.** Materialize inspectable jobs and dependencies before spending
   simulation resources.
3. **Execute.** Run locally, in CI, or on shared compute through adapters, with
   bounded concurrency and resumable work.
4. **Evaluate.** Turn raw outputs into named measurements, specification
   results, plots, tables, and machine-readable summaries.
5. **Decide.** Let a human, script, or agent accept the evidence, revise the
   work, or propose the next bounded experiment.
6. **Preserve.** Record enough provenance to explain and reproduce each result
   and identify work made stale by changed inputs.

These are conceptual responsibilities, not a mandate for one large workflow
module. Different components may implement different responsibilities. Their
shared vocabulary aligns component contracts and keeps the operator experience
coherent.

## Why

Closed commercial environments impose recurring costs through freezing
sessions, heavy resource use, complex APIs, and reusable intent bound to
licenses and GUI-centered state. We should reimplement only the features that
serve daily engineering needs, as open, file-based, headless modules.

The recurring pains are concrete:

- copying the same simulation setup into many variants;
- managing parameters, corners, and sweeps;
- reusing testbench structure across projects;
- launching many runs without turning the workflow into shell glue;
- evaluating results in code rather than by hand; and
- knowing which results depend on which inputs and what must be rerun.

## AI-assisted work

AI lowers the cost of creating and operating specialized workflows. An
assistant can turn an engineering procedure into code and build small tools to
investigate a hypothesis. Humans and agents may both propose what to try, but
intuition does not replace evidence and expert judgment remains necessary.
Conclusions must rest on inspectable inputs, simulator results, explicit
measurements and specifications, and recorded provenance.

The system must remain useful without AI and safe to extend with it. Humans, CI
jobs, scripts, and agents use the same public interfaces and produce artifacts
held to the same standards. Agents have no privileged route around validation,
provenance, review, or version control. This preserves the value of
conventional automation as agent capabilities improve.

Autonomy is a policy attached to a study, not a separate architecture. Policies
bound which files an agent may edit, which operations it may invoke, how many
resources it may spend, which stop conditions end an exploration, and which
decisions require human approval. Increasing autonomy changes explicit
permissions, not study formats or component contracts, and cannot introduce
unreviewable state.

## Filesystem ontology composition

Components are nested Git subrepositories with ontologies. The directory
hierarchy is part of the architecture, not merely storage. Filesystem
containment expresses composition: a descendant contributes to its closest
containing ontology node, and that contribution continues upward into the
whole system.

Containment grants no inheritance, specialization, override, or precedence. A
deterministic postorder may present the composed ontology, but presentation
order never defines authority.

An ontology declares a component’s semantic responsibility: its purpose,
scope, contracts, and the contributions of contained components. The
composition root describes the whole system. Nested ontologies add local
precision without restating the manifesto. Together, the repository tree and
the ontology files beside the code make the architecture discoverable to a
human or agent.

## Component boundaries and contracts

A component earns its boundary by being independently useful, testable, and
replaceable through explicit contracts. Those contracts use the same basic
distinctions throughout the system:

- **Authored intent** is the human- or agent-written source of truth.
- **Materialized artifacts** are derived evidence and can be regenerated.
- **Operations** are headless CLI and Python entry points.
- **Provenance** records inputs, versions, configuration, and operations.
- **Composition** connects declared outputs and inputs without hidden shared
  state.

Put a capability in the smallest component whose ontology can fully explain
it, and promote only its explicit contract upward. A cross-cutting
responsibility belongs in its own component when it has an independent
purpose; directories higher in the tree gain no implicit privilege.

A subrepository is an implementation and versioning boundary. Its ontology is
the semantic boundary. Stable contracts and shared conventions create
operator coherence without requiring a monolith. Work remains traceable across
components, and one component’s artifacts remain consumable without knowledge
of its internals.

Each new module should deliver a useful end-to-end slice, declare its boundary,
and compose without precedence rules.

## Verification and progress

The existence of an API or command does not verify a capability. The system
should keep at least one versioned, representative, end-to-end reference
workflow. Feature parity with a commercial suite is not the first milestone.
The reference workflow should prove that an operator can:

1. author a reusable setup once and derive named variants from it;
2. inspect resolved parameters, corners, jobs, and dependencies before
   execution;
3. execute again from a clean environment, interrupt safely, and resume
   without repeating results whose inputs remain valid;
4. evaluate measurements and specifications in code without manual
   transcription while retaining human-inspectable evidence;
5. change an input and explain which work is stale, which remains valid, and
   what must run again; and
6. trace a reported conclusion back to its exact inputs.

Further capabilities should extend this path without hidden state or a second
way to express the same intent.

Progress is measured in useful vertical slices. A slice is complete when it
removes recurring manual work, crosses component boundaries through explicit
contracts, and leaves a reproducible conclusion. The next slice is selected
from friction and daily benefit observed while using the current one. Shared
infrastructure is built only when a slice requires it.

Start from whatever runnable base exists, and adopt an existing component when
it fits; explicit module boundaries make adoption safe. Early implementation
limits must not be baked into the vision. When a module needs a narrower local
contract, it documents that narrowing while the manifesto retains the broader
target.

---

## Active development inquiry: rebuild ASS Flow

> **Dialectic scope:** Everything above this heading is inherited, approved
> main content and must remain byte-for-byte unchanged. Proposals may modify
> only this section and its descendants. The inherited text may be cited as
> context but must not be reconciled, pruned, restated, or edited during this
> run.

**Status:** historical pre-graduation dialecticH seed

The later human-curated graduation is identified by source run
`20260802-095704`, graduation `20260802-214949-a68fd038`, and main SHA-256
`cd5c54e288bc5008b316650ec2a7a8920c645678ec4acf25f3d499e9fd69efc7`.
Its ASS Flow concepts and the evidence produced by subsequent authorized work
are classified in the component-owned
[architecture and research ledger](../children/ass-flow/docs/architecture.md). This
older seed is retained as inquiry provenance, not as the current implementation
contract.

**Prior implementation:** retired prototype, recoverable from Git at `528c02f`

### Why reopen the design

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

### Scope of the inquiry

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

### Preferred hypothesis: Dask remains the kernel

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

### Authoring hypothesis

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

### Execution modes

#### Local

Local is the default and should require no LSF installation. It uses ordinary
Dask execution and supplies the fast feedback path for development. Decide
whether externally executable operations should use the same invocation runner
and file contract locally as they do under LSF, while allowing ordinary
in-memory Python tasks to remain inexpensive.

#### Direct LSF

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

#### Pooled LSF

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

### Policy and placement

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

### Durable boundary

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

### First falsifiable vertical slice

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

### Questions the dialectic must resolve

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
