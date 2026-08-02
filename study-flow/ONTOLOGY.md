# Study Flow Ontology

## Purpose and scope

Study Flow is a runnable experiment in applying a replaceable Dask execution
substrate to an engine-neutral, inspectable plan. It records one local
preparation, maps an injected chain of ordinary Python operations over two
generic work items, reduces their outputs, and preserves attempts and artifacts
independently of live Dask Futures.

The current backend boundary includes an in-process local Dask cluster and a
configuration factory for Dask Jobqueue on LSF. This is evidence about a
possible execution seam, not a selection of Dask as the project-wide flow
engine.

## Mode of being

**Development state:** `prototype`

Its present form studies whether authored inputs, port-declared operations,
resolved invocations, execution attempts, and output artifacts remain
intelligible while Dask supplies temporary scheduling. The same contract can
run unrelated operation bindings without changing the executor. Running it on
an available LSF farm should expose further friction around networking,
environments, artifact publication, and executor boundaries.

The graph shape remains deliberately bounded: one shared input, one mapped
operation chain, and one reduction. The current contracts and backend API are
not presumed final.

## Current contracts

- Python model: `FlowSpec`, `WorkItemSpec`, `OperationSpec`, resolved
  `InvocationSpec`, `ArtifactRef`, append-only `AttemptRecord`, `PreparedFlow`,
  and `CompletedFlow`.
- Python execution: `prepare_flow`, injected operation bindings passed to
  `submit_prepared`, explicit local/LSF flow runners, and convenience demo
  runners.
- CLI: `ass-flow-demo`, which runs the two-item neutral demonstration locally
  by default and can target an explicitly configured LSF cluster.
- Authored input: frozen contract envelopes with JSON-compatible shared and
  per-item values, snapshotted as `flow-spec.json` for each run.
- Derived plan: `plan.json`, materialized before mapped work and naming
  operation identities, ports, dependencies, and placement roles without
  naming an executor as semantic authority.
- Materialized history: one shared-input artifact and preparation attempt,
  per-operation output and attempt files, and one reduced `result.json`.
- Executor state: `DaskExecutionHandles`, Futures, worker addresses, and LSF
  identifiers are operational details and do not replace those files.

## Contribution to the parent

The unit contributes a headless experiment for compiling generic operation
bindings into mapped and reduced Dask work, plus a concrete LSF Jobqueue
configuration seam and inspectable attempt/artifact history.

## Exclusions

It is not a complete study runtime, workflow language, domain-operation
registry, durable reconciler, cache, evidence authority, or production cluster
service. It provides no built-in integration with a characterization system or
other domain framework. Successful operation output remains an attempt result,
not accepted engineering evidence.

## Child composition

There are currently no child units.
