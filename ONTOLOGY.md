# Analog Sim Studies Ontology

## Purpose and scope

This repository is the composition node for independently useful analog-design
capabilities governed by [MANIFESTO.md](MANIFESTO.md). It owns project-wide
vision, the explicit child-unit contract, aggregate workflows, cross-unit
integration checks, and documentation that explains how the units compose.

Filesystem containment expresses composition only. It grants no inheritance,
override, precedence, or authority to a child, its parent, or a sibling.
Deterministic traversal is presentation and execution order, not semantic rank.

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

- `sidecar-edits` contributes reviewable simulation-directory preparation.
- `spice-canonical` contributes canonical netlist extraction.
- `netlist-decomposition` contributes functional block recognition over the
  canonical representation.

These contributions compose into the larger vision but do not yet implement
the full study lifecycle described by the manifesto.

## Exclusions

The root does not own a unified Python package, source tree, unit-test suite,
API guide, example catalog, or component-specific build script. It is not a
package-distribution boundary and does not imply that every future capability
must use the current three implementations.

## Child composition

The immediate children are authored in `unit.toml`. A future child may declare
children with the same contract; the loader and test traversal already recurse.
Deeper documentation composition can extend the same explicit source contract
when a real nested unit requires it.
