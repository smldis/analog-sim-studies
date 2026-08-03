# Analog Sim Studies Ontology

## Purpose and scope

This repository is the composition node for independently useful analog-design
capabilities governed by [MANIFESTO.md](MANIFESTO.md). It owns project-wide
vision, the explicit child-unit contract, aggregate workflows, cross-unit
integration checks, and documentation that explains how the units compose.

Filesystem containment expresses composition only. It grants no inheritance,
override, precedence, or authority to a child, its parent, or a sibling.
Deterministic traversal is presentation and execution order, not semantic rank.

## Mode of being

**Development state:** `prototype`

Prototype is this repository's mode of being as self-study. The composed,
runnable units propose hypotheses about the system's architecture, features,
and boundaries; their use supplies evidence for revising those hypotheses and
this ontology. The implementation is useful capability and an instrument of
inquiry, not an inevitable final form.

At this stage, architectural learning, useful features, and runnable vertical
slices take priority over production hardening. High availability, enterprise
deployment, exhaustive compatibility, premature migration machinery, and
speculative scale work belong only when a concrete use case makes them
relevant. Prototype does not excuse careless work: changes should preserve
inspectability, explicit boundaries, proportionate tests, reversibility,
honest limitations, and evidence-backed conclusions. Failures and friction are
valid evidence that may require revising code, contracts, boundaries, or
ontology. Any maturity change must be explicit and update this ontology and
any affected child ontology.

## Current contracts

- `unit.toml` declares immediate children and parent-owned workflows using
  relative paths.
- `composition.py` validates declarations, renders the ontology tree, composes
  child tests with parent integration tests, and builds aggregate docs from
  child-owned sources.
- Child public Python and CLI contracts remain owned and versioned by their
  units.
- Root integration checks may verify explicit relationships such as
  `netlist-decomposition` consuming `spice-canonical`.
- `docs/vision/open-concepts.md` registers every concept raised by the ASS Flow
  rebuild inquiry with its current status, including concepts that fell out of
  direct development without a decision. It spans both units, so it belongs at
  the composition root rather than in either one.
- `docs/reference/ota-pvt-plan/` owns one representative, non-executing
  cross-unit Plan declaration and its versioned input fixtures. It tests static
  composition through public ASS Flow contracts: four repository-relative
  sources are declared as addressed artifact references with explicit data-only
  representation/access requirements, while all operation-output edges and the
  final evaluation remain ephemeral. This does not promote its analog-domain
  labels into a child API or claim sibling adapters.

## Contributions from children

- `ass-flow` contributes generic Python-authored static operation/flow planning
  and immutable, deterministic Plan IR without executor or runtime authority.
- `ass-exec` contributes the durable lifecycle of one attempt at one planned
  invocation: identity chosen before submission, an append-only record, atomic
  terminal publication, and reconciliation. It owns no graph and decides no
  readiness.

`ass-exec` consumes `ass-flow`'s schema-2 Plan **document**, not its package.
The cross-unit contract is therefore the portable plain-data artifact: neither
unit imports the other, and any producer of the same document composes equally
well. `ass-flow` stays executor-neutral; `ass-exec` reads a Plan but neither
produces nor validates one.
- `sidecar-edits` contributes reviewable simulation-directory preparation.
- `spice-canonical` contributes canonical netlist extraction.
- `netlist-decomposition` contributes functional block recognition over the
  canonical representation.

These contributions compose into the larger vision. Flow execution is now
partly owned. `ass-flow` and `ass-exec` together deliver one runnable vertical
slice — author a flow, plan it, execute it, edit one input, and rerun with
unchanged work skipped and superseded results retained — demonstrated by
`ass-exec/examples/planned_characterization.py`. No real batch or distributed
transport has been exercised: direct `bsub -I` submission exists but has never
contacted a cluster, and pooled execution refuses. The retired `study-flow`
prototype remains
recoverable in Git history at `528c02f`, while
[`docs/vision/ass-flow-rebuild-main.md`](docs/vision/ass-flow-rebuild-main.md)
records the architectural inquiry that preceded the bounded planning work.
The declared `ass-flow` child owns only static planning; its refusing
`submit(...)` boundary confers no local, distributed, simulator, or study
runtime authority.

The root-owned OTA/PVT reference composes these capabilities only at the level
of declared artifact and operation boundaries. Its Sidecar, canonicalization,
and decomposition names are proposed adapter seams; its simulator, measurement,
and evaluation operations are refusing stubs. The validated Plan is evidence of
static expressiveness and an addressed-source/ephemeral-edge distinction, not
evidence that addresses resolve, codecs execute, access succeeds, artifacts are
published, outputs materialize, or any operation can run.

## Exclusions

The root does not own a unified Python package, source tree, unit-test suite,
API guide, example catalog, or component-specific build script. It is not a
package-distribution boundary and does not imply that every future capability
must use the current four implementations.

## Child composition

The immediate children are authored in `unit.toml`. A future child may declare
children with the same contract; the loader and test traversal already recurse.
Deeper documentation composition can extend the same explicit source contract
when a real nested unit requires it.
