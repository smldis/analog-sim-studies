# OTA PVT Plan Reference planning tracker

## Work-order identity and source hierarchy

**Work-order ID:** `ASS-FLOW-WO-2026-08-03-OTA-PVT-PLAN`

**Status:** active until its acceptance evidence is reviewed, a stop condition
is reached, or the user withdraws it.

The controlling architectural seed is the human-curated dialecticH graduation:

- source run: `20260802-095704`;
- graduation: `20260802-214949-a68fd038`;
- graduated `main.md` SHA-256:
  `cd5c54e288bc5008b316650ec2a7a8920c645678ec4acf25f3d499e9fd69efc7`;
- graduated `objective.md` SHA-256:
  `defb4d4885fbb439c6966cfb8efaba57bbee6588543d40ff74785b94fb69be80`.

The graduated files under `.dialecticH/runs/20260802-095704/graduation/` are
the exact continuation baseline. `docs/vision/ass-flow-rebuild-main.md` is an
older pre-graduation seed and must not be substituted for the graduated main.
`MANIFESTO.md` and the current root/child ontologies govern the repository;
`ass-flow/PLANNING.md` records the later user authorization that turned the
graduation's non-authorized planning candidate into bounded implementation;
`ass-flow/IMPLEMENTATION.md` records the resulting evidence.

The attempted continuation run `20260802-220447` crashed before producing a
Judge decision. Its partial proposals are not authority for this work order.

## Authority and decision

On 2026-08-03 the user authorized continued development after trying only the
existing ASS Flow characterization example. That result is smoke-test evidence,
not acceptance of the larger architecture. This phase therefore introduces one
representative, non-executing OTA/PVT plan before considering any executor
lowering.

A fresh Codex high-reasoning review inspected the root and all four child
contracts. It recommended a root-owned reference because the root already owns
cross-unit composition, while ASS Flow deliberately owns no analog-domain
meaning and a single reference does not justify a new permanent component.

**Decision:** implement one bounded `OTA PVT Plan Reference` under
`docs/reference/ota-pvt-plan/` and verify it through root integration tests.

**Status:** authorized for plan-only implementation.

The graduated main's initial planning work order has now been implemented and
promoted as the `ass-flow` prototype. Its sequential convenience hypothesis was
later explicitly archived by the user. Those later reviewed directions
supersede that one candidate acceptance example without altering the main's
generic-planner, explicit-plan, no-hidden-runtime boundaries.

## Decision question

Can ordinary Python plus the current ASS Flow Plan IR express a small but
realistic, fully inspectable OTA/PVT strategy across preparation,
canonicalization, structural decomposition, simulation, measurement, and
evaluation boundaries without executing an operation or inventing a second
graph model?

## Evidence selection

Current evidence consists of the static planner's component tests and one
characterization example. The user has tried only that example, so it is not
evidence that a domain-sized cross-unit graph is adequate or that executor
lowering is ready.

This reference is preferred over immediate local/Dask lowering because it is
the smaller reversible observation: it exercises the current plan against real
preparation, canonicalization, and decomposition boundaries while adding no
runtime authority. It should reveal whether the next problem is still Plan IR
expressiveness or, as expected, explicit artifact/adapter contracts. Its cost
is one small Python declaration, four text fixtures, focused integration tests,
and documentation. It requires no simulator, scheduler, farm access, network,
paid service, mutable external state, or generated evidence.

Prerequisites are the committed four-child composition at `ce0ce5c`, the
current ASS Flow public planning API, and the existing sibling public contracts.
If implementation requires changing any prerequisite contract, the work order
stops instead of expanding.

## Ownership boundary

The composition root owns this single reference because it combines meanings
from multiple child units. The following alternatives remain rejected:

- `ass-flow/`: would incorrectly give a generic planner OTA, PVT, simulator,
  measurement, or study-lifecycle meaning;
- a new direct child: would promote one architectural probe into a component
  before it has a reusable API or independently useful capability;
- a general root example framework: is unnecessary for one named reference and
  conflicts with the root's exclusion of an example catalog.

Revisit the boundary only if later evidence produces reusable adapter or
OTA-study vocabulary.

## Authored PVT points

The graph uses three ordered sentinel points. They are architectural probes,
not exhaustive verification coverage or accepted product requirements.

| Key | Process | Supply | Temperature |
| --- | --- | ---: | ---: |
| `tt_1v80_27c` | `tt` | 1.80 V | 27 C |
| `ss_1v62_125c` | `ss` | 1.62 V | 125 C |
| `ff_1v98_m40c` | `ff` | 1.98 V | -40 C |

The Python plan and the versioned Sidecar input fixture must contain the same
ordered values. A test guards against drift; neither location becomes a shared
PVT schema.

## Static graph

All definitions use version `"1"`, and every flow boundary and invocation uses
an explicit authored key.

For every PVT point `p`:

```text
base directory --\
                  prepare_run[p] --> canonicalize_deck[p] --> decompose_ota[p] --\
edit file -------/          \                                                    \
                            +--> simulate_ac[p] --> measure_ac[p] ----------------+--> evaluate_pvt
measurement definition ------------------------------/                           /
specification limits ------------------------------------------------------------/
```

The final evaluation receives ordered collections of point measurements and
point decompositions in the declared PVT order. Decomposition is independent
structural context for evaluation, not a simulator prerequisite.

| Operation identity | Inputs | Configuration | Output kind | Contract boundary |
| --- | --- | --- | --- | --- |
| `reference.ota_pvt.prepare_run@1` | `base: sidecar-base-directory`, `edits: sidecar-edit-file` | `point_id`, `param_set`, `process`, `vdd_v`, `temp_c` | `prepared-simulation-directory` | Declared plan stub corresponding conceptually to `sidecar-render`, edit loading, parameter selection, and `render_job`; no ASS Flow adapter currently accepts these bindings. |
| `reference.ota_pvt.canonicalize_deck@1` | `run: prepared-simulation-directory` | `deck_relpath="ota_ac.cir"`, `spice_format="ngspice"`, `top_name="ota_pvt"` | `canonical-netlist` | Declared plan stub corresponding to `spice_canonical.canonical_netlist.from_file`; no adapter locates a planned deck or publishes a durable canonical artifact. |
| `reference.ota_pvt.decompose_ota@1` | `canonical: canonical-netlist` | `circuit_name="ota_core"`, `vdd_nets=["vdd"]`, `vss_nets=["vss"]`, `max_level=4`, `suppress_false_stacks=true` | `ota-functional-decomposition` | Declared plan stub corresponding to circuit selection, `decompose`, and optional suppression; no combined adapter or serialized tag artifact exists. |
| `reference.ota_pvt.simulate_ac@1` | `run: prepared-simulation-directory` | `point_id`, `process`, `vdd_v`, `temp_c`, `simulator_profile="ngspice-ac"`, `analysis="ac"` | `simulator-raw-results` | Pure declared stub; no simulator adapter or runtime exists. Descriptive resource requests make no scheduling claim. |
| `reference.ota_pvt.measure_ac@1` | `raw: simulator-raw-results`, `definition: ota-measurement-definition` | `point_id` | `ota-point-measurements` | Declared stub for gain, gain-bandwidth, and phase-margin extraction; no waveform reader or measurement implementation exists. |
| `reference.ota_pvt.evaluate_pvt@1` | `measurements: artifacts("ota-point-measurements")`, `decompositions: artifacts("ota-functional-decomposition")`, `limits: ota-specification-limits` | ordered `point_ids` | `ota-pvt-evaluation` | Declared evaluation stub; its planned output is neither published evidence nor a study decision. |

The artifact kinds are local declared labels. ASS Flow validates kind equality;
it does not define their formats, schema versions, locations, checksums, or
provenance.

## Expected normalized shape

- four external sources: base directory, Sidecar edit file, measurement
  definition, and specification limits;
- six operation definitions;
- two flow definitions: `reference.ota_pvt.point@1` and
  `reference.ota_pvt.study@1`;
- four keyed flow boundaries: one study plus three point flows;
- sixteen keyed invocations: five per point plus one evaluation;
- eighteen operation-output dependency edges: four within each point plus
  three positioned measurement and three positioned decomposition fan-in
  edges;
- sixteen named Plan outputs: five per point plus the final evaluation.

Scalar external inputs are source bindings, not dependency-edge records in the
current IR. The tests must preserve that distinction.

## What this slice may prove

- Python can author this domain-specific static strategy while ASS Flow remains
  generic.
- A fixed ordered tuple can expand into inspectable nested PVT branches.
- Preparation can fork into independent structural and simulation paths.
- Ordered collection fan-in preserves declared PVT ordering.
- Artifact kinds, versions, configuration, policies, resources, keys, and
  named outputs survive normalization and inspection.
- Rebuilding the same authored inputs yields identical Plan data and JSON.
- Planning succeeds without executing any declared operation body.
- Current Plan IR is expressive enough for this static graph.

## What this slice may not claim

- execution of any operation or existence of an ASS Flow adapter for a sibling;
- successful materialization, deck discovery, parsing, simulation, measurement,
  evaluation, or artifact publication;
- portable serialization for `CanonicalNetlist`, `Circuit`, or `BlockTag`;
- file, schema, checksum, or semantic validation from an artifact-kind string;
- cache/content identity, staleness, resume, retry, attempts, atomic
  publication, provenance, evidence promotion, or durable study state;
- exhaustive PVT coverage or behavioral proof from structural decomposition;
- executor keys, cache keys, or complete provenance from authored Plan keys and
  version labels.

## Planned files

The implementation pass may add only this bounded material:

- `ota_pvt_plan.py`: artifact declarations, six refusing operations, two
  flows, the ordered PVT tuple, and `build_plan()`;
- `inputs/base/ota_ac.cir`: a small versioned OTA AC text fixture;
- `inputs/pvt_edits.py`: typed Sidecar edit declarations and the three named
  parameter sets;
- `inputs/measurement_definition.json`: proposed metric names and units;
- `inputs/spec_limits.json`: explicitly provisional reference limits;
- `integration-tests/test_ota_pvt_plan_reference.py`: structural, validation,
  determinism, fixture, and no-execution evidence;
- links/status wording in root `README.md`, `docs/index.md`, and `ONTOLOGY.md`.

`unit.toml`, `requirements-dev.txt`, all child packaging and ontologies, ASS
Flow source, and the archived sequential-flow convenience remain unchanged.

## Delegated and reserved choices

The implementation agent may choose private helper names, immutable local data
structures for the PVT tuple, fixture formatting, and how to organize focused
test helpers, provided the exact public Plan shape and file boundary above stay
unchanged. It may narrow implementation when less code proves the same
observation and may add proportionate diagnostics.

Reserved for coordinating review are any change to a public child API, artifact
kind or graph cardinality, component ownership, ontology scope, sibling adapter
semantics, execution/lowering design, or the claim supported by the evidence.
The agent may report such a need but may not decide or implement it.

## Acceptance matrix

| Check | Required evidence | Must not imply |
| --- | --- | --- |
| Boundary | Reference remains in root docs; four children remain unchanged | New component or root example framework |
| PVT resolution | Exact ordered three-point tuple appears in invocation configuration | Exhaustive coverage |
| Static shape | 4 sources, 6 operations, 2 flows, 4 boundaries, 16 invocations, 18 edges, 16 outputs | Runtime graph |
| Branching | Each preparation output feeds canonicalization and simulation | Execution concurrency |
| Fan-in | Both evaluation collections retain point order and positions 0 through 2 | Runtime discovery |
| Contract mapping | Docs name real sibling APIs and every missing adaptation seam | Existing adapter |
| Determinism | Two builds have identical data, JSON, identities, bindings, and edges | Cache identity |
| Keys | Every flow/call is keyed and keyed operation edges are stable | Attempt/executor identity |
| Validation | Plan validates; focused malformed kind/config/order cases fail | File/schema validation |
| No execution | Refusing bodies remain uncalled; `submit` still refuses | Simulator or sibling invocation |
| Fixtures | Source URIs resolve to committed paths; PVT edit values match authored points | Successful preparation or parsing |
| Scope | No executor, filesystem publication, waveform parser, cache, provenance, or study state | Partial runtime |
| Composition | Existing child and root verification remains the test path | New packaging system |

Do not commit golden Plan JSON. Repeated construction and structural assertions
are the source-of-truth evidence.

## Stop conditions

Stop and report instead of broadening this slice if implementation requires:

- calling Sidecar Edits, `from_file`, `decompose`, a simulator, or measurements
  while building the Plan;
- executing an operation body to determine the graph;
- durable object serialization, output directories, temporary files, attempts,
  publication, caches, or provenance;
- changes to a sibling's public contract or ASS Flow's Plan IR;
- a shared artifact-schema registry;
- reusable OTA-study APIs, sequential-flow convenience, an executor, or a
  lowering interface.

Each is a separate ontology and authorization decision.

## Commit boundaries

1. `docs: plan root-owned OTA PVT reference`
   records this boundary, graph, trackers, acceptance criteria, exclusions, and
   the component-owned review of every graduated ASS Flow research section.
2. `feat: add plan-only OTA PVT reference`
   adds the refusing workflow declarations, inputs, integration evidence, and
   root documentation updates.
3. A focused corrective commit is allowed only if independent review exposes a
   real defect; verification-log churn alone does not justify one.

## Completion rule

This authorization completes when the exact static reference and fixtures are
committed, focused and full-composition checks pass, an independent review
confirms the no-execution boundary, and the implementation tracker records the
observations and next decision. Obtaining that evidence ends this work order;
it does not authorize executor lowering or any follow-on repair.
