# ASS Run

ASS Run is the step that was missing between authoring a Plan and executing one
invocation: the loop that walks the graph.

It executes invocations in the order the Plan already determines, threads each
one's outputs into the inputs that reference them, reuses work whose inputs
have not changed, and stops (or, under one kernel, blocks only the affected
branch) rather than running successors against inputs that do not exist.

What it owns: dependency order, readiness, the binding of an invocation to a
substrate and a command, and what happens to the rest of a plan when
something fails. What it does not own: attempt identity, journals, transports,
and reuse policy (all `ass_exec`), and the Plan itself (`ass_flow`) — this unit
imports neither `ass_flow` nor Dask's base package; a Plan arrives here as a
document, and `distributed` is an optional dependency reached only when a
caller asks for the graph kernel.

## Two kernels, one meaning

Two kernels exist, and they are required to agree: the same Plan, walked by
either one, must produce the same input digests and the same values, and a
result recorded by one must be reusable by the other. What decides *when*
work runs is a kernel's job; what a placement means, which command
implements an operation, and which address an upstream output landed at are
not — those binding rules live once, in `ass_run.binding`, and both kernels
import them rather than restating them. That sharing is the whole guarantee
behind the invariant this unit exists to hold:

    Changing which kernel decides readiness changes how long a plan takes
    and nothing else — the same results, under the same identities.

### `driver.run_plan` — the sequential kernel

```python
from ass_run.driver import run_plan

report = run_plan(
    document, transports=transports, plan_id="rc-corners",
    root=str(work / "attempts"), workspace_root=str(work / "work"),
    source_addresses=site.source_addresses(document, fingerprints),
    source_fingerprints=fingerprints,
)
```

Executes one invocation at a time, in the order the Plan already determines.
It needs no scheduler and remains the reference implementation: a plan that
runs, reuses everything on a second run, reruns exactly the edited branch and
its dependents on a third, blocks successors of a failure rather than running
them against inputs that do not exist, and passes a file written by one step
to the step that reads it. `stop_on_failure=True` (the default) reports every
downstream invocation as `blocked` the moment anything fails; passing `False`
keeps walking the rest of the plan instead.

### `graph.run_plan_graph` — the Dask kernel

```python
from ass_run.graph import run_plan_graph

report = run_plan_graph(document, client=client, transports=transports, ...)
```

Gives readiness to Dask: one task per invocation, edges where one
invocation's output feeds another's input. Dask decides what is ready and how
much runs at once; it does not decide where anything runs, what an attempt's
identity is, or whether work may be reused — those stay with the Plan and
with `ass_exec`, exactly as under the sequential kernel. `client` is a
`distributed.Client`, required rather than created here: a cluster's shape —
how many concurrent jobs a site tolerates, whether a dashboard is served — is
an operational decision, and a library that started one silently would be
choosing it for the operator.

Adoption is recorded (2026-08-04, user direction; see
`docs/vision/open-concepts.md` at the repository root for the argument and the
measurements behind it), and `ass_run.graph.run_plan_graph` is a working
kernel, exercised by this unit's own test suite (`tests/test_graph.py`) and by
`ass/examples/ota_pvt_clean.py`, the one example in this repository that runs
on it. What remains unmet: a real farm. Every placement any example or test
has actually run is `local`; the LSF launcher reaching a real `bsub -I` job
under the graph kernel is designed and untested against a real cluster.

**Cluster shape matters, and the recommended one is unusual.** Use a local,
threaded cluster on the submit host:

```python
from distributed import Client, LocalCluster
cluster = LocalCluster(processes=False, threads_per_worker=32)
```

Three measured reasons, recorded in `docs/vision/open-concepts.md`:

* An invocation waiting on `bsub -I` costs about 16 KiB of thread and one
  client process. Concurrency here is a safety rail, not a scarce resource,
  and `threads_per_worker` *is* the rail — there is deliberately no limit
  parameter in this module. Size it from the site's MAX JOB policy and
  per-user process limits, which are facts to ask for rather than guess.
* Nothing secedes. A worker holding live `bsub -I` clients should read as
  running, and `secede()` would report it idle by excluding the task from the
  parallelism count.
* Threads avoid supervision and duplication, not serialization. A nanny that
  restarts a worker under memory pressure would take that worker's blocked
  clients with it — and, under owner-bound lifetime, that many running farm
  jobs. Measured, though, and worth knowing: Dask serializes every task even
  on an in-process cluster, so a **transport always travels as a copy**,
  never as a shared live object. Ours are effectively stateless per
  submission, so a copy is correct. A transport that must be a singleton — a
  pooled one holding a client to a second cluster — cannot be passed this way
  and needs a factory constructed on the worker instead.

A failed invocation blocks its dependents by returning a blocked outcome, not
by raising. Independent branches continue: one corner failing does not
abandon the other forty-nine, which is what a sweep wants and what the
sequential kernel cannot offer — a deliberate difference in the *scope* of a
failure between the two kernels, not in what a result means. Task keys are
named after the authored key rather than a digest, so an operator watching a
sweep's dashboard sees corners, not hashes; tasks are submitted `pure=False`,
because reuse is `ass_exec`'s decision against declared inputs, never Dask's
against call signatures.

## `ass_run.binding` — the rules both kernels share

- `select_transport(item, transports)` honours the placement the Plan already
  resolved for this invocation — ASS Flow resolves call override, operation
  default, plan default, then `local`, at planning time, and stores the
  result on the invocation; this is where that decision finally takes effect.
  A placement no transport provides raises `UnsupportedPlacement` rather than
  falling back silently: running work somewhere other than where it was asked
  to run is how a study quietly stops meaning what it says.
- `build_bundle(...)` assembles what one attempt is executed from: the
  invocation's own `placement` (requested and resolved, kept apart from what
  is later *observed*, so a run that came out slow or misplaced stays
  explainable), and `resolved_inputs` — upstream addresses and values,
  resolved for execution and never folded into identity, because which
  values they are is already implied by the declared input digests.
- `produced_by(item, result)` decides what an invocation contributes to its
  successors: a file output contributes its recorded **address**, because
  that is what a downstream command opens; anything else contributes its
  **value**.
- `resolve(reference, produced)` is one lookup that serves two kinds of
  reference. An operation's output is in `produced` because the invocation
  that made it already ran; a declared source is in there because the run
  seeded it before walking the plan at all — a source is produced before it
  is used. A reference nothing seeded resolves to nothing, which is exactly
  what every declared source did before this unit located them (see `Site`,
  below).

## `Site`

`ass_run.site.Site` holds what a Plan must not carry and a run needs anyway:
which substrate provides each named placement, the roots attempt records and
workspaces are written under, the address spaces a declared source resolves
through, and the thread count the graph kernel runs at.

```python
site = Site(
    root=str(work / "attempts"),
    workspace_root=str(work / "work"),
    address_spaces={"repository-relative": str(repo_root)},
)
```

`Site.__post_init__` anchors `root`, `workspace_root`, and every address
space to absolute paths at construction time; a relative root used to
silently break `shell()` operations run from a working directory other than
the one the study was authored in.

`Site.from_file(path)` reads a profile from TOML, anchoring every relative
path to the *profile's own directory* rather than the working directory, so a
study run from elsewhere still means the same thing. A `[placement.*]` table
names a substrate the site can build from configuration alone — today only
`kind = "lsf-interactive"` — and refuses an unknown `kind` outright rather
than skipping it, because a silently missing placement would surface much
later as an opaque `UnsupportedPlacement`, blaming the Plan for what is a
site configuration mistake. `kind = "in-process"` needs Python callables no
TOML can hold; that placement is added afterwards with
`Site.with_transports(...)`.

### Fingerprints: a source's identity must change when its content does

`ass_exec` identifies a declared source by its address and codec, never by
what is *at* that address — deliberately, since it resolves no addresses and
should not start. The consequence, before this unit existed: editing an
input netlist in place changed nothing about its declared address, so every
downstream invocation was reused and a study reported results computed from a
file that no longer existed in that form.

`site.fingerprints(document)` closes that gap by hashing what a declared
source's address currently resolves to, and both kernels pass the result into
`plan_bundles`. Sources are **hashed**, not stat'ed: an authored input is a
netlist or a JSON document, kilobytes at most, so hashing it costs nothing
and is immune to the `mtime` churn an ordinary `git checkout` causes.
Anything larger than 64 MiB — implausible for an authored input — falls back
to size and modification time, and the fingerprint's own prefix
(`blake2b:...` vs `stat:...`) says honestly which method produced it, so two
runs that fingerprinted the same file by different methods never look
identical. A directory source is identified by the content of everything
under it, so editing one file inside invalidates the whole tree. A declared
source that cannot be found is fatal, and fatal *before anything runs* — the
alternative is a run that reuses results computed from a file nobody can
show you. A run that supplies no fingerprints keeps the old, stale
behaviour: still correct, just blind to an edit made in place.

### `source_addresses`: delivering a declared source to the body that named it

A source has always been "produced" before it is used, in the identity
model's own terms; until `site.source_addresses(document, fingerprints)`
existed, nothing actually *delivered* it. Both kernels seed the `produced`
map with these addresses before walking the plan, so an operation that
declares an external file as an input receives a real path, resolved once,
on the machine that submits — the same reading that already fingerprinted it,
so delivery and staleness cannot disagree about which file was meant.
`fingerprints` is a required argument, not optional, because the key each
source takes is *derived* from it: passing a mismatched mapping would name
strings nothing looks up, indistinguishable from having no sources at all. A
run that supplies no addresses leaves such an input resolving to nothing, as
every run did before this existed.

Addresses resolve on the submitting machine, which is a claim about the
site: a path must mean the same thing on whatever host actually runs the
work. True on a shared filesystem, and assumed rather than checked — a site
without one would need staging, which this unit does not do.

## `threads`

`Site.threads` is concurrency for the graph kernel, not a tuning knob this
project invents values for: size it from the site's MAX JOB policy and
per-user process limits, and pass it to whatever `LocalCluster` the caller
constructs (`ass_run.graph`'s own docstring above states the reasoning this
field exists to record).

## Binding rules and what stays unowned

`commands` and `outputs`, passed to either kernel, bind an operation to how
it actually runs — a command line, and which files or streams count as
results — for a caller that has not (yet) adopted `ass`'s `@operation`/`shell()`
surface, which supplies both implicitly through the body itself. The Plan
declares meaning; a run binds mechanism. Operations named in neither run
in-process through the transport.

This unit owns no attempt identity, journal, transport, or reuse policy — all
`ass_exec` — and neither produces nor validates a Plan. It does not branch on
results: every plan it runs was fully determined before it started, which is
what makes a rerun predictable. Result-dependent control, fallback, and
recovery remain open architectural questions recorded in
`docs/vision/open-concepts.md`, not features quietly added here. It does not
own the cluster: it neither creates, sizes, nor tears one down, and with
`bsub -I` a transport blocks from submission to terminal, so nothing here
distinguishes a corner pending in the queue from one simulating — that
observation belongs to a watcher over the attempt records
(`ass_exec.watch`), not to this unit.
