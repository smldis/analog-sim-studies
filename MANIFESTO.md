# Analog Sim Studies: A Headless, Python-Native Study System

This manifesto defines the system we aim to build, not the implementation that
exists today. The gap is intentional and will be closed module by module.

## Vision

Build our own headless, Python-native system for analog-design work. To an
operator it should feel like one coherent tool; underneath, it should remain a
composition of narrow, independent modules. We favor composition over
inheritance because explicit boundaries make the system easier to maintain,
test, replace, and extend.

Plain files and CLI-first interfaces make the same capabilities available to
an engineer at a shell, a CI job, a script, or an agent. Operations should be
low-latency, scriptable, and reviewable in version control. Authored intent
must not be owned by GUI state or a proprietary database. Python is the common
authoring and extension language, while materialized files are portable
evidence.

## Core commitments

### Headless authority

Headless describes where authority lives, not which interfaces may exist.
Every essential operation must work without an interactive session, and every
durable piece of authored intent must survive outside a process or user
interface.

Human-facing interfaces may improve exploration and visualization, but they
are replaceable clients of the same public contracts. Closing a client cannot
erase the work, and using one cannot create a second form of intent hidden from
the CLI, CI, or an agent.

This gives every capability a design test. If it depends on private process
state, an unrecorded click sequence, or an opaque database, it is not yet part
of the coherent system. Once it has an explicit operation, inspectable intent,
named outputs, and provenance, human-facing interfaces can be added without
weakening the headless core.

### Python-native composition

Python-native means that engineers can author, compose, inspect, and extend the
system in ordinary Python. It does not require every dependency to be
implemented in Python. Simulators, schedulers, data tools, and adopted
components may use whatever implementation suits them. Explicit adapters
isolate those dependencies, while Python remains the common language for
connecting their capabilities.

### File-based portability

File-based boundaries are visible and transferable. Authored files are
reviewable source. Materialized files are portable evidence, with manifests
and metadata describing derived artifacts. Large or externally stored results
remain addressable through recorded identities and provenance.

Portability does not require committing every raw waveform to Git. It requires
that another permitted operator can discover what exists, determine how it was
produced, and retrieve or reproduce it without reconstructing hidden session
state.

## The unit of work: a “study” (working name)

“Study” is the current umbrella name for a bounded unit of analog-design work.
It may be a characterization or verification campaign, a design change, a
sizing exploration, a comparison between variants, an investigation of a
failure, or the production of an engineering conclusion. It may begin before
the question is fully formed and become more precise as evidence accumulates.
Simulation may be central, secondary, or absent from its earliest stages.

The durable envelope around the work matters more than the noun. It brings
together:

- **Intent:** what the engineer is trying to learn, change, demonstrate, or
  decide.
- **Context:** the designs, testbenches, models, assumptions, constraints, and
  tool configuration on which the work depends.
- **Actions:** the edits, generations, simulations, transformations, and
  evaluations performed.
- **Evidence:** the materialized inputs, outputs, measurements, plots, tables,
  and reports produced.
- **Decisions:** the conclusions, accepted tradeoffs, rejected alternatives,
  and next questions that give the evidence meaning.

The name is deliberately provisional. A future vocabulary may distinguish an
experiment, investigation, campaign, task, or design iteration, or replace
“study” altogether. Renaming it must not require redesigning component
contracts: those contracts depend on intent, context, actions, evidence, and
decisions, not on one favored noun.

## Work capabilities and integration boundaries

Trusted simulators, device models, process data, and other facilities remain
external dependencies reached through narrow adapters. Backend-specific
details stay at that boundary. Authored intent, evaluation logic, provenance,
and results remain inspectable and portable. Changing a backend should require
an adapter or explicit configuration change, never manual rediscovery of the
work.

The system should support these shared responsibilities:

1. **Author.** State questions, inputs, variations, measurements, and
   acceptance criteria in Python and plain files.
2. **Plan.** Materialize inspectable jobs and dependencies before spending
   simulation resources.
3. **Execute.** Run locally, in CI, or on shared compute through adapters, with
   bounded concurrency and resumable work.
4. **Evaluate.** Turn raw outputs into named measurements, specification
   results, plots, tables, and machine-readable summaries.
5. **Decide.** Let a human, script, or agent accept the evidence, revise the
   work, or propose the next bounded experiment.
6. **Preserve.** Record enough provenance to explain and reproduce each result
   and identify work made stale by changed inputs.

These are conceptual responsibilities, not a mandate for one large workflow
module. Different components may implement different responsibilities. Their
shared vocabulary aligns component contracts and keeps the operator experience
coherent.

## Why

Closed commercial environments impose recurring costs through freezing
sessions, heavy resource use, complex APIs, and reusable intent bound to
licenses and GUI-centered state. We should reimplement only the features that
serve daily engineering needs, as open, file-based, headless modules.

The recurring pains are concrete:

- copying the same simulation setup into many variants;
- managing parameters, corners, and sweeps;
- reusing testbench structure across projects;
- launching many runs without turning the workflow into shell glue;
- evaluating results in code rather than by hand; and
- knowing which results depend on which inputs and what must be rerun.

## AI-assisted work

AI lowers the cost of creating and operating specialized workflows. An
assistant can turn an engineering procedure into code and build small tools to
investigate a hypothesis. Humans and agents may both propose what to try, but
intuition does not replace evidence and expert judgment remains necessary.
Conclusions must rest on inspectable inputs, simulator results, explicit
measurements and specifications, and recorded provenance.

The system must remain useful without AI and safe to extend with it. Humans, CI
jobs, scripts, and agents use the same public interfaces and produce artifacts
held to the same standards. Agents have no privileged route around validation,
provenance, review, or version control. This preserves the value of
conventional automation as agent capabilities improve.

Autonomy is a policy attached to a study, not a separate architecture. Policies
bound which files an agent may edit, which operations it may invoke, how many
resources it may spend, which stop conditions end an exploration, and which
decisions require human approval. Increasing autonomy changes explicit
permissions, not study formats or component contracts, and cannot introduce
unreviewable state.

## Filesystem ontology composition

Components are nested Git subrepositories with ontologies. The directory
hierarchy is part of the architecture, not merely storage. Filesystem
containment expresses composition: a descendant contributes to its closest
containing ontology node, and that contribution continues upward into the
whole system.

Containment grants no inheritance, specialization, override, or precedence. A
deterministic postorder may present the composed ontology, but presentation
order never defines authority.

An ontology declares a component’s semantic responsibility: its purpose,
scope, contracts, and the contributions of contained components. The
composition root describes the whole system. Nested ontologies add local
precision without restating the manifesto. Together, the repository tree and
the ontology files beside the code make the architecture discoverable to a
human or agent.

## Component boundaries and contracts

A component earns its boundary by being independently useful, testable, and
replaceable through explicit contracts. Those contracts use the same basic
distinctions throughout the system:

- **Authored intent** is the human- or agent-written source of truth.
- **Materialized artifacts** are derived evidence and can be regenerated.
- **Operations** are headless CLI and Python entry points.
- **Provenance** records inputs, versions, configuration, and operations.
- **Composition** connects declared outputs and inputs without hidden shared
  state.

Put a capability in the smallest component whose ontology can fully explain
it, and promote only its explicit contract upward. A cross-cutting
responsibility belongs in its own component when it has an independent
purpose; directories higher in the tree gain no implicit privilege.

A subrepository is an implementation and versioning boundary. Its ontology is
the semantic boundary. Stable contracts and shared conventions create
operator coherence without requiring a monolith. Work remains traceable across
components, and one component’s artifacts remain consumable without knowledge
of its internals.

Each new module should deliver a useful end-to-end slice, declare its boundary,
and compose without precedence rules.

## Verification and progress

The existence of an API or command does not verify a capability. The system
should keep at least one versioned, representative, end-to-end reference
workflow. Feature parity with a commercial suite is not the first milestone.
The reference workflow should prove that an operator can:

1. author a reusable setup once and derive named variants from it;
2. inspect resolved parameters, corners, jobs, and dependencies before
   execution;
3. execute again from a clean environment, interrupt safely, and resume
   without repeating results whose inputs remain valid;
4. evaluate measurements and specifications in code without manual
   transcription while retaining human-inspectable evidence;
5. change an input and explain which work is stale, which remains valid, and
   what must run again; and
6. trace a reported conclusion back to its exact inputs.

Further capabilities should extend this path without hidden state or a second
way to express the same intent.

Progress is measured in useful vertical slices. A slice is complete when it
removes recurring manual work, crosses component boundaries through explicit
contracts, and leaves a reproducible conclusion. The next slice is selected
from friction and daily benefit observed while using the current one. Shared
infrastructure is built only when a slice requires it.

Start from whatever runnable base exists, and adopt an existing component when
it fits; explicit module boundaries make adoption safe. Early implementation
limits must not be baked into the vision. When a module needs a narrower local
contract, it documents that narrowing while the manifesto retains the broader
target.
