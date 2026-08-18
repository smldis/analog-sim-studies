# OTA PVT Plan Reference

This directory owns one root-level, cross-unit reference workflow. Its original
purpose was to test whether Hedloom Flow can describe a realistic static
analog-study graph without acquiring simulation or runtime meaning. That
question is answered and recorded below. A second question was answered
separately: whether the execution units can run that exact graph for real,
against a real simulator, with honest reuse. They can, and the file that shows
it now lives in [`../../../studies/ota_pvt.py`](../../../studies/README.md).

**This directory stays plan-only, and that is its whole job.**
`ota_pvt_plan.py`'s six operations raise `NotImplementedError` on purpose: it is
a document meant to be inspected without acquiring runtime meaning, and
`integration-tests/test_ota_pvt_plan_reference.py` holds it to that — the Plan
must validate, keep its exact normalized shape, and build without opening a
fixture or importing a sibling package.

It was once accompanied by `run_study.py`, six hundred and fifty lines that
re-declared all six operations, supplied their output paths, transports and
roots, and wrote `del base, edits  # unresolved source reference` three times
because a declared source could not reach a body. `hedloom`'s `@study` closed
that seam: an operation's body *is* its implementation, so the second file has
no remaining job. It has been retired rather than updated, and
`studies/ota_pvt.py` is the same study in one file with real bodies:

```console
python studies/ota_pvt.py
```

That study renders each corner's deck with the real Sidecar Edits `render_job`,
parses it with real SPICE Canonical, decomposes it with real Netlist
Decomposition, simulates it with real `ngspice -b -r` (an AC sweep), computes DC
gain, gain-bandwidth and phase margin from the real raw waveform file, and checks
every corner against `inputs/spec_limits.json` — this directory's fixtures, still
the authored sources. A second invocation reuses every attempt whose inputs are
unchanged.

Names that correspond to Sidecar Edits, SPICE Canonical, or Netlist
Decomposition are no longer merely proposed adapter boundaries for this
reference's own use — `studies/ota_pvt.py` calls their real public APIs. They
remain proposed boundaries for Hedloom Flow itself: Hedloom Flow has no adapter
that accepts the declared bindings, locates or publishes their artifacts, or
serializes the sibling values on its own. That study is an ordinary consumer of
the published packages, not a change to Hedloom Flow, and it does not promote
this reference into a fifth component or a reusable OTA-study API.

The proposed preparation boundary corresponds to the existing
`sidecar-render`/`sidecar_edits.render.load_editfile` and `render_job` surfaces,
now actually called. The canonicalization boundary corresponds to
`spice_canonical.canonical_netlist.from_file`, now actually called. The
structural boundary selects a canonical `Circuit`, calls
`netlist_decomposition.decompose`, and calls `suppress_false_stacks`, now
actually called. `studies/ota_pvt.py` also gives the `canonical-netlist` and
`ota-functional-decomposition` artifact kinds their first real, JSON-safe
serialization — a concrete answer to the "no portable serialization" limitation
recorded below, scoped to what a single in-process run needs.

[`ota_pvt_plan.py`](ota_pvt_plan.py) declares the exact three-point graph and
builds a validated Plan without reading its fixtures:

```console
PYTHONPATH=hedloom/flow/src python docs/reference/ota-pvt-plan/ota_pvt_plan.py \
  | python -m json.tool
```

The versioned `inputs/` files are descriptive authored sources. In particular,
`pvt_edits.py` is a typed Sidecar Edits input with the same ordered values as
the Python declaration, but the Plan module neither imports nor calls Sidecar
Edits. Schema-2 source declarations record repository-relative addresses and a
repository-checkout access assumption. The base directory uses a directory-tree
codec contract; the edit file uses Python-source/UTF-8; the measurement
definition and limits use JSON/UTF-8. These are data-only declarations: this
reference does not resolve an address, execute a codec, or check accessibility.
No generated Plan JSON is maintained.

All six operations retain their original logical artifact contracts and
version `1`. No output advertises a materialization capability because the
reference has no real output codec. Consequently all 18 operation-output edges
and the final evaluation reference remain `ephemeral`; only the four external
source references have value class `artifact`. Nothing published by
`ota_pvt_plan.py`'s own declarations changes: `value_class` is a planning-time
fact about the Plan document, not about whether some later binding chooses to
materialize a result. `studies/ota_pvt.py` declares each operation's outputs on
the operation itself, so `hedloom_exec` verifies and records a real address for
them; that is execution binding it, not a change to what the Plan says.

The authorized shape and stop conditions are recorded in
[PLANNING.md](PLANNING.md). Progress and verification evidence are recorded in
[IMPLEMENTATION.md](IMPLEMENTATION.md).

This is not a fifth component, a reusable OTA-study API, an example catalog, or
a general executor prototype. All four child ontologies and packages remain
unchanged; the execution units are used as documented, from `studies/`.

```{toctree}
:hidden:
:maxdepth: 1

PLANNING
IMPLEMENTATION
```
