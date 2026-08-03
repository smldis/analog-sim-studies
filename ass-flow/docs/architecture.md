# ASS Flow architecture and research ledger

## Provenance and authority

This note adapts the ASS Flow-specific material from the human-curated
dialecticH graduation into the component that now owns the implemented planning
contract. It does not copy the root manifesto or silently graduate the
graduation's provisional execution hypotheses.

Source baseline:

- source run: `20260802-095704`;
- graduation: `20260802-214949-a68fd038`;
- graduated `main.md` SHA-256:
  `cd5c54e288bc5008b316650ec2a7a8920c645678ec4acf25f3d499e9fd69efc7`;
- graduated `objective.md` SHA-256:
  `defb4d4885fbb439c6966cfb8efaba57bbee6588543d40ff74785b94fb69be80`.

That graduation was a reviewed continuation seed, not implementation
authorization. The later user-authorized work and its evidence are recorded in
the component `PLANNING.md` and `IMPLEMENTATION.md`. Those trackers and the
current `ONTOLOGY.md` govern implemented scope. The project `MANIFESTO.md`
continues to govern the broader system.

The tracked root `docs/vision/ass-flow-rebuild-main.md` predates the graduation
and is retained as historical inquiry context. When its text differs from the
graduated baseline, it is not the source for the decisions classified here.

## Review vocabulary

This review does not equate "not implemented now" with rejection:

- **adopt** retains a direction or invariant as current architecture;
- **adapt** retains the concept with a narrower owner or revised mechanism;
- **defer** preserves a live hypothesis and names the evidence required to
  select it;
- **discard** rejects a mechanism or default while retaining the rationale that
  made it worth considering.

## Complete graduated-section disposition

The inherited manifesto sections remain adopted at the composition root and
are referenced rather than duplicated here. ASS Flow contributes only their
author-and-plan responsibilities; the working `study` envelope, evidence, and
decisions remain outside this component.

| Graduated section or concept | Disposition | Current interpretation |
| --- | --- | --- |
| Vision and core commitments | adopt by reference | Headless authority, Python-native composition, and file portability govern the project. ASS Flow provides inspectable authored Plan data, including declarations about materialized external sources, but does not produce materialized evidence. |
| Study as the unit of work | adapt outside ASS Flow | Keep intent/context/actions/evidence/decisions as the wider system vocabulary; do not make the static planner own a `Study` object. |
| Author/Plan/Execute/Evaluate/Decide/Preserve responsibilities | adopt as system decomposition | ASS Flow owns generic authoring and planning only. Later units or explicit adapters must own the other responsibilities. |
| AI-assisted work and bounded autonomy | adopt | Agents use the same files and APIs and gain no route around validation, provenance, review, or authorization. Runtime permission remains external policy. |
| Filesystem ontology composition | adopt | `ass-flow/` earned a direct child boundary for an independently testable planning capability; containment grants no runtime authority. |
| Component boundaries and contracts | adopt | Keep authored intent, materialized artifacts, operations, provenance, and composition distinct. Promote only explicit contracts. |
| Representative end-to-end reference | adapt into staged evidence | The current root-owned OTA/PVT Plan Reference tests authoring and planning first. It must not be described as end-to-end execution. |
| Retired `study-flow` as the implementation base | discard | Its fixed graph and whole-run backend choice remain evidence, not compatibility constraints or code to revive. |
| Generic arbitrary graph with per-invocation policy | adopt | Static arbitrary graphs and data-only policy resolution are implemented. Executable placement remains unresolved. |
| Dask as the initial kernel | adopt as the first falsifiable execution hypothesis | Do not hide it behind a speculative generic engine interface, but do not make it a package dependency until a bounded lowering spike succeeds. |
| Both Delayed and Futures | adapt | Compare them as lowerings of one normalized invocation contract. Do not create ambient, mode-dependent Python-call behavior. |
| One operation with explicit `plan(...)` and `submit(...)` surfaces | partially adopt | The immutable operation and explicit planning surface are accepted. `submit(...)` remains refusing until lowering evidence shows whether one operation description can serve both timings honestly. |
| Ambient-client detection | discard | A live client must never silently change a bare operation call into execution. |
| Invocation wrapper and optimization boundary | defer with a mandatory spike | Preserve each authored invocation initially; test Dask fusion, annotation survival, keys, serialization, and policy revalidation before choosing a lowering. |
| Literal/artifact/ephemeral value classes | partially adopt as static Plan metadata | External source references are declared artifacts and operation-output references are ephemeral. Source address, codec, and assumed access scope are inspectable data; literals and runtime values still require a future lowering contract. |
| Explicit materialization edges | adopt as a requirement when crossing execution environments | No automatic hidden transfer into direct LSF. The exact operation/schema is deferred until a real boundary needs it. |
| Reusable custom flows and nested static composition | adopt | Implemented by `@flow`, explicit Plan scope, nested boundaries, branching, and ordered fan-in. |
| Sequential stable-slot convenience | discard from active scope | Archived after explicit user direction; revisit only from repeated real editing friction. |
| Hidden imperative `Flow.run()` controller | discard | Result-dependent work must remain a visible state transition/new Plan or a later explicit conditional contract. |
| Result-dependent fallback/recovery | defer | Challenge "commit explicit state then reapply a flow" against a visible conditional/recovery node when an actual recovery case exists. |
| Local execution | adopt as the first execution mode to test | It must need no LSF and should prove normalized invocation lowering and boundary preservation before remote modes. It is not authorized by the current reference work order. |
| Direct LSF as one visible job per selected invocation | adopt as a required remote capability | Preserve this user-facing requirement. Reject implementations that merely allocate a Dask worker pool and call it direct execution. |
| Named Dask worker executor as durable LSF owner | discard | A worker executor/Future cannot be the durable identity of an LSF job that outlives the worker. It may still be compared as a transport/capacity hook over a separate attempt protocol. |
| Dask owns readiness; attempt protocol owns external LSF lifecycle | adopt the authority split, defer the exact adapter | Never let the adapter schedule successors or replay DAG readiness. Prove launch-or-attach, cancellation intent, reconciliation, and atomic terminal publication. |
| Acceptance-to-receipt and terminal-to-manifest failure injections | adopt as mandatory evidence | These are stronger gates than a nominal `bsub` smoke test and must precede real-farm acceptance. |
| Pooled LSF via Dask Jobqueue | adopt as the leading pool mechanism, defer integration | Use it for warm reusable workers/data locality, not one-job-per-invocation semantics. Validate one scheduler topology rather than assuming cross-cluster Futures. |
| Requested/resolved/observed policy and named profiles | adapt | Current Plan stores resolved data-only policy and descriptive resources. A runtime contract must retain requested and observed placement separately and keep fallback absent by default. |
| File-first durable sidecar | adopt as a future boundary, not current ASS Flow state | Plan, invocation, attempt, artifact, and terminal publication identities must remain distinct from Dask handles. The smallest facts should be learned from recovery evidence. |
| Dask Futures/worker state as durable history | discard | They are operational handles and observations only. |
| Reviewed evidence work orders | adopt | The current root reference has a durable identity, scope, exclusions, stop conditions, and completion rule. Passing it does not authorize the next slice. |
| Fixed roadmap or agent-selected expansion as default | discard as defaults | Retain reviewed evidence work orders while architecture is provisional; reassess if review ceremony ceases to change scope. |
| Candidate first planning work order | adapt and close as historical input | Its generic static-planning question was implemented and reviewed; sequential editing was later archived, while typed state/atomic publication stayed deferred. |

## Enduring architectural intent

The following direction remains applicable to ASS Flow:

- ordinary Python is the authoring and composition language;
- operation definitions and reusable flow definitions are distinct;
- an explicit lexical planning scope prevents ambient clients or process state
  from changing the meaning of a call;
- arbitrary static branching, fan-in, and nested flows normalize into one
  inspectable Plan rather than competing graph models;
- requested policy and resolved policy are visible before execution;
- planning performs no executor, scheduler, filesystem-publication, or hidden
  runtime side effect;
- an authored invocation identity is separate from any future executor task,
  attempt, or cache identity;
- unsupported execution placement or artifact crossing must eventually fail
  explicitly rather than silently fall back;
- a hidden imperative `Flow.run()` controller must not privately choose
  branches or submit work outside an inspectable plan.

These are architectural constraints. Only the subset named by the ontology and
public API is an implemented contract today.

## Implemented and accepted prototype contract

The user-authorized planning work established this bounded component:

- `@operation` creates immutable, versioned definitions with declared scalar
  and ordered collection artifact inputs, configuration, outputs, descriptive
  resources, and default policy;
- `@flow` creates reusable Python planning strategies and preserves nested
  boundaries in the authored Plan view;
- calls are legal only inside explicit `plan(...)` scope;
- operation bodies do not execute during planning, while flow bodies execute as
  ordinary authored Python to construct the static graph;
- immutable invocation bindings and dependency edges form one normalized Plan
  IR with deterministic data and JSON inspection;
- planning validates required and unexpected bindings, configuration types,
  artifact kinds, collection membership/order, output ownership, and key scope;
- schema-2 source declarations record opaque addresses, codec identity/options,
  and assumed access scope; source references are artifacts and ordinary
  operation-output references are ephemeral;
- optional output materialization capability is inspectable declaration data
  only and does not publish or change an output reference's value class;
- `.options(policy=..., key=...)` is immutable; call policy outranks operation,
  Plan, and local defaults;
- explicit scoped keys provide stable identities for fully keyed nodes and
  operation-to-operation edges within stable keyed boundaries;
- `submit(...)` refuses with `NotImplementedError` and confers no runtime
  authority.

This evidence accepts the static planning implementation as a prototype. It
does not accept the execution architecture described later in the graduation.

## Revisions made by development evidence and user direction

### Sequential editing

The graduation proposed a sequential helper with stable-slot insertion,
removal, and substitution as one acceptance example. The user later chose to
avoid that convenience layer. It is now rejected from active scope and retained
only in `docs/archive/sequential-flow-convenience.md`, with a reactivation
trigger. Arbitrary Python composition remains the sole flow-authoring model.

### Component boundary

The graduation deliberately deferred the public boundary. Later reviewed
implementation evidence and user direction promoted the planner to the direct
child `ass-flow/`. The accepted boundary is narrow: this component owns static
authoring and Plan IR only. Execution, attempt persistence, artifact
publication, and the wider study lifecycle have not thereby been assigned to
ASS Flow.

### Authored identity

The graduation distinguished invocation identity from Dask task keys and
attempt IDs. Development confirmed a narrower current contract: explicit keys
identify scoped Plan nodes and some connecting edges. They are not code hashes,
external-source identities, cache keys, executor keys, or attempts. Unkeyed
ancestors and external sources retain deterministic authored-order identity.

### Collection fan-in

The implementation supports fixed, non-empty, ordered collections of artifact
references and records one positioned edge per member. This is static authored
fan-in, not runtime result discovery or dynamic graph expansion.

## Preserved execution research

The dispositions above preserve the execution line of inquiry. The sections
below state what is already selected as an invariant and what still requires a
falsifiable implementation check.

### One operation, two explicit evaluation surfaces

The leading hypothesis is that the same immutable operation description could
support an inspectable `plan(...)` surface and an explicit `submit(...)`
surface without ambient-client semantics. Planning is implemented; submission
is not. A future bounded lowering experiment must test whether normalized
invocation meaning survives execution timing, Dask optimization, and result
handling before this hypothesis can graduate.

If equivalent dependencies require materially different argument/result
semantics, policy resolves after work begins, or durable identity depends on an
optimized Dask key, the public surfaces may need to split over a shared
operation description.

The comparison must use the same branching/fan-in graph and compare normalized
operation identity, bindings, resolved policy, explicit materialization edges,
and output kinds. Dask keys, submission timestamps, and transient handles are
not expected to match. The one-description hypothesis is rejected if Futures
cannot expose the normalized invocation before execution begins, if the two
surfaces need different dependency semantics, or if Dask optimization must
become the durable source of identity.

### Value and materialization boundaries

The graduation proposed classifying each future execution input as a small
serializable literal, an addressable artifact reference, or an ephemeral Dask
value. It also required an explicit materialization operation before ephemeral
data could cross into direct LSF.

Current schema-2 Plan IR distinguishes addressed external artifact references
from ephemeral operation-output references. It records opaque source addresses,
codec contract identity/options, assumed access scope, and optional output
materialization capability as canonical declaration data. It does not resolve
addresses, execute codecs, check real accessibility, publish artifacts,
materialize operation outputs, provide runtime artifact values, or record
checksums/provenance. A real adapter or lowering work order must own those
behaviors and decide what additional runtime contract is necessary.

### Dask kernel

Dask owning graph readiness, dependencies, routing, ordinary retries, and
diagnostics is the first execution hypothesis to test, rather than one option
hidden behind a new generic ASS engine interface. It is not yet a selected
runtime dependency. A local lowering spike must test preservation of authored
invocation boundaries, policy metadata, branching/fan-in, and explicit
materialization without adding a second graph scheduler.

The named-worker-executor hook remains a real Dask mechanism: a Worker accepts
a mapping of named `concurrent.futures.Executor` instances, and the worker
selects one from an `executor` task annotation. That makes it credible as a
transport experiment. It does not grant durability: Dask may retry tasks and
worker cancellation cannot necessarily stop already running thread work.

Dask's own documentation also warns that annotations on Delayed and other
collections can be lost during optimization unless fusion is disabled. This
supports the graduated requirement to preserve an explicit invocation wrapper
and validate resolved policy at execution; annotation alone is insufficient.

### Direct LSF attempt protocol

The graduation provisionally separated authorities:

- Dask would own graph readiness and delivery;
- a restartable adapter would own one external attempt;
- LSF would own batch state after acceptance;
- a runner would atomically publish a terminal result manifest;
- a file-first sidecar would own durable identities and facts.

That authority split is adopted; the exact adapter remains unimplemented. It is
motivated by the gateway-loss interval after `bsub` acceptance: IBM LSF assigns
a unique job ID at submission, while Dask can reschedule a lost task. A retry
must therefore attach to the recorded attempt/job or reconcile an attempt token,
not blindly call `bsub` again.

Cancellation likewise records durable intent before `bkill`; Dask cancellation
or the return from `bkill` is not by itself proof that a remote payload stopped.
Direct LSF must remain unavailable until the two graduated failure injections
prove idempotent attach/reconciliation and atomic terminal publication without
an ASS graph coordinator. If recovery requires replaying graph readiness outside
Dask, compare an existing workflow engine instead.

The proposed adapter contract is preserved for that future spike:

- create an immutable invocation bundle and stable attempt ID before
  submission;
- `launch_or_attach(attempt_id)` atomically claims an unsubmitted attempt,
  attaches to its recorded LSF job ID, or returns its already-published terminal
  manifest;
- if the site cannot make acceptance-to-receipt atomic, include the attempt ID
  in the job identity and prove it can be reconciled; otherwise declare direct
  execution unsupported at that site;
- `request_cancel(attempt_id)` records idempotent cancellation intent before
  invoking `bkill`;
- re-entering the same attempt attaches rather than submitting again; a new
  retry attempt is legal only after the previous attempt is terminal or an
  explicit overlap policy permits it;
- success requires both an acceptable observed LSF terminal state and an
  atomically published result manifest; conflicts are reconciliation failures.

Its durable state is deliberately smaller than a workflow database:
`unsubmitted`, `submitted(job_id)`, cancellation requested, terminal
observation, and manifest publication. Reject this boundary and compare an
existing engine if correctness requires persisting/replaying Dask readiness,
the receipt-loss window cannot be reconciled, a worker must stay alive to avoid
duplication, cancellation depends on undocumented scheduler transitions, or an
ASS coordinator must decide when mixed-mode successors become runnable.

### Pooled LSF

Dask Jobqueue's current `LSFCluster` supports LSF worker-job submission,
scaling/adaptation, structured queue/project/core/memory parameters, job script
prologues, worker resource arguments, and scheduler options. It remains the
leading pool mechanism for warm workers and Dask-managed data locality.

Integration is deferred until a workload needs those properties. `LSFCluster`
normally creates and owns a scheduler, so the desired one-scheduler mixed
topology must be demonstrated rather than assumed. Pooled LSF does not
substitute for one visible LSF job per direct invocation.

### Policy, placement, and durable records

Named site profiles and deterministic call/operation/Plan/local precedence are
adopted. Arbitrary raw `bsub` fragments in authored flows and silent fallback
remain rejected. Current Plan IR stores one resolved data-only policy; it does
not yet preserve requested versus observed placement. A future runtime record
must add that distinction without turning transient scheduler state into
history.

The file-first durable sidecar concept is also retained. It should record only
the facts recovery and explanation require: logical Plan/invocation identity,
separate append-only attempts, requested/resolved/observed policy, job ID,
timestamps and diagnostics, result manifest, and artifact references. It must
not become a second graph scheduler or a database prerequisite by default.

### Evidence ladder, not an authorized roadmap

The graduated sequence remains useful as ordered falsification evidence, with
one prerequisite exposed by the completed domain reference:

1. **complete:** construct a representative static domain Plan;
2. **complete:** specify and test the
   minimal declarative source-handoff contract exposed by that Plan, without
   expanding it into a general artifact store or runtime adapter;
3. after a separate reviewed work order, lower a small arbitrary
   graph locally through Dask while preserving normalized invocation identity,
   policy, branching, and fan-in;
4. compare Delayed and Futures descriptions before accepting `submit(...)`;
5. exercise a fake command-compatible LSF attempt adapter, including both loss
   windows and atomic manifest publication;
6. only then run one real direct-LSF smoke test if the site contract supports
   reconciliation;
7. add one Dask Jobqueue LSF pool and mixed topology only when a workload needs
   warm workers or data locality.

Each numbered item requires a new reviewed work order. Failure at one step may
change the mechanism or component boundary; it does not authorize repairing the
hypothesis by adding hidden scheduler authority.

## Current technical recheck

The Dask/LSF research was rechecked on 2026-08-03 against current primary
documentation:

- [Dask Worker](https://distributed.dask.org/en/stable/worker.html) still
  documents named executor mappings;
- [Dask Worker source](https://distributed.dask.org/en/latest/_modules/distributed/worker.html)
  still selects the executor named by a task annotation;
- [Dask resources](https://distributed.dask.org/en/latest/resources.html) warns
  that collection annotations can be lost during optimization and documents
  fusion disabling as a mitigation;
- [Dask worker state](https://distributed.dask.org/en/latest/worker-state.html)
  documents rescheduling after worker loss and the limits of cancelling running
  thread work;
- [Dask Jobqueue `LSFCluster`](https://jobqueue.dask.org/en/latest/generated/dask_jobqueue.LSFCluster.html)
  remains a supported mechanism for LSF-hosted Dask workers;
- IBM documents that [`bsub`](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=bsub-submit-job)
  assigns the job ID, [`bjobs`](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=reference-bjobs)
  observes job state, and [`bkill`](https://www.ibm.com/docs/en/spectrum-lsf/10.1.0?topic=reference-bkill)
  requests termination.

This check strengthens the main file's central warning: the named executor is
a plausible Dask hook, but durable direct-LSF correctness needs an independent
attempt identity and reconciliation protocol.

## Decision ledger

| Question | Current status | Evidence or trigger |
| --- | --- | --- |
| Static custom-flow composition | accepted with domain-sized evidence | The completed root-owned OTA/PVT reference expresses preparation forks, three ordered PVT branches, and two ordered fan-ins in one deterministic Plan without a second graph model. |
| Sequential-flow convenience | archived/rejected from active scope | Reconsider only after repeated real workflows show the same stable-step editing burden. |
| Result-dependent fallback/recovery | deferred | Compare reapplying a flow to committed explicit state with a visible conditional/recovery node when a concrete failure workflow requires it. Hidden controllers remain rejected. |
| Authoring surfaces | planning accepted; submission unresolved | A bounded lowering experiment must compare normalized meaning before any working `submit(...)` surface is accepted. |
| Typed state/artifact transition | declarative prerequisite accepted | Schema-2 Plans distinguish addressed artifact sources from ephemeral operation outputs and record codec/access assumptions. Independent review accepted the data-only boundary after one structured-validation defect was corrected. Resolution, codec execution, real access checking, publication, materialized outputs, and runtime values remain unimplemented. |
| Local execution | selected first execution hypothesis; not authorized | A separately reviewed Dask lowering work order may now test normalized invocation meaning without LSF or durable runtime expansion; completion of the prerequisite did not authorize implementation. |
| Dask executor boundary | selected first kernel hypothesis; unvalidated | Local lowering and invocation-boundary preservation must be tested before accepting the dependency or public execution surface. |
| Direct LSF lifecycle | authority split adopted; adapter unvalidated | Fake acceptance-to-receipt and terminal-to-manifest failure injections are required before farm use. |
| Mixed local/direct/pool topology | deferred | Requires credible local lowering and direct-attempt ownership first. |
| Durable Plan/attempt/artifact projection | Plan only is implemented | Fresh-process attempt reconciliation must determine the minimal additional facts. |
| Component boundary and name | accepted for static planning only | Revisit if executor/runtime responsibilities prove independently useful or cannot fit this ontology honestly. |
| Plugins and declarative flows | deferred | Require a concrete multi-repository or non-Python authoring need. |

## Current evidence work order

The user-authorized
`ASS-FLOW-WO-2026-08-03-ARTIFACT-HANDOFF` work order is recorded in
`PLANNING.md`. It is complete: implementation and integration evidence pass,
and independent source/boundary review returned `ACCEPT` after one malformed
source-validation defect was corrected and reverified. It enriches static Plan declarations only: external sources
become structured, addressed artifact references with explicit codec and
assumed-access requirements, while every ordinary operation output remains an
ephemeral reference.

An initial review proposal to make publication mandatory on every output was
rejected after rechecking the exact graduated main. That mechanism would have
discarded the retained in-memory Dask composition hypothesis. Optional output
materialization capability is declaration data only; it cannot publish or
change an edge's value class. Final-output publication and cross-environment
materialization remain visible decisions for later work orders.

The completed root-owned OTA/PVT Plan reference, now adapted to schema 2,
supplies the acceptance graph without moving its domain meaning into ASS Flow.
Local Dask lowering remains the next candidate execution experiment only under
a new reviewed work order. Current passing evidence does not authorize Dask, LSF, sibling
adapters, codec execution, address resolution, publication, materialized
outputs, runtime values, or a study runtime.

## Rules for the next development decision

Choose the smallest reversible experiment that answers one live question.
Before implementation, record an exact work-order identity, current evidence,
files and contracts in scope, external resources, delegated choices, acceptance
checks, stop conditions, and a completion rule. Stop when the discriminating
observation is obtained or an excluded boundary becomes necessary.

Passing tests accept only the stated evidence. They do not automatically
accept an execution architecture, authorize the next slice, or turn deferred
research into a backlog.
