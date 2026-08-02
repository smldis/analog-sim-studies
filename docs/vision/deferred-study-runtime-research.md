# Deferred study-runtime and flow-engine findings

**Status:** deferred architecture research

**Research snapshot:** 2026-07-31

**Revisit when:** a representative study needs execution, interruption and
resume, stale-result detection, or shared-compute scheduling

This note preserves research for a future runtime use case. It is not an
implementation plan and does not select a workflow engine.

Since this research snapshot, the repository has gained a bounded `study-flow`
experiment using local Dask and a Dask Jobqueue configuration seam. That
prototype tests the engine-independent contract below; it does not supersede
the deferred engine decision.

## Current conclusion

Analog Sim Studies needs **workflow semantics**, but it does not currently need
a generic workflow engine.

The manifesto already requires an operator to inspect planned jobs and
dependencies, execute with bounded concurrency, interrupt and resume work,
evaluate measurements and specifications, identify stale results, and trace a
conclusion to its inputs. Those requirements eventually imply a runtime
contract.

The current units do not yet implement that study lifecycle. Introducing a
general DAG framework, provenance service, scheduler abstraction, or workflow
database before a useful vertical slice requires it would build shared
infrastructure ahead of observed friction. This would conflict with the
manifesto's direction to select infrastructure from actual daily use.

The root `composition.py` is also not the beginning of this runtime. It
composes repository-owned tests, documentation, and ontologies. Study
execution is a distinct responsibility and should eventually belong to an
independently useful unit.

## Contract to preserve

The durable study format should remain independent of any selected engine.
Engine-specific objects such as Pydra task values, LibreLane classes, redun
database identities, Parsl futures, or AiiDA ORM nodes must not become the only
representation of authored intent or materialized evidence.

A future runtime should approximate this transition:

```text
Step(validated_config, explicit_state, declared_artifacts) -> StepResult
commit(StepResult) -> new explicit_state
```

A step should have a stable type and version, declare its inputs, possible
outputs, configuration and resource needs, execute in an isolated attempt
directory, and write outputs out-of-place. Successful outputs should be
validated and published atomically. Failed attempts may leave diagnostic
evidence but must not masquerade as committed state.

The state should be serializable and should distinguish:

- authored study intent and resolved configuration;
- logical artifacts from their current path or storage location;
- small, queryable measurements, specification outcomes and diagnostics;
- large materialized artifacts such as waveforms, raw simulator output,
  netlists, plots and logs;
- logical steps, concrete invocations, cache identities, execution attempts
  and produced artifacts;
- complete, failed, skipped, stale and partial branches; and
- code, simulator, model, PDK, environment and adapter identities.

Large results should remain portable files or externally addressable
artifacts. The state should carry their identities, provenance and retention
policy rather than embedding large opaque values.

Planning, execution, artifact storage and indexing should remain separable.
This permits a transparent local runner first and a different executor later
without changing authored studies or historical evidence.

## Minimum useful vertical slice

The first study-runtime slice should implement only what proves the manifesto:

1. Resolve authored parameters, corners and variations into an inspectable job
   plan before simulation.
2. Give inputs, jobs and outputs stable identities.
3. Execute locally with bounded concurrency and one isolated attempt directory
   per job.
4. Publish a result manifest only after validating the attempt.
5. Resume by retaining results whose complete input identity is still valid.
6. Explain which results became stale after an input changes.
7. Produce named measurements and specification outcomes without manual
   transcription.
8. Trace one engineering conclusion to its exact inputs, tools and evidence.

This slice does not initially require a generic dynamic-DAG language, workflow
server, Kubernetes deployment, provenance database, plugin marketplace,
distributed scheduler, or workflow GUI. Those become candidates only when a
real study demonstrates the need.

## Candidate systems and transferable ideas

No system examined supplied the entire desired contract without imposing its
own durable authority or leaving important domain semantics to the
application.

| System | Useful ideas | Important qualification |
| --- | --- | --- |
| CACE | Analog vocabulary for parameters, conditions, corners, measurements, plots, units and specification limits; likely interchange target | Its vocabulary does not by itself provide the desired generic execution and provenance substrate |
| LibreLane | Immutable validated configuration, explicit state transitions, declared inputs and outputs, isolated step directories, seed discipline and reproducible bundles | Its state and configuration are shaped around digital implementation views, and scheduling, cache identity and queryable provenance are not its central contract |
| Pydra | Typed Python and shell tasks, content-aware file types, one hashed directory per task, caching, and explicit Cartesian/zipped split-combine algebra | It was still on the `1.0a` line at the research cutoff; construction and hashing semantics were evolving |
| AiiDA | Immutable scientific provenance, typed data, external-code plugins, parsers, restart handlers, transports and scheduler integration | Full durable/HPC operation brings profiles, database and messaging infrastructure; its virtual repository can conflict with plain-file authority |
| Parsl | Credible execution from a workstation through Slurm and other HPC systems, with retries, futures and checkpointing | It is an execution layer rather than a portable study-state, artifact or provenance contract |
| redun | Dynamic Python control flow, content-aware caching, queryable call history, execution attempts and explicit external-file values | It lacks maintained first-party Slurm support, does not enforce isolated immutable steps, and has artifact invalidation and pickled-history edge cases |
| jobflow / FireWorks | Nested and dynamic flows, typed outputs, future output references, detours and replacement operations | UUID-oriented persistence and rerun behavior are not equivalent to stable logical identity or content-addressed recomputation |
| Snakemake / CWL | Mature files-first execution and useful command-workflow interchange concepts | Files alone are too weak a representation for typed measurements, diagnostics, decisions and an aggregate study state |
| SiliconCompiler | Per-node manifests, metric goals and weights, selected fan-in inputs, and EDA tool/environment records | Its broad mutable schema and digital-compilation model would introduce a different domain authority |

The most useful synthesis is therefore conceptual rather than a package
selection:

- CACE contributes the analog vocabulary and interchange boundary.
- LibreLane contributes strict step-transition invariants.
- Pydra contributes typed task, work-directory, cache and sweep mechanics.
- AiiDA contributes the scientific provenance model.
- Parsl contributes a replaceable local/HPC execution boundary.
- SiliconCompiler contributes per-node EDA manifests and metric records.

## Adversarial findings

An initial research pass ranked redun as the most plausible low-burden
dependency. A follow-up search of issue trackers and practitioner reports
materially weakened that conclusion:

- Redun's request for a Slurm/HPC executor had remained open and unassigned
  since 2022.
- Redun users reported cases where script-produced files were not associated
  strongly enough with their producer for deletion to trigger the expected
  rerun.
- Cached Python objects could become unreadable after modules or classes were
  refactored.
- Pydra remained the closest generic task contract, but open discussions and
  hashing regressions confirmed meaningful pre-1.0 stability risk.
- AiiDA's lightweight local SQLite mode reduced the entry burden, but its full
  daemon/HPC mode retained database and RabbitMQ coupling.
- Jobflow users reported reconstructed dynamic flows receiving new UUIDs that
  broke stored output references.
- Parsl's HPC support remained credible, but cross-run memoization and
  heterogeneous scheduling had produced operational edge cases.

Consequently, no full engine merits unconditional adoption. Pydra is the
closest source of task and sweep ideas; AiiDA is the strongest mature
provenance reference; Parsl is the strongest shortlisted execution/HPC layer.
Redun remains a possible workstation or AWS-oriented implementation behind an
adapter, not the default architectural choice.

Practitioner evidence was sparse. A small number of Reddit reports described
redun as useful but young, AiiDA as difficult to learn but valuable once its
provenance model was adopted, and Parsl as useful for Slurm with potentially
large intermediate directory trees. These are anecdotes, not technical
verdicts. No credible first-hand Reddit production reports were found for
Pydra or jobflow during this pass.

## Default deferred hypothesis

Until an actual runtime slice falsifies it, retain this hypothesis:

> ASS owns a small, explicit analog study-state and artifact contract, while
> execution engines remain replaceable adapters.

“Small” means domain contracts and atomic publication rules, not a homemade
distributed scheduler. A transparent local executor may be sufficient for the
first slice. Pydra, Parsl, AiiDA, redun or another system can be adopted later
when its value is demonstrated by the use case.

The strongest alternative is to adopt AiiDA as the complete substrate. That
becomes reasonable if managed database authority, its repository abstraction
and its operational services are accepted as part of ASS. It is not aligned
with the current plain-file and low-burden commitments by default.

## Triggers for reopening the choice

Re-evaluate the engines when one or more of these become concrete:

- local execution can no longer express the required fan-out, fan-in or
  adaptive branching clearly;
- interruption, retries and partial results become difficult to make correct;
- shared Slurm, batch or cloud execution is required;
- provenance must be queried across many studies rather than inspected within
  one study;
- cache invalidation becomes too complex for explicit manifests;
- the number or granularity of simulation points creates material scheduler
  overhead; or
- interactive exploration must promote provisional evidence into a
  reproducible study.

At that point, evaluate candidates with a representative study rather than a
feature checklist. Record the simulator and license constraints, job count and
duration, desired execution granularity, concurrency, storage and waveform
retention, retry safety, determinism, shared-compute interface, query needs,
and promotion rules for exploratory results.

The evaluation should prove interruption and resume, partial failure, changed
input invalidation, exact conclusion provenance, and portability of material
evidence. A candidate that cannot preserve the engine-independent authored
study and result manifests should not become the durable authority.

## Research sources

Primary references:

- [CACE datasheet format](https://cace.readthedocs.io/en/latest/reference/datasheet_format.html)
- [LibreLane architecture](https://librelane.readthedocs.io/en/latest/reference/architecture.html)
- [Pydra hashing and caching](https://nipype.github.io/pydra/explanation/hashing-caching.html)
- [Pydra splitting and combining](https://nipype.github.io/pydra/explanation/splitting-combining.html)
- [AiiDA calculation concepts](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/calculations/concepts.html)
- [Parsl documentation](https://parsl.readthedocs.io/en/stable/)
- [redun design overview](https://insitro.github.io/redun/design.html)
- [jobflow documentation](https://materialsproject.github.io/jobflow/)
- [SiliconCompiler schema](https://docs.siliconcompiler.com/en/stable/reference_manual/schema.html)

Adversarial issue evidence:

- [redun Slurm/HPC request](https://github.com/insitro/redun/issues/25)
- [redun script-produced artifact association](https://github.com/insitro/redun/issues/106)
- [redun cached object refactoring failure](https://github.com/insitro/redun/issues/132)
- [Pydra third-party object hashing regression](https://github.com/nipype/pydra/issues/717)
- [jobflow local resume and UUID reconstruction](https://github.com/materialsproject/jobflow/issues/873)
- [Parsl cross-run checkpoint discovery](https://github.com/Parsl/parsl/issues/4040)

This evidence is a dated snapshot. Versions, maintenance and operating models
must be checked again when a concrete study triggers the decision.
