# OTA PVT Plan Reference implementation tracker

## Status

**Phase:** work order complete

**Follow-on:** schema-2 source-handoff adaptation complete and independently
accepted

**Authorized slice:** one root-owned, plan-only OTA/PVT reference

**Runtime status:** explicitly unimplemented

**Component impact:** none; the repository retains four direct children

## Work items

| ID | Work | State | Evidence |
| --- | --- | --- | --- |
| R1 | Freeze ownership, graph, acceptance criteria, and stop conditions | complete | `PLANNING.md`; independent Codex high architecture review |
| R2 | Add six refusing operation declarations, two keyed flows, three ordered points, and `build_plan()` | complete | Validated Plan has 6 version-1 operations, 2 version-1 flows, 4 keyed boundaries, 16 keyed invocations, 18 keyed dependency edges, and 16 outputs |
| R3 | Add small versioned input fixtures without executing them | complete | Four repository-relative source URIs exist; Sidecar loader accepts all typed edits and resolves the exact ordered point values |
| R4 | Add root integration evidence for shape, branching, fan-in, determinism, validation, and non-execution | complete | 9 focused integration tests lock the exact operation contracts and Plan output producers; all 52 ASS Flow tests pass |
| R5 | Link the implemented reference from root documentation and record its narrow ontology evidence | complete | Root README, docs index, root ontology, and reference docs describe only plan-level evidence |
| R6 | Independent source and boundary review | complete | Fresh Codex high review found no graph, source-boundary, fixture, ontology, or scope defect; two low-severity regression-evidence findings were corrected and reverified |
| R7 | Decide whether this evidence is sufficient to design executor lowering | complete | The Plan IR is adequate for this fixed graph, but real boundary values lack address, codec, publication, and handoff semantics; resolve the minimal artifact/adapter contract before local Dask lowering |

The R1-R7 table is the closed historical record of
`ASS-FLOW-WO-2026-08-03-OTA-PVT-PLAN`; its authorization was not reopened.

## Follow-on schema-2 adaptation

| ID | Work | State | Evidence |
| --- | --- | --- | --- |
| A1 | Declare four structured external sources through the strict public API | implemented and verified | Base uses repository-relative/repository-checkout/directory-tree; Sidecar edit uses Python-source/UTF-8; measurement definition and limits use JSON/UTF-8 |
| A2 | Preserve logical contracts and graph identity | implemented and verified | Ten artifact declarations, six version-1 operations, two version-1 flows, policies, resources, configuration, topology, keys, pinned source/invocation/edge/boundary IDs, and 16 named outputs remain unchanged |
| A3 | Prove the artifact/ephemeral split without output materialization | implemented and verified | Schema 2 has four artifact source declarations; all 18 operation-output edges and every named output, including final evaluation, are ephemeral; every output capability is null |
| A4 | Preserve canonical and no-runtime boundaries | implemented and verified | 10 focused tests cover repeated data/JSON, exact representations, legacy rejection, refusing bodies/submit, source-import audit, and guarded no-I/O construction |
| A5 | Independent Phase 4 acceptance | complete | Fresh full-diff review accepted the reference and data-only boundary after one ASS Flow malformed-source validation defect was corrected and independently reverified |

## Required implementation constraints

- Every operation body raises `NotImplementedError` with plan-declaration-only
  wording.
- Planning imports no simulator and calls no sibling public API.
- Names corresponding to existing tools are documented as proposed adapter
  boundaries, not working integration.
- Every operation and flow call has an explicit scoped key.
- The final operation uses two ordered collection artifact inputs.
- Fixture paths are versioned repository-relative external-source addresses;
  their codec and repository-checkout access declarations are data only, and
  Plan construction performs no file I/O.
- No child source, ontology, packaging, or active examples change.
- The inactive sequential-flow convenience remains archived.

## Verification log

- R2-R4 focused integration (2026-08-03):
  `PYTHONPATH=ass-flow/src:sidecar-edits/src python -m pytest -q integration-tests/test_ota_pvt_plan_reference.py`
  passed 9 tests. The assertions cover exact normalized cardinalities and
  identities; every operation's complete input kind/cardinality, output kind,
  configuration name/type/required, and resource contracts; the exact producer
  reference for all 16 named Plan outputs; per-point branch edges and resolved
  configuration; both ordered collection bindings and positions; repeated
  data/JSON identity; early authoring/model validation failures;
  repository-relative fixtures; typed Sidecar input resolution; refusing
  bodies; and `submit(...)` refusal. A source-import audit excludes sibling and
  runtime modules, while build-time guards cover `builtins.open`, `io.open`,
  `os.open`, and common `pathlib.Path` open/read surfaces.
- ASS Flow regression (2026-08-03): `python -m pytest -q` from `ass-flow/`
  passed all 52 unchanged component tests.
- Root integration regression (2026-08-03):
  `PYTHONPATH=ass-flow/src:sidecar-edits/src:spice-canonical/src:netlist-decomposition/src python -m pytest -q integration-tests`
  passed all 16 root integration tests, including the 9 focused reference
  checks and the existing four-child composition contracts.
- Coordinating full composition verification (2026-08-03), using absolute
  source paths because the composition runner changes its working directory:
  52 ASS Flow, 45 Netlist Decomposition, 77 Sidecar Edits, 28 SPICE Canonical,
  and 16 root integration tests passed. The earlier relative-`PYTHONPATH`
  import error was an invocation-environment issue, not a product failure.
- Independent R6 review (2026-08-03): a fresh read-only Codex high session
  independently checked the graduated-source hashes, graph construction,
  fixtures, public sibling boundaries, ontology placement, and documentation.
  It found no design or scope defect. Its two low-severity test-evidence
  findings were addressed by exhaustive operation/output assertions and wider
  no-I/O guards, then reverified by the focused and ASS Flow suites.
- Follow-on A1-A5 verification (2026-08-03): the schema-2 focused suite passed
  10 tests and the final ASS Flow suite passed 63. Root integration passed 17
  tests with absolute source paths. Full composition passed 63 ASS Flow, 45
  Netlist Decomposition, 77 Sidecar Edits, 28 SPICE Canonical, and 17 root
  integration tests. All changed Python modules passed `py_compile`; both the
  characterization and OTA/PVT stdout parsed as JSON, with canonical repeated
  data/JSON locked by tests. Fresh independent review covered the full follow-on
  diff, exposed one ASS Flow malformed-source validation leak, and returned
  `ACCEPT` after the focused correction and regression were independently
  reverified.

## Observed evidence

- The current Plan IR expresses the complete fixed OTA/PVT graph without a
  domain-specific planner type or second graph model.
- Preparation forks independently to canonicalization/decomposition and to
  simulation/measurement at each ordered point. Evaluation retains measurement
  and decomposition order in distinct collection bindings and positioned edges.
- Every flow and invocation has a scoped authored key. Repeated builds preserve
  normalized data, JSON, IDs, bindings, and edges; all operation-output edges in
  this fully keyed graph use stable keyed identities.
- Plan construction succeeds while every operation implementation refuses.
  Instrumentation rejects the common Python file-opening and `Path` read
  surfaces during construction, alongside the source-import audit; this is
  meaningful regression evidence that the fixtures are not read, not a claim
  that arbitrary hidden code paths are mathematically impossible.
- The typed Sidecar fixture and Python point tuple agree, but that agreement is
  test evidence rather than a new shared PVT schema.

## Honest limitations

- Artifact kinds remain logical labels. External sources now carry opaque
  repository-relative addresses plus codec and assumed-access declarations,
  but no address is resolved, no codec executes, no real access is checked, and
  no format/schema content is validated.
- The sibling-facing names remain proposed adapter boundaries. Nothing prepares
  a directory, discovers a deck, constructs or serializes canonical/decomposition
  values, invokes a simulator, reads waveforms, measures results, or evaluates
  limits.
- The fixture netlist and limits are architectural probes, not validated design
  collateral, exhaustive PVT coverage, simulator evidence, or product criteria.
- Keyed Plan identities are not executor, attempt, cache, content, or provenance
  identities. Source identity retains the current authored-order limitation.
- There is still no executor, lowering, runtime value, materialized operation
  output, caching, recovery, publication, durable study lifecycle, or reusable
  OTA-study API.

## Evidence decision

- The current Plan IR is adequate for this fixed graph: it retains every point
  configuration and both ordered fan-ins without domain-specific support.
- Every flow and invocation in this reference is keyed; external-source identity
  limitations remain explicit and unchanged.
- The declarative source-handoff prerequisite now distinguishes addressed
  artifact sources from ephemeral operation outputs and records codec/access
  assumptions. Independent Phase 4 acceptance is complete; no runtime
  artifact/adapter contract has been accepted.
- Dask remains the first execution-kernel hypothesis only under a separate
  reviewed work order.
  Direct and pooled LSF concepts, separate attempt ownership, reconciliation,
  and the two mandatory receipt/manifest failure injections remain preserved
  research rather than discarded scope.

## Explicitly deferred

- sibling ASS Flow adapters;
- simulator and waveform integration;
- address resolution, codec execution, real access checking, publication,
  materialized operation outputs, and runtime artifact values;
- execution, lowering, scheduling, retries, attempts, recovery, and caching;
- provenance, evidence promotion, decisions, and durable study lifecycle;
- production hardening and generalized OTA-study APIs.
