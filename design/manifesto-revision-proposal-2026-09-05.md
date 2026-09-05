# Manifesto revision proposal

2026-09-05 — suggested replacement text, followed by its rationale.
This is a proposal for discussion, not an adopted change to `MANIFESTO.md`.

My recommendation is to update the manifesto around what building the system
has taught us about its purpose. Keep the broad vision, while giving more
weight to continuity of engineering work, learning through use, and the freedom
to revise the system's own structure. These ideas can guide architecture and
API choices without making the manifesto an agent procedure or a technical
roadmap.

## Suggested manifesto

### Analog Sim Studies: A Headless, Python-Native Study System

This manifesto states why we are building this system and the direction in
which we want it to grow. Its commitments guide development; its present
implementation is one evolving expression of them.

### Why we build

Engineering work accumulates through questions, experiments, interpretations,
and revisions. Too much of that work is spent reconstructing context: copying
setups, agreeing paths between tools, discovering which inputs produced a
result, repeating work whose validity is unclear, and recovering the reasoning
behind an earlier choice.

We want more of an engineer's effort to become reusable knowledge and useful
capability. A study should remain understandable when its author returns to it,
when another person takes it over, and when the tools used to perform it change.
The work should carry enough of its intent, context, evidence, and decisions
to continue without depending on one person's memory or one live session.

Our experience with commercial environments includes freezing sessions, heavy
resource use, complex APIs, and reusable intent tied to licenses and
GUI-centered state. Building our own open tools lets us shape the workflow
around daily engineering needs and retain control over how the work is
represented, inspected, and extended.

That freedom is useful when it improves the work. We should adopt, connect,
adapt, or build components according to the capability and clarity they bring.
Existing tools can supply part of the system or teach us a better way to
structure it.

### What we are building

We aim to build a coherent, headless, Python-native system for analog-design
work from independently useful, composable capabilities. It should support
the path from an initial question to an inspectable engineering conclusion,
including preparing designs, planning experiments, executing work, evaluating
results, and deciding what to do next.

Analog studies remain our present use and proving ground. Hedloom provides
planning and execution capabilities whose contracts carry no analog-specific
meaning. This separation lets the core serve its current users well and remain
available to other uses as they emerge. Generality should grow from meaningful
shared needs, with concrete studies keeping it accountable.

To an operator, the parts should form one understandable way of working.
Independently, each part should offer a useful capability through an explicit
contract. Coherence depends on agreeing what concepts mean and how work passes
between components; it does not require every capability to live in one package.

### Where we are now

The project already has runnable capabilities that compose into useful studies.
Development has moved beyond asking whether the pieces can be built. Their use
now lets us ask whether we have chosen the right pieces, whether their
boundaries explain the work, and whether their composition makes an engineer's
next step easier.

The current system is a prototype through which we study these questions.
Useful software and architectural inquiry belong to the same effort: each
real use can supply both a result and evidence about the system that produced it.

An awkward workflow may reveal an unfinished feature, a misplaced responsibility,
or an abstraction that no longer fits. We should be willing to distinguish
those possibilities. A mechanism earns its place through the work it enables;
the effort already invested in it is not sufficient reason to preserve it.

### A study carries the work forward

“Study” names a bounded piece of engineering inquiry. It can begin before the
question is fully formed and become more precise as evidence accumulates. It
may include a comparison, a design change, a characterization, an investigation
of failure, or a sequence of experiments. Simulation may be central, secondary,
or initially absent.

A study brings together intent, relevant context, actions, evidence, and
decisions. Its value includes what was learned, which alternatives were
rejected, and why the next question became worth asking. A negative result can
be useful evidence; successful execution alone does not establish a sound
engineering conclusion.

The system should make it practical to continue this work across runs, edits,
people, and tools. A particular executable plan or API may represent only one
part of that broader envelope. The vocabulary and representations should remain
free to develop as the work teaches us what distinctions matter.

### Keep intent accessible and authority explicit

Essential capabilities must be usable without an interactive session. Authored
intent and durable evidence must survive outside the process or interface that
created them. An engineer, script, CI job, or agent should be able to inspect
and operate on the same work through public contracts.

Plain files and CLI-first interfaces support portability, low-latency use,
version-control review, and automation. Python is the common language for
authoring and extending capabilities. Dependencies may use other languages;
their boundaries should make their contribution explicit.

Human-facing interfaces should help people understand and direct the work.
They remain replaceable clients of the same capabilities, and must not create
a second, hidden source of intent. Temporary process state is useful for doing
work; the information needed to explain or continue that work must not exist
only there.

### Make evidence and its meaning inspectable

The system should make clear what was requested, what was performed, what was
observed, and which conclusion was drawn. Assumptions, versions, configuration,
and dependencies matter because they determine what a result can support.

We aim for full reproducibility of engineering results. Progress toward that
aim should be explicit about what has been preserved and demonstrated. A
record of a procedure, the bytes it produced, and the reasoning that accepts
its result each contribute something different. Large or external artifacts
may remain outside version control while retaining discoverable identity,
provenance, and a way to retrieve or reproduce them.

Reuse should preserve valid work and explain why other work must be repeated.
Its justification must remain visible. A representation that omits a relevant
dependency cannot establish that the dependency did not matter.

Before committing resources, make the intended work and its bounds inspectable.
Where an investigation proceeds in stages, preserve the connection between
each stage, the evidence available to it, and the decision to continue. The
system should support developing questions without allowing their evolution
to disappear into unrecorded behavior.

### Let composition serve the work

A component earns its boundary through a coherent responsibility, independent
usefulness, and explicit contracts that make it testable and replaceable.
Responsibilities should sit where they can be fully explained. Shared concepts
and relationships should be stated at the point where components compose.

The filesystem makes this composition discoverable. Each component's ontolome
states its purpose, scope, contracts, contribution, and development state.
Containment expresses contribution to a whole; it does not confer inheritance,
override, or authority merely through location. Authority and obligations come
from explicit contracts.

The component tree is itself open to learning. We may refine, combine, split,
replace, or retire components when evidence supports a better account of the
work. A change of structure should preserve or deliberately revise the
relationships others rely on, and the ontolomes should change with that account.

The manifesto preserves the broader direction. Ontolomes explain the current
form and its commitments. Neither should make an early implementation choice
look inevitable, and implementation drift should not silently redefine a
commitment.

### Develop through useful experiments

Choose the next work from observed friction, useful opportunities, and questions
whose answers could change the system. Build enough of a path to use it and
learn from it. A runnable starting point can be valuable before it contains
the final data or expresses the final design.

Prefer progress that improves a real study and exposes how the components
compose. Keep representative, versioned workflows that demonstrate authoring,
inspection, execution, evaluation, reuse after change, and traceability back
from a conclusion. Targeted experiments may answer narrower architectural
questions; their conclusions should remain within the evidence they produce.

At the current prototype stage, useful capability and architectural learning
take priority over production hardening. Maintain inspectability, explicit
boundaries, proportionate verification, and recoverable changes. Introduce
additional infrastructure when a concrete use requires it.

Progress can mean removing a workaround, simplifying an API, replacing a
dependency, or discovering that an abstraction is unnecessary. It can also mean
adding a capability whose value becomes visible only through use. Evaluate
both by the improvement they bring to engineering work and to our understanding
of the system.

### Work with humans and agents

AI makes it practical to create and operate specialized tools around a question.
Humans and agents may both author work, propose experiments, evaluate evidence,
and contribute to the system's development. Their contributions should remain
inspectable and subject to the same contracts and standards.

The system must remain useful without AI. Greater autonomy should come through
explicit permissions and bounded resources while preserving the same authored
intent, evidence, and public interfaces. Conclusions need an inspectable basis;
the fluency or confidence of their author is not evidence.

### Direction

Build a system in which useful engineering work is easier to start, understand,
revise, and continue. Let real studies test the design, preserve what they
teach us, and reshape the implementation when a better account of the work
becomes available.

## Why I suggest these changes

The existing [manifesto](../MANIFESTO.md) already contains much of this
direction. I would change its emphasis and connect its ideas more clearly,
rather than replace its identity.

| Change | Why it fits the current situation | What it should encourage |
| --- | --- | --- |
| Lead with continuity of engineering work. | The system now connects authoring, execution, reuse, and evidence. Its value extends beyond automating individual steps. | Judge a feature by whether it helps someone understand, revise, or continue a study. |
| Add “Where we are now.” | Runnable composition gives us evidence about boundaries, not just evidence that implementation is possible. | Reconsider mechanisms and ownership when using them exposes friction. |
| Bring prototype-as-inquiry into the manifesto. | This stance is already explicit in the root ontolome and agent guidance, but deserves a place in the project's explanation of itself. | Treat useful execution and architectural learning as complementary outcomes. |
| Make the component tree revisable. | A composition can acquire conventions and workarounds that outlast the needs that produced them. | Permit simplification and restructuring when justified, without making every local difficulty a redesign. |
| Strengthen the meaning of a study. | A named executable plan supports an inquiry but does not contain every part of its reasoning. | Keep intent, negative results, decisions, and continuation in view as the system develops. |
| Connect reproducibility to evidence and meaning. | The project now has concrete records, source identities, output paths, and retention behavior. | Preserve the broad ambition while making the scope of each demonstrated capability honest. |
| Replace the expectation that every gap will simply be closed module by module. | Some gaps may disappear when a boundary changes; some modules may cease to be useful. | Treat the current decomposition as a hypothesis that can improve. |

I would retain the analog-design purpose, the generic core, headless authority,
Python authoring, file portability, independent components, and useful vertical
slices. There is no need to rename the project or claim a general-purpose
product to recognize what Hedloom has contributed.

I would also keep concrete decisions about nested submission, scheduler
equivalence, source fingerprinting, storage policy, and API ownership in their
respective ontolomes and design discussions. The proposed manifesto explains
why those decisions matter and what they should serve; it does not select their
mechanisms or remove current component exclusions.

The current situation informing this proposal is documented in the
[root ontolome](../ONTOLOME.md), the
[Hedloom ontolome](../hedloom/ONTOLOME.md), and the
[philosophical review](philosophical-review-2026-09-05.md). The earlier
[annotated manifesto catalog](../docs/vision/manifesto-change-catalog.md)
also records the author's preference for a broad vision that remains open to
opportunities beyond the current implementation.
