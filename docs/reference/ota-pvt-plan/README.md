# OTA PVT Plan Reference

This directory owns one root-level, cross-unit reference workflow. Its purpose
is to test whether ASS Flow can describe a realistic static analog-study graph
without acquiring simulation or runtime meaning.

The reference is intentionally plan-only. Its operations are declarations whose
bodies refuse execution. Names that correspond to Sidecar Edits, SPICE
Canonical, or Netlist Decomposition identify proposed adapter boundaries; they
do not claim that such adapters exist. Simulator, measurement, and evaluation
operations are explicit stubs.

The authorized shape and stop conditions are recorded in
[PLANNING.md](PLANNING.md). Progress and verification evidence are recorded in
[IMPLEMENTATION.md](IMPLEMENTATION.md).

This is not a fifth component, a reusable OTA-study API, an example catalog, or
an executor prototype. The implementation slice must leave all four child
ontologies and packages unchanged.
