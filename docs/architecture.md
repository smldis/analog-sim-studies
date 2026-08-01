# Recursive ownership and composition

The root and every component are ontology nodes. A node owns only what it can
explain independently: source and packaging, unit tests, documentation,
examples, scripts, and design records remain inside the responsible child.
Root content is limited to vision, aggregation, and genuine cross-unit
integration.

`unit.toml` is the composition boundary. It declares immediate children with
relative paths and exposes the node's own test and documentation capabilities.
`composition.py test` traverses children in deterministic postorder and then
runs the parent's integration suite. The parent does not rediscover or select
individual child test files.

For documentation, the composer makes an ignored source view under `build/`.
Root-authored pages and a generated child toctree are combined with links to
each child's original documentation tree. Sphinx reads those owned sources
directly, so there is no second maintained copy. Generated static HTML is no
longer tracked because its source and exact build command are reproducible.

Containment and traversal order do not imply inheritance or precedence.
Ontologies state semantic responsibility and explicit contributions; manifests
state executable composition contracts.

Every current ontology also records `Development state: prototype`. Prototype
is the repository's self-study mode: each useful runnable unit tests hypotheses
about its architecture, features, and boundary, and observed consequences may
revise both implementation and ontology. This favors learning and vertical
slices without relaxing inspectability, explicit contracts, proportionate
tests, reversibility, or honest limitations.

Each ontology node owns an adjacent `AGENTS.md`; its filesystem scope therefore
mirrors the ontology's semantic scope. The root file holds shared project
guidance, while child files inherit it and add only their unit-specific
ownership boundary.

To add a unit, give it a stable capability directory, README, ontology,
concise adjacent `AGENTS.md`, manifest, and any locally owned source/test/docs
trees. Record its development state, declare its directory in its parent's
`unit.children`, then add only cross-unit behavior to the parent's integration
area.
