# SPICE Canonical Ontology

## Purpose and scope

SPICE Canonical extracts a deterministic structural view of Eldo and ngspice
decks: circuits, devices, nets, hierarchy, and diagnostics suitable for graph
consumers. The simulator deck remains authoritative.

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
