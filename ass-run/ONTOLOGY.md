# ASS Run Ontology

## Purpose and scope

ASS Run walks a validated Plan and executes it. It owns dependency order,
readiness, the threading of each invocation's outputs into the inputs that
reference them, and what happens to the rest of a plan when something fails.

It exists because that responsibility had no home. A Plan could be authored and
a single attempt could be executed durably, but the loop joining them lived in
an example. Deciding *when* work runs is a distinct concern from owning one
attempt's record, and keeping it separate is what allowed the obvious
alternative — letting Dask decide readiness — to arrive as a second kernel
rather than a rewrite. That alternative has now been adopted (2026-08-04, user
direction); see `docs/vision/open-concepts.md` for the argument and the
measurements behind it.

**Readiness is a kernel, not the unit.** What the unit owns is the *binding* a
run performs: which substrate provides a placement, which command implements an
operation, and which address an upstream output landed at. `ass_run.binding`
holds those rules once, and both kernels use them, because changing which
kernel decides readiness must change how long a plan takes and nothing else.

## Mode of being

**Development state:** `prototype`

Two kernels exist, holding the same meaning.

`driver.run_plan` executes one invocation at a time in the order the Plan
already determines. It needs no scheduler and remains the reference: its
evidence is a plan that runs, reuses everything on a second run, reruns exactly
the edited branch and its dependents on a third, blocks successors of a failure
rather than running them against inputs that do not exist, and passes a file
written by one step to the step that reads it.

`graph.run_plan_graph` gives readiness to Dask. Its decisive evidence is that
the two kernels produce the same input digests and the same values for the same
Plan, and that a result recorded by one is reused by the other. Adoption is
recorded, but the kernel has not yet run a real study; its concurrency,
dashboard, and failure isolation are untested against anything but fakes.

## Current contracts

- Distribution: `ass-run`, Python 3.10 or newer, depending on `ass-exec`. It
  does not import `ass_flow`: the Plan arrives as a document.
- `run_plan(document, transport, ...)` executes every invocation in dependency
  order and returns a `RunReport`.
- `run_plan_graph(document, ..., client=...)` executes the same Plan as a Dask
  graph and returns the same `RunReport`, in the same plan order. The
  `distributed.Client` is required rather than created: a cluster's shape is an
  operational decision — how many concurrent jobs a site tolerates, whether a
  dashboard is served — and a library that started one silently would be making
  it for the operator. `distributed` is an optional dependency reached by
  explicit import.
- Concurrency under the graph kernel is `threads_per_worker`. There is
  deliberately no limit parameter: a waiting invocation costs about 16 KiB of
  thread and one client process, so this is a safety rail rather than a scarce
  resource, and the real ceiling is the site's MAX JOB policy, per-user process
  limits, and the licence count.
- A transport is copied to the worker that runs an invocation, because Dask
  serializes every task — even on an in-process cluster. A transport that
  cannot be serialized is refused by placement name before anything runs, and
  one that must stay a singleton has to be built on the worker rather than
  passed to it.
- Task keys are named after the authored key, so an operator watching a sweep
  sees corners rather than digests. Tasks are submitted impure: reuse is
  `ass-exec`'s decision against declared inputs, never Dask's against call
  signatures.
- `transports` maps a policy name to the substrate providing it. Each
  invocation lands on the placement ASS Flow already resolved for it, so one
  corner may take a dedicated LSF job while cheap reductions stay local. A
  placement no transport provides is fatal: running work somewhere other than
  where it was asked to run would change what a study means.
- A single `transport` provides every placement, which suits a uniform run and
  is wrong as soon as placements differ.
- Each attempt records requested, resolved, and observed placement separately.
- The placement's *options* travel with it on the bundle. This unit does not
  interpret them: which queue or licence an option names is a fact about the
  substrate, so the transport reads them. A transport that cannot express a
  declared option refuses, and the run reports the invocation as failed rather
  than running it under conditions nobody asked for.
- `commands` and `outputs` bind an operation to how it actually runs — a
  command line, and which files or streams count as results. The Plan declares
  meaning; a run binds mechanism. Operations absent from both run in-process.
- A file output contributes its recorded address to downstream inputs, because
  that is what a downstream command opens. Other outputs contribute values.
- Work whose inputs are unchanged is reused rather than repeated; that decision
  belongs to `ass-exec` and is not re-implemented here.
- On failure the sequential kernel stops. Successors are reported as `blocked`,
  never run against inputs that do not exist. `stop_on_failure=False` continues.
- The graph kernel blocks *dependents* and lets independent branches finish: a
  dependent of failed work returns a blocked outcome rather than raising. One
  corner failing does not abandon the other forty-nine, which is what a sweep
  wants and what the sequential kernel cannot offer. This is a deliberate
  difference in scope of failure, not in the meaning of a result.
- `on_event` reports each outcome as it happens, so a long run is observable
  without waiting for the report.

## Contribution to the parent

With `ass-flow` and `ass-exec` this completes one operator-facing path: author
a flow, plan it, run it, and rerun it. This unit is the "run it" step.

## Exclusions

ASS Run owns no attempt identity, journal, transport, reuse policy, or artifact
recording — all `ass-exec` — and neither produces nor validates a Plan.

It does not branch on results. Every plan it runs was fully determined before it
started, which is what makes a rerun predictable. Result-dependent control,
fallback, and recovery remain open architectural questions recorded in
`docs/vision/open-concepts.md`, not features quietly added here.

It has no scheduling or placement policy of its own, no retry policy, and no
study lifecycle. Concurrency is no longer its question: under the graph kernel
it is the cluster's thread count, and under the sequential one there is none.

It does not own the cluster. It neither creates, sizes, nor tears one down, and
it does not report LSF's view of a job: with `bsub -I` a transport blocks from
submission to terminal, so nothing here distinguishes a corner pending in the
queue from one simulating. That observation belongs to a watcher over the
attempt records, recorded as wanted in `docs/vision/open-concepts.md`.

## Child composition

There are currently no child units.
