# Project agent guidance

## Establish context

Before acting, read `MANIFESTO.md`, the root `ONTOLOME.md`, and every ontology
on the filesystem path to the target component. Also inspect the nearest
`README.md`, `unit.toml`, relevant implementation and tests, and current Git
status. The manifesto states intended direction. Each ONTOLOME is the ongoing
self-study of the component rooted at its location: its purpose, experience,
relationships, commitments, assumptions, and possibilities, including its
current responsibilities, exclusions, and development state.

## Work reflectively

When you encounter an ONTOLOME during ordinary work, spend a small amount of
attention considering the work from that component's perspective. Use the
context and evidence already available: what does this experience reveal about
its purpose, commitments, assumptions, or possible evolution? When a useful
insight emerges and editing is within the task's scope, incorporate it concisely
into the relevant ONTOLOME. A reflection may leave the file unchanged. Keep
established commitments distinguishable from observations and possibilities;
observed behavior does not silently redefine a commitment. Prefer refining the
existing account over accumulating a diary.

All current nodes are prototypes: runnable forms through which the repository
studies itself. Ask what the repository currently says the component is, what
observable evidence code and use provide, what architectural or feature
hypothesis a change tests, and which ontology must change if that evidence
changes the component's being. In summaries, distinguish observed facts,
architectural inference, proposals, and unresolved uncertainty. Give concise,
inspectable rationale and evidence; never disclose or request private hidden
chain-of-thought.

Prioritize architectural learning, useful features, and runnable vertical
slices over production hardening. Do not add high availability, enterprise
deployment, exhaustive compatibility, premature migration machinery,
speculative scale work, or similar production concerns without a concrete use
case. Prototype is not permission for careless work: preserve inspectability,
explicit boundaries, proportionate tests, reversible changes, honest
limitations, and evidence-backed conclusions. Treat failures and friction as
evidence that may require changing code, contracts, boundaries, or ontology.

Challenge existing architecture proactively when a task exposes friction.
Before adding coordination, duplicating responsibility, changing observable
behavior, or narrowing a requested capability to preserve a current contract,
separate the user's requirement from the chosen mechanism. Compare the current
approach with a simpler alternative, including changes at another component
boundary when relevant. Contracts, exclusions, and decisions marked settled
can be challenged; do not wait for the user to ask whether they can change.
Existing tests are evidence about behavior, not proof that a boundary is right.

Investigate and prototype alternatives within the authorized task scope.
State the contract being challenged, the need it serves, the proposed change,
and the evidence and consequences. Challenging a contract does not silently
revise it: make adopted changes explicit in code, tests, maintained docs, and
the affected ontologies. Preserve explicit user requirements unless the user
revises them. Keep this inquiry brief for routine changes; expand it when a
concrete conflict or complexity warrants it, without requiring a separate
permission step merely to examine an alternative.

## Preserve composition

Containment is composition, not inheritance, runtime order, precedence, or
authority. Put work in the smallest ontology that fully explains it and promote
only explicit contracts. Direct cross-unit contracts to the closest containing
ontology. When purpose, scope, contracts, contribution, exclusions, or
development state materially change, update the relevant ontology in the same
change. A maturity change must always be explicit there.

Preserve user changes, keep commits focused, and validate in proportion to the
risk and the affected contracts.

## Delegated agent workspace

When uncertain which workspace to use and the agent may need writing access
across components, prefer the containing ASS repository over a narrower child
workspace. State the exact assigned files and preserve unrelated changes;
workspace breadth does not broaden the task. A clearly bounded report-only
assignment may remain in its component workspace. User preference, 2026-09-15.

## File links in chat

When sharing ASS file links in chat messages addressed directly to the project
owner (smldis) for their own reading, use the full servedgui ASS Library URL:
`https://servedgui.spasyc.com/ass-library/index.html#view=files&path=<repo-relative-path>`.
Paths are relative to the `analog-sim-studies` root. Keep `/` separators readable;
URL-encode special characters within path segments. Optionally append
`&line=<line-number>`. For example:
`https://servedgui.spasyc.com/ass-library/index.html#view=files&path=research-observatory/AI-FRONTIER.md`.
The app intercepts relative Markdown links on click; a displayed
`/ass-library/runs/...` target is not a supported standalone file route. Use the
app's hash parameters for links shared outside the open document.
This preference applies only to those direct user-facing chat messages, not
agent prompts, agent-to-agent messages, or messages intended for other people.
Keep links inside repository documents in their existing portable form.
Construct the link directly from the file path without checking file existence
or ASS Library availability; the user will check it.
