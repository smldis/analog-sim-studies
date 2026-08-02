# Study Flow

This unit is a runnable architectural experiment: can ASS keep a neutral plan,
attempt history, and its artifacts intelligible while Dask supplies temporary
scheduling and Dask Jobqueue supplies an optional LSF worker pool?

It deliberately tests only this shape:

```text
                           mapped item alpha
                       operation -> operation
                      /                       \
local shared input                              reduction
                      \                       /
                       operation -> operation
                            mapped item beta
```

The graph shape is bounded, but its operation functions and JSON values are
injected. The component does not require domain-specific nouns or numeric
results.

## Observable contract

`prepare_flow()` snapshots a `FlowSpec` as `flow-spec.json` and writes the
resolved `plan.json` before mapped work. The plan names each operation, visible
input/output ports, dependencies, item identity, and placement role. It does
not make Dask part of authored intent.

Preparation then runs synchronously in the controller. It publishes
`shared-input.json` and a successful append-only preparation attempt. This is
the one local dependency consumed by both mapped chains; local placement does
not give it a different kind of domain meaning.

Each bound mapped operation receives an `OperationContext` and a dictionary of
declared input ports. It must return a JSON object whose keys exactly equal its
declared output ports. The executor wrapper, rather than the function, owns:

- attempt identity and placement metadata;
- input and output `ArtifactRef` records;
- atomic JSON publication;
- successful or failed attempt records; and
- dependency validation between mapped stages.

The reduction consumes the final output from every authored item in authored
order and publishes `result.json`. The demonstration reducer merely collects
the outputs; domain evaluation and evidence promotion are outside this unit.

## Headless seams

Run an arbitrary set of bindings through a caller-owned Dask client:

```python
prepared = prepare_flow(spec, shared_output_root)
handles = submit_prepared(client, prepared, operation_bindings)
completed = complete(handles)
```

Or let the package create the client while retaining the same authored and
operation contracts:

```python
completed = run_local_flow(output_root, spec, operation_bindings)
completed = run_lsf_flow(output_root, lsf_settings, spec, operation_bindings)
```

`DaskExecutionHandles` contains stage and reduction Futures. `CompletedFlow`
contains the preparation, all durable attempts, and the final `ArtifactRef`.
The temporary type is explicitly Dask-named so it cannot be mistaken for the
engine-neutral record.

## Reference bindings

The command-line demonstration uses two work items, `alpha` and `beta`, and
three ordinary Python functions:

1. `combine_inputs()` retains the shared and per-item JSON values.
2. `describe_output()` reports their field names.
3. `collect_outputs()` places both descriptions in one collection.

These operations intentionally do not model a useful engineering domain. A
second automated test binds unrelated uppercase, character-count, and total
operations to the same executor, demonstrating that the runtime does not
dispatch by the reference operation names.

```bash
ass-flow-demo --output build/demo
ass-flow-demo --list-deferred
```

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
`dask_jobqueue.LSFCluster`. It starts with zero workers, uses the selected
Python executable, requests random ports, enables per-cluster mutual TLS, and
scales to the requested number of LSF worker jobs. The generated worker script
is retained for inspection.

The prototype assumes the output root and Python environment are visible on
every worker, the network interface connects workers to the scheduler, and LSF
permits the requested queue and resources. Repository tests render the secured
job script without submitting real farm jobs.

## Architectural reading

This experiment distinguishes:

- an authored `FlowSpec` from its derived plan;
- an operation identity from the Python function currently bound to it;
- an engine-neutral invocation from its placement role;
- an attempt record from the output artifact it produced;
- successful execution from evidence acceptance; and
- durable records from Dask Futures and scheduler job identifiers.

It does not yet provide arbitrary graph authoring, recovery, caching, adaptive
planning, evidence promotion, or cross-component operation discovery. Those
remain explicit research seams. The next change should be selected from using
this generic slice with an independently useful ASS operation, not by embedding
one domain's vocabulary back into the executor.
