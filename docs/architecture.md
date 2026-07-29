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

To add a unit, give it a stable capability directory, README, ontology, manifest,
and any locally owned source/test/docs trees. Declare its directory in its
parent's `unit.children`, then add only cross-unit behavior to the parent's
integration area.
