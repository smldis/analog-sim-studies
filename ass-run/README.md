# ASS Run

Walk a validated Plan and run it.

```python
from ass_exec.transport import InProcessTransport
from ass_run import run_plan

report = run_plan(
    plan_document,
    transport,
    plan_id="ota-pvt",
    root="attempts",
    workspace_root="/nfs/studies/ota-pvt",
    commands={"simulate": ["ngspice", "-b", "corner.spice"]},
    outputs={"simulate": {"raw": {"path": "corner.raw"}}},
)

print(report.summary())
```

The Plan declares meaning; the run binds mechanism. `commands` and `outputs`
say how an operation actually runs and which files count as its results;
operations named in neither run in-process.

A second run reuses everything. Edit one corner and only that corner and its
dependents rerun. A failure stops the run, and its successors are reported as
`blocked` rather than executed against inputs that do not exist — a failed step
is not cached, so fixing the cause and rerunning retries exactly it.

Run the evidence:

```console
PYTHONPATH=src:../ass-exec/src python -m pytest -q
```

This is a plain sequential driver: one invocation at a time, no concurrency, no
scheduling policy. That is the point — the open question is whether a scheduler
is needed, and if it is, Dask should replace this unit rather than be absorbed
into it. See [`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary.
