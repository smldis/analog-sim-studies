# ASS Flow Ontology

## Purpose and scope

ASS Flow owns generic, Python-authored definitions of operations and reusable
static flows, plus the immutable normalized Plan IR produced by explicit
planning scopes. It makes planned invocations, dependencies, nested flow
boundaries, policies, artifact contracts, and named outputs inspectable before
any execution boundary. It also owns data-only declarations for addressed
external sources: codec identity/options, materialization and access
assumptions, fixed source/output reference value classes, and optional output
materialization capability metadata.
It also owns one non-reexported experimental instrument that lowers a validated
Plan, explicit implementation registry, and injected decoded source mapping to
inspectable Dask Delayed values. This instrument tests Plan sufficiency; it is
not a public or general execution surface.

## Mode of being

**Development state:** `prototype`

The current runnable API studies whether ordinary Python authoring can produce
one deterministic, executor-neutral graph while retaining explicit contracts
and nested flow structure. Its tests and simulator-free example now provide
evidence for ordered collection fan-in, scoped authored Plan identity, the
static distinction between addressed artifact sources and ephemeral operation
outputs, and a bounded local Delayed lowering of those contracts. Changes
should preserve
inspectability, immutability, early validation, and the separation between
planning and runtime authority.

## Current contracts

- Distribution: `ass-flow`, independently installable on Python 3.10 or newer;
  the base package has no dependencies, and the optional `dask` extra pins
  `dask==2026.7.1` for the experimental instrument.
- Python API: `ass_flow` exposes immutable planning model values and the
  `@operation`, `@flow`, `plan(...)`, `input_artifact(...)`, policy, and
  contract-authoring surfaces.
- Authored operation calls are legal only in an explicit planning scope, and
  operation bodies do not execute during planning.
- Flow bodies are ordinary authored Python that constructs a static graph;
  avoiding external side effects in those bodies is an authoring responsibility.
- Plan IR is immutable, validates operation bindings and artifact dependencies,
  preserves nested flow boundaries, and provides deterministic plain-data and
  JSON inspection.
- `address(...)`, `codec(...)`, and `materialization(...)` declare opaque
  source addresses, representation identity/options, and assumed access scope
  as canonical data. Strict `input_artifact(...)` records an already-
  materialized external source without resolving, reading, or decoding it.
- External source references have inspectable value class `artifact`; ordinary
  operation-output references have value class `ephemeral`. An optional output
  `can_materialize_as` declaration advertises capability only and does not
  change that output's value class or create an artifact.
- `artifacts(kind)` declares a required, non-empty ordered collection input.
  Its binding retains member order and its dependencies contain one edge per
  member with an explicit zero-based position.
- Operation and flow call views may carry an explicit key. Keys share one
  operation/flow namespace within their containing boundary and may be reused
  only in distinct scopes. Keyed invocation and boundary IDs, and edges between
  keyed invocations, derive from that scoped authored identity.
- Keys are Plan identity only. They are never cache keys, scheduler keys,
  attempt identities, runtime identities, or sequential slots.
- Cross-edit stability is conditional: a keyed call beneath an unkeyed
  enclosing boundary inherits that counter-derived boundary's instability.
  External source IDs, unkeyed sources/invocations/boundaries, and fallback
  edges involving an external source or unkeyed endpoint remain deterministic
  authored-order identities and can change after earlier insertions.
- Explicit module `ass_flow.experimental.local_dask` consumes a validated Plan,
  exact `OperationIdentity`-keyed callables, and a complete source-ID mapping of
  already-decoded values. Each lowering has a fresh Dask-key namespace and
  returns immutable mappings for invocation tasks, named output projections,
  and pre-optimization invocation keys. Neither package initializer imports or
  reexports it.
- The experimental lowerer accepts only option-free `local` policy and
  resource-free used operations, builds no second readiness graph, performs no
  source I/O or codec work, and has no compute, submit, persistence,
  cancellation, publication, or scheduling method. Callers explicitly choose
  whether and how to compute returned Delayed values.
- `submit(...)` is a refusing boundary that raises `NotImplementedError`; it
  grants no executor contract.

## Contribution to the parent

The unit contributes static operation/flow planning and inspectable Plan IR to
the repository's broader author-plan-execute-evaluate vision. Only the planning
contract is promoted through the parent composition node.

## Exclusions

ASS Flow does not own simulation meaning, public or general operation
execution, local or remote scheduling, placement enforcement, a working
`submit(...)`, general Dask lowering, Dask Distributed/Futures, LSF transport,
retries or attempts, persistence, address resolution, codec execution, real
accessibility checking, artifact publication, materialized operation outputs,
runtime artifact values, recovery, plugins, dynamic or result-dependent
replanning, production hardening, runtime study ownership, or the complete
study lifecycle. It does not provide sequential editing helpers. The archived
sequential convenience is inactive historical material, not an API or backlog.

## Child composition

There are currently no child units.
