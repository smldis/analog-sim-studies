# Analog Sim Studies Ontology

## Purpose and scope

This repository is the composition node for independently useful analog-design
capabilities and the domain-generic planning and execution core that serves
analog use cases first, governed by [MANIFESTO.md](MANIFESTO.md). It owns
project-wide vision, the explicit child-unit contract, aggregate workflows,
cross-unit integration checks, and documentation that explains how the units
compose.

The repository name `analog-sim-studies` still states its first and present
domain, but it is narrower than a composition that now includes a
domain-generic core. Choosing a wider name is deliberately deferred until the
core's use beyond analog studies supplies evidence for that name; the need is
recorded here so the current name is not mistaken for the core's boundary.

Filesystem containment expresses composition only. It grants no inheritance,
override, precedence, or authority to a child, its parent, or a sibling.
Deterministic traversal is presentation and execution order, not semantic rank.

## Mode of being

**Development state:** `prototype`

Prototype is this repository's mode of being as self-study. The composed,
runnable units propose hypotheses about the system's architecture, features,
and boundaries; their use supplies evidence for revising those hypotheses and
this ontology. The implementation is useful capability and an instrument of
inquiry, not an inevitable final form.

At this stage, architectural learning, useful features, and runnable vertical
slices take priority over production hardening. High availability, enterprise
deployment, exhaustive compatibility, premature migration machinery, and
speculative scale work belong only when a concrete use case makes them
relevant. Prototype does not excuse careless work: changes should preserve
inspectability, explicit boundaries, proportionate tests, reversibility,
honest limitations, and evidence-backed conclusions. Failures and friction are
valid evidence that may require revising code, contracts, boundaries, or
ontology. Any maturity change must be explicit and update this ontology and
any affected child ontology.

## Current contracts

- `unit.toml` declares immediate children and parent-owned workflows using
  relative paths.
- `composition.py` validates declarations, renders the ontology tree, composes
  child tests with parent integration tests, and builds aggregate docs from
  every descendant's owned sources. A workflow declaring `python` runs under the
  interpreter composing the units, so a reported pass describes the environment
  the composition was invoked in rather than whichever one `PATH` names.
  Descendant documentation is staged by its stable unit ID so cross-unit links
  do not depend on repository nesting;
  generated `_runs` evidence is excluded from that authored-documentation view.
- Child public Python and CLI contracts remain owned and versioned by their
  units.
- Root integration checks may verify explicit relationships such as
  `netlist-decomposition` consuming `spice-canonical`.
- `docs/vision/open-concepts.md` registers every concept raised by the Hedloom Flow
  rebuild inquiry with its current status, including concepts that fell out of
  direct development without a decision. It spans both units, so it belongs at
  the composition root rather than in either one.
- `docs/reference/ota-pvt-plan/` owns one representative cross-unit Plan
  declaration (`ota_pvt_plan.py`) and its versioned input fixtures. The Plan
  declaration remains non-executing: it tests static composition through public
  Hedloom Flow contracts alone -- four repository-relative sources declared as
  addressed artifact references with explicit data-only representation/access
  requirements, while all operation-output edges and the final evaluation
  remain ephemeral.
- `studies/` owns the runnable studies, each an ordinary consumer of `hedloom`'s
  public contracts. `studies/ota_pvt.py` runs the exact same graph end to end
  against real `ngspice` and the real Sidecar Edits, SPICE Canonical and Netlist
  Decomposition public APIs. It replaced a companion binding script that
  re-declared every operation beside the Plan; `hedloom`'s `@study` removed the
  need for it. Neither the declaration nor the study promotes this reference's
  analog-domain labels into a child API, claims a sibling adapter Hedloom Flow
  itself provides, or adds a fifth component. The domain vocabulary lives here
  and in `studies/`, never inside `hedloom`, which names no simulator anywhere.

## Contributions from children

- `hedloom` contributes the domain-generic, operator-facing join between
  authored operations and their execution. Its three children retain their
  narrower contracts: `hedloom-flow` owns static planning and deterministic
  Plan IR, `hedloom-exec` owns the durable lifecycle of one attempt, and
  `hedloom-run` owns plan traversal and readiness.
- `sidecar-edits` contributes reviewable simulation-directory preparation.
- `spice-canonical` contributes canonical netlist extraction.
- `netlist-decomposition` contributes functional block recognition over the
  canonical representation.

`hedloom-exec` consumes `hedloom-flow`'s schema-2 Plan **document**, not its package.
The cross-unit contract is therefore the portable plain-data artifact: neither
unit imports the other, and any producer of the same document composes equally
well. `hedloom-flow` stays executor-neutral; `hedloom-exec` reads a Plan but neither
produces nor validates one.

`hedloom-run` depends on `hedloom-exec` as an ordinary Python package, which is the
honest shape of a consumer: a driver must call `execute`. That is deliberately
different from the flow-to-exec coupling, which stays document-only so that
planning cannot acquire executor knowledge. Hedloom provides an operator-facing
package over those contracts, while the composition root has no unified source
tree or package distribution; units compose through `unit.toml` and
`composition.py`, and each distribution remains independently installable.

These contributions compose into the larger vision. Flow execution is now
partly owned. `hedloom-flow` and `hedloom-exec` together deliver one runnable vertical
slice — author a flow, plan it, execute it, edit one input, and rerun with
unchanged work skipped and superseded results retained — demonstrated by
`hedloom-exec/examples/planned_characterization.py`. No real batch or distributed
transport has been exercised: direct `bsub -I` submission exists but has never
contacted a cluster, and pooled execution refuses. The retired `study-flow`
prototype remains
recoverable in Git history at `528c02f`, while
[`docs/vision/hedloom-flow-rebuild-main.md`](docs/vision/hedloom-flow-rebuild-main.md)
records the architectural inquiry that preceded the bounded planning work.
The declared `hedloom-flow` child owns only static planning; its refusing
`submit(...)` boundary confers no local, distributed, simulator, or study
runtime authority.

The root-owned OTA/PVT reference composes these capabilities only at the level
of declared artifact and operation boundaries. Its Sidecar, canonicalization,
and decomposition names are proposed adapter seams; its simulator, measurement,
and evaluation operations are refusing stubs. The validated Plan is evidence of
static expressiveness and an addressed-source/ephemeral-edge distinction, not
evidence that addresses resolve, access succeeds, artifacts are published,
outputs materialize, or any operation can run.

## Exclusions

The root does not own a unified Python package, source tree, unit-test suite,
API guide, example catalog, or component-specific build script. It is not a
package-distribution boundary and does not imply that every future capability
must use the current four implementations.

## Child composition

The immediate children authored in `unit.toml` are `hedloom`, `sidecar-edits`,
`spice-canonical`, and `netlist-decomposition`. Hedloom in turn declares its
three constituent units. A future child may declare children with the same
contract; the loader, test traversal, and documentation composition recurse.
