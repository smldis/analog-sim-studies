# Analog Sim Studies: A Headless, Python-Native Study System

This is a vision statement, not a description of what exists today. Where it
says "is", read "aims to be". The implemented scope is currently much narrower
(see [the challenges analysis](design/manifesto-challenges.md)); that gap is
intentional and is closed module by module.

## The vision

Build our own headless study and development system on analog circuit design.

 It should feel like one coherent tool to an operator while
remaining a composition of narrow independent modules underneath.
We value composition over inheritance to enhance maintainability.

Headless is the key word. Plain files and CLI-first interfaces make every
capability equally usable by a human at a shell, a CI pipeline, and an agent —
low latency, scriptable, reviewable in version control. No cockpit, no GUI
project state, no proprietary database holding the authored intent. Python is
the authoring and extension language; materialized files are the
portable evidence.

## Why

The commercial environments (Virtuoso ADE Explorer/Assembler, Solido) list the
right features — corners, sweeps, Monte Carlo, regressions, spec reports — but
their day-to-day usability is low: freezing sessions, heavy resource use,
complex APIs, and reusable intent bound to licenses and GUI-centered state.
Reimplementing the features that matter as open, file-based, headless modules
serves the actual daily needs better, and is free of charge.

With the advent of AI new tooling can be build to automate from basic tasks to
advanced ones, and the scope is greatly widening. Now, even the handcrafted work
such as analog design can be enhanced by AI, and intuition is not anymore an
exclusive quality of human work.

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

## Components:

Components have ontologies. They are concrete git sub repositories that we
are building for composition. Nested in a hierarchy of directories.

## Verification
The concrete pains have not changed:

- repeating the same simulation setup in many variants
- managing parameters, corners, and sweeps
- reusing testbench structure across projects
- launching many runs without turning everything into shell glue
- evaluating results in code instead of by hand
- knowing which results depend on which inputs, and what must be re-run

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
