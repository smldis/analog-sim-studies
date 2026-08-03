# ASS Flow implementation tracker

## Status

**Phase:** component promotion authorized; agent plan ready

**Authorized slice:** inspectable static planning only

**Permanent component status:** undecided

## Work items

| ID | Component | Owner | State | Evidence |
| --- | --- | --- | --- | --- |
| C1 | Immutable contracts, policies, references, and Plan IR | Codex high agent (`ass-flow-core-ir`) | complete | 9 focused tests pass; independent scope review accepted the boundary |
| C2 | `@operation`, `@flow`, explicit `plan(...)`, and nested flow capture | Codex high agent (`ass-flow-authoring`) | complete | 18 focused C1+C2 tests pass, including canonical mapping order |
| C3 | Acceptance example and adversarial validation coverage | Codex high agent (`ass-flow-acceptance`) | complete | Runnable example plus 7 acceptance tests pass |
| I1 | Cross-component integration and API review | Coordinating session | complete | All material source, tests, example, and delegated reports inspected |
| I2 | Focused and repository-level verification | Coordinating session | complete | 25 prototype tests plus all declared repository tests pass |
| I3 | Prototype conclusion and promotion recommendation | Coordinating session | complete | Accept as runnable evidence; do not promote to a declared unit yet |

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
- An explicit `submit(...)` stub that refuses execution.

## Explicit stubs and deferrals

- sequential-flow editing convenience: deferred by the user;
- `submit(...)` and executor integration: `NotImplementedError` boundary;
- Dask and LSF lowering: deferred;
- retries, attempts, recovery, and durable publication: deferred;
- dynamic or result-dependent replanning: deferred;
- plugins and declarative flow configuration: deferred;
- distribution packaging and compatibility promises: deferred;
- permanent unit/ontology promotion: requires a later review.

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
- Artifact inputs are scalar, so genuinely dynamic collection fan-in is not
  expressible directly. The example uses an honest fixed three-input reducer;
  broader collection/reducer semantics remain deferred rather than simulated.
- **Conclusion — retain as evidence, do not promote yet.** The spike answers its
  decision question positively for static planning. It should remain outside
  `unit.toml` until a later review decides whether stable identity across graph
  edits and collection-valued fan-in belong in the same component. Sequential
  editing remains deferred by the user; runtime work remains unauthorized.
- **Superseding direction (2026-08-03):** the user selected `ass-flow/` as the
  component's actual location and authorized continued core development. Phase
  1 promotes the tested code without changing its prototype maturity. Phase 2
  addresses collection fan-in and explicit stable authored keys. The sequential
  convenience idea is archived and removed from active development scope.
