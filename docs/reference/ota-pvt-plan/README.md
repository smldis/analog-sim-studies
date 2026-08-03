# OTA PVT Plan Reference

This directory owns one root-level, cross-unit reference workflow. Its purpose
is to test whether ASS Flow can describe a realistic static analog-study graph
without acquiring simulation or runtime meaning.

The reference is intentionally plan-only. Its operations are declarations whose
bodies refuse execution. Names that correspond to Sidecar Edits, SPICE
Canonical, or Netlist Decomposition identify proposed adapter boundaries; they
do not claim that such adapters exist. Simulator, measurement, and evaluation
operations are explicit stubs.

The proposed preparation boundary corresponds conceptually to the existing
`sidecar-render`/`sidecar_edits.render.load_editfile` and `render_job` surfaces.
The proposed canonicalization boundary corresponds to
`spice_canonical.canonical_netlist.from_file`. The proposed structural boundary
would select a canonical `Circuit`, call `netlist_decomposition.decompose`, and
optionally call `suppress_false_stacks`. ASS Flow currently has no adapter that
accepts the declared bindings, locates or publishes their artifacts, or
serializes the sibling values. The matching names document those missing seams;
they are not working integration.

[`ota_pvt_plan.py`](ota_pvt_plan.py) declares the exact three-point graph and
builds a validated Plan without reading its fixtures:

```console
PYTHONPATH=ass-flow/src python docs/reference/ota-pvt-plan/ota_pvt_plan.py \
  | python -m json.tool
```

The versioned `inputs/` files are descriptive authored sources. In particular,
`pvt_edits.py` is a typed Sidecar Edits input with the same ordered values as
the Python declaration, but the Plan module neither imports nor calls Sidecar
Edits. No generated Plan JSON is maintained.

The authorized shape and stop conditions are recorded in
[PLANNING.md](PLANNING.md). Progress and verification evidence are recorded in
[IMPLEMENTATION.md](IMPLEMENTATION.md).

This is not a fifth component, a reusable OTA-study API, an example catalog, or
an executor prototype. All four child ontologies and packages remain unchanged.
