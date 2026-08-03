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
