# ASS Flow planning spike

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

## Provisional location and status

The spike lives at `prototypes/ass-flow-planning/`. It is deliberately not
listed in the root `unit.toml`, has no public distribution contract, and does
not yet claim a permanent ontology boundary. If the evidence supports an
independently useful component, promotion into a declared child is a separate
review decision.

## User-directed narrowing

The graduated main proposed a sequential-flow editing helper as one acceptance
example. The user has explicitly deferred that separate convenience layer.
This spike therefore does **not** implement ordered slots, insertion, removal,
or substitution. Arbitrary Python composition is the only flow authoring model
in this slice.

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

The recommendation is to retain this directory as runnable design evidence and
not promote it into `unit.toml` or a permanent public package yet. Sequential
editing remains deferred by the user, and all runtime surfaces remain explicit
stubs or exclusions.
