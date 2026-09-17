# Studies

Runnable analog studies, written against [`hedloom`](../hedloom/README.md).

They live here rather than in `hedloom/examples/` because they are about this
domain and not about the tool. Each one names a simulator, reads a netlist,
and measures a circuit; `hedloom` itself names no simulator anywhere, and its
own examples run `awk` and `/bin/sh` so that nothing in the package assumes
what the work is. The split is not cosmetic — these studies already read
`docs/reference/ota-pvt-plan/inputs/` and import `spice-canonical`,
`netlist-decomposition` and `sidecar-edits`, so they never could have run from
inside the `hedloom` checkout on their own.

Run any of them from the repository root:

```console
python studies/rc_corners.py
python studies/ota_pvt.py
python studies/ota_pvt_clean.py
python studies/ota_pvt_clean_nested.py
```

Results land under `studies/_runs/`, which is generated evidence rather than
source and is not committed.

| Study | Hedloom name | What it is for |
| --- | --- | --- |
| [`rc_corners.py`](rc_corners.py) | `rc-corners` | The smallest honest end-to-end study: three RC corners on real `ngspice`, whose −3 dB frequency is analytic, so the measured number can be checked rather than believed. The 4.3% gap is the `dec 50` sweep grid. |
| [`ota_pvt.py`](ota_pvt.py) | `ota-pvt-study` | The full OTA/PVT reference. Sixteen invocations over three PVT points, four declared external sources, real AC sweeps, and gain/GBW/phase-margin computed from the raw file rather than transcribed. |
| [`ota_pvt_clean.py`](ota_pvt_clean.py) | `ota-pvt-clean` | The same sign-off with the structural analysis removed, fanning corners out from the edit file and writing `report.md` as the deliverable. Opens its own session so the dashboard link is available before anything is submitted. |
| [`ota_pvt_clean_nested.py`](ota_pvt_clean_nested.py) | `ota-pvt-clean-nested` (outer), `ota-pvt-clean-nested-corners` (inner) | The corner set as a *result*: an outer plan whose invocation authors and submits an inner plan, so per-corner identity and reuse survive a fan-out that could not be named in advance. |

`ota_pvt.py` is the reference the root documentation cites. The other three are
variations on it, kept because each answers a different question about the
composition rather than about the circuit.

The OTA measurement helpers retain legacy JSON metric keys. `dc_gain_db` is
gain at the first AC sample, and `phase_margin_deg` is transfer phase plus 180
at the first downward unity crossing; neither alone establishes DC gain or loop
stability. Measurement version 2 unwraps successive phases before interpolation.
This fixes a phase-wrap error covered by the analytical
[measurement contract test](../integration-tests/test_ota_ac_measurement_contract.py).
It still assumes a sufficiently dense frequency grid and a meaningful initial
phase branch. Historical evidence that used measurement version 1 remains
versioned as recorded; new study runs use version 2.

Preparation version 2 declares each rendered tree with Hedloom's public
`directory("run", kind="prepared-simulation-directory")`; raw waveforms and reports
remain `file(...)` outputs. The shared Sidecar fixture opts into interpolation
only on its three parameterized replacements (point comment, supply parameter,
temperature), leaving SPICE expressions in the base deck intact. The
[preparation contract test](../integration-tests/test_ota_preparation_contract.py)
checks all three consumer forms against a temporary local Site.

The nested `run_corner_study` operation is version 2 and submits its small local
inner plan explicitly with `sequential=True`. This avoids a graph scheduler
requesting the sole local slot while the outer invocation waits for it. Inner
corners retain separate identities and reuse; this study does not demonstrate
parallel or farm execution. Its outer API reads all three authored selectors;
`corner_study(jobs)` can exercise a nominal subset directly. The focused tests
are contract checks, not simulator runs or proof of production PVT coverage;
the process labels in this Level-1 fixture remain comments rather than
process-model corners.
