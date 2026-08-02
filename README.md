# Analog Sim Studies

Analog Sim Studies is a composition root for small, independently useful analog
design tools. The governing direction is [MANIFESTO.md](MANIFESTO.md), while
[ONTOLOGY.md](ONTOLOGY.md) records the responsibilities implemented here.

## Owned units

- [`sidecar-edits/`](sidecar-edits/) prepares simulation directories through a
  typed Python edit API and owns its examples and Sphinx user/API guide.
- [`spice-canonical/`](spice-canonical/) extracts a canonical graph-oriented
  representation from Eldo and ngspice netlists.
- [`netlist-decomposition/`](netlist-decomposition/) recognizes functional MOS
  blocks and explicitly depends on `spice-canonical`.
- [`study-flow/`](study-flow/) experiments with an ASS-owned preparation and
  artifact contract executed through local Dask or Dask Jobqueue on LSF.

These stable capability names are direct children instead of entries in a
generic `src`, `components`, or `packages` bucket. Each child owns its source,
packaging, tests, docs, scripts, README, and ontology. Root `docs/` and
`integration-tests/` contain only composition glue, project-wide material, and
cross-unit checks.

All current ontology nodes have development state `prototype`. Here prototype
means a useful runnable form that lets the repository test hypotheses about its
architecture, features, and boundaries and revise them from observed evidence;
it does not mean careless or merely aspirational work. Each `ONTOLOGY.md`
records that state and has an adjacent `AGENTS.md`, so filesystem instruction
scope mirrors semantic scope.

## Fresh developer setup

Python 3.10 or newer and a C compiler available as `cc` are required. From a
fresh checkout:

```bash
python3 -m venv ../eda-venv
. ../eda-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

There is deliberately no root Python distribution, so `pip install -e .` is
replaced by the explicit child bootstrap above. It installs the four editable
distributions together and preserves the imports `sidecar_edits`,
`spice_canonical`, `netlist_decomposition`, and `ass_study_flow`, plus the
`sidecar-render`, `spice-canonical`, and `ass-flow-demo` commands. Individual
package installation is documented in each child README.

## Recursive composition

Every composition node uses the same small `unit.toml` contract: identity,
ontology, immediate child paths, an optional owned test command, and an optional
documentation source. [`composition.py`](composition.py) validates that contract
without absolute paths, orders children by stable ID, and can operate on any
node selected with `--root`.

```bash
python composition.py tree
python composition.py test
python composition.py docs
```

`test` walks children postorder, running each child's owned tests before the
root integration checks. Failures stop composition and retain the child's exit
status. `docs` creates an ignored, generated Sphinx source view under `build/`;
it links each immediate child's authored docs, adds the root-owned pages, and
builds `build/docs/html/`. No child documentation is copied into maintained root
source.

This proves the convention at the root and one child level. The manifest and
tree loader are recursive, but no generic plugin framework or nested repository
machinery is introduced.

## Common workflows

Run a single unit in its owned context after the developer bootstrap:

```bash
cd spice-canonical
python -m pytest -q tests
python -m build --wheel
```

Build all documentation:

```bash
python composition.py docs
python -m http.server --directory build/docs/html 8000
```

Run sidecar examples and native-helper flows from `sidecar-edits/`; run the
canonical corpus verifier from `spice-canonical/`; and run decomposition
dependency generation or OTA verification from `netlist-decomposition/`. Run
the bounded Dask map-reduce experiment with `ass-flow-demo`. Exact commands and
external prerequisites live in the owning README.

## Adding another unit

Create a direct directory with `README.md`, `ONTOLOGY.md`, `AGENTS.md`, and
`unit.toml`; keep its source, packaging, tests, docs, examples, and scripts
there; then add only its relative directory name to this node's
`unit.children`. Record development state in its ontology and keep its local
agent guidance concise by inheriting project guidance and stating only the
unit-specific boundary. Give the child its own workflow and docs contracts.
Parent integration tests should exercise only the promoted cross-unit
contract, never absorb the child's unit suite.
