# ASS Run Ontology

## Purpose and scope

ASS Run walks a validated Plan and executes it. It owns dependency order,
readiness, the threading of each invocation's outputs into the inputs that
reference them, and what happens to the rest of a plan when something fails.

It exists because that responsibility had no home. A Plan could be authored and
a single attempt could be executed durably, but the loop joining them lived in
an example. Deciding *when* work runs is a distinct concern from owning one
attempt's record, and keeping it separate is what allows the obvious
alternative — letting Dask decide readiness — to replace this unit rather than
require rewriting another.

## Mode of being

**Development state:** `prototype`

The unit currently studies whether a plain sequential driver is sufficient
before reaching for a scheduler. It executes one invocation at a time in the
order the Plan already determines. No concurrency, no scheduling policy, no
placement decisions.

Its evidence is a plan that runs, reuses everything on a second run, reruns
exactly the edited branch and its dependents on a third, blocks successors of a
failure rather than running them against inputs that do not exist, and passes a
file written by one step to the step that reads it.

## Current contracts

- Distribution: `ass-run`, Python 3.10 or newer, depending on `ass-exec`. It
  does not import `ass_flow`: the Plan arrives as a document.
- `run_plan(document, transport, ...)` executes every invocation in dependency
  order and returns a `RunReport`.
- `transports` maps a policy name to the substrate providing it. Each
  invocation lands on the placement ASS Flow already resolved for it, so one
  corner may take a dedicated LSF job while cheap reductions stay local. A
  placement no transport provides is fatal: running work somewhere other than
  where it was asked to run would change what a study means.
- A single `transport` provides every placement, which suits a uniform run and
  is wrong as soon as placements differ.
- Each attempt records requested, resolved, and observed placement separately.
- `commands` and `outputs` bind an operation to how it actually runs — a
  command line, and which files or streams count as results. The Plan declares
  meaning; a run binds mechanism. Operations absent from both run in-process.
- A file output contributes its recorded address to downstream inputs, because
  that is what a downstream command opens. Other outputs contribute values.
- Work whose inputs are unchanged is reused rather than repeated; that decision
  belongs to `ass-exec` and is not re-implemented here.
- On failure the default is to stop. Successors are reported as `blocked`,
  never run against inputs that do not exist. `stop_on_failure=False` continues.
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

It has no concurrency, no scheduling or placement policy, no retry policy of its
own, and no study lifecycle. Concurrency is the next real question and will
either be added deliberately or answered by adopting Dask.

## Child composition

There are currently no child units.
