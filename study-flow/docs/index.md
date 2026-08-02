# Study Flow

This unit is a runnable architectural experiment: can ASS keep a plan and its
artifacts intelligible while Dask supplies temporary scheduling and Dask
Jobqueue supplies an optional LSF worker pool?

It deliberately tests only this shape:

```text
                          basic flow A
                    simulate -> measure
                   /                     \
local preparation                         reduce
                   \                     /
                    simulate -> measure
                          basic flow B
```

## Observable contract

`prepare_study()` runs synchronously in the controller. It snapshots the
`StudySpec` as `study-spec.json`, then publishes `prepared.json` and an
inspectable `plan.json` before submitting tasks. The plan points to the spec
snapshot rather than becoming another authored source. The prepared artifact
is the one local dependency consumed by both mapped basic flows.

Each basic flow contains two Dask tasks:

1. `simulate_placeholder()` publishes a unique attempt directory and
   `simulation.json`.
2. `measure_placeholder()` validates that artifact and publishes a named
   normalized measurement.

`reduce_measurements()` consumes exactly the two published measurements and
writes `summary.json`. Dask Futures express the live dependencies, while the
run directory retains what the demonstration produced after the scheduler is
closed.

The headless Python seam is intentionally small:

```python
prepared = prepare_study(spec, shared_output_root)  # synchronous local work
handles = submit_prepared(client, prepared)         # two mapped basic flows
completed = complete(handles)                       # reduction is durable
```

The supplied local and LSF helpers create the `client`; the workflow functions
do not otherwise depend on how its workers were provisioned.

## Local experiment

```bash
ass-flow-demo --output build/demo
```

The local backend uses two threaded Dask workers and disables the dashboard.
It exercises the task graph and artifact contract without LSF.

## LSF experiment

```bash
ass-flow-demo \
  --backend lsf \
  --queue normal \
  --project example \
  --interface eth0 \
  --output /shared/path/ass-flow-runs
```

`LsfClusterSettings` maps a deliberately small ASS-facing configuration into
`dask_jobqueue.LSFCluster`. It starts with zero workers, uses the invoking
Python executable, selects random scheduler and dashboard ports, enables
per-cluster mutual TLS, and scales to the requested number of LSF worker jobs.
The generated worker script is retained for inspection. Temporary TLS material
uses an owner-only `.dask-control` directory inside the run unless an explicit
shared temporary directory is supplied through the Python API. Jobqueue keeps
that material for the cluster object's lifetime, so abnormal termination can
leave private control files that require operator cleanup.

The prototype assumes:

- the output root and Python environment are visible on every worker;
- `--python-executable` names that shared environment when the invoking Python
  path is not suitable;
- the selected network interface lets workers reach the scheduler;
- LSF permits the requested queue, project, memory, CPU, and wall time; and
- cluster policy permits a Dask worker allocation to execute the placeholder.

No real compute-farm or LSF smoke test is possible in the repository test
suite. The pure LSF translation is tested without submitting jobs.

## Architectural reading

This experiment does not equate a Dask task with an ASS invocation, an LSF job
with a logical flow node, or a completed Future with accepted evidence. It also
does not settle whether long licensed simulations should execute inside Dask
worker allocations or through a future direct-LSF adapter.

The current arithmetic functions make intended replacement seams executable.
The named deferred-capability catalog keeps additional questions visible
without turning them into prematurely stable interfaces:

- real Sidecar, simulator, parser, and CACE-shaped operations;
- restart and scheduler reconciliation;
- complete artifact identity, caching, and staleness;
- result validation and evidence promotion;
- local, direct-LSF, and Dask routing;
- retry, cancellation, concurrency, licence, and budget policy;
- result-dependent plan extension; and
- the generic `StudySpec` versus domain-profile boundary.

The next change should be selected from running this slice against a real
study, not by filling every stub in advance.
