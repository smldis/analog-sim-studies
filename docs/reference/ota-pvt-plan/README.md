# OTA PVT Plan Reference

This directory owns one root-level, cross-unit reference workflow. Its original
purpose was to test whether ASS Flow can describe a realistic static
analog-study graph without acquiring simulation or runtime meaning. That
question is answered and recorded below. A second question is now answered
too: whether the three execution units (`ass-flow`, `ass-exec`, `ass-run`) can
run that exact graph for real, against a real simulator, with honest reuse.

**The Plan declaration is unchanged and still plan-only.** `ota_pvt_plan.py`'s
six operations still raise `NotImplementedError`; that is the correct shape
for a document meant to be inspected without acquiring runtime meaning, and
nothing here edits it. What changed is that a *binding* now exists alongside
it: [`run_study.py`](run_study.py) supplies a real implementation for every
operation name and executes the same Plan end to end with
`ass_run.run_plan`, exactly the split `ass-run`'s own README states — "The
Plan declares meaning; the run binds mechanism" — and the same shape as
`ass-exec/examples/planned_characterization.py`.

Run it, from the repository root, with every sibling source tree on the path:

```console
PYTHONPATH=ass-flow/src:ass-run/src:ass-exec/src:sidecar-edits/src:\
spice-canonical/src:netlist-decomposition/src \
  python docs/reference/ota-pvt-plan/run_study.py
```

It renders each corner's deck with the real Sidecar Edits `render_job`, parses
it with real SPICE Canonical, decomposes it with real Netlist Decomposition,
simulates it with real `ngspice -b -r` (an AC sweep), computes DC gain,
gain-bandwidth, and phase margin from the real raw waveform file, and checks
every corner against `inputs/spec_limits.json`. Attempts and workspaces land
under `_runs/` (git-ignored, generated evidence, not source). A second
invocation reuses every attempt whose inputs are unchanged; editing one
corner's declared configuration reruns exactly that corner's chain and the
shared final evaluation, and leaves the other corners' results untouched on
disk.

The run's own stdout is diagnostics, per this study's own rule for every
`ngspice` invocation it runs. The real, durable result is
`_runs/report.json`, written after every run (reused or not): every
invocation's disposition/outcome/duration and the full evaluation, so a human
or a script can inspect a run without re-parsing terminal output. Written by
ordinary post-processing in `run_study.py`, not a Plan operation — adding one
would change the reference's declared invocation/edge/output cardinality,
which `PLANNING.md` reserves for coordinated review.

Names that correspond to Sidecar Edits, SPICE Canonical, or Netlist
Decomposition are no longer merely proposed adapter boundaries for this
reference's own use — `run_study.py` calls their real public APIs. They remain
proposed boundaries for ASS Flow itself: ASS Flow has no adapter that accepts
the declared bindings, locates or publishes their artifacts, or serializes the
sibling values on its own. `run_study.py` is a companion binding script that
lives beside the Plan declaration, not a change to ASS Flow, and it does not
promote this reference into a fifth component or a reusable OTA-study API.

The proposed preparation boundary corresponds to the existing
`sidecar-render`/`sidecar_edits.render.load_editfile` and `render_job` surfaces,
now actually called. The canonicalization boundary corresponds to
`spice_canonical.canonical_netlist.from_file`, now actually called. The
structural boundary selects a canonical `Circuit`, calls
`netlist_decomposition.decompose`, and calls `suppress_false_stacks`, now
actually called. `run_study.py` also gives the `canonical-netlist` and
`ota-functional-decomposition` artifact kinds their first real, JSON-safe
serialization (see its module docstring) — a concrete answer to the "no
portable serialization" limitation recorded below, scoped to what a single
in-process run needs.

[`ota_pvt_plan.py`](ota_pvt_plan.py) declares the exact three-point graph and
builds a validated Plan without reading its fixtures:

```console
PYTHONPATH=ass-flow/src python docs/reference/ota-pvt-plan/ota_pvt_plan.py \
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
materialize a result. `run_study.py` declares its own `outputs=` mapping at
run time (`prepare_run`'s rendered directory, `simulate_ac`'s raw file) for
`ass_exec` to verify and record a real address for; that is execution
binding it, exactly as `ass-run`'s README describes, not a change to what the
Plan says.

The authorized shape and stop conditions are recorded in
[PLANNING.md](PLANNING.md). Progress and verification evidence are recorded in
[IMPLEMENTATION.md](IMPLEMENTATION.md).

This is not a fifth component, a reusable OTA-study API, an example catalog, or
a general executor prototype: `run_study.py` binds only this Plan's six named
operations, by name, the same way the ASS Exec example binds a two-operation
plan. All four child ontologies and packages remain unchanged; only `ass-exec`
and `ass-run`, already public execution units, are used as documented.

```{toctree}
:hidden:
:maxdepth: 1

PLANNING
IMPLEMENTATION
```
