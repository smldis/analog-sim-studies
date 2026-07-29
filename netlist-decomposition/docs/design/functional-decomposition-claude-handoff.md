# Claude Code Handoff: Paper-Aligned Transistor-Stack Decomposition

This handoff was executed from the Analog Sim Studies repository root. The
decomposition unit now lives at:

```text
netlist-decomposition/
```

Upgrade the existing functional-block decomposition prototype so that its HL1
transistor classification and transistor-stack recognition follow Abel et al.
(2021), *A Functional Block Decomposition Method for Automatic Op-Amp Design*,
more faithfully.

The paper was supplied from a local Zotero library as:

```text
Abel et al. - 2021 - A Functional Block Decomposition Method for Automatic Op-Amp Design.pdf
```

Read the relevant paper sections before changing code:

- Section 3: hierarchy level 1, especially Equations 7 and 8.
- Section 4 introduction: transistor stacks, especially Equation 9.
- Sections 4.1 and 4.2 and Figures 4 and 5 for voltage-bias/current-bias stack
  variants.
- Section 4.6 for multiple assignments and false stack suppression.

Do not rely only on this handoff for the mathematical definitions. Check the
paper, including whether symbols mean connected or explicitly not connected;
PDF text extraction may lose overbars or other mathematical formatting.

## Repository boundaries

Follow `AGENTS.md` before editing.

Keep functional decomposition under:

```text
src/netlist_decomposition/
```

Do not move decomposition logic into `sidecar_edits`. The decomposition package
may consume the canonical data classes currently provided by
`spice_canonical.canonical_netlist`, maintained as an independent package in
this repository, but it is a separate concern.

Relevant files:

```text
src/netlist_decomposition/engine.py
src/netlist_decomposition/__init__.py
tests/test_netlist_decomposition.py
src/spice_canonical/canonical_netlist.py
design/canonical-netlist-representation.md
```

The working tree may already contain user changes. Inspect `git status` and do
not overwrite or revert unrelated work. In particular, canonical-netlist and
device-type-normalization work may be uncommitted.

## Existing behavior

The current engine:

- accepts one canonical `Circuit` at a time;
- assumes MOS drain/source orientation is already correct;
- applies ordered rules to a fixed point;
- supports overlapping `BlockTag` assignments;
- recognizes diode-connected MOS devices;
- recognizes generic oriented stacks of two or three MOS devices;
- recognizes simple current mirrors, differential-pair candidates, and CMOS
  inverters.

The current stack matcher is only an approximation. It works directly from raw
MOS devices, omits one-device stacks, does not build from explicit HL1 normal
and diode transistor tags, and does not enforce all Equation 9 exclusions.

## Required implementation

### 1. Make MOS recognition reusable

Keep normalized canonical types `nmos` and `pmos` as the primary polarity
classes. Generic `mosfet` may be supported only where its polarity is known
well enough to make a same-doping comparison meaningful. Do not infer polarity
from device names.

Centralize helpers for:

- testing whether a device is a supported MOS;
- retrieving `d`, `g`, `s`, and `b` nets;
- comparing transistor doping/polarity;
- testing pin-to-pin net connectivity.

Do not add drain/source swapping or normalization to the decomposition engine.

### 2. Implement explicit HL1 transistor tags

Add paper-aligned HL1 tags:

```text
normal_transistor
diode_transistor
```

A diode transistor is a MOS whose drain and gate are connected. A normal
transistor is a supported MOS that is not diode-connected, subject to the exact
paper exclusions in Equations 7 and 8. Verify the equations visually in the PDF
because extracted text may omit negation bars.

Each HL1 transistor tag should contain:

- the single member device;
- role `device`;
- MOS polarity/doping as a property;
- relevant terminal nets;
- the rule that created it.

Decide whether to retain `diode_connected_mos` as a compatibility alias or
replace it with `diode_transistor`. Prefer one canonical internal kind. If an
alias is retained, document and test its behavior so higher-level rules do not
double-count the same physical classification.

### 3. Replace the generic stack matcher with Equation 9 behavior

Construct transistor stacks from HL1 `normal_transistor` and
`diode_transistor` tags, not directly from arbitrary devices.

Implement stacks of length 1, 2, and 3. For multi-device stacks:

- all members must have the same doping/polarity;
- consecutive devices must have the paper-defined lower-drain to higher-source
  connection;
- enforce the paper's forbidden cross-connections:
  - a higher transistor gate must not be connected to a lower transistor drain;
  - a higher transistor drain must not be connected to a lower transistor
    source;
- do not reuse a transistor within one stack;
- produce each ordered stack only once;
- preserve the paper's source-to-drain or bottom-to-top ordering explicitly and
  document which convention is used.

Represent at least:

```text
kind: transistor_stack
roles:
  ordered_devices: (...)
nets:
  source: ...
  drain: ...
properties:
  length: 1 | 2 | 3
  mos_type: nmos | pmos
  member_classes: normal_transistor/diode_transistor sequence
```

Do not silently keep the current extra restriction that an internal net must
have exactly two MOS drain/source incidents unless the paper requires it. If it
is useful as an optional conservative policy, expose it explicitly, name it,
default it appropriately, and test both modes.

### 4. Add stack-variant classification

After the generic Equation 9 stack tags work, add structural subtype metadata or
separate tags for the paper's recognizable member-class variants. At minimum,
cover the variants that can be determined from the `nt`/`dt` sequence alone,
such as:

- all-normal stack;
- diode pair (`dip`);
- mixed normal/diode arrangements corresponding to the paper's mixed-pair
  variants where topology is sufficient.

Do not claim to recognize voltage reference, voltage bias, current bias, or
cascode functional meaning from member classes alone when the paper requires
connections to other blocks. For those cases, either:

- implement the full required connectivity rule; or
- emit a clearly named structural candidate and document what remains
  unverified.

Use the terminology in Figures 4 and 5 only after confirming exactly which
names refer to stack composition and which refer to the enclosing HL2 voltage
or current bias.

### 5. Update dependent rules

Update simple-current-mirror recognition to consume the new canonical
`diode_transistor`/bias inputs without regression. Do not let compatibility
aliases create duplicate mirrors.

Review differential-pair and CMOS-inverter rules for interactions with
one-device stacks. Do not broaden their claims without implementing the paper's
full constraints. Candidate names are preferable to false certainty.

### 6. Handle multiple assignments deliberately

Overlapping assignments are valid, especially at HL2. Preserve them.

Add only the suppression needed to prevent demonstrably false duplicate stack
interpretations described by the paper. Keep candidate generation separate from
suppression/selection where practical. A rule should not discard a valid
low-level tag merely because a higher-level interpretation also exists.

If full Section 4.6 suppression depends on functional blocks not implemented
yet, document that limitation and add an explicit extension point rather than
inventing a partial rule that appears complete.

## Tests

Extend `tests/test_netlist_decomposition.py` with small canonical circuits that
cover at least:

1. One normal MOS produces `normal_transistor` and a length-one stack.
2. One diode-connected MOS produces `diode_transistor` and a length-one stack.
3. Valid two-device all-normal stack.
4. Valid three-device stack.
5. Same-polarity requirement rejects mixed NMOS/PMOS chains.
6. Higher-gate/lower-drain forbidden connection rejects a candidate.
7. Higher-drain/lower-source forbidden connection rejects a candidate.
8. Reversed or duplicate enumeration does not produce duplicate stack tags.
9. A transistor is not reused within a cyclic path.
10. Diode-pair and mixed-member structural classifications.
11. Existing simple current-mirror recognition still works.
12. Multiple-output current mirrors still work.
13. Existing differential-pair and CMOS-inverter behavior does not regress.

Prefer constructing circuits through `canonical_netlist.from_text` so tests also
exercise the real canonical device representation. Add direct `Circuit` unit
tests only where they isolate an engine invariant more clearly.

Also test the existing SKY130 OTA fixture if it can be done without coupling the
publishable package tests to the sibling workspace. Otherwise use an equivalent
small fixture inside the test file and give a manual verification command.

## Manual verification fixture

After tests pass, run the decomposition against:

```text
../sky130-analog-workspace/canonical-index/analog_frontend_hier_op.canonical.txt
```

The corresponding canonical generation pipeline now supports an explicitly
activated device type map. SKY130 extraction maps:

```text
sky130_fd_pr__nfet_01v8 -> nmos
sky130_fd_pr__pfet_01v8 -> pmos
```

using:

```text
../sky130-analog-workspace/canonical/sky130_device_types.json
```

The existing OTA should at least identify:

- `XM3` and `XM8` as diode transistors;
- `XM1` and `XM2` as normal transistors and a differential-pair candidate;
- `XM3`/`XM4` as a PMOS simple mirror;
- `XM8` with `XM5` and `XM7` as an NMOS multi-output simple mirror;
- the paper-valid status of the `XM6`/`XM7` stack, determined using all Equation
  9 constraints rather than the old approximate matcher.

Do not add a permanent parser for rendered canonical text merely for this test.
Prefer obtaining `CanonicalNetlist` from the source extraction pipeline and
passing its `Circuit` objects directly to `decompose`. If a text reader is a
separate desired feature, keep it out of this upgrade.

## Documentation

Add a focused design note or module documentation that states:

- which paper hierarchy levels and equations are implemented;
- the ordering convention for stack members;
- which named variants are exact versus candidates;
- which paper rules remain unimplemented;
- that drain/source orientation is assumed canonical;
- that tags overlap and are not a strict device partition.

Avoid claiming that the full Abel et al. decomposition is implemented.

## Verification commands

Run at minimum:

```bash
cd netlist-decomposition
python -m pytest -q tests/test_netlist_decomposition.py
python -m pytest -q tests
git diff --check
```

Do not regenerate documentation HTML or install dependencies unless necessary.

## Acceptance criteria

The work is complete when:

- HL1 normal and diode transistor tags are explicit and tested;
- stacks of length 1–3 are derived from those HL1 tags;
- Equation 9 polarity, adjacency, and forbidden-connection rules are enforced;
- member ordering and stack terminal naming are unambiguous;
- paper terminology is used only where its full structural predicate is met;
- dependent mirror behavior remains correct without duplicate tags;
- overlapping assignments remain supported;
- limitations around HL2 bias variants and Section 4.6 suppression are explicit;
- the complete test suite passes;
- the final response summarizes changed files, exact implemented rules, test
  results, and remaining paper gaps.
