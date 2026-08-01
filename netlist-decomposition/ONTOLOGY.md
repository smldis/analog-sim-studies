# Netlist Decomposition Ontology

## Purpose and scope

Netlist Decomposition recognizes functional MOS structures in a canonical
SPICE circuit using explicit tagging sets, dependency metadata, and composition
passes aligned in part with Abel, Neuner, and Graeb (2021).

## Mode of being

**Development state:** `prototype`

Its present runnable rules study whether explicit, inspectable structural
evidence can support useful functional interpretations over the canonical
netlist contract. Matches, false positives, missed structures, and dependency
friction may justify revisions to rules, passes, the sibling contract, this
unit's boundary, or its ontology. The current paper alignment and tag taxonomy
are evidence-bearing implementations rather than a claim of completeness;
changes should retain explainable outputs and proportionate regression tests.

## Current contracts

- Python API: `netlist_decomposition`, including `decompose` and
  `suppress_false_stacks`.
- Input contract: `Circuit` and `Device` objects from the separately packaged
  `spice-canonical` unit.
- Output contract: immutable functional tags and dependency metadata.
- Maintainer operations: deterministic dependency-table generation and an
  optional real-workspace OTA check.

The distribution metadata explicitly requires `spice-canonical`; no shared
root source path supplies that dependency.

## Contribution to the parent

The unit contributes explainable structural-to-functional analysis over the
canonical netlist boundary.

## Exclusions

It does not parse raw netlist syntax, edit simulator inputs, guarantee the full
published decomposition algorithm, simulate circuits, or infer behavior from
waveforms.

## Child composition

There are currently no child units.
