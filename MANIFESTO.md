# Analog Sim Studies: A Headless, Python-Native Study System

This manifesto explains the situation that motivates our work, the needs we
intend to serve, and the future we want to make possible. It provides shared
reasons for choosing a direction when the answer is open. Each ONTOLOME is an
ongoing study of the component at its location. Humans and agents lend it the
capacity to reflect on its purpose, experience, relationships, and possibilities,
allowing its understanding of itself to evolve through use. Its responsibilities
and commitments are part of that understanding; its present boundaries and
implementation remain open to revision.
These aims guide judgment. The degree of structure and formality should serve
the work at hand.

## The environment we work in

Analog engineering advances through questions, experiments, interpretation,
and decisions. A design is understood through the conditions under which it
was examined, the alternatives considered, and the evidence behind its
tradeoffs. Much of that understanding accumulates across iterations rather
than within any single simulation.

The tools we use do not always carry that understanding forward. In our daily
work, commercial environments impose recurring costs through freezing
sessions, heavy resource use, complex APIs, and reusable intent tied to
licenses and GUI-centered state. Around them, copied directories, local
scripts, manual evaluation, and remembered procedures fill the gaps. A result
may survive while the question, assumptions, or decisions that explain it
become difficult to recover.

The recurring needs are concrete: reuse a testbench without rediscovering its
setup, express parameters and corners coherently, compare design variants,
coordinate dependent work, evaluate results without manual transcription,
and understand what a changed input makes necessary to reconsider. These
activities belong to one engineering inquiry even when different tools
perform them.

Programmable tools and AI assistance create opportunities to build workflows
closer to these needs. Autonomous agents can reduce the effort of trying an
idea, building a prototype, and exploring alternatives. That freedom is
valuable: it lets us learn from possibilities we would otherwise leave
unexamined. The system should support this exploration alongside human work
and conventional automation, and remain useful without AI.

## The future we want

We want engineers to spend more of their effort on the question and its
consequences, with less effort reconstructing how to do the work. Starting an
investigation, extending an existing one, or returning to it later should
preserve what has already been learned.

An engineer should be able to express an idea, examine the proposed work,
carry it out with appropriate tools, interpret the evidence, and revise the
question. Another permitted person or automated collaborator should be able
to continue from the recorded work without reconstructing a private session
or relying on the original author's memory.

We aim to build an open, headless, Python-native system for analog-design work
that makes this continuity ordinary. Its capabilities should feel coherent
to the operator and remain independently useful. Analog design supplies our
purpose and proving ground. Capabilities that serve broader needs should be
reusable beyond it without requiring other users to adopt analog concepts.

This ambition includes authoring, preparation, execution, evaluation,
exploration, and the preservation of engineering conclusions. Existing tools
may contribute individual capabilities or substantial parts of the system.
We should adopt, connect, adapt, or build according to how well the resulting
work serves the engineer.

## Carry the inquiry forward

We use “study” as a working name for an inquiry that brings together intent,
context, actions, evidence, and decisions. It may concern characterization,
verification, a design change, a comparison, or an unexplained failure. It may
begin before the question is precise, and simulation may be central,
secondary, or initially absent.

The question may change as we learn. Retaining useful context helps us
understand what we tried and why we chose a next step. Failed experiments and
rejected alternatives can be worth preserving when they help us continue the
inquiry or avoid repeating a mistake.

A completed computation is evidence within this inquiry. An engineering
conclusion also depends on interpretation, assumptions, and the criteria by
which it is accepted. Keeping those relationships understandable allows
others to challenge a conclusion and makes later revision possible.

## Keep engineering work under the operator's control

Engineers should be able to inspect, preserve, share, and extend their work
without surrendering its meaning to a particular interface or vendor. Open
tools give us room to improve usability, reduce dependence on costly access,
and develop capabilities around the work we actually need to do.

Headless access serves that control. Essential capabilities should be
available to a person, script, CI job, or agent without requiring an
interactive session. Visual interfaces can make exploration and
interpretation much better; closing or replacing one should leave the work
available and understandable through the same underlying capabilities.

Python is our chosen common language for authoring and extension because it
lets engineering procedures become inspectable, reusable programs and connects
them to a broad scientific computing ecosystem. Dependencies may use other
languages. The commitment is to make the work approachable and programmable,
with room for engineers to extend it themselves.

Ordinary files and documented representations support review, transfer, and
preservation. Work should remain meaningful beyond the process, machine, or
service that produced it. Large results and external resources belong in this
vision too: an authorized collaborator should be able to discover, retrieve,
and understand them through the recorded work.

## Make evidence trustworthy and reusable

Confidence should come from evidence that can be examined. We should be able
to understand the basis of a result or conclusion well enough for the use we
make of it. An exploratory result and a conclusion others will rely on call
for different depths of verification and supporting context.

Full reproducibility is an ambition of the system. We should preserve or make
recoverable the dependencies needed to reproduce the work, including external
models, tool versions, and data. A record should make clear what can be
reproduced when that matters to its use: exact artifacts, a procedure, or an
engineering conclusion under stated conditions. Building toward this
capability should make reproducible work easier, with room for lightweight
experiments before we decide what deserves fuller preservation.

Reuse should preserve the justification for trusting a result. When something
changes, we should be able to understand which evidence remains applicable,
which conclusions need reconsideration, and what further work is needed.
Saving computation matters because engineering time and resources are finite;
understanding why saved work is still relevant matters just as much.

## Compose capabilities around real needs

Engineering work crosses tool boundaries. The system should allow useful
capabilities to participate without demanding that every tool, design, or
working practice be replaced at once. Existing runnable setups can provide a
starting point, and their reuse should leave room for substantial change.

We favor composition because it lets capabilities improve independently and
lets engineers use the parts they need. Clear responsibilities and explicit
agreements make it possible to replace a part while preserving the meaning
of the work around it. Coherence means that people can understand how the
parts contribute to their inquiry.

Boundaries earn their place through that usefulness. Our understanding may
require combining, separating, replacing, or retiring components. The needs
that motivate the system should guide those choices; an existing division
of responsibilities is a revisable means of serving them.

## Learn what deserves to be built

The vision is broader than any current implementation. Its pursuit should
remain responsive to the needs revealed by actual work and to opportunities
we have not yet anticipated. Useful experiments can test both engineering
ideas and our assumptions about the tools that support them.

Prototypes benefit from latitude to act, fail, and change direction. Structure,
documentation, and review earn their effort when they help us learn, use a
capability, or make a consequential decision. Their cost in time, attention,
and computation belongs in that judgment.

We should judge progress by whether people can ask better questions, reduce
recurring effort, understand their evidence, and continue or revise work with
greater confidence. New capabilities, simplification, and the removal of an
unhelpful abstraction can each contribute. Early limitations should remain
visible without becoming limits on what we believe is worth pursuing.

The reason to build this system is to make engineering effort accumulate as
accessible, reusable, and revisable knowledge. That purpose should continue
to guide us as the tools, component boundaries, and possibilities change.
