# Conceptual flow foundation

**Status:** architectural hypothesis

**Development mode:** prototype self-study

This note records a possible foundation for flows within Analog Sim Studies.
It is not an implementation plan, a production specification, or a workflow
engine selection. The broader engine survey remains in
[Deferred study-runtime and flow-engine findings](deferred-study-runtime-research.md).

The current repository does not implement a complete durable study runtime.
The bounded `study-flow` unit now exercises one local-preparation and
Dask/Jobqueue execution shape, without claiming authority for the rest of the
lifecycle. The manifesto distinguishes authoring, planning, execution,
evaluation, decision, and preservation as responsibilities of a coherent study
system. The hypothesis below gives those responsibilities a vocabulary that
can be tested by runnable prototypes and revised from the resulting evidence.

## A flow is not a DAG

A directed acyclic graph can represent one resolved plan, but it is not the
being of a flow. An ASS study may begin with incomplete intent, branch after an
observed result, revisit an earlier assumption, or require a human, script, or
agent to decide what should happen next. Treating the graph as the authored
flow would collapse strategy, planning, execution history, and engineering
judgment into one object.

Within ASS, a **flow** is instead a reusable strategy for moving a study toward
evidence or a decision. Applying that strategy to the study's present intent,
context, evidence, and policy produces a plan. The plan may be a DAG, a simple
sequence, a set of independent jobs, or an increment that is followed by
another planning decision.

This is intended to be generic within ASS. It is not an attempt to define a
universal workflow platform.

## Foundational vocabulary

The following nouns should remain distinguishable even if an early prototype
represents several of them with the same files or Python types.

### Study

The durable envelope around a bounded piece of analog-design work. It relates
intent, context, actions, evidence, and decisions without requiring the initial
question to be complete or simulation to be present from the beginning.

### StudySpec

The authored and versioned expression of the study's current intent and its
selected domain profile. It identifies the question, relevant context,
constraints, requested evaluations, and policies without embedding executor
state.

### Flow

A reusable planning strategy. It interprets a `StudySpec` together with
available evidence and policy and proposes inspectable work that may advance
the study.

### Plan

Resolved, inspectable work produced by applying a flow to the current study.
It records dependencies and complete proposed invocations before execution
resources are spent. A plan is derived evidence about what the system intends
to do, not another source of authored intent.

### Invocation

One executable operation with resolved inputs, configuration, operation
identity, and resource requirements. It is independent of the executor that
will eventually run it.

### Attempt

An append-only historical fact about trying an invocation. Successful, failed,
partial, cancelled, and policy-stopped attempts all remain attempts; none is
silently rewritten into a different history.

### ArtifactRef

A portable reference to materialized data. It identifies the artifact's
logical kind, location or retrieval information, format or schema, producer,
relevant identity, and provenance without requiring large data to live inside
the study manifest.

### Evidence

Validated outputs promoted from attempts. Evidence can include artifact
references, measurements with units, diagnostics, specification outcomes,
plots, tables, and explicit uncertainty. Successful process completion alone
does not establish engineering evidence.

### Decision

An interpretation of evidence by an authorized human, script, or agent. A
decision may accept a conclusion, reject an alternative, revise intent, or
initiate another bounded iteration. It points to its evidence and retains
material uncertainty rather than replacing it with an untraceable assertion.

### Policy

Explicit bounds on resources, concurrency, retries, simulator licences,
budgets, autonomy, stop conditions, and authority to promote evidence or make
decisions. Policy changes what actors may do; it does not create a different
study format.

## Lifecycle and revision

```text
StudySpec + existing evidence + policy
                  |
                Flow
                  v
                Plan
                  |
              Executor
                  v
              Attempts
                  |
         evaluate and promote
                  v
              Evidence
                  |
              Decision
           _______|_______
          |               |
      conclude       revise StudySpec,
                     evidence, or policy
                           |
                           +----> plan again
```

Planning, execution, evaluation, promotion, and decision are separate
responsibilities. This separation permits an executor to report what happened
without deciding what the result means, and permits an evaluator to produce a
valid specification failure without misclassifying it as an execution error.

The revision loop is fundamental. An iterative or adaptive study is not a
malformed DAG; it is a sequence of explicit states, plans, attempts, evidence,
and decisions whose history remains inspectable.

## Relation to the four execution concepts

The four concepts extracted from the workflow-tool research occupy distinct
places in this lifecycle:

1. **Domain-owned study state and artifact identities** surround the complete
   lifecycle and keep its durable meaning independent of an engine.
2. **Cartesian, zipped, and adaptive sweep algebra** belongs to planning. It
   expands domain intent into invocations without deciding how they execute.
3. **Immutable evidence and provenance publication** validates attempts and
   makes selected results part of the durable study.
4. **A replaceable executor boundary** consumes invocations and produces
   attempts without becoming the authority for intent, evidence, or decisions.

Authored study and evaluation semantics precede these execution seams.
Evidence promotion and engineering decision follow them. The four concepts are
therefore a runtime middle, not the whole study lifecycle.

## Study state as a projection

The current hypothesis is that `StudyState` should be a reproducible projection
or snapshot over durable authored and append-only records, rather than one
mutable, ever-growing object. A convenient current-state view may exist, but it
should be reconstructable from versioned intent, plans, attempts, promoted
evidence, decisions, and explicit supersession relations.

This is not yet a storage decision. A prototype may use directories and plain
manifests, while a later client may maintain an index or database. The
projection hypothesis exists to prevent a client cache, scheduler database, or
live Python object from becoming the only account of the study's being.

## Hybrid authoring hypothesis

The current authoring hypothesis combines inspectable data with ordinary
Python:

- Authored study intent is serializable, reviewable, and durable.
- Python defines reusable operations, evaluators, and flow strategies.
- Applying a flow materializes a resolved plan as inspectable plain data before
  execution.
- Attempts and evidence are append-only records or manifests.
- Executor futures, scheduler job identifiers, and engine database objects do
  not become the only durable authority.
- Repository and ontology composition identify capability ownership; they do
  not imply runtime flow order.

This keeps a shell, CI job, script, interface, or agent on the same public
contracts while allowing Python-native extension where declarative data alone
would be restrictive.

## Generic core and domain profiles

The generic foundation should own the lifecycle nouns, identity boundaries,
publication rules, and adapter seams. It should not presume that every study
is a characterization campaign.

A CACE-compatible characterization profile may add analog parameters, corners,
sweeps, simulator setup, measurements, units, plots, and specification limits.
Other profiles may support comparisons, structural investigations, design
changes, failure investigations, or work in which simulation is initially
absent. Profiles add domain meaning; they do not replace the common lifecycle.

The principal unresolved boundary is:

> What belongs in the generic `StudySpec`, and what belongs in a domain profile
> such as CACE?

Answering this from abstraction alone would contradict the repository's
prototype mode. A representative end-to-end study should expose which ideas
are genuinely shared and which only appeared generic before use.

## Foundational invariants

The following are stronger than any current choice of file format or engine:

- Durable authored intent and evidence remain engine-neutral and inspectable.
- An attempt does not become evidence without explicit validation and
  publication.
- A decision points to evidence and preserves relevant uncertainty.
- Dependency and staleness identity includes every relevant code, simulator,
  model or PDK, adapter, configuration, and environment input that can affect
  meaning.
- Infrastructure failure, simulator or tool failure, valid engineering or
  specification failure, partial result, cancellation, and policy stop remain
  distinguishable.
- Capability ownership follows ontology composition, while containment grants
  no runtime order, precedence, or authority.
- Schema evolution must not make preserved evidence unintelligible.

## Deferred choices

This foundation does not yet choose:

- a workflow engine or executor implementation;
- a directory, JSON, YAML, database, or object-store encoding;
- exact hashing and cache-key algorithms;
- a query or indexing service;
- static, incremental, or dynamically generated planning as the sole model;
- the granularity of an invocation or attempt; or
- the final boundary between the generic core and domain profiles.

These are questions for runnable prototype slices. Their failures, awkwardness,
and useful features are evidence through which the repository can revise this
foundation and its future ontology.
