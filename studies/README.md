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

| Study | What it is for |
| --- | --- |
| [`rc_corners.py`](rc_corners.py) | The smallest honest end-to-end study: three RC corners on real `ngspice`, whose −3 dB frequency is analytic, so the measured number can be checked rather than believed. The 4.3% gap is the `dec 50` sweep grid. |
| [`ota_pvt.py`](ota_pvt.py) | The full OTA/PVT reference. Sixteen invocations over three PVT points, four declared external sources, real AC sweeps, and gain/GBW/phase-margin computed from the raw file rather than transcribed. |
| [`ota_pvt_clean.py`](ota_pvt_clean.py) | The same sign-off with the structural analysis removed, fanning corners out from the edit file and writing `report.md` as the deliverable. Opens its own session so the dashboard link is available before anything is submitted. |
| [`ota_pvt_clean_nested.py`](ota_pvt_clean_nested.py) | The corner set as a *result*: an outer plan whose invocation authors and submits an inner plan, so per-corner identity and reuse survive a fan-out that could not be named in advance. |

`ota_pvt.py` is the reference the root documentation cites. The other three are
variations on it, kept because each answers a different question about the
composition rather than about the circuit.
