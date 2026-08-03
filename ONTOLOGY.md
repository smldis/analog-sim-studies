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

## Contributions from children

- `ass-flow` contributes generic Python-authored static operation/flow planning
  and immutable, deterministic Plan IR without executor or runtime authority.
- `sidecar-edits` contributes reviewable simulation-directory preparation.
- `spice-canonical` contributes canonical netlist extraction.
- `netlist-decomposition` contributes functional block recognition over the
  canonical representation.

These contributions compose into the larger vision. Flow execution still has
no implementation unit: the retired `study-flow` prototype remains recoverable
in Git history at `528c02f`, while
[`docs/vision/ass-flow-rebuild-main.md`](docs/vision/ass-flow-rebuild-main.md)
records the architectural inquiry that preceded the bounded planning work.
The declared `ass-flow` child owns only static planning; its refusing
`submit(...)` boundary confers no local, distributed, simulator, or study
runtime authority.

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
