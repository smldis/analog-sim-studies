# Manifesto Challenges: Competitive and Architectural Analysis

This note tests the claims in [the manifesto](../manifesto.md) against existing
tools and against realistic analog-design practice. It is a companion analysis,
not a replacement roadmap. The repository's current implemented scope is much
narrower than the manifesto: `sidecar_edits` copies an existing simulator input
directory and applies typed, source-traced text/file edits, including named
parameter sets and Cartesian parameter matrices. It does not launch simulators,
parse results, evaluate specifications, schedule dependencies, or cache runs.
Those are therefore new opportunities unless stated otherwise below.

## 1. CACE differentiation

### CACE

Efabless CACE is the closest existing answer to the manifesto and must be
treated as the baseline competitor. Its current datasheet is YAML (format 5.2
in the current documentation; the pre-June-2024 4.0 text format is deprecated)
and serves as both design specification and executable characterization input.
It records metadata, PDK and project paths, pins, default conditions, parameters,
tool-specific testbench settings, plots, and limits. Conditions can be
minimum/typical/maximum, enumerated, or linearly/logarithmically stepped; a
parameter can override defaults and cross product process corner, voltage,
temperature, load, and similar conditions. Specifications name result variables
and minimum/typical/maximum targets, with selectable aggregation/limit behavior
and pass/fail control. See the [datasheet format](https://cace.readthedocs.io/en/latest/reference/datasheet_format.html).

CACE explicitly advertises characterization under varied conditions plus Monte
Carlo and mismatch analysis. Iterations can be collated for Python
post-processing, although the documented custom-script interface is still WIP
and currently limited to the ngspice tool. See the [CACE overview](https://cace.readthedocs.io/en/latest/),
[custom post-processing](https://cace.readthedocs.io/en/latest/tutorials/custom_scripts.html),
and [template substitutions](https://cace.readthedocs.io/en/latest/reference/template_format.html).
The normal documented simulation path is ngspice; the surrounding flow also
integrates schematic/layout netlisting and physical tools, and can select
schematic, layout/LVS, capacitance-extracted (PEX), or RC-extracted (RCX)
netlists. Its CLI parallelizes jobs and parameters and emits an annotated
datasheet/summary; see the [CLI reference](https://cace.readthedocs.io/en/latest/usage/cace_cli.html)
and [5T OTA tutorial](https://cace.readthedocs.io/en/latest/tutorials/ota_5t.html).

What CACE covers well relative to the manifesto is substantial: reusable
testbench templates, conditions/corners, Monte Carlo, named measurements,
limits, plots, parallel execution, reproducible directory conventions, and
schematic-to-extracted characterization. The manifesto cannot differentiate by
claiming those categories alone.

What CACE leaves open for this project is a less prescriptive, Python-native,
deck-first layer. CACE asks a design to adopt its datasheet schema, project
layout, placeholder syntax, and tool adapters; the examples are closely aligned
with open-source IC flows and ngspice/Xschem. It does not make a sequence of
ordinary file transformations the primary inspectable artifact, and its YAML is
less naturally composable than Python functions and packages. Its public model
also does not foreground a general study-to-study artifact DAG or a portable,
content-addressed run identity. These are limitations relative to this
manifesto, not claims that CACE is defective.

The concrete differentiator should be: **take an arbitrary working simulator
directory as input; describe small typed transformations, studies,
measurements, and dependencies in normal Python; materialize every expanded
deck plus a provenance manifest; and use pluggable simulator/result adapters
without requiring a CACE-style project conversion.** A useful demonstration
would reuse the same OTA study against an existing Spectre directory and an
ngspice directory while showing the exact file diff and cache key for every
corner. Competing with CACE on “YAML-driven open-source IP characterization” is
not a credible differentiator.

### spicelib / PyLTSpice

[spicelib](https://spicelib.readthedocs.io/en/latest/readme.html), which
underpins the PyLTSpice-facing workflow, provides editors for SPICE and
schematic formats, batch simulation, parallel runs, sweeps, and raw/log result
access. Its documented simulator integrations include LTspice, ngspice,
QSPICE, and Xyce. `SimRunner` plus `SpiceEditor` is a pragmatic answer to
“change values and run many simulations”; see the
[runner example](https://spicelib.readthedocs.io/en/latest/_modules/spicelib/sim/sim_runner.html).

Its center of gravity is scripting editors, runners, and simulator outputs, not
a declarative study/specification/provenance model. It leaves the user to invent
the reusable organization of corners, requirements, dependency artifacts, and
cache identity. Our differentiator would be a higher-level, reviewable study
contract whose backend may even call spicelib, while retaining copied-deck
fidelity and explicit edit objects.

### Hdl21 simulation and VLSIR

[Hdl21](https://github.com/dan-fritchman/Hdl21) takes the opposite starting
point: circuits and testbenches are Python objects, with generators,
parameterization, primitives, and hierarchy. It exports through
[VLSIR](https://github.com/Vlsir/Vlsir), a protobuf-defined interchange family
for circuit descriptions, netlists, and simulation data; the VLSIR toolchain
provides netlisting and simulator-facing infrastructure. This is strong for
programmatic circuit construction and typed reuse.

Relative to the manifesto, Hdl21/VLSIR make structure reusable but require the
circuit to enter their object/IR world. They do not solve the common adoption
case here: a mature Spectre/Eldo/ngspice directory containing proprietary
directives, scripts, includes, and a schematic-exported DUT that must remain
authoritative. Round-tripping every dialect is a high lock-in and fidelity
risk. Our differentiator is therefore not a better Python netlist DSL; it is
composition *around* ordinary, simulator-valid files, with structural IR used
only when it adds value.

### Mapping to the current repository

This topic is **partially answered today**. Typed edits, source stacks, copied
directories, parameter sets, and matrices already establish the deck-first,
inspectable differentiator. Simulator abstraction, launches, result adapters,
measurements, specification checks, Monte Carlo semantics, provenance
manifests, and cache identities are **new opportunities**. The manifesto
understates CACE's overlap and should not be read as a competitive survey.

## 2. Testbench representation

No representation wins every axis. The important distinction is between the DUT
source and the usually much smaller study harness.

### Jinja-templated SPICE decks

```jinja
.include "{{ model_file }}"
.include "{{ dut_netlist }}"
VDD vdd 0 {{ vdd }}
XOTA inp inn out vdd 0 ota
.ac dec 100 1 1G
```

- **Portability:** high when limited to common SPICE; dialect directives and
  model libraries remain backend/PDK-specific.
- **Git reviewability:** excellent because the emitted language is recognizable
  SPICE and rendered decks can be diffed.
- **Learning curve:** low for SPICE users, plus a small templating vocabulary.
- **Lock-in:** low to Jinja itself, but uncontrolled templating can become an
  untyped second programming language and can hide which parameters matter.

### Schematic-exported netlists (Xschem or Virtuoso)

The authored source is schematic metadata; a representative netlisted fragment
is:

```spice
* generated from ota_ac.sch / ota_ac cellview
VDD vdd 0 1.8
XUUT inp inn out vdd 0 ota
CLOAD out 0 2p
.ac dec 100 1 1G
```

- **Portability:** medium for Xschem projects and low-to-medium for Virtuoso
  cellviews; symbols, callbacks, config views, and PDK bindings travel poorly.
- **Git reviewability:** generated netlists are reviewable, but schematic source
  diffs are noisy or opaque and regeneration can reorder text.
- **Learning curve:** lowest for schematic-centric analog designers, but
  automation requires netlister knowledge.
- **Lock-in:** medium for Xschem and high for a commercial database/netlister.

### Python-constructed netlists (Hdl21 style)

```python
@h.module
class OtaAcTb:
    vdd, inp, inn, out = h.Signals(4)
    supply = Vdc(dc=1.8)(p=vdd, n=VSS)
    dut = Ota()(inp=inp, inn=inn, out=out, vdd=vdd, vss=VSS)
    load = C(c=2e-12)(p=out, n=VSS)
```

- **Portability:** high within supported primitives and netlisters, but lower
  for proprietary devices, analyses, Verilog-A, encrypted models, and obscure
  simulator syntax.
- **Git reviewability:** excellent at the intent/structure level; reviewing the
  final simulator deck still requires generated artifacts.
- **Learning curve:** medium-to-high because analog designers must learn an
  object model, connection semantics, generators, and escape hatches.
- **Lock-in:** high to the Python HDL/IR if it becomes the authoritative circuit
  representation, even if its emitted SPICE is portable.

### Hybrid: authoritative exported DUT plus a small text harness and typed edits

```python
BASE_DIR = "base_spectre_deck"       # contains dut.scs from the schematic
PARAM_MATRIX = {"vdd": [1.62, 1.8, 1.98], "temp_c": [-40, 27, 125]}
EDITS = [
    edits.replace(path="ota_ac.scs", old="VDD vdd 0 1.8",
                  new="VDD vdd 0 {vdd}"),
]
```

- **Portability:** high at the framework level because existing decks remain
  valid, but each base deck still carries its simulator/PDK dependencies.
- **Git reviewability:** excellent for the harness and explicit edits; generated
  DUT netlist churn can be isolated or checksum-pinned.
- **Learning curve:** low because users keep their schematic/netlisting flow and
  learn only typed Python study/edit declarations.
- **Lock-in:** lowest for adoption; the copied directory remains runnable
  without reconstructing the circuit through the framework.

### Recommendation and reconciliation

Use the **hybrid as the default**, with a small plain-SPICE or narrowly
templated harness where practical, and treat Python-constructed netlists as an
optional producer rather than the canonical user contract. Prefer explicit,
typed substitutions or generated include files over unrestricted Jinja logic;
if Jinja is supported, render it as one declared edit and record both template
and output hashes. This best fits “text-first” because the inspectable unit is
the ordinary materialized directory, while reuse lives in Python helpers and
small harness templates.

`canonical-netlist-representation.md` **already answers part of this topic**:
the original Eldo/ngspice deck is authoritative, and the canonical structural
view complements rather than replaces simulator input. It therefore supports
the hybrid and argues against making an Hdl21-like IR mandatory. It leaves open
how a user authors the testbench and how schematic exports are refreshed.
The current sidecar edit API **already implements the hybrid preparation
mechanism**, but not a first-class template abstraction. There is no direct
contradiction; there is a useful tension between the manifesto's broad phrase
“user-authored reusable templates” and the implementation's safer explicit
edits, which should be resolved in favor of explicit edits plus small templates.

## 3. Simulation dependencies

### Extracted-netlist prerequisite

An RCX study depends on a layout extractor producing `ota_rcx.spf` and perhaps
an LVS-clean marker. This is a file/artifact dependency with a clear producer
and consumer. A DAG suffices if extraction is modeled as an external/preparation
node with declared inputs and immutable outputs. It pressures toward a workflow
engine only if this package also owns iterative DRC/LVS/PEX tool orchestration,
which the repository's stated scope explicitly rejects. The minimal package
should accept a pinned external artifact or a user-supplied preparation command,
not become a physical-design flow.

### Operating-point handoff to AC/noise

A nominal DC operating-point run may write a restart/state file consumed by AC
or noise analyses, particularly when convergence is difficult or when a
simulator supports saved-state handoff. This is one-to-many artifact flow:
`dc_op -> {ac, noise}`. A DAG suffices. The edge must name the artifact and its
compatibility scope (same expanded DUT, models, corner, temperature, simulator
version/options); “depends on study name” alone is unsafe.

### Measurement-derived parameter feeding a second sweep

A transient run can measure settling time or output common-mode, after which a
second study chooses a stop time, bias point, or narrow sweep interval from that
value. A DAG still suffices when the transform is deterministic and produces a
typed JSON-like artifact, for example `{"vcm": 0.873}`. Dynamic fan-out—where
the first measurement decides how many new sweep points exist—pressures toward
a workflow engine because the execution graph is discovered at runtime. The
minimal model should initially require a statically declared downstream study
and a deterministic parameter-mapping function; defer dynamic graph expansion.

### Monte Carlo seeded from a nominal pass

A nominal run can validate convergence, choose tolerances, or derive an initial
condition before launching seeds 1..N. This is `nominal -> mc[seed]`, a static
fan-out DAG. It becomes workflow-engine territory if the run adaptively adds
samples until a confidence interval or yield error target is reached. Initial
support should require an explicit seed list/count and make each seed part of
the run identity; adaptive stopping is a later orchestration feature.

### Minimal dependency model and reconciliation

The minimum useful model is a **static acyclic graph of named studies**, expanded
into per-run nodes, with edges carrying named immutable artifacts. Each consumer
declares: producer study/run selector, artifact schema/path, parameter mapping,
and fan-in rule. Validate cycles before launching; hash artifact content into
the consumer key; allow deterministic one-to-one, one-to-many, and fixed fan-in;
exclude loops, adaptive fan-out, retries-as-control-flow, and conditional
branches. This covers all four cases in bounded form without building a general
workflow engine.

The manifesto **raises but does not answer** this topic. Despite their names,
`functional-decomposition-dependencies.md` and
`plan-composition-passes.md` **do not answer simulation dependency handling**.
They describe recognition-rule dependencies and fixed-point composition inside
the netlist functional-decomposition algorithm; indeed, their same-pass cycles
show why that internal algorithm is not a simple DAG. Reusing that machinery
for study scheduling would conflate circuit-analysis passes with run artifacts.
There is no product-level contradiction, but there is a terminology collision
worth documenting. All simulation dependency behavior is a **new opportunity**
and lies beyond today's preparation-only scope.

## 4. Caching and incrementality

### Mechanism

After expanding a study, compute a canonical run key such as:

```text
SHA256(schema_version || rendered_input_tree || normalized_parameters ||
       simulator_adapter+version || command/options || model_manifest ||
       dependency_artifact_hashes || measurement_code_hash)
```

“Rendered input tree” means sorted relative paths, file modes where relevant,
and file bytes after all edits—not merely the template text. The model manifest
must include the bytes (or a trusted immutable digest) of every resolved model,
include, Verilog-A source/binary, and section selection. Environment variables
that influence resolution must be captured after expansion. The simulator
executable/version, adapter version, command-line options, and relevant license
or numerical environment should be recorded; whether all of them invalidate the
cache must be a documented policy. On a cache hit with a complete success
manifest, restore/link the run outputs and evaluation record and skip simulation.
Failures and partial directories should not be reusable success entries.

This is content-addressed *reuse*, not merely “the output directory exists.” It
needs atomic publication, a manifest that maps logical run coordinates to the
key, validation of required outputs, locking for concurrent writers, explicit
`--force`/cache-disable controls, and garbage collection. Measurement-only
changes can reuse raw simulator output if simulation and evaluation have
separate keys; combining both into one key is simpler but reruns too much.

### Prior art

[mflowgen](https://mflowgen.readthedocs.io/en/stable/) is relevant for the
mechanism of Python-defined, parameterized graphs whose sandboxed steps expose
well-defined inputs/outputs and are lowered to Make/Ninja. It demonstrates
hardware-flow modularity and file shuttling, not by itself the complete
content-addressed run cache proposed here. [Snakemake](https://snakemake.readthedocs.io/en/v9.23.0/project_info/faq.html)
tracks inputs, parameters, code, software environment, and timestamps and uses
content checksums for eligible input files to avoid false timestamp-triggered
reruns. [DVC](https://dvc.org/blog/dvc-vs-rclone/) demonstrates content-addressed
artifact storage keyed by file hashes and deduplication. The lesson is to borrow
their explicit inputs/outputs, metadata-based invalidation, and immutable object
store—not to embed a general workflow system.

### Worked 3 x 3 x 3 example

Suppose `process = [ss, tt, ff]`, `vdd = [1.62, 1.80, 1.98]`, and
`temp_c = [-40, 27, 125]`. Expansion creates 27 logical coordinates and 27
keys. A completed first run populates all 27 cache entries.

Now the author corrects only the voltage axis from `1.98` to `2.00`; no deck,
model, simulator, or other parameter changes. The 18 coordinates at 1.62 V and
1.80 V expand byte-for-byte identically and hit their old keys. The nine
coordinates `(process in {ss,tt,ff}, vdd=2.00, temp in {-40,27,125})` are new
and run. The obsolete nine 1.98 V objects remain eligible for garbage
collection but are not results of the new study. Thus 9/27 simulations run,
not all 27. If instead a global model file changes, all 27 keys correctly
change. If only the `ss` model section's immutable digest changes and the model
manifest records section-level dependencies safely, only the nine `ss` runs
invalidate; without trustworthy section granularity, conservatively rerun all.

### Required study-definition properties and current mapping

The definition must make expansion deterministic and expose: typed axes with
stable names/serialization; exact template/base-tree inputs; every external
include/model and selected section; simulator adapter/version/options; seed;
dependency artifacts; declared outputs; and measurement/evaluation code. It
must prohibit hidden dependence on ambient current time, random state, mutable
absolute files, or undeclared environment variables—or mark such runs
uncacheable. A `schema_version` and canonical serialization are mandatory so
Python dictionary ordering, float formatting, or framework upgrades do not
silently alias identities.

Today's parameter sets/matrix and fully materialized copied directories
**partially answer expansion and provide an excellent hashing boundary**. There
is no cache manifest, include-closure hashing, simulator identity, result model,
or atomic cache, so incrementality is otherwise a **new opportunity**. The
canonical-netlist representation must not be used as the sole netlist hash: it
intentionally omits analyses, options, model bodies, and proprietary directives
that can change simulation results. Doing so would contradict its documented
non-lossless purpose; hash authoritative rendered bytes instead.

## 5. Concrete end-to-end sketch

The following 30-line design sketch uses the recommended hybrid: an existing
schematic-exported DUT in a copied base directory, a small SPICE harness, typed
sidecar edits, a Python study matrix, and Python measurements/specifications.
Names beyond `edits` are proposed API, not implemented behavior.

```python
from sidecar_edits import edits
from analog_studies import Axis, Measurement, Spec, Study, spice

BASE_DIR = "ota_ac_base"          # checked-in harness + exported dut.scs
COMMON_PARAMS = {"cload": "2p", "vcm_ratio": 0.5}
EDITS = [
    edits.write_file(
        path="generated/case.inc",
        content=".temp {temp_c}\n.param VDD={vdd} VCM={vdd}*{vcm_ratio}\n",
        description="materialize PVT operating conditions",
    ),
    edits.replace(
        path="ota_ac.sp",
        old='.lib "models.spice" tt',
        new='.lib "models.spice" {process}',
        description="select process model section",
    ),
]

ota_pvt = Study(
    name="ota_gain_gbw_pm",
    deck="ota_ac.sp", simulator=spice.ngspice(),
    axes=[Axis("process", ["ss", "tt", "ff"]),
          Axis("vdd", [1.62, 1.80, 1.98]), Axis("temp_c", [-40, 27, 125])],
    measurements=[Measurement.ac_gain_db("v(out)"),
                  Measurement.gbw("v(out)"), Measurement.phase_margin("v(out)")],
    specs=[Spec.min("gain_db", 60), Spec.min("gbw", 10e6), Spec.min("pm_deg", 60)],
)

STUDIES = [ota_pvt]
```

The base `ota_ac.sp` would remain ordinary simulator text, for example including
`dut.scs`, `generated/case.inc`, an AC source and load, and `.ac dec ...`.
Before execution the framework would materialize and expose all 27 directories;
after execution it would emit per-corner measurements, per-spec pass/fail, and
an aggregate worst-case report with links back to rendered inputs and logs.

This topic is almost entirely a **new opportunity**. The current renderer can
perform the base copy, edits, and matrix expansion shown here. `Study`, simulator
adapters, measurements, specs, execution, reports, and caching are deliberately
not implemented. The sketch should guide a future API discussion, not expand
the current package without an explicit scope decision.

## Overall conclusion

The manifesto remains plausible only with a narrower claim than “parameterized
analog characterization”: CACE already occupies that space. The project's
distinctive foundation is the reviewable sidecar transformation of arbitrary
working input decks. Preserve that foundation, add a small hybrid testbench
contract, and—only if scope is explicitly expanded—layer deterministic study
expansion, static artifact dependencies, simulator/result adapters, spec
evaluation, and content-addressed reuse. Avoid mandatory canonical IR, a new
schematic system, or a general workflow engine.
