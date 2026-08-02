# Study Flow

Study Flow is a conceptual, runnable prototype of Dask as a replaceable ASS
execution substrate. Version 0.2 replaces the original simulation-shaped demo
contracts with a domain-neutral operation and artifact model; compatibility
with the 0.1 prototype is intentionally not retained.

The reference workflow contains one dependency executed and recorded by the
controller, followed by two identical mapped chains and one reduction:

```text
materialize shared input locally
        |
        +-> combine(alpha) -> describe(alpha) -+
        |                                        +-> collect -> result.json
        +-> combine(beta)  -> describe(beta)  --+
```

The operations receive declared JSON input ports and return declared JSON
output ports. They do not interpret simulation, measurement, characterization,
or other domain vocabulary. `run_local_flow()` accepts a `FlowSpec` and a
mapping from stable operation IDs to ordinary Python callables, while the
bundled demo supplies deliberately meaningless combine/describe/collect
bindings.

## Install and run locally

From this directory:

```bash
python -m pip install -e .
ass-flow-demo --output build/demo
```

The command starts two local threaded Dask workers. It prints the locations of
the derived plan and reduced result plus the number of durable attempt records.
Every run gets a new directory, so an existing result is never silently
replaced.

The headless seam is also directly usable:

```python
prepared = prepare_flow(spec, output_root)
handles = submit_prepared(client, prepared, operation_bindings)
completed = complete(handles)
```

`DaskExecutionHandles` owns the temporary Futures. `CompletedFlow` contains
only durable attempt and artifact references.

## Run through Dask Jobqueue on LSF

The same plan and operation bindings can allocate Dask workers through LSF:

```bash
ass-flow-demo \
  --backend lsf \
  --queue normal \
  --project my-project \
  --interface eth0 \
  --output /shared/path/ass-flow-runs
```

The output path and installed Python environment must be visible from the
submission host and every worker. Use repeated `--job-prologue` arguments when
the site requires environment setup, and `--python-executable` when workers
must use a different shared installation. The LSF worker script is saved beside
the plan before worker jobs are scaled.

Each cluster uses random scheduler ports and per-cluster mutual TLS. The Dask
dashboard binds to loopback. These defaults prevent accidental port clashes and
reject clients or workers without the credentials; they do not replace site
policy or a managed multi-user service.

## What the files mean

```text
<run-id>/
├── flow-spec.json
├── plan.json
├── shared-input.json
├── prepared.json
├── lsf-worker-job.sh       # LSF backend only
├── .dask-control/          # private temporary TLS material during LSF runs
├── attempts/
│   ├── prepare/<attempt-id>/attempt.json
│   ├── alpha/<operation-id>/<attempt-id>/
│   │   ├── attempt.json
│   │   └── output.json
│   ├── beta/<operation-id>/<attempt-id>/
│   │   ├── attempt.json
│   │   └── output.json
│   └── reduce/<operation-id>/<attempt-id>/attempt.json
└── result.json
```

The spec snapshot, plan, attempts, and artifacts remain after the Dask cluster
closes. An attempt records execution history separately from the data it
produced. Successful completion does not promote an output to engineering
evidence. The current files remain demonstration schemas rather than a complete
provenance model.

The LSF helper creates `.dask-control` with owner-only permissions because its
temporary credentials must be visible to workers through shared storage. Dask
Jobqueue retains those files for the cluster object's lifetime; an abnormally
terminated controller may leave private control material for operator cleanup.

## Deliberately deferred seams

`ass-flow-demo --list-deferred` prints unresolved questions including real
component bindings, restart reconciliation, artifact identity and staleness,
evidence promotion, executor routing, policy, adaptive planning, and operation
discovery. There is no deferred characterization-system integration in this
component. These entries are research stubs, not promised functionality.
