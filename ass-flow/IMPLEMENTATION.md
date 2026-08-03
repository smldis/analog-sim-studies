# ASS Flow implementation tracker

## Status

**Phase:** explicit materialized-source handoff complete

**Authorized slice:** static planning plus materialized-source declarations only

**Component boundary:** declared direct child at `ass-flow/`

**Development state:** `prototype`

## Work items

| ID | Component | Owner | State | Evidence |
| --- | --- | --- | --- | --- |
| C1 | Immutable contracts, policies, references, and Plan IR | Codex high agent (`ass-flow-core-ir`) | complete | 9 focused tests pass; independent scope review accepted the boundary |
| C2 | `@operation`, `@flow`, explicit `plan(...)`, and nested flow capture | Codex high agent (`ass-flow-authoring`) | complete | 18 focused C1+C2 tests pass, including canonical mapping order |
| C3 | Acceptance example and adversarial validation coverage | Codex high agent (`ass-flow-acceptance`) | complete | Runnable example plus 7 acceptance tests pass |
| I1 | Cross-component integration and API review | Coordinating session | complete | All material source, tests, example, and delegated reports inspected |
| I2 | Focused and repository-level verification | Coordinating session | complete | 25 prototype tests plus all declared repository tests pass |
| I3 | Historical prototype conclusion before user promotion direction | Coordinating session | complete | Accepted as runnable evidence; its location recommendation was superseded by the authorized Phase 1 plan |

## Phase 1 promotion work

| ID | Work | State | Evidence |
| --- | --- | --- | --- |
| P1.1 | Move the complete tracked prototype to `ass-flow/` | complete | Source, tests, example, README, and both trackers retain their content under the direct-child path; unchanged implementation/test/example blobs match the committed originals |
| P1.2 | Establish the child boundary | complete | Local ontology, inherited/narrowed agent guidance, unit manifest, Python 3.10+ `ass-flow` packaging, and composable docs contract added |
| P1.3 | Own test configuration in packaging | complete | `pyproject.toml` carries the former Python path and test-path settings; `pytest.ini` removed |
| P1.4 | Archive sequential convenience | complete | [Inactive archive record](docs/archive/sequential-flow-convenience.md) states origin, user status/date, rationale, excluded APIs, and reactivation trigger |
| P1.5 | Promote root composition contracts | complete | Root unit declaration, developer requirements, README, ontology, and four-child integration expectation updated without adding runtime authority |
| P1.6 | Verify the promoted slice | complete | 25 focused tests pass; four-child tree and full composed tests pass; wheel builds; aggregate docs discovery/staging includes ASS Flow; reference scans are clean |

## Phase 2 core graph semantics

| ID | Work | State | Evidence |
| --- | --- | --- | --- |
| P2A | Collection-valued artifact inputs | complete | Public `artifacts(kind)` produces required ordered non-empty collection contracts; immutable bindings retain source/output artifact references in member order; every member has a positioned dependency edge; authoring and Plan validation reject invalid values and malformed positions; all 36 component tests pass |
| P2B | Explicit stable authored identity | complete | Immutable operation policy/key views and keyed flow views preserve scoped authored keys in Plan IR; duplicate namespaces and rollback are validated; keyed IDs and fully keyed connecting edges survive unrelated unkeyed sibling insertion; all 49 component tests pass |

## Phase 3 acceptance and boundary review

| ID | Work | State | Evidence |
| --- | --- | --- | --- |
| P3.1 | Public characterization example | complete | The reducer declares `artifacts("corner-metrics")`; the root, per-corner flows, corner operations, and summary call use explicit scoped keys; nominal-only planning binds one real member and planning with extremes binds three distinct members |
| P3.2 | Adversarial acceptance coverage | complete | Acceptance tests verify collection binding/edge order for one and three members, visible scoped keys, fully keyed connecting edges, repeat data/JSON identity, canonical stdout, and operation-body non-execution while retaining rollback, foreign-handle, no-runtime, mapping-canonicalization, and refusal coverage |
| P3.3 | Independent source-boundary review | complete | Complete committed `src/ass_flow` inspection found immutable data/validation, explicit scoped graph capture, and the refusing `submit(...)` boundary; no execution, scheduler, transport, persistence, retry, publication, plugin, cache, or dynamic-replanning authority was found |

## Phase 4 explicit materialized-source handoff

| ID | Work | Owner | State | Evidence |
| --- | --- | --- | --- | --- |
| P4.1 | Freeze corrected three-value boundary and schema-2 acceptance contract | Coordinating session plus Codex high (`artifact-handoff-plan-review`) | complete | Exact graduated main recheck rejected mandatory publication on ordinary outputs; `PLANNING.md` records the corrected external-artifact/ephemeral-output split |
| P4.2 | Add immutable codec, address, materialization, and value-class model | Codex high (`artifact-handoff-core`) | complete | Schema-2 model records canonical codec/options, opaque address, materialization/access assumptions, fixed artifact/ephemeral reference classes, and nullable output capability; the final 63-test component suite passes |
| P4.3 | Add strict authoring surface and focused component evidence | Codex high (`artifact-handoff-core`) | complete | Public `address`, `codec`, `materialization`, `materializable`, and strict keyword-only source contract are covered; legacy kind-only sources fail and capable outputs remain ephemeral; the final 63-test component suite passes |
| P4.4 | Adapt OTA/PVT sources and cross-unit evidence | Codex high (`artifact-handoff-evidence`) | implemented and verified | 10 focused tests prove four exact repository-relative source representations, schema 2, nullable output capability, artifact source references, 18 ephemeral operation-output edges, an ephemeral final evaluation, unchanged version-1 definitions/topology/IDs, canonical repetition, legacy/runtime refusal, and no-I/O/import boundaries |
| P4.5 | Independent source/boundary review | Codex high (`artifact-handoff-review`) | complete | Full-diff review found one structured-validation leak for a malformed source artifact; the core owner added the defensive guard and regression, and independent re-review replaced `REVISE` with `ACCEPT` |
| P4.6 | Full verification and completion decision | Coordinating session | complete | Final verification passed 63 component, 10 focused OTA/PVT, 17 root integration, and full composition 63/45/77/28/17; both examples emitted valid schema-2 JSON, changed Python compiled, the wheel built, and `git diff --check` passed |

## File ownership during delegation

The agents share one worktree. Each task prompt assigns exact files. Agents
must preserve the pre-existing user changes to `OBJECTIVE.md`, `.dialecticH/`,
`IDEAS_PROMPT.md`, and `MANIFESTO_orphans.md`, and must not edit the live
dialecticH run evidence.

## Implemented behavior

- Frozen executor-neutral contract, policy, identity, reference, invocation,
  edge, nested-flow-boundary, and Plan values.
- Structured Plan validation and deterministic plain-data/JSON inspection.
- Immutable `@operation` and `@flow` definitions, explicit `plan(...)` scope,
  nested boundary capture, early binding validation, and stable repeated-plan
  IDs.
- Required ordered collection artifact inputs through `artifacts(kind)`, with
  explicit collection contract/binding cardinality and one positioned
  dependency edge per member.
- Optional authored keys on immutable operation and flow call views, with one
  operation/flow namespace per containing boundary, stable scoped Plan IDs,
  stable fully keyed connecting edges, and explicit canonical IR fields.
- Schema-2 data-only declarations for external source addresses, codec
  identity/options, materialization/access assumptions, artifact source
  reference class, ephemeral output reference class, and optional output
  materialization capability metadata.
- Strict external-source authoring through `input_artifact(..., artifact=...,
  materialized_as=...)`; the former kind-only form is not retained.
- An explicit `submit(...)` stub that refuses execution.

## Inactive historical material

- sequential-flow editing convenience is inactive historical
  [archive material](docs/archive/sequential-flow-convenience.md), not a work
  item or backlog;

## Explicit runtime stubs and exclusions

- `submit(...)` and executor integration: `NotImplementedError` boundary;
- Dask and LSF lowering: deferred;
- retries, attempts, recovery, and durable publication: deferred;
- address resolution, codec execution, real access checking, materialized
  operation outputs, and runtime artifact values: deferred outside ASS Flow;
- dynamic or result-dependent replanning: deferred;
- plugins and declarative flow configuration: deferred;

## Verification log

- C1 (2026-08-03): `python -m pytest -q` in the prototype passed 9 tests;
  `python -m py_compile src/ass_flow/model.py tests/test_model.py` also passed.
- C2 (2026-08-03): focused C1+C2 verification passed 17 tests; authoring and
  public API modules plus both test modules passed `python -m py_compile`.
- C3 (2026-08-03): the first review pass exposed one declaration-order
  determinism defect. C2 canonicalized name-keyed declarations and added a
  regression; the acceptance test now passes normally. The example's printed
  Plan JSON passed `python -m json.tool`, and all C1-C3 source and test modules
  passed `python -m py_compile`.
- Integration (2026-08-03): the final prototype suite passed all 25 tests. The
  repository composition test initially stopped because the current Python
  environment did not have the sibling packages installed; rerunning with the
  three existing child `src` directories on `PYTHONPATH` passed 45
  netlist-decomposition, 77 sidecar-edits, 28 spice-canonical, and 7 root
  integration tests.
- Phase 1 promotion (2026-08-03): `python -m pytest -q` from `ass-flow/`
  passed 25 tests, and the unchanged characterization example emitted valid
  JSON with `PYTHONPATH=src`. `python composition.py tree` reported four
  direct children including `ass-flow`.
- Phase 1 composition (2026-08-03): with absolute source-checkout paths for all
  four children on `PYTHONPATH`, `python composition.py test` passed 25
  ass-flow, 45 netlist-decomposition, 77 sidecar-edits, 28 spice-canonical,
  and 7 root integration tests. The root integration suite also passed 7 tests
  independently with child source paths supplied.
- Phase 1 packaging and docs (2026-08-03): `python -m build --wheel` produced
  `ass_flow-0.1.0-py3-none-any.whl`. Aggregate docs discovery/staging linked
  all four child docs, including `children/ass-flow/docs/index.md`. A full HTML
  build was not run because Sphinx is not installed in this environment.
- Phase 1 scope check (2026-08-03): retained implementation, tests, and example
  files match their committed prototype blobs; the Phase 2 plan section retains
  SHA-256 `a04bf2aedfc72e3278cfc0dda2ffd730c609b53cf5ac3081764629f9104444a9`.
- Phase 2A (2026-08-03): the complete component suite passed 36 tests, including
  ordered collection fan-in, positioned edges for external-source and
  operation-output members, deterministic repeat planning/JSON, early authoring
  rejection, malformed member-position/source matching, and scalar regressions.
  All package source and component test modules passed `python -m py_compile`.
- Phase 2A composition (2026-08-03): the full four-child composition passed 36
  ASS Flow, 45 netlist-decomposition, 77 sidecar-edits, 28 spice-canonical, and
  7 root integration tests with the child source checkouts on `PYTHONPATH`.
- Phase 2B (2026-08-03): the complete component suite passed 49 tests. Focused
  evidence covers policy/key option composition in both orders, keyed nested
  flows, canonical repeat planning, cross-edit keyed invocation/boundary/edge
  stability, scalar and collection edge behavior, scoped duplicate rejection,
  distinct-scope reuse, complete operation/flow rollback, early key syntax
  rejection, and independent Plan validation. All package and test modules
  passed `python -m py_compile`, and `git diff --check` passed.
- Phase 2B composition (2026-08-03): the full four-child composition passed 49
  ASS Flow, 45 netlist-decomposition, 77 sidecar-edits, 28 spice-canonical, and
  7 root integration tests with the child source checkouts on `PYTHONPATH`.
- Phase 3 focused evidence (2026-08-03): the updated acceptance file passed 10
  parametrized cases and the complete component suite passed 52 tests. Both
  nominal-only and nominal-plus-extremes plans validate and reconstruct
  identical plain data and canonical JSON without executing operation bodies.
- Phase 3 component verification (2026-08-03): characterization stdout passed
  `python -m json.tool`; every package, test, and example module passed
  `py_compile`; and `python -m build --wheel` produced
  `ass_flow-0.1.0-py3-none-any.whl`.
- Phase 3 composition (2026-08-03): the full four-child composition passed 52
  ASS Flow, 45 netlist-decomposition, 77 sidecar-edits, 28 spice-canonical, and
  7 root integration tests with all child source paths on `PYTHONPATH`.
- Phase 3 docs (2026-08-03): aggregate staging included ASS Flow's current
  index and inactive archive record and linked
  `children/ass-flow/docs/index.md`. A full Sphinx build was unavailable because
  Sphinx is not installed in the verification environment.
- Phase 3 scope (2026-08-03): `git diff --check` passed; `ass-flow/src` has no
  review changes; and sequential convenience has no occurrence in active
  source, tests, or example. Remaining mentions are inactive archive/provenance
  statements and explicit exclusions, not an API or backlog.
- Phase 4 core verification (2026-08-03): the final ASS Flow suite passed 63
  tests. Coverage includes immutable/canonical source materialization data,
  strict source authoring and legacy rejection, source/output value classes,
  nullable output capability, malformed Plan rejection, and unchanged graph
  semantics. All changed package, component-test, example, OTA/PVT, and focused
  integration Python modules passed `py_compile`.
- Phase 4 OTA/PVT evidence (2026-08-03): 10 focused tests passed. The schema-2
  reference retains 4 sources, 6 operations, 2 flows, 4 boundaries, 16
  invocations, 18 edges, and 16 outputs; pins the previous source, invocation,
  edge, and boundary IDs; declares exact directory-tree, Python-source/UTF-8,
  and JSON/UTF-8 source representations; and proves artifact source references,
  ephemeral operation-output edges/final output, canonical reconstruction,
  legacy rejection, refusing bodies/submit, and guarded no-I/O/import behavior.
- Phase 4 repository verification (2026-08-03): root integration passed 17
  tests with absolute source-checkout `PYTHONPATH`. Final composition passed 63
  ASS Flow, 45 Netlist Decomposition, 77 Sidecar Edits, 28 SPICE Canonical, and
  17 root integration tests. Both the characterization and OTA/PVT command
  outputs parsed as schema-2 JSON; their suites assert canonical repeated
  data/JSON. All changed Python compiled, the wheel built, and
  `git diff --check` passed.
- Phase 4 independent review (2026-08-03): a fresh Codex high full-diff review
  accepted the artifact/ephemeral discriminator and no-runtime boundary but
  first found one medium structured-validation defect: a malformed source
  artifact was recorded and then dereferenced, leaking `AttributeError`. The
  core owner guarded that path and added the `artifact=None` regression. The
  reviewer independently proved `invalid_source_artifact`, retained valid-kind
  checking, reran all 63 component tests, and replaced `REVISE` with `ACCEPT`.

## Findings and changes to the plan

- **Phase 3 independent scope review — accepted the then-bounded core.** Complete
  inspection of the committed source found immutable contract/IR values, structured
  graph validation, deterministic serialization, public declarations, explicit
  scoped capture with rollback, binding checks, and the refusing `submit(...)`
  boundary. Its imports and behavior introduce no
  scheduler, transport, retry, persistence, plugin, publication, or execution
  machinery. No accidental runtime authority or source defect was found, and no
  production-hardening subsystem is present.
- Authored keys are case-sensitive exact strings using the executor-neutral
  Plan-ID rule: an ASCII letter or digit followed by ASCII letters, digits,
  `.`, `_`, `:`, `/`, `@`, `+`, or `-`. A keyed invocation or boundary ID is
  `kind:key:<sha256>` over its kind, containing boundary ID (or root marker),
  and exact key. Keys share one operation/flow namespace only within that
  containing boundary. They are Plan identity, not cache keys, scheduler keys,
  attempts, sequential slots, or runtime authority.
- A connecting edge between two keyed invocations is `edge:key:<sha256>` over
  its source output reference, target invocation, target input, and scalar or
  collection-member position. Such edges do not consume the fallback edge
  counter. Edges involving an unkeyed invocation or external source retain
  deterministic authored-order counter IDs.
- Stability is scoped rather than absolute. A keyed node beneath an unkeyed
  enclosing flow can be only as stable as that counter-derived boundary ID;
  likewise an edge can be only as stable as its enclosing scopes and endpoint
  references. External source IDs and all unkeyed source, invocation, boundary,
  and fallback-edge IDs remain authored-order counters and may change when an
  earlier unkeyed sibling or source is inserted. A fully keyed subgraph under a
  stable keyed boundary retains its keyed nodes and connecting edges across an
  unrelated unkeyed sibling insertion.
- Operation bodies are proven unexecuted by the runnable example's
  unconditional failure bodies, but arbitrary Python flow bodies do execute to
  author the graph and cannot be proven side-effect-free by this API. Flow-body
  purity remains an authored discipline, not an enforced invariant.
- Phase 2A demonstrates direct static collection fan-in without encoding
  references as configuration: a collection binding preserves authored member
  order and produces correspondingly positioned dependency edges. Phase 3 now
  exercises that contract in the public characterization example for both one
  and three distinct members.
- Phase 4 implementation evidence distinguishes addressed external artifact
  sources from ephemeral operation-output references without changing graph
  identity. The OTA/PVT adaptation pins the prior IDs and keeps all output
  materialization capabilities null. The fresh independent source/boundary
  review accepted this data-only boundary after its one validation finding was
  corrected and reverified.
- **Historical conclusion (superseded).** The spike answered its decision
  question positively for static planning and initially recommended remaining
  outside `unit.toml` until a later boundary review. The user direction recorded
  below superseded that location recommendation. The sequential convenience is
  now inactive [archive material](docs/archive/sequential-flow-convenience.md);
  runtime work remains unauthorized.
- **Superseding direction (2026-08-03):** the user selected `ass-flow/` as the
  component's actual location and authorized continued core development. Phase
  1 promotes the tested code without changing its prototype maturity. Phase 2
  addresses collection fan-in and explicit stable authored keys. The sequential
  convenience idea is archived and removed from active development scope.

## Remaining limitations

- Planning is static. Flow bodies execute as ordinary authored Python, can have
  external side effects, and cannot branch on unavailable operation results.
- Collection inputs are required non-empty authored sequences; they do not add
  runtime discovery, dynamic graph expansion, or result-dependent replanning.
- Only keyed nodes under stable keyed enclosing boundaries, and edges between
  keyed invocations, have the demonstrated cross-edit identity promise. Unkeyed
  boundaries and calls, external sources, and fallback edges remain
  deterministic authored-order identities.
- Keys remain Plan identity only. No cache, scheduler, attempt, runtime,
  persistence, recovery, or sequential-editing semantics follow from them.
- Source address, codec, and access data are declarations only. ASS Flow does
  not resolve addresses, execute codecs, verify accessibility, publish values,
  materialize operation outputs, or represent runtime artifact values.
- The component remains a prototype and owns no execution, Dask/LSF lowering,
  retries, persistence, plugins, dynamic replanning, production hardening, or
  complete study lifecycle.
- The sequential convenience archive remains inactive historical provenance,
  not a backlog.

## Next decision question

The schema-2 source-handoff prerequisite is accepted. The next separately
authorized experiment may ask whether the normalized Plan IR lowers locally
through Dask without giving authoring hidden runtime authority. It must first
freeze executor ownership, identity-to-task binding, injected source decoding,
invocation-boundary visibility, local failure/cancellation behavior, and the
explicit exclusions for publication, durability, retries, and LSF.
