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

## Running a sweep on Dask

`run_plan` is one invocation at a time. For a real sweep, readiness belongs to
Dask (adopted 2026-08-04):

```python
from distributed import Client, LocalCluster
from ass_run.graph import run_plan_graph

# Concurrency is this number. There is no limit parameter: a waiting
# invocation costs ~16 KiB of thread and one client process, so size it from
# your site's MAX JOB policy rather than from anything this library knows.
cluster = LocalCluster(processes=False, threads_per_worker=32)

with Client(cluster) as client:
    report = run_plan_graph(
        plan_document,
        client=client,
        transports={"local": local, "lsf-direct": lsf},
        plan_id="ota-pvt",
        root="attempts",
        on_event=lambda outcome: print(outcome.authored_key, outcome.outcome),
    )
```

Same Plan, same identities, same report order — the kernel decides how long a
run takes, never what it means, and `ass_run.binding` holds the rules both use
so they cannot drift. Two differences are deliberate: a failed corner blocks
its dependents while independent branches finish, and tasks are keyed by
authored name so a dashboard shows corners rather than digests.

The cluster is local and threaded on purpose. No nanny to restart a worker
holding live `bsub -I` clients — under owner-bound lifetime that would kill
their farm jobs — and nothing secedes, so a worker with jobs in flight reads as
running. Note that Dask serializes every task even in-process, so a transport
is *copied* to its worker; one that cannot be serialized is refused by
placement name before anything runs.

`distributed` is an optional dependency (`pip install ass-run[dask]`), reached
by explicit import: a plan small enough to walk in one thread should not need a
scheduler. What Dask still cannot tell you is whether a corner is `PEND` or
`RUN` — that needs a watcher over the attempt records, and is not built yet.

See [`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary.
