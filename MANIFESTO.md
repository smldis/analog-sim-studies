# Analog Sim Studies: A Headless, Python-Native Study System

This is a vision statement, not a description of what exists today. Where it
says "is", read "aims to be". The implemented scope is currently much narrower
(see [the challenges analysis](design/manifesto-challenges.md)); that gap is
intentional and is closed module by module.

## The vision

Build our own headless analog-study system in the same broad product category
as CACE: define studies, expand conditions, prepare simulator inputs, launch
runs, evaluate measurements and specifications, track dependencies, and retain
the resulting evidence. It should feel like one coherent tool to a user while
remaining a composition of narrow Python modules underneath.

Headless is the key word. Plain files and CLI-first interfaces make every
capability equally usable by a human at a shell, a CI pipeline, and an agent —
low latency, scriptable, reviewable in version control. No cockpit, no GUI
project state, no proprietary database holding the authored intent. Python is
the authoring and extension language; materialized files and manifests are the
portable evidence.

## Why

The commercial environments (Virtuoso ADE Explorer/Assembler, Solido) list the
right features — corners, sweeps, Monte Carlo, regressions, spec reports — but
their day-to-day usability is low: freezing sessions, heavy resource use,
complex APIs, and reusable intent bound to licenses and GUI-centered state.
Reimplementing the features that matter as open, file-based, headless modules
serves the actual daily needs better, and is free of charge.

There is also a new reason that did not exist when the commercial environments
were designed: AI-assisted creation of tooling. When the working substrate is
plain files, typed transformations, and CLIs, an assistant can build ad-hoc
advanced tooling tailored to one team's — or one study's — specific needs, on
demand and at negligible cost: a bespoke sweep strategy, a one-off report, a
project-specific spec checker, a migration script for an old deck. Tooling
stops being a scarce product to buy and becomes something grown around the
problem at hand. Closed GUI environments cannot participate in this: their
state is not readable, their actions are not scriptable, and so an assistant
can neither inspect what exists nor safely extend it.

The natural progression is from assisted tooling to intelligent automation:
first an agent drafts edits and studies for a human to review, then it runs
bounded loops itself — propose a variant, launch it, evaluate the result,
decide what to try next — with the artifact trail as its memory and audit log.
Every property this manifesto commits to (headless interfaces, explicit
typed edits, named artifacts, provenance, reviewable diffs) is exactly what
makes such automation trustworthy: the agent's work arrives as inspectable
changes with the same guarantees as a human's, and version control remains
the shared record. The modules are designed for human use, but agents are
first-class users of the same contracts.

The concrete pains have not changed:

- repeating the same simulation setup in many variants
- managing parameters, corners, and sweeps
- reusing testbench structure across projects
- launching many runs without turning everything into shell glue
- evaluating results in code instead of by hand
- knowing which results depend on which inputs, and what must be re-run

## Product direction: a CACE-like tool of our own

The project is no longer defined by the scope of `sidecar_edits`.
`sidecar_edits` is the first proven component and preserves an important
adoption boundary, but the repository-level goal includes the complete
analog-study lifecycle.

The integrated tool should provide:

- Python-authored studies, conditions, corners, sweeps, Monte Carlo policies,
  measurements, specifications, and plots
- explicit expansion from authored intent to individually inspectable run cases
- preparation of arbitrary existing simulator directories without forcing the
  circuit into a new canonical representation
- pluggable simulator, netlisting, extraction, and result adapters
- local and parallel execution first, with remote execution as an adapter
- named input/output artifacts and dependency-aware stale detection
- content-addressed run identity, provenance, resumability, and selective reuse
- machine-readable results plus concise human reports
- the same contracts for interactive users, CI, and bounded agentic loops

This is not a compatibility clone of CACE and need not inherit its datasheet
schema, project layout, placeholder language, or internal names. CACE is both a
baseline and a source of working ideas. Our differentiator is a Python-native,
deck-first system in which ordinary simulator inputs remain authoritative,
every generated case is materialized and inspectable, and dependencies and
results have explicit artifact identities.

The product-level interface should compose the modules rather than hide them.
A user may run one end-to-end study through a coherent CLI and Python API, while
another user may import only preparation, execution, measurement, or dependency
facilities. Modularity is an architectural property of the product, not a
reason to avoid building the integrated tool.

## Shape: an integrated tool over composable modules

Each module has a narrow contract, a CLI where that is useful, and a Python API.
The integrated study layer owns lifecycle composition and shared identities; it
does not absorb every implementation into a monolith.

The module map, roughly in dependency order:

1. **Study model and expansion.** Define named studies, testbenches, parameter
   sets, conditions, corners, sweeps, measurements, specifications, and
   execution policies in normal Python. Expand them deterministically into
   explicit cases and preparation requests.
2. **Preparation — `sidecar_edits` (exists, proven).** Copy an authoritative,
   already-working simulator input directory and apply typed, explicit,
   source-traced edits. The simulator-valid files remain authoritative; the
   edits are the reviewable record of intent. This is the project's strongest
   architectural commitment, and it lives in its own module so the commitment
   does not cap the rest of the vision. A working base can also be pure
   scaffolding — something that already runs, later filled with the real data.
3. **Execution.** Headless launching of the expanded runs: local, parallel,
   or farmed out through replaceable backends; no GUI in the loop.
4. **Verification-flow dependencies.** Studies and steps declare the named
   artifacts they consume and produce (an extracted netlist, an operating
   point, a measured value), and the flow re-runs only what is stale — the
   part of CACE's design most worth adopting, and what mflowgen demonstrates
   at build-flow scale. This needs care: it is where scope creep toward a
   general workflow engine would start, but the need is real enough that
   dedicated tools exist for it.
5. **Measurement and specification evaluation.** Measures and pass/fail
   checks in Python, with results traceable to the runs and inputs that
   produced them.
6. **Study record and reporting.** Persist the expanded plan, exact inputs,
   tool identities, logs, raw-result references, measurements, limits, and
   summaries as one navigable study record. Reports are projections of this
   record, not the only copy of the result.

The integrated layer composes these contracts into the CACE-like user
experience: author once, inspect the expansion, execute, resume, evaluate, and
understand why each result exists or is stale.

The old build-worthiness checklist maps onto these modules: each item is
judged inside the module that owns it, against that module's users and
baseline, not as one monolithic test. Build-worthiness itself is answered —
`sidecar_edits` already pays for itself in daily use.

## First credible vertical slice

The first integrated milestone should be deliberately smaller than CACE but
exercise the whole architectural spine:

1. author one OTA study in Python;
2. expand process, voltage, and temperature conditions into explicit cases;
3. materialize each case from an existing ngspice directory through
   `sidecar_edits`;
4. launch ngspice locally with bounded parallelism;
5. extract one or two measurements and evaluate named limits;
6. emit a provenance manifest and machine-readable study result;
7. rerun without repeating cases whose declared inputs and evaluation code are
   unchanged.

The milestone is successful when the generated decks, commands, logs,
measurements, limits, cache decisions, and their relationships can all be
inspected without hidden framework state. Supporting every simulator, every
CACE feature, a GUI, adaptive optimization, or a general workflow language is
not required for this slice.

## Reproducibility

Full reproducibility is the target, not just repeatable text preparation.
External inputs — model libraries, simulator versions, numerical options,
seeds — are tracked by version and provenance, or vendored locally when
tracking is not enough. Weaker, cheaper tiers (repeatability of the prepared
inputs, byte-identical materialization) are still offered, but as explicitly
labeled lighter guarantees, not as the ceiling.

To be precise about terms: study-level dependencies above mean one study
consuming a named artifact produced by another. They are unrelated to the
recognition-pass dependencies in the functional-decomposition design
documents, which are internal to netlist analysis.

## Reuse: templates and typed edits

Reuse must be explicit, not "a directory that happened to work once" copied
around undocumented. Typed edits are the current reviewable backbone; template
harnesses answer a real need for concise, reusable testbench structure. How
much logic a template may contain before its rendered effect stops being
reviewable is a module-level design question — the manifesto commits to the
goal (explicit, inspectable reuse), not to today's implementation defaults.

## The landscape

Existing tools are references, contributors of ideas, and sometimes candidate
parts of the composition itself — their submodules may map directly onto ours.

- **CACE** — the closest product baseline and proof that integrated,
  file-authored analog characterization is useful. Its conditions,
  testbenches, execution, measurements, limits, reporting, and verification
  dependencies should be studied feature by feature. We are building our own
  Python-native, deck-first member of this category rather than treating CACE
  as merely an external tool or copying its schema and terminology.
- **Hdl21 / VLSIR** — Python-native circuits, generators, and parameters done
  well; strong inspiration for authoring ergonomics. VLSIR is an
  implementation detail, not part of this scope.
- **cocotb** — inspiration in packaging and author experience (Python-first,
  reusable verification assets), explicitly not in mechanism: no live
  procedural access to the analog domain.
- **mflowgen** — explicit artifact graphs with sandboxed steps; the reference
  point for the dependency module.
- **Edalize** — tool/backend abstraction boundaries.
- **Commercial ADE** — the feature checklist to reimplement headlessly, and
  the usability bar to beat.

Licensing caution: GPL-licensed tools (spicelib, PyOPUS) are off-limits at the
source level — do not read their code, to keep this codebase safely
permissive. Concepts and documentation are fair game; for PyOPUS it may be
worth asking the maintainer about an Apache-2/MIT relicense.

## Final thoughts: scoping and opportunism

The sections above optimize for clarity of direction, so two looser principles
live here instead of diluting them:

- **Opportunism.** Start from whatever runnable base exists, adopt an existing
  tool's component when it fits, and let real daily benefit (as with
  `sidecar_edits`) decide what gets built next — the module boundaries make
  this safe.
- **Scoping.** Early phases should avoid baking today's limits into the
  vision. When a module needs a narrower contract than the manifesto's
  language, the module documents the narrowing; the manifesto stays the
  broader target.
