# ASS Flow implementation tracker

## Status

**Phase:** Phase 2A collection-valued artifact inputs complete; Phase 2B pending

**Authorized slice:** inspectable static planning only

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
| P2B | Explicit stable authored identity | pending | Authorized in `PLANNING.md`; no key API or identity redesign implemented in Phase 2A |

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
- An explicit `submit(...)` stub that refuses execution.

## Inactive historical material

- sequential-flow editing convenience is inactive historical
  [archive material](docs/archive/sequential-flow-convenience.md), not a work
  item or backlog;

## Explicit runtime stubs and exclusions

- `submit(...)` and executor integration: `NotImplementedError` boundary;
- Dask and LSF lowering: deferred;
- retries, attempts, recovery, and durable publication: deferred;
- dynamic or result-dependent replanning: deferred;
- plugins and declarative flow configuration: deferred;

## Later authorized semantics

- explicit authored keys remain pending as Phase 2B in `PLANNING.md`; Phase 2A
  does not add or alter authored identity behavior.

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

## Findings and changes to the plan

- **Independent scope review — accept the bounded core.** The 1,118-line model
  remains immutable contract/IR values, structured graph validation, and
  deterministic serialization; the 820-line authoring layer remains public
  declarations, explicit scoped capture with rollback, binding checks, and the
  refusing `submit(...)` boundary. Their imports and behavior introduce no
  scheduler, transport, retry, persistence, plugin, publication, or execution
  machinery. No evidence-backed removable production subsystem or concrete
  blocker was found; line count alone does not justify weakening the explicit
  invariants.
- Authored-order IDs are deterministic reconstructions, not content-addressed
  identities: inserting earlier graph nodes renumbers later sources,
  invocations, edges, and boundaries. Name-keyed declaration order is now
  canonicalized, so semantically identical input/config/output mappings produce
  identical normalized data and edge IDs. Identity stability across graph
  insertion remains a deliberate later design question, not a hidden promise.
- Operation bodies are proven unexecuted by the runnable example's
  unconditional failure bodies, but arbitrary Python flow bodies do execute to
  author the graph and cannot be proven side-effect-free by this API. Flow-body
  purity remains an authored discipline, not an enforced invariant.
- Phase 2A demonstrates direct static collection fan-in without encoding
  references as configuration: a collection binding preserves authored member
  order and produces correspondingly positioned dependency edges. The
  characterization example intentionally retains its Phase 1 fixed three-input
  reducer until the authorized Phase 3 update.
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
