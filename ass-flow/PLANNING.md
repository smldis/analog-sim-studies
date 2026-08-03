# ASS Flow planning and evidence work orders

## Authority and provenance

This bounded implementation spike was authorized by the user on 2026-08-03.
Its source contract is the human-graduated dialecticH baseline:

- source run: `20260802-095704`
- graduation: `20260802-214949-a68fd038`
- graduated main SHA-256:
  `cd5c54e288bc5008b316650ec2a7a8920c645678ec4acf25f3d499e9fd69efc7`
- graduated objective SHA-256:
  `defb4d4885fbb439c6966cfb8efaba57bbee6588543d40ff74785b94fb69be80`

The graduation itself did not authorize implementation. The later user request
authorizes only the experimental slice described here. It does not authorize
Dask or LSF execution, durable attempt storage, plugins, migration, production
packaging, or a complete ASS study runtime.

The dialecticH continuation launched from the graduation crashed before its
Judge decision. Its run evidence remains untouched and is not treated as an
implementation work order.

## Decision question

Can a small Python-native planning layer express reusable operations and
nested static flows as one stable, fully inspectable plan without performing
executor work or acquiring hidden runtime authority?

## Historical provisional location and status

The spike originally lived at the historical path
`prototypes/ass-flow-planning/`. At that time it was deliberately absent from
the root `unit.toml` and had no distribution or permanent ontology contract.
The later authorized development plan below superseded that provisional status
and promoted the same tested graph semantics to `ass-flow/`.

## User-directed narrowing

The graduated main proposed a sequential-flow editing helper as one acceptance
example. The user deferred and later archived that separate convenience layer;
its provenance and reactivation conditions are recorded in
[`docs/archive/sequential-flow-convenience.md`](docs/archive/sequential-flow-convenience.md).
Arbitrary Python composition is the only flow authoring model in this slice.

## Core implementation priorities

1. **Immutable definitions and contracts**
   - An `OperationDefinition` owns stable callable identity and version,
     declared inputs, configuration, outputs, resources, and a default policy.
   - A `FlowDefinition` owns reusable Python planning logic and a stable
     identity/version.
   - Decoration must not bind an executor or run user operation code.

2. **One normalized Plan IR**
   - Each authored operation call becomes an immutable invocation.
   - Dependencies are explicit edges derived from output references.
   - Nested flow boundaries remain visible in an authored view.
   - Normalized invocation and edge identities are deterministic for repeated
     construction of the same authored graph.
   - The plan has deterministic plain-data and JSON inspection surfaces.

3. **Explicit planning authority**
   - Operation and flow calls are legal only inside `with plan(...)`.
   - Calls outside an explicit scope fail with a short actionable error.
   - Ambient clients or process state never change call semantics.
   - Planning has no executor, scheduler, or artifact-publication side effects.

4. **Ahead-of-execution validation**
   - Required and unexpected input/configuration bindings fail during planning.
   - Literal configuration values are checked against declared Python types.
   - Connected output/input artifact kinds must be compatible.
   - Flow outputs must refer to values in the same plan.
   - Policy precedence is call override, operation default, plan default, then
     local.

5. **Honest non-core boundaries**
   - `submit(...)` is present only as an explicit `NotImplementedError` boundary
     directing the caller to `plan(...)`.
   - Dask lowering, local execution, LSF modes, retries, attempts, artifact
     publication, result-dependent replanning, and dynamic graph expansion are
     not partially simulated.
   - No hidden `Flow.run()` controller is provided.

## Provisional authoring surface

The intended acceptance shape is:

```python
@operation(
    inputs={"deck": artifact("spice-deck")},
    config={"corner": parameter(str)},
    outputs={"raw": artifact("simulation-raw")},
)
def simulate(deck, *, corner):
    raise AssertionError("operation bodies do not run during planning")


@flow
def characterize(deck, *, corners):
    return [simulate(deck, corner=corner) for corner in corners]


with plan(default_policy=local()) as draft:
    raw_results = characterize(input_artifact("input.spice", "spice-deck"),
                               corners=["tt", "ss", "ff"])

normalized = draft.finish(outputs={"raw": raw_results})
normalized.validate()
normalized.to_json()
```

Exact result-handle ergonomics may change if the implementation shows that a
single- versus multiple-output shortcut hides important identity or contract
information. The normalized representation is authoritative over syntactic
convenience.

## Acceptance evidence

- A nested custom flow creates static branching and fan-in in one normalized
  plan, while preserving nested flow boundaries for inspection.
- Constructing the same flow twice produces equivalent normalized plain data,
  including stable invocation and edge IDs.
- Operation bodies are not executed by planning.
- `.options(...)` is immutable and policy resolution follows the declared
  precedence.
- Missing configuration, unexpected bindings, incompatible artifact edges,
  foreign-plan outputs, and calls outside a planning scope fail before any
  execution boundary.
- Deterministic JSON makes the plan inspectable without importing the authored
  Python module.
- `submit(...)` and other excluded runtime capabilities fail clearly rather
  than pretending to work.

## Stop conditions

Stop and report evidence instead of broadening the spike if:

- nested flows and normalized invocations require competing graph models;
- deterministic identities require executor-specific keys or mutable global
  state;
- validation requires executing an operation body;
- planning needs filesystem publication, a scheduler, or a live client; or
- implementation requires selecting a permanent package/ontology boundary.

## Delegated component boundaries

Implementation is delegated to fresh Codex high-reasoning agents in bounded,
non-overlapping passes:

1. immutable contracts, policies, references, and normalized Plan IR;
2. decorators, scoped planning, nested flow capture, and public authoring API;
3. acceptance examples, adversarial validation tests, and independent review.

The coordinating session owns integration decisions, tracker updates, full
verification, and the final commit scope.

## Outcome of this slice

The implementation and acceptance evidence support the core planning contract
as a prototype. Immutable definitions, explicit scoped authoring, nested static
flows, branching/fan-in, early validation, and deterministic Plan JSON share
one model without adding executor behavior.

The evidence also narrows three claims:

- Name-keyed declarations are canonicalized and identical reconstructions have
  identical IDs/data, but inserting earlier authored nodes renumbers later
  authored-order IDs. Cross-edit identity stability is not yet promised.
- Artifact inputs are scalar. The example proves fixed-shape fan-in; a direct
  collection-valued fan-in contract remains deferred.
- The library never executes operation bodies or initiates runtime work, but an
  arbitrary Python flow body is executable planning code. Its freedom from
  external side effects is an authored discipline, not something this API can
  prove.

That slice originally recommended retaining the provisional directory as
runnable design evidence. The authorized development plan below superseded the
location recommendation and promoted the unchanged semantics to a declared
prototype child. The sequential convenience is now inactive historical
[archive material](docs/archive/sequential-flow-convenience.md), and all
runtime surfaces remain explicit stubs or exclusions.

## Authorized development plan: promote ASS Flow

**Authorization:** On 2026-08-03 the user directed development to continue,
selected `ass-flow/` as the actual component location, and archived the
sequential-flow convenience idea. This supersedes the preceding recommendation
to retain the implementation under `prototypes/`, but it does not change the
component's `prototype` maturity or authorize executor work.

### Invariants for every phase

- `ass-flow` owns generic Python-authored operation/flow planning and normalized
  Plan IR; it does not own simulation meaning, Dask scheduling, LSF transport,
  attempt recovery, evidence promotion, or the complete study lifecycle.
- Planning remains explicit. Operation bodies never execute during planning;
  arbitrary flow bodies remain ordinary authored Python and therefore cannot be
  statically proven side-effect-free.
- Normalized plans remain immutable, deterministic, JSON-inspectable, and
  validated before any future execution boundary.
- `submit(...)` remains a refusing `NotImplementedError` boundary in this pass.
- Existing user changes and dialecticH run evidence remain outside all commits.
- Each phase is independently testable and committed before the next phase.

### Phase 1 — component promotion and archive

Move the complete prototype to the direct child path `ass-flow/` and establish
the repository's normal component boundary:

- retain `src/ass_flow/`, `tests/`, `examples/`, `PLANNING.md`, and
  `IMPLEMENTATION.md` under `ass-flow/`;
- add `ass-flow/ONTOLOGY.md`, `ass-flow/AGENTS.md`, `ass-flow/unit.toml`, and a
  minimal `ass-flow/pyproject.toml` for an independently testable Python 3.10+
  prototype;
- add `ass-flow/docs/index.md` and
  `ass-flow/docs/archive/sequential-flow-convenience.md`;
- archive sequential editing as inactive historical design material: no active
  checklist item, acceptance criterion, implementation stub, or implied
  backlog; the archive may name a concrete reactivation trigger;
- replace the temporary `pytest.ini` with package-owned pytest configuration;
- add `ass-flow` to root `unit.toml`, developer bootstrap, README, ontology, and
  composition expectations without claiming an execution contract.

Acceptance:

- `python composition.py tree` lists `ass-flow` as one of four direct units;
- the component can be tested from `ass-flow/` without relying on the old path;
- aggregate docs can discover the child docs contract;
- `rg` finds no maintained reference that treats
  `prototypes/ass-flow-planning/` as the active implementation;
- the sequential helper appears only in its archive record and provenance
  history, not active scope.

### Phase 2 — finish the core static graph semantics

Implement only the two gaps exposed by the first prototype's evidence.

#### 2A. Collection-valued artifact inputs

- Add an explicit public declaration such as `artifacts("corner-metrics")` for
  an operation input containing a non-empty ordered collection of homogeneous
  artifact references.
- Preserve scalar `artifact(...)` behavior unchanged.
- Represent collection cardinality in the immutable input contract and binding;
  never encode artifact references as JSON configuration values.
- Emit and validate one dependency edge per collection member, including a
  stable member position so multiple edges may target one declared input.
- Reject non-sequences, empty collections, foreign-plan values, multi-output
  results without explicit selection, and mixed artifact kinds during planning.
- Replace the fixed three-input characterization reducer with the direct public
  shape `summarize(measurements)`.

#### 2B. Explicit stable authored identity

- Extend immutable operation and flow call views with an optional explicit
  authored key through `.options(key="...")`; policy and key overrides remain
  immutable and composable.
- Scope keys by the containing flow boundary and reject duplicates before plan
  finalization.
- Derive keyed invocation/boundary IDs and their edge IDs from normalized
  authored identity rather than global counters, so inserting an unrelated
  sibling does not rename explicitly keyed work.
- Keep deterministic generated IDs for unkeyed calls and document that only
  explicitly keyed identities promise stability across authored graph edits.
- Do not turn keys into cache keys, Dask keys, attempt identities, sequential
  slots, or runtime authority.

Acceptance:

- an arbitrary number of statically authored corner outputs feeds one summary
  invocation through a collection contract;
- repeated construction yields identical Plan data and JSON;
- inserting an unrelated unkeyed sibling leaves explicitly keyed invocation,
  boundary, and connecting edge IDs unchanged;
- duplicate keys, foreign handles, empty collections, and kind mismatches fail
  before execution;
- no sequential editing or executor behavior enters the public API.

### Phase 3 — acceptance and boundary review

- Update the simulator-free characterization example to use collection fan-in
  and explicit keys through public APIs only.
- Add adversarial tests for ordering, duplicate keys, nested boundaries,
  rollback, collection validation, canonical JSON, and operation-body
  non-execution.
- Update the component ontology only with behavior demonstrated by tests.
- Record limitations and the next decision question in `IMPLEMENTATION.md`.
- Run component tests, wheel build, root composition tests, and aggregate docs.

### Delegation map

1. `ass-flow-boundary` — Phase 1 filesystem/package/composition promotion and
   sequential archive; no core semantic changes.
2. `ass-flow-collections` — Phase 2A model/authoring implementation and focused
   tests; no identity redesign.
3. `ass-flow-identities` — Phase 2B keyed identity implementation and focused
   tests after 2A lands.
4. `ass-flow-review` — Phase 3 example, adversarial acceptance, and independent
   scope/ontology review; source defects are reported to their owning agent.

The coordinating session owns phase ordering, plan delivery, diff review,
cross-component integration, tracker updates, verification, and commits.

## Authorized work order: explicit materialized-source handoff

**Work-order ID:** `ASS-FLOW-WO-2026-08-03-ARTIFACT-HANDOFF`

**Authorization:** On 2026-08-03 the user directed development to proceed from
the completed OTA/PVT Plan reference. This authorizes the bounded static
contract below. It does not authorize Dask lowering, execution, publication,
materialization, a codec implementation, a store, or a runtime artifact value.

### Decision question

Can ASS Flow distinguish an addressed external artifact from an ephemeral
operation result, and record the external artifact's codec and accessibility
requirements, without materializing a value or changing the existing graph?

### Review correction and ownership

A fresh read-only Codex high architecture review initially proposed mandatory
publication on every artifact contract. Rechecking the exact graduated main
rejected that mechanism: it would force every local edge through a durable
artifact and discard the preserved ability for compatible local and pooled
Dask work to retain ephemeral values.

The corrected boundary is narrower:

- ASS Flow owns immutable declarations, value-class inspection, serialization,
  and structural validation because those extend its current Plan contract;
- authored external sources are already-materialized artifact references;
- ordinary operation outputs remain ephemeral references, even when an output
  advertises a possible materialized representation;
- a future adapter/lowering boundary owns address resolution, codecs,
  accessibility checks, publication, and runtime materialized values;
- a future explicit materialization operation or visible final-output request
  must turn an ephemeral result into an addressed artifact. This work order
  does not invent either mechanism.

The root-owned OTA/PVT reference supplies cross-unit acceptance evidence. No
new child or adapter unit is justified by data-only declarations alone.

### Authorized immutable model

Keep `ArtifactContract(kind)` purely logical. Add four data-only concepts:

- `CodecContract(name, version, options)` identifies a codec contract; options
  use the existing deeply frozen canonical JSON values;
- `ArtifactAddress(address_space, locator)` records a structured, opaque
  authored address without resolving or normalizing it;
- `MaterializationSpec(codec, address_space, access_scope)` describes the
  representation and environment assumption of an addressed artifact;
- `OutputContract.can_materialize_as` optionally advertises one representation
  that a later explicit materializer could request. It is capability metadata,
  not publication or a change of value class.

`ArtifactSource` replaces its free-form `uri` field with an `address` and a
required `materialized_as`. `ArtifactSourceReference` has the fixed inspectable
value class `artifact`; `OutputReference` has the fixed inspectable value class
`ephemeral`.

The reference classes, not artifact kinds or execution policies, determine the
binding value class. Collection bindings may contain both classes while
retaining order. An output capability must never create a source, address,
edge, publication, or runtime value.

### Authorized public authoring surface

Preserve `artifact(kind)` and `artifacts(kind)` as logical declarations. Add:

```python
JSON_V1 = codec("json", version="1", encoding="utf-8")
REPOSITORY_JSON = materialization(
    codec=JSON_V1,
    address_space="repository-relative",
    access_scope="repository-checkout",
)

limits = input_artifact(
    address("repository-relative", "inputs/spec_limits.json"),
    artifact=artifact("spec-limits"),
    materialized_as=REPOSITORY_JSON,
)

@operation(
    outputs={
        "report": materializable(
            artifact("report"),
            as_=REPOSITORY_JSON,
        )
    },
)
def report():
    ...
```

The legacy `input_artifact(uri, kind)` form must fail rather than preserve a
kind-only external handoff. `materializable(...)` is accepted for outputs only.
There is no `publish(...)`, default materialization, or automatic transfer.

### Schema and identity

Canonical Plan data changes to schema version 2. It serializes structured
source addresses, source codec/access data, fixed reference value classes, and
nullable output capability metadata. This prototype gets no v1 writer,
migration layer, or compatibility shim.

Graph topology, operation/flow versions, invocation IDs, boundary IDs, edge
IDs, and scoped authored keys must remain unchanged. The OTA/PVT operations
retain version `1` because their logical contracts do not change. Adding only
external source materialization declarations is not an operation semantic
version change.

### Validation and acceptance evidence

- codec name/version, address space, and access scope are trimmed
  executor-neutral identifiers;
- codec options are finite, canonical JSON-compatible data;
- a locator is non-empty and opaque; planning performs no normalization,
  existence check, read, resolution, or I/O;
- an address space must exactly match its `MaterializationSpec`;
- every external source has an address, codec, and access scope; the kind-only
  legacy surface fails during authoring and independently malformed Plans fail
  validation;
- source and operation-output bindings retain logical kind checking;
- reference value classes serialize as `artifact` and `ephemeral`
  respectively, including positioned members of mixed collections;
- optional output capability changes only operation contract metadata and
  remains an ephemeral `OutputReference` when invoked;
- the OTA/PVT graph retains 4 sources, 6 operations, 2 flows, 4 boundaries, 16
  invocations, 18 edges, and 16 outputs with unchanged keyed identities;
- its four sources declare honest repository-relative representations: a
  directory-tree codec, Python-source/UTF-8 for the edit file, and JSON/UTF-8
  for the measurement definition and limits;
- the OTA/PVT final evaluation and all ordinary operation dependencies remain
  ephemeral; no nonexistent output codec is claimed;
- repeated construction and canonical JSON remain deterministic under schema
  2, planning performs no I/O, and operation bodies remain unexecuted;
- component, root integration, full composition, and diff checks pass;
- maintained code contains no materializer, publisher, resolver, codec
  implementation, runtime artifact value, Dask/LSF integration, cache,
  attempt, or provenance state.

### Files and delegation

Core scope is limited to `ass-flow/src/ass_flow/`, its three test modules and
example, local ontology/README/trackers/architecture ledger, the root OTA/PVT
reference and focused integration test, and the root ontology claim supported
by that reference. Sibling component source and ontologies remain untouched.

Implementation is delegated sequentially to fresh Codex high-reasoning agents:

1. `artifact-handoff-core` owns the immutable model, authoring API, schema-2
   serialization, focused component tests, and characterization example;
2. `artifact-handoff-evidence` owns OTA/PVT source declarations, root
   integration evidence, and documentation updates after the core is stable;
3. `artifact-handoff-review` independently reviews the full diff and boundary.

The coordinating session owns prompts, integration decisions, tracker state,
independent verification, corrections, staging, and commits.

### Stop and completion rules

Stop instead of broadening if correctness requires reading/decoding an
artifact, resolving an address, checking real accessibility, publishing a
value, allocating a target, introducing a materialized operation result,
selecting Dask/LSF policy, adding adapter-specific code to ASS Flow, or adding a
second graph model.

This work order completes when the schema-2 static distinction is implemented,
the OTA/PVT reference demonstrates four explicit artifact sources and
ephemeral internal edges, all checks pass, and an independent high review
accepts the no-runtime boundary. Completion authorizes drafting the local Dask
lowering work order; it does not implement or pre-accept that hypothesis.

**Completion:** Complete on 2026-08-03. Independent full-diff review found one
structured-validation leak for a deliberately malformed source artifact. The
core owner corrected the dereference and added a regression; independent
re-review returned `ACCEPT`. Final verification passed 63 ASS Flow tests, 10
focused OTA/PVT tests, 17 root integration tests, full composition
63/45/77/28/17, both schema-2 JSON commands, Python compilation, wheel build,
and diff checks. The next executor experiment still requires a separate
reviewed work order before delegation.

## Authorized work order: local Dask Delayed lowering

**Work-order ID:** `ASS-FLOW-WO-2026-08-03-LOCAL-DASK-LOWERING`

**Authorization:** After reviewing the proposed executor sequence, the user
directed development to proceed on 2026-08-03. This authorizes only the bounded
local lowering experiment below. It does not authorize a working `submit(...)`
surface, Dask Distributed/Futures, LSF, retries, persistence, publication,
materialized operation outputs, source resolution, codec execution, a generic
executor abstraction, or a study runtime.

### Decision question

Can one immutable schema-2 `Plan` be lowered to a locally computable Dask
Delayed graph while preserving authored invocation meaning, policy rejection,
static branching, ordered collection fan-in, and explicit operation/source
binding, without making Dask task state authoritative or adding a second graph
scheduler?

### Ownership and identity boundary

`ass_flow.experimental.local_dask` is a non-reexported experimental adapter
owned by this component solely to test whether Plan IR is a sufficient lowering
contract. Its presence assigns the experiment—not general execution,
scheduling, or a public runtime—to ASS Flow. If retained, the same integrated
change must update the local ontology to describe that experimental
contribution and narrow the Dask exclusion accordingly. The parent continues
to promote planning only. If the hypothesis is rejected and the code is not
retained as explicit negative evidence, remove the module before commit.

Neither `ass_flow.__init__` nor `ass_flow.experimental.__init__` may import or
reexport the Dask module. Creating a child unit before learning whether the
Plan lowers is premature; the completion review must revisit component
ownership before any public execution surface is accepted.

The lowerer consumes only:

- a validated immutable `Plan`;
- an explicit mapping from exact `OperationIdentity` values to Python
  implementation callables; and
- an explicit mapping from `ArtifactSource.id` to already-decoded runtime
  values.

The lowerer consumes model values only and is compatible with a future
independently reconstructed Plan; this work order adds no Plan reader or
deserializer. It must not receive or inspect an authored `Operation`, its
private callable, or its authoring module. It also must not resolve an artifact
address, execute a codec, or read a source file.

Plan invocation IDs remain logical authored identities. Every lowering call
allocates a fresh opaque namespace. Source, invocation-wrapper, and projection
keys combine that namespace with their role and logical Plan identity through
public Dask naming APIs. Actual Dask keys are unique within one lowering and
different across independent lowerings. Correctness must not derive from
`pure=True`, callable/source tokenization, or Plan IDs alone.

The inspection record maps Plan invocation IDs to actual pre-optimization keys
for that lowering; no cross-lowering key stability is promised. Dask keys are
never Plan IDs, attempt IDs, cache keys, or durable records. Registry keys are
exact `OperationIdentity` name/version values, not callable object identity.

### Minimal experimental surface

Add one explicitly experimental module under
`ass_flow.experimental.local_dask`. It may expose:

```python
lowered = lower_delayed(
    normalized_plan,
    operations={operation_identity: implementation},
    sources={source_id: decoded_value},
)
```

`lower_delayed(...)` returns a small immutable inspection record containing
the Dask Delayed task for every Plan invocation, the Delayed projection for
every named Plan output, and the explicit invocation-ID-to-Dask-key mapping.
It has no `run`, `compute`, `submit`, cancellation, persistence, or publication
method. Callers use Dask's own `compute(...)` explicitly during the experiment.

The wrapper receives keyword arguments for the invocation's bound input and
configuration names, not absent optional declarations. Scalar inputs receive
one runtime value and collection inputs an ordered tuple. Frozen list/object
configuration is thawed inside each wrapper execution into fresh ordinary
list/dict values.

The result is copied once into an ordinary dict. Failure while reading it, a
non-mapping value, or a key set different from the exact declared output-name
set is an attributable invocation failure. Runtime output value types are
otherwise unrestricted. There is no single-output shortcut, implicit tuple
convention, runtime artifact wrapper, or automatic materialization.

A zero-output invocation must return an empty mapping and still has an
invocation task. An orphan invocation also has a task. The lowerer does not
choose execution roots: computing top-level outputs executes only their
ancestor closure, while computing all invocation tasks executes every
invocation, including orphans and zero-output invocations. Empty top-level
outputs are valid. Flow-boundary outputs remain Plan inspection metadata and
create no invocation work. Multiple top-level names referencing the same
`OutputReference` reuse one projection Delayed.

One visible pre-optimization invocation wrapper produces the complete output
mapping; mechanical projection tasks must not duplicate it. Within one
`dask.compute(...)` evaluation over merged requested roots, a wrapper key is
evaluated at most once by the tested local scheduler. Separate compute calls
may execute it again; no persistence, memoization, retry, or cross-call
exactly-once guarantee exists. Wrapper failures carry the Plan invocation ID
and operation identity while preserving the original exception as the cause.

### Preflight and runtime refusal

Preflight must check the Plan type, call `Plan.validate()`, and copy both
supplied mappings once. Every operation-registry key must be an
`OperationIdentity` and every value callable. Every identity referenced by an
invocation must be present exactly; an equal-name/different-version entry does
not bind. Additional well-formed entries are allowed and ignored.

Source keys must equal the complete set of Plan source IDs exactly; missing and
extra IDs fail. A top-level injected source that is itself a Dask collection
fails. Concrete source containers are opaque and must not be traversed for
hidden dependencies.

Every invocation must resolve to option-free `local`, and every operation
referenced by an invocation must have no resource declarations because this
experiment selects no local resource semantics. Unused well-formed registry
entries and unused operation definitions do not create work and are not
rejected for unused resource declarations.

Graph construction must be independent of Plan tuple order: a consumer may
precede its producer in stored invocations or edges. Build dependencies
recursively with memoization from validated input references rather than
introducing a second readiness graph.

The invocation wrapper rechecks its captured policy immediately before calling
the implementation. Signature incompatibility, implementation exceptions,
result mapping access/copy failures, and exact output-name mismatch are
execution-time failures carrying invocation ID, operation identity, and their
original `Exception` cause. Do not catch `BaseException`. Returned values
remain ordinary ephemeral Python/Dask values; logical artifact kinds are not
runtime Python type assertions.

### Dask and packaging boundary

Use Dask Delayed only. Do not import `dask.distributed`, create a `Client`, use
Futures, define scheduler plugins, or select a named worker executor. The
ordinary `ass_flow` import and all planning-only behavior must remain usable
without Dask installed.

Core/evidence review first reaches provisional technical acceptance using the
installed Dask 2026.7.1. Only then may packaging add an optional
`dask==2026.7.1` extra and may `requirements-dev.txt` select it. Final
acceptance follows clean-environment and full-composition verification.
Rejection leaves both packaging files unchanged. Dask must not become an
unconditional runtime dependency of the planning package. Installed metadata
supports Python 3.10+, but the current environment tests Python 3.14.6 only.

`local` is the only Plan policy admitted and the only tested compute recipe;
it is not an enforceable placement property of a returned Delayed collection.
The lowerer performs no scheduling and does not infer ambient scheduler state.
Acceptance uses `dask.compute(..., scheduler="synchronous",
optimize_graph=False)`. If enforced local placement is required, this
Delayed-only surface is insufficient and the experiment stops.

The raw graph must expose the invocation mapping before optimization. Evidence
also computes under installed default optimization and with
`optimization.fuse.delayed=True`, recording observed keys and whether authored
invocation boundaries disappear. If the desired contract requires keys to
survive ordinary optimization, their disappearance falsifies the hypothesis;
do not add private anti-fusion machinery. This option-free local spike emits no
routing annotation and makes no annotation-survival claim. Live handles and
cancellation remain for the separate Delayed/Futures comparison.

### Acceptance evidence

- A simulator-free graph includes branching, fan-in, shuffled invocation/edge
  tuple order, a scalar source and predecessor binding, and a collection mixing
  source and predecessor references in intentionally significant order. It
  computes the expected result from injected values and explicit callables.
- The graph also includes a multi-output invocation, aliased top-level names,
  nested list/dict configuration proving fresh per-wrapper thawing, an orphan
  invocation, and a zero-output invocation. Tests distinguish computing named
  output closure from explicitly computing all invocation tasks.
- Every authored invocation has exactly one pre-optimization wrapper and one
  distinct actual Dask-key mapping; no wrapper is created from an edge or flow
  boundary. Aliased outputs reuse one projection.
- Lower the same Plan twice with different source values and/or
  implementations, compute roots from both lowerings in one `dask.compute`,
  and obtain both correct distinct results without key collision.
- Explicit per-invocation counters prove one wrapper evaluation within one
  merged compute. Separate compute calls are documented to re-execute.
- Raw, installed-default-optimization, and forced-fusion observations record
  the executed keys and whether invocation task boundaries survive.
- A nonexistent/poison authoring module identity and refusing decorated bodies
  prove that only explicitly registered implementations run.
- A strange but valid runtime output value proves the lowerer adds no artifact
  kind/Python type assertion. A top-level Dask collection source is rejected.
- Missing/extra source bindings, malformed registry keys/values, missing exact
  operation versions, unsupported policy/options/resources, invalid result
  shape, missing/extra result names, mapping access failures, and implementation
  exceptions cover the complete attributable refusal matrix.
- Lowering performs no filesystem I/O, address resolution, codec execution,
  publication, materialization, dynamic replanning, retry, persistence, or
  distributed scheduling.
- Existing 63 component tests, focused lowering tests, root integration, and
  full composition pass. Changed Python compiles and diff checks remain clean.
- After provisional technical acceptance, build the wheel with Dask only in
  optional metadata. Install it with `--no-deps` into an isolated environment
  without Dask; `import ass_flow` and the planning-only characterization path
  succeed, while explicit experimental-module use fails with a short
  optional-dependency message.
- Python 3.10 compatibility receives static/package-metadata inspection only
  unless a real 3.10 interpreter becomes available. No runtime-tested claim is
  made from the Python 3.14.6 evidence.
- The implementation states that Delayed does not establish enforced
  placement, process/distributed serialization, optimization invariance, live
  handles, cancellation, retries, persistence, side-effect safety, or
  cross-compute exactly-once behavior.

### Files and delegation

The intended implementation scope is limited to:

- `ass-flow/src/ass_flow/experimental/` for the lowering experiment;
- one focused component test module and one simulator-free example;
- `ass-flow/pyproject.toml` and root `requirements-dev.txt` only after
  provisional technical acceptance, and only for the exact optional Dask
  dependency selected above;
- the local README, ontology, planning/implementation trackers, docs index, and
  architecture ledger where demonstrated evidence changes their claims.

Core planner/model/authoring changes require a stop and review unless a small
source defect blocks the experiment. Root OTA/PVT declarations and sibling
component source remain unchanged.

Implementation is delegated sequentially:

1. a fresh Codex high architecture reviewer challenges this work order before
   code is assigned;
2. `local-dask-core` implements the experimental lowering and focused tests;
3. `local-dask-evidence` adds the runnable simulator-free example and updates
   documentation only after the core contract is stable;
4. `local-dask-review` independently reviews the complete diff, execution
   boundary, packaging, and evidence.

The coordinating session owns work-order correction, commits, prompts,
integration decisions, independent verification, tracker state, and final
scope review.

### Stop and completion rules

Stop instead of broadening if the experiment requires executing decorated
authoring callables implicitly, mutating Plan IR, storing Dask handles in Plan
data, resolving source addresses, implementing codecs, inferring a scheduler
from ambient state, accepting non-local policy, materializing outputs, adding a
second readiness graph, using Distributed/Futures, implementing cancellation,
or adding LSF/durable attempt behavior.

Also stop and record the hypothesis as falsified or narrowed if correctness
requires stable Dask keys across lowerings, tokenizing runtime values or
callables as identity, implicit authored-callable/module access, scheduler
enforcement by the lowerer, private Dask graph APIs, global anti-fusion controls
hidden from callers, attaching orphan work to named outputs implicitly, or core
Plan changes. On falsification, do not add the optional dependency or authorize
`submit(...)`.

The work order completes only when the bounded lowering and refusal evidence
pass, an independent high review accepts the identity/authority boundary, and
the component/root composition remains green. Completion may authorize a
separate Delayed/Futures comparison work order. It does not authorize a public
`submit(...)` or remote execution.

**Pre-handoff review:** Accepted on 2026-08-03 after revision. The first
Codex-high review rejected repeat-stable Dask keys because independently bound
graphs with equal keys merged to the wrong value, and required explicit
orphan/zero-output roots, tuple-order independence, fusion observations,
ontology treatment, and non-circular packaging gates. The corrected contract
uses fresh per-lowering namespaces and received `ACCEPT`.

**Completion review:** Accepted on 2026-08-03. The delegated core and evidence
passes produced 24 focused and 87 total ASS Flow tests, deterministic reuse of
the public characterization Plan, and an optional-only Dask wheel gate. A fresh
Codex-high full-diff review found no actionable defect and returned `ACCEPT`
after independently probing key separation, default/forced fusion, ordering,
source-I/O refusal, import isolation, wheel contents, and ontology scope. The
coordinating session passed the complete 87/45/77/28/17 composition matrix,
repeat example, compilation, isolated no-Dask installation, and diff/scope
checks. The bounded hypothesis is accepted; `submit(...)`, Futures/Distributed,
LSF, placement enforcement, and general execution remain unauthorized.
