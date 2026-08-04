# ASS Ontology

## Purpose and scope

ASS is the operator-facing composition of the three units beneath it. It owns
one thing none of them could own alone: the join between an authored study and
its execution. An author writes operations, a flow, and a plan; `submit` runs
exactly those, because it holds both halves rather than requiring two files to
agree about them.

It exists because that agreement kept being written by hand. A Plan declared
what work meant; a separate binding supplied implementations, command lines,
output paths, transports and roots; a third caller walked the result. Every
seam was a place where a study could run as something other than what was
authored, and the OTA reference needed six hundred lines of binding whose only
purpose was to restate the first file correctly.

## Mode of being

**Development state:** `prototype`

The unit studies whether one file can be a whole study without the Plan ceasing
to be inspectable before it spends anything. Its evidence is
`examples/rc_corners.py`: three RC corners against real ngspice, whose −3 dB
frequency is analytic, so the measured 165.96 kHz against an expected 159.15 kHz
is checkable — the 4.3% gap is the `dec 50` sweep grid, not a fabricated
number. A second run reuses all ten invocations; editing one corner's declared
temperature reruns that corner and the shared reduction only; editing an
operation's *body* reruns every invocation of that operation and nothing else.

Its second evidence is `examples/ota_pvt.py`, the OTA/PVT reference study
ported from the two files it used to be. Sixteen invocations over three PVT
points, four declared external sources, real ngspice AC sweeps, and gain/GBW/
phase-margin computed from the raw file rather than transcribed. What the port
demonstrates is the seam closing: `run_study.py` re-declared all six operations,
supplied their output paths, and wrote `del base, edits  # unresolved source
reference` three times because a declared source could not reach a body. None of
that survives. Editing `spec_limits.json` reran `evaluate-pvt` alone — fifteen
invocations reused — and flipped the verdict to failing; restoring the file
reused the original attempt rather than recomputing it.

What it has not met: a farm. Every placement it has run is `local`, so the
`shell` launcher reaching an `lsf` job is designed and untested. `ota_pvt.py`
carries the one-line policy change that would place each corner on its own job,
as a comment rather than a claim.

## Current contracts

- Distribution: `ass`, Python 3.11 or newer, depending on `ass-flow`,
  `ass-exec` and `ass-run`. `distributed` remains optional and is reached only
  when a run is given a client.
- `@operation` is `ass_flow`'s decorator, wrapped so the body it already kept is
  registered as callable under the operation identity the Plan records. The
  registry resolves a name the document names; it introduces no second notion
  of what an operation is.
- An operation body **runs**. It receives the inputs the Plan resolved, its
  declared config, and — if it names the reserved parameter `out` — a
  `Workspace` addressing that attempt's own directory. A body that computes a
  value returns it; a body that writes files writes to `out.<name>`.
- Returning a `Shell` makes the body a launcher: the command is executed at the
  placement the invocation resolved to. Locally that is a subprocess bound to
  this process's lifetime, and on `lsf` it is the delegate's `bsub -I` job with
  that invocation's queue, cores and licences.
- `A body decides what runs; it never decides whether it runs.` Reuse,
  identity, ordering and placement are all settled before a body is called, so
  writing Python cannot acquire scheduling authority.
- `sweep(points, key=...)` opens a keyed scope, so calls inside take
  `<point>:<operation>` unless they name a key. This is what keeps reuse from
  depending on an author keying every call by hand, where a mistake is silent
  staleness rather than an error.
- `study(plan).summary()` shows every invocation, its operation and its
  placement, and spends nothing. `submit(site=...)` then runs it; passing a
  `client` gives readiness to Dask, and without one the plan is walked in one
  thread.
- `StudyRun` is addressable the way the study was authored: `run["cold:simulate"]`
  is that invocation's outcome, and `run.value` is the plan's conclusion.
- A study may begin from a file it did not write. An operation declaring an
  `input_artifact` source as an input is handed its located path, and the same
  reading that locates it fingerprints it, so delivery and staleness cannot
  disagree about which file was meant. The path is resolved where the study is
  submitted, which assumes a shared filesystem for any placement that is not
  local.
- Nothing about the site is authored into the study. Placements, roots, address
  spaces and thread counts come from a `Site`, which a profile file can supply.

## Contribution to the parent

This is where the repository's author-plan-execute-evaluate path becomes one
operator gesture instead of three. It also answers a question the register left
open — whether any unit should be the operator-facing "flow" — by being it,
without absorbing what the others own.

## Exclusions

ASS owns no attempt record, no identity, no reuse policy, no transport, no
readiness, and no Plan validation. It composes; each of those remains where it
was, and `ass-exec` in particular imports neither this package nor Dask, which
is what keeps the kernel and the façade independently replaceable.

It does not branch on results. A flow body runs at planning time and produces a
fixed graph, so a Plan still predicts what will run. Result-dependent control is
recorded as future work in `docs/vision/open-concepts.md`, and `submit` is named
there as the façade where it would most plausibly arrive disguised as
convenience — a `retry=`, `max_iterations=` or `until=` argument is the
tripwire, not a feature.

The implementation fingerprint is coarser than "the behaviour changed": it
ignores blank lines and trailing whitespace, so an added comment reruns the work
that operation produced. Deliberate, since a needless rerun costs time and a
missed one costs correctness, but it is a limitation rather than a property.

## Child composition

There are currently no child units.
