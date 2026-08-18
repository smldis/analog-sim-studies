# Project agent guidance

## Establish context

Before acting, read `MANIFESTO.md`, the root `ONTOLOME.md`, and every ontology
on the filesystem path to the target component. Also inspect the nearest
`README.md`, `unit.toml`, relevant implementation and tests, and current Git
status. The manifesto states intended direction. Ontologies state the current
semantic being: responsibility, contribution, explicit contracts, exclusions,
and development state.

## Work reflectively

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

## Preserve composition

Containment is composition, not inheritance, runtime order, precedence, or
authority. Put work in the smallest ontology that fully explains it and promote
only explicit contracts. Direct cross-unit contracts to the closest containing
ontology. When purpose, scope, contracts, contribution, exclusions, or
development state materially change, update the relevant ontology in the same
change. A maturity change must always be explicit there.

Preserve user changes, keep commits focused, and validate in proportion to the
risk and the affected contracts.
