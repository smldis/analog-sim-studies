# SPICE Canonical Ontology

## Purpose and scope

SPICE Canonical extracts a deterministic structural view of Eldo and ngspice
decks: circuits, devices, nets, hierarchy, and diagnostics suitable for graph
consumers. The simulator deck remains authoritative.

## Mode of being

**Development state:** `prototype`

Its runnable parser studies how much deterministic, graph-oriented structure
can be exposed across real Eldo and ngspice inputs while leaving the simulator
deck authoritative and unsupported meaning visible in diagnostics. Corpus
friction, consumer needs, and parsing failures are evidence for changing the
representation, syntax boundary, or ontology. Compatibility should grow from
concrete decks and consumers, with inspectable output and focused tests, not
from an attempt at speculative or exhaustive dialect coverage.

## Current contracts

- Python API: `spice_canonical.canonical_netlist`.
- CLI: `spice-canonical`.
- Inputs: netlist text/files, format selection, include boundaries, external
  subcircuit pin declarations, and device type mappings.
- Outputs: canonical circuit data and explicit diagnostics.

## Contribution to the parent

The unit contributes the structural input contract consumed explicitly by
`netlist-decomposition` and available to future analysis units.

## Exclusions

It is not a lossless netlist serializer, simulator, sidecar editor, functional
classifier, model-library interpreter, or project-wide study representation.

## Child composition

There are currently no child units.
