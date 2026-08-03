# ASS Flow Ontology

## Purpose and scope

ASS Flow owns generic, Python-authored definitions of operations and reusable
static flows, plus the immutable normalized Plan IR produced by explicit
planning scopes. It makes planned invocations, dependencies, nested flow
boundaries, policies, artifact contracts, and named outputs inspectable before
any execution boundary.

## Mode of being

**Development state:** `prototype`

The current runnable API studies whether ordinary Python authoring can produce
one deterministic, executor-neutral graph while retaining explicit contracts
and nested flow structure. Its tests and simulator-free example provide
evidence for the current boundary; limitations in identity and fan-in remain
questions for the authorized later semantic phase, not capabilities claimed by
this ontology. Changes should preserve inspectability, immutability, early
validation, and the separation between planning and runtime authority.

## Current contracts

- Distribution: `ass-flow`, independently installable on Python 3.10 or newer
  with no runtime dependencies outside the standard library.
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
- `submit(...)` is a refusing boundary that raises `NotImplementedError`; it
  grants no executor contract.

## Contribution to the parent

The unit contributes static operation/flow planning and inspectable Plan IR to
the repository's broader author-plan-execute-evaluate vision. Only the planning
contract is promoted through the parent composition node.

## Exclusions

ASS Flow does not own simulation meaning, operation execution, local or remote
scheduling, Dask lowering, LSF transport, retries or attempts, persistence,
artifact publication, recovery, plugins, dynamic or result-dependent
replanning, or the complete study lifecycle. It does not provide sequential
editing helpers. Current scalar artifact inputs and authored-order generated
identities are documented limitations, not collection fan-in or cross-edit
identity promises.

## Child composition

There are currently no child units.
