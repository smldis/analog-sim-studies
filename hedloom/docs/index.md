# Hedloom

Hedloom is the front door: author a study, see what it will do, and run it — from
one import.

```python
from hedloom import Site, artifact, file, flow, local, operation, plan, shell, study, sweep
```

This page is the user guide, and covers all of that. How the package is put
together, and why it exists at all, is in [Hedloom internals](internals.md) — a
contributor's page that nothing here depends on.

The runnable examples referenced throughout live in
[`examples/`](../examples/rc_corners.py), and are the source of every snippet
below — nothing here is invented.

## Authoring an operation

`@operation` here is `hedloom_flow`'s decorator, wrapped so the body it already
kept is remembered as callable, under the operation identity the Plan
records. Calling a decorated operation inside a flow does not run it — it only
threads a graph edge — but the body is real code that runs later, at
`submit`:

```python
@operation(config={"key": parameter(str), "temp_c": parameter(int)},
           outputs={"deck": file("corner.cir", kind="spice-deck")})
def write_deck(out, *, key: str, temp_c: int) -> None:
    out.deck.write_text(DECK_TEMPLATE.format(key=key, temp_c=temp_c, ...))
```

(`examples/rc_corners.py`)

Because the fingerprint that decides reuse is taken from this source —
docstring included — editing an operation body reruns every invocation of
that operation, and editing only a comment or blank line does not (the
fingerprint ignores blank lines and trailing whitespace). This is coarser
than "the behaviour changed": a needless rerun costs time, a missed one costs
correctness, and the tradeoff is made in favour of correctness.

## Authoring a flow

A `@flow` body is ordinary Python that runs once, at authoring time, to build
the static graph. It does not run again at `submit`; only the operations it
called do:

```python
@flow
def rc_sweep(corners):
    measured = []
    for corner in sweep(corners, key="key"):
        deck = write_deck(key=corner["key"], temp_c=corner["temp_c"])
        measured.append(corner_frequency(simulate(deck)))
    return {"verdict": compare.options(key="compare")(measured).verdict}
```

Because a flow body runs at planning time and produces a fixed graph, a Plan
still predicts everything that will run before anything is spent. There is no
result-dependent control here — a flow cannot branch on a value it does not
yet have, because it never has one; every value inside a flow body is a
handle, not a value (see below). Result-dependent control (retry, `until=`,
conditional reapplication of a flow to committed state) is an open
architectural question, not a feature quietly available through `submit` —
see `docs/vision/open-concepts.md` at the repository root.

A Plan is built inside a `plan(...)` block and finished with the flow's own
outputs:

```python
def build():
    with plan(default_policy=local()) as draft:
        outputs = rc_sweep.options(key="rc")(CORNERS)
    return draft.finish(outputs=outputs)
```

## Handles are references, never values

Calling an operation or a flow does not run it — it returns a handle: a
reference to a planned result, plus the artifact kind it will carry. A handle
is not the value it will eventually stand for, and reading it as though it
already had one is refused rather than silently answered:

```python
deck = write_deck(key="cold", temp_c=-40)   # a handle, not a path
if deck:                                    # HandleUsedAsValue (also TypeError)
    ...
```

`hedloom_flow.authoring.ArtifactValue.__bool__` and `__eq__` both raise
`HandleUsedAsValue`. The alternative — answering `True`, or comparing handles
by identity or by name — would be an answer about the *reference*, and
silently wrong about the *result*: a plan is built before anything runs, so
no handle has a value yet to be true, false, or equal to anything. This is
also why a `@flow` body cannot branch on what an operation "returns": there is
nothing there to branch on until `submit` runs it.

## Config vs inputs

An operation's `config` is data folded directly into that invocation's
identity — a temperature, a queue name, a spec limit. Two invocations of the
same operation with different config are different attempts, full stop; there
is no dependency edge, because nothing has to run first to produce a
temperature.

An operation's `inputs` are artifacts: references to another invocation's
declared output, or to a source declared outside the plan. Every input
becomes a dependency edge in the Plan, and the invocation cannot run until
whatever produces that input has.

```python
@operation(inputs={"deck": DECK},                    # an edge: waits on write_deck
           outputs={"raw": file("corner.raw", kind="simulator-raw-results")})
def simulate(deck, out):
    ...
```

```python
@operation(config={"point_id": parameter(str), "vdd_v": parameter(float), ...},
           inputs={"base": SIDE_CAR_BASE, "edits": SIDE_CAR_EDITS},
           ...)
def prepare_run(base, edits, out, *, point_id, param_set, process, vdd_v, temp_c):
    ...
```

(`examples/ota_pvt.py`) — `point_id`, `vdd_v` and the rest are config: they
are PVT-point facts already known when the study is authored, and changing one
reruns exactly that invocation. `base` and `edits` are declared sources
(external files this plan did not produce) and still arrive as inputs, because
a source is "produced" before it is used — see reuse, below.

## `sweep`

`sweep(points, key=...)` opens a keyed scope: every operation and flow call
made inside the loop is scoped under `<point-key>:<operation>` unless it names
its own key. This is what lets three operations across three PVT corners not
need nine hand-written keys, and it is what keeps reuse from depending on an
author remembering to key every call — an unkeyed call's identity depends on
authored order, so inserting an unrelated call earlier can silently renumber
it.

```python
for corner in sweep(corners, key="key"):
    deck = write_deck(key=corner["key"], temp_c=corner["temp_c"])
    measured.append(corner_frequency(simulate(deck)))
```

`key=` may be a string naming a field on each item, or a callable
(`key=lambda item: item.key`, used in `examples/ota_pvt.py`, where a PVT point
is a small object rather than a dict).

## `shell()` bodies vs value-returning bodies

An operation body decides *what* runs; it never decides *whether* it runs.
Reuse, identity, ordering and placement are all settled before the executor
calls the body, so writing Python inside an operation cannot acquire
scheduling authority.

A body that computes a value returns it directly:

```python
@operation(inputs={"raw": RAW}, outputs={"hz": returned(kind="corner-frequency")})
def corner_frequency(raw) -> float:
    ...
    return frequency
```

A body that wants a command run *at its placement* returns `shell(...)`
instead of calling a subprocess itself:

```python
@operation(inputs={"deck": DECK},
           outputs={"raw": file("corner.raw", kind="simulator-raw-results")})
def simulate(deck, out):
    return shell("env", "SPICE_ASCIIRAWFILE=1", "ngspice", "-b", "-r", out.raw, deck)
```

Returning a `Shell` rather than running a subprocess is what lets the command
reach a placement: locally it is a subprocess bound to this process's
lifetime; give the operation an `lsf(...)` policy and the identical body puts
that same command on its own `bsub -I` job instead, with that invocation's
queue, cores and licences — a one-line change on the operation, not a
different body:

```python
@operation(..., policy=lsf(queue="normal", cores=1, memory_mb=2048,
                            licences={"ngspice": 1}))
def simulate_ac(...):
    return shell("ngspice", "-b", "-r", out.raw, deck)
```

(`examples/ota_pvt.py`, `simulate_ac`, with the LSF policy left as a comment —
every placement this reference has actually run against a real substrate is
`local`; the launcher reaching a real LSF job is designed and, at the `hedloom`
layer, untested against a real farm.)

## `out.<name>` workspaces

A body that declares a file output — `file("corner.cir", ...)` — receives an
`out` argument if (and only if) its signature names `out`. `out.<name>` is a
path inside that attempt's own workspace directory, at exactly the location
the executor will check afterwards for that declared output. The two cannot
drift apart because they are the same declaration, read once:

```python
def write_deck(out, *, key: str, temp_c: int) -> None:
    out.deck.write_text(...)
```

A body that names no file outputs — only `returned(...)` or `stdout(...)` —
is not handed `out` at all; asking `out.<name>` for a name the operation never
declared raises `AttributeError` rather than resolving to something
unexpected.

## `Site` and site profiles

Nothing about *where* a study runs is authored into the study. A `Site` holds
what is not the study: which substrate provides each named placement, the
roots attempt records and workspaces are written under, the address spaces a
declared source resolves through, and (for the Dask kernel) a thread count.

```python
site = Site(
    root=str(work / "attempts"),
    workspace_root=str(work / "work"),
    address_spaces={"repository-relative": str(repo_root)},
)
```

(`examples/rc_corners.py`, `examples/ota_pvt.py`) — constructed directly here,
because these examples need no placement besides the default in-process one.

A profile can also be read from TOML with `Site.from_file(path)`. Relative
paths in the profile resolve against the *profile's own directory*, not the
working directory, so a study run from elsewhere still means the same thing.
A profile may declare:

```toml
[study]
root = "attempts"
workspace_root = "work"

[address_space]
repository-relative = "../.."

[placement.lsf]
kind = "lsf-interactive"
queue = "normal"

[kernel]
threads = 32
```

`[study].root` is required; everything else is optional. A `[placement.*]`
table names a substrate this site can *build* from configuration alone —
today only `kind = "lsf-interactive"` — and refuses an unknown `kind` outright
rather than silently dropping the placement, because a study that quietly
lost a placement would fail much later as an opaque `UnsupportedPlacement`
that blames the Plan for what is a site configuration mistake.
`kind = "in-process"` needs Python callables no TOML can hold; that
placement's transport is added afterwards with `Site.with_transports(...)`.

`Site.__post_init__` anchors `root`, `workspace_root`, and every address space
to absolute paths at construction time; a relative root used to silently
break `shell()` operations run from a different working directory than the
one the study was authored in.

## `study(...)`

`study(plan_object)` pairs a finished Plan with the operation bodies declared
in this process (every `@operation` this module has imported, keyed by the
identity the Plan already recorded), or with an explicit
`implementations={...}` mapping:

```python
subject = study(build())
```

## `.summary()` — before anything is spent

`Study.summary()` renders every invocation, its operation, and the placement
it resolved to, and spends nothing:

```python
print(subject.summary(), "\n")
```

```
plan schema 2: 10 invocations, 0 sources
  cold:write_deck        write_deck        local
  cold:simulate           simulate          local
  cold:corner_frequency   corner_frequency  local
  ...
  compare                 compare           local
```

This is the manifesto's requirement made concrete: a study is complete and
inspectable before it spends anything, because `study.plan` is the exact
document `submit` will run — not a second, hand-written description of it.

## `.submit(site=, client=, watch=, on_event=)`

```python
run = subject.submit(site=site, watch=True)
```

`submit` binds the same operations, resolves the same Site, and walks the
same document `summary()` showed. `site=` is required. `client=None` (the
default) walks the plan sequentially, in one thread — right for a plan small
enough not to need a cluster. Passing a `distributed.Client` gives readiness
to Dask instead (`hedloom_run.graph.run_plan_graph`); the cluster is always the
caller's to build, never something `submit` starts silently, because how many
concurrent jobs a site tolerates is an operational decision a library must
not make on its own. Nothing about *what* runs or what it means changes
between the two kernels — only how long it takes:

```python
cluster = LocalCluster(processes=False, n_workers=1, threads_per_worker=len(jobs),
                        dashboard_address=":8787")
with cluster, Client(cluster) as client:
    run = subject.submit(site=site, client=client, watch=True)
```

(`examples/ota_pvt_clean.py`, the one example that runs on Dask.) Run it with
`.toolchain/venv/bin/python hedloom/examples/ota_pvt_clean.py [--fresh]` — it needs
`bokeh` for the dashboard, which the units themselves deliberately do not
depend on, so it runs through the project-local toolchain venv rather than
plain `python` (`.toolchain/README.md`). `--fresh` points the run at records
nothing has written yet, so every corner really simulates and is watchable on
the dashboard; an ordinary second run reuses everything and finishes before
the dashboard repaints, which is correct and not a bug to work around. The
example also declares `SIMULATOR_HOLD_SECONDS`, a config value each corner's
body waits on before invoking ngspice purely so a sweep this small stays on
screen long enough to watch — a documented instrument, not a claim about how
the study behaves in general.

`watch=True` prints one line per invocation as it settles
(`[disposition] key  operation  outcome`). `on_event=callback` is the same
hook without the printing, for a caller that wants its own progress reporting;
passing both is redundant — `on_event` wins.

Every declared source is read exactly once per submission, before anything
else runs: that one reading both fingerprints the source (decides whether
downstream work is stale) and locates it (what the body that named it as an
input actually receives), because those two questions must agree about which
file was meant.

## `StudyRun`

`submit()` returns a `StudyRun`, addressable the way the study was authored:

```python
run["cold:simulate"].artifacts["raw"]["address"]
run.value            # the plan's conclusion: its final invocation's value
run.succeeded         # True iff every invocation succeeded
run.summary()          # one line per invocation: disposition, key, outcome
```

`run["cold:simulate"]` looks up an `InvocationOutcome` by the authored key
(or, for an unkeyed call, its Plan-assigned ID) — raising `KeyError` for a key
nothing was authored with, rather than returning `None` and deferring the
mistake. `run.value` is deliberately "the last invocation's value", not
"whatever the flow returned as a Python dict": a plan's conclusion is its
final step, by construction.

## Reuse, and what invalidates it

Work whose declared inputs are unchanged since a previous run is reused, not
repeated — this is `hedloom_exec`'s decision, made against content-addressed
identity, and `hedloom` neither re-implements nor overrides it. What is folded
into that identity, concretely:

- the operation's name, version, and a fingerprint of its body's *source*
  (comments and blank lines excluded, everything else included — see
  "Authoring an operation" above);
- every declared `config` value;
- every declared input's own identity, transitively — an upstream change
  propagates downstream automatically;
- a declared external source's **content** fingerprint (a hash for a file
  small enough to hash cheaply, a hash of every file under a directory
  source, or a `stat` fallback for anything implausibly large for an
  authored input) — so editing an input netlist *in place*, without changing
  its declared address, correctly invalidates every invocation that read it.

What is deliberately **excluded**, so that changing it never invalidates a
result: which queue an invocation ran on, its walltime, cores, host, and
general environment. Retuning a corner's memory request or moving it to
another queue reuses the result it already produced.

Only a `succeeded` attempt is reused automatically. A failure may be the
work's own verdict, or something incidental to it (an OOM kill, a preempted
node) that the record cannot tell apart from a real failure — so failed
attempts are retained rather than silently retried, and a human decision to
accept one is a separate, durable action (`hedloom_exec.reuse.accept_for_reuse`).

## `hedloom.visualize` — looking at a study before running it

`hedloom_flow.experimental.local_dask` lowers a Plan to Dask `Delayed` values, as
a bounded instrument for testing whether Plan IR lowers to Dask at all — see
`hedloom-flow/docs/architecture.md`. `hedloom.visualize` gives that lowering the one
use that needs no execution: a picture. Every operation is bound to a
stand-in that refuses to run — computing it raises `RefusedComputation`
(wrapped in the lowerer's own `InvocationExecutionError`) rather than
producing a number nobody simulated. `submit()` remains the only way a study
runs.

Two independent views, because they answer different questions:

- `structure(study)` reads the Plan document itself into plain nodes and
  edges — authored keys, operations, and placements, in the vocabulary the
  study was authored in. No Dask, no graphviz; works even for a plan the
  local lowering refuses (any plan bound for a farm).
- `render(study, "graph.svg")` draws the *lowered Dask graph* — task keys and
  projections, the shape a scheduler would see. Needs `graphviz` and a system
  `dot` binary.

```python
import hedloom.visualize as visualize

subject = study(build())
print(json.dumps(visualize.structure(subject), indent=2))
visualize.render(subject, "graph.svg")
```

`hedloom.visualize` is a submodule, not part of `hedloom`'s top-level `__all__` —
importing it is a deliberate, separate step from importing `hedloom` itself,
which is consistent with drawing a graph being a diagnostic, not part of the
authoring surface. `graphviz` (and, for the Dask dashboard shown above,
`bokeh`) are diagnostics the units themselves do not depend on; install them
into the project-local `.toolchain/venv` described in `.toolchain/README.md`
rather than into the unit's own environment.

## Further reading

- [`hedloom/ONTOLOGY.md`](https://github.com/smldis/analog-sim-studies/blob/main/hedloom/ONTOLOGY.md)
  for the unit's current contracts and what its own examples have and have not
  demonstrated (in particular: every placement run against a real substrate
  so far is `local`; the `lsf` launcher path is designed and untested against
  a real farm).
- `examples/ota_pvt.py` — the full OTA/PVT reference: structural analysis,
  real `ngspice`, real spec checking.
- `examples/ota_pvt_clean.py` — the same study reduced to the sign-off path:
  a written `report.md` deliverable, run on the Dask graph kernel.
- `examples/ota_pvt_clean_nested.py` — the staged-plan variant, described in
  [Hedloom internals](internals.md).
- [`docs/reference/ota-pvt-plan/`](../../../reference/ota-pvt-plan/README.md)
  at the repository root — the root-owned, cross-unit Plan declaration this
  study's shape is drawn from, plus its own real-execution binding.

```{toctree}
:maxdepth: 1
:caption: Working on this package

internals
```
