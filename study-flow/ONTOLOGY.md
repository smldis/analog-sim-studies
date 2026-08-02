# Study Flow Ontology

## Purpose and scope

Study Flow is a runnable experiment in applying a replaceable Dask execution
substrate to ASS-owned study intent. It materializes an inspectable local
preparation, maps two small `simulate -> measure` flows, reduces their
measurements, and preserves the resulting demonstration artifacts independently
of live Dask Futures.

The current backend boundary includes an in-process local Dask cluster and a
configuration factory for Dask Jobqueue on LSF. This is evidence about a
possible execution seam, not a selection of Dask as the project-wide flow
engine.

## Mode of being

**Development state:** `prototype`

Its present runnable form studies whether a locally authored dependency,
derived task plan, mapped execution, reduction, and filesystem publication can
remain intelligible while Dask supplies temporary scheduling. Running the same
shape locally and on an available LSF farm should expose useful friction around
networking, environments, attempt publication, and executor boundaries.
Failures and awkwardness are evidence for revising the component or rejecting
the dependency; the current data classes, graph shape, and backend API are not
presumed final.

## Current contracts

- Python API: `ass_study_flow`, including the demonstration specification,
  local preparation, Dask submission, local execution, and LSF cluster
  configuration.
- CLI: `ass-flow-demo`, which runs the two-case demonstration locally by
  default and can target an explicitly configured LSF cluster.
- Authored input: a small immutable `StudySpec`; the reference instance has
  exactly two cases and is snapshotted as `study-spec.json` for each run.
- Derived plan: `plan.json`, materialized before Dask work is submitted.
- Materialized outputs: one study-spec snapshot, one preparation manifest,
  per-attempt simulation and measurement JSON, and one reduced `summary.json`.
- Executor state: Dask Futures and LSF identifiers are transient operational
  details and do not replace those files.

## Contribution to the parent

The unit contributes a headless, inspectable experiment for local preparation
followed by mapped and reduced Dask execution, plus a concrete LSF Jobqueue
configuration seam.

## Exclusions

It is not a complete study runtime, workflow language, simulator adapter,
durable reconciler, cache, evidence authority, CACE implementation, or
production cluster service. Its arithmetic operations stand in for real
simulation and measurement. It does not claim that Dask workers are preferable
to direct per-simulation LSF jobs.

## Child composition

There are currently no child units.
