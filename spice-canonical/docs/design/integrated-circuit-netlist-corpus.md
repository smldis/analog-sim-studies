# Integrated-Circuit Netlist R&D Corpus

This note identifies existing open netlists that are useful for research and
development of the canonical SPICE graph extractor. The focus is transistor-level
integrated circuits rather than board-level or discrete-component examples.

The proposed corpus mixes four kinds of material:

1. Self-contained decks that can be executed by ngspice.
2. Structural analog benchmarks that do not include simulation models.
3. Dialect stress cases that expose unsupported syntax.
4. PDK-backed and generated designs for realistic include and hierarchy testing.

## Recommended Sources

| Source | Integrated-circuit coverage | Current result | Primary value |
| --- | --- | --- | --- |
| [ngspice 4-bit MOS adder](https://github.com/ngspice/ngspice/blob/master/examples/various/adder_mos.cir) | NAND hierarchy and a transistor-level four-bit digital adder | ngspice and strict canonical extraction pass | Digital hierarchy and repeated subcircuits |
| [ngspice transimpedance amplifier](https://github.com/ngspice/ngspice/blob/master/examples/TransImpedanceAmp/output.net) | TIA containing AD780 and OP177 macromodels | ngspice and strict canonical extraction pass | Large BJT, dependent-source, and macromodel hierarchy |
| [ALIGN examples](https://github.com/ALIGN-analoglayout/ALIGN-public/tree/master/examples) | OTAs, comparators, VCOs, mixers, switched-capacitor and RF blocks | Five-transistor OTA and high-speed comparator extract cleanly | Small structural regression cases |
| [ALIGN Circuits Database](https://github.com/ALIGN-analoglayout/ALIGN-public/tree/master/CircuitsDatabase) | Low-frequency analog, power management, RF, and wireline circuits | Requires per-dialect and PDK handling | Main topology-diversity dataset |
| [MAGICAL examples](https://github.com/magical-eda/MAGICAL/tree/master/examples) | Comparator, several OTAs, and continuous-time delta-sigma ADC | Exposes unsupported Spectre and HSPICE constructs | Dialect compatibility development |
| [OpenFASOC generators](https://github.com/idea-fasoc/OpenFASOC/tree/main/openfasoc/generators) | Temperature sensor, LDO, LC-DCO, DC-DC converter, and SCPA | Templates require rendering and an installed PDK | Generated decks, includes, and system-level hierarchy |
| [SKY130 high-density cells](https://github.com/google/skywater-pdk-libs-sky130_fd_sc_hd/tree/main/cells) | Hundreds of transistor-level standard cells | Requires SKY130 primitive definitions | Scale, body pins, and repeated cell patterns |
| [IHP SG13G2 tests](https://github.com/IHP-GmbH/IHP-Open-PDK/tree/main/ihp-sg13g2/libs.tech/xschem/sg13g2_tests) | CMOS, SiGe HBT, RF MOS, passives, and Monte Carlo tests | Requires xschem netlisting and IHP models | BiCMOS, RF, and device diversity |

## Locally Verified Examples

The following upstream files were downloaded and tested with ngspice 46 and the
canonical extractor.

### Four-Bit MOS Adder

Source: [ngspice `adder_mos.cir`](https://github.com/ngspice/ngspice/blob/master/examples/various/adder_mos.cir)

- ngspice batch simulation: passed.
- Strict canonical extraction: passed without diagnostics.
- Top-level devices: 10.
- Subcircuits: 4.
- Devices inside subcircuits: 17.
- Relevant structures: NAND, one-bit adder, two-bit adder, and four-bit adder.

This is a compact test of repeated instance names in different subcircuit scopes,
deep named-pin resolution, and transistor-level digital hierarchy.

### Transimpedance Amplifier

Source: [ngspice `output.net`](https://github.com/ngspice/ngspice/blob/master/examples/TransImpedanceAmp/output.net)

- ngspice batch simulation: passed.
- Strict canonical extraction: passed without diagnostics.
- Top-level devices: 50.
- Subcircuits: 3.
- Devices inside subcircuits: 188.
- Relevant structures: TIA, voltage reference, operational amplifiers, BJTs,
  diodes, controlled sources, noise networks, and current limiting.

This is the best immediately available large acceptance case. It exercises a
substantially broader primitive set than the inverter and transmission-line
examples in the initial ngspice corpus.

### ALIGN Structural Cells

Sources:

- [Five-transistor OTA](https://github.com/ALIGN-analoglayout/ALIGN-public/blob/master/examples/five_transistor_ota/five_transistor_ota.sp)
- [High-speed comparator](https://github.com/ALIGN-analoglayout/ALIGN-public/blob/master/examples/high_speed_comparator/high_speed_comparator.sp)

Both files pass strict structural extraction. They do not contain complete model
and analysis environments, so they were not treated as standalone simulator
acceptance tests.

The OTA contains five MOS devices. The comparator contains fifteen MOS devices and
provides a useful clocked regenerative topology.

## ALIGN Circuits Database

The ALIGN Circuits Database is the strongest general-purpose source for this
prototype. It is released under the BSD 3-Clause license and organizes sized
netlists into four classes.

### Low-Frequency Analog

- Cascode current-mirror OTA
- Clocked and unclocked comparators
- Current-mirror OTA
- Five-transistor OTA variants
- Fully differential and telescopic OTAs
- Non-overlapping clock generator
- Switched-capacitor filter
- Switched-capacitor common-mode feedback

### Power Management

- Charge pump
- Gate-driver digital LDO
- 1:1 switched-capacitor DC-DC converter
- 3:1 switched-capacitor DC-DC converter

### Wireless and RF

- Band-pass filter
- Low-noise amplifier
- Mixer
- Oscillator

### Wireline

- Adder
- Double-tail sense amplifier
- Linear equalizers
- Single-to-differential converter
- Transimpedance amplifier
- Variable-gain amplifiers

Many database entries include a circuit netlist, testbench, schematic, or layout.
Some use HSPICE or Spectre syntax and PDK primitive names, so inclusion in an
executable corpus must be decided per file.

## Parser-Gap Cases

These examples are valuable precisely because they do not yet extract cleanly.

### ALIGN Hierarchical VCO

Source: [ALIGN `VCO_type2_65`](https://github.com/ALIGN-analoglayout/ALIGN-public/tree/master/examples/VCO_type2_65)

The netlist uses trailing backslashes for continuation, buses such as `o<8>`, and
hierarchical subcircuit arrays. Extraction currently fails because trailing `\`
continuations are not joined. This should become the acceptance case for that
feature.

### MAGICAL Comparator and OTAs

Sources:

- [Comparator](https://github.com/magical-eda/MAGICAL/blob/master/examples/comp/comp.sp)
- [OTA examples](https://github.com/magical-eda/MAGICAL/tree/master/examples)

The files use Spectre-style constructs including:

- `subckt`, `ends`, and `topckt` without leading dots;
- parenthesized connection lists;
- trailing backslash continuations;
- process-specific primitive names.

These are suitable canaries for a future Spectre dialect rather than ngspice
fixtures.

### MAGICAL Delta-Sigma ADC

Source: [MAGICAL `CTDSM_TOP.sp`](https://github.com/magical-eda/MAGICAL/blob/master/examples/adc1/CTDSM_TOP.sp)

This approximately 30 KB hierarchy contains standard cells, analog blocks,
resistors, capacitors, and a continuous-time delta-sigma signal path. Many devices
are emitted as `X` instances of PDK primitives such as `nch_lvt_mac`,
`pch_lvt_mac`, `rppolywo_m`, and `cfmom_2t`.

It exposes the need for primitive schemas or complete PDK library composition.
Treating every `X` line as an ordinary user subcircuit is insufficient when the
primitive declarations are external.

## PDK-Backed Generated Decks

### OpenFASOC

Recommended material:

- [Temperature sensor ngspice template](https://github.com/idea-fasoc/OpenFASOC/blob/main/openfasoc/generators/temp-sense-gen/simulations/templates/tempsenseInst_ngspice.sp)
- [LDO ngspice templates](https://github.com/idea-fasoc/OpenFASOC/tree/main/openfasoc/generators/ldo-gen/simulations/templates)
- [LC-DCO ngspice simulations](https://github.com/idea-fasoc/OpenFASOC/tree/main/openfasoc/generators/lc-dco/simulations/Ngspice)

These decks exercise:

- generated `${...}` and template-language expressions;
- large bus interfaces using square-bracket notation;
- `.lib` model-corner selection;
- generated `.include` paths;
- standard-cell and analog-macro hierarchy;
- inductors, MiM capacitors, and extracted subcircuits;
- control blocks and measurement statements.

They should be tested only after rendering with the generator and installing the
matching PDK. Raw templates are useful parser canaries but are not valid simulator
inputs by themselves.

### SKY130 Standard Cells

The SKY130 high-density cell library provides a large set of transistor-level
subcircuits with explicit power and body pins. A representative corpus should
sample several functional classes instead of importing the whole library at
first:

- inverter, NAND, NOR, XOR, and multiplexer;
- latch and flip-flop;
- clock-gating and clock-buffer cells;
- level shifter and isolation cells;
- decap, diode, and tap cells.

This tier is useful for scale, naming conventions, body-pin connectivity, and
PDK-primitive subcircuit resolution.

### IHP SG13G2

The IHP test library adds structures absent from a CMOS-only corpus:

- SiGe HBT devices;
- RF NMOS devices;
- high-voltage and isolated MOS devices;
- Schottky and ESD diodes;
- MiM and RF capacitors;
- Monte Carlo and temperature sweeps.

The sources are xschem schematics. Reproducible use requires the IHP PDK and a
headless xschem netlisting step before canonical extraction.

## Proposed Corpus Tiers

### Tier 1: Executable Acceptance

Require both ngspice success and diagnostic-free strict extraction:

- Official ngspice four-bit MOS adder
- Official ngspice transimpedance amplifier
- Existing gain-stage, inverter, and LTRA cases

### Tier 2: Structural Topology

Require diagnostic-free extraction but not simulation:

- ALIGN five-transistor OTA
- ALIGN high-speed comparator
- Selected ALIGN current-mirror and telescopic OTAs
- Selected charge-pump, mixer, and TIA cells

### Tier 3: Dialect Canaries

Expected to fail until a named parser feature is implemented:

- ALIGN hierarchical VCO for trailing `\` continuation
- MAGICAL comparator for Spectre connection syntax
- MAGICAL delta-sigma ADC for external PDK primitive schemas

### Tier 4: Rendered PDK Integration

Require a pinned PDK and generator environment:

- OpenFASOC temperature sensor
- OpenFASOC LDO
- OpenFASOC LC-DCO
- Selected SKY130 and IHP cells

## Development Priorities Exposed by the Corpus

1. Add trailing-backslash continuation support.
2. Add an explicit Spectre dialect with `subckt`, `ends`, `topckt`, and
   parenthesized connection lists.
3. Add `.lib <file> <section>` expansion and model-corner selection.
4. Separate PDK primitive schemas from ordinary user-defined subcircuits.
5. Support both angle-bracket and square-bracket bus naming consistently.
6. Define a preprocessing interface for generated template decks.
7. Record source provenance for every circuit, device, and connection, not only
   diagnostics.
8. Add corpus metadata for source URL, revision, checksum, license, expected
   dialect, required PDK, and expected extraction status.

The immediate next corpus additions should be the official ngspice adder and TIA,
because both are already executable and extract cleanly. ALIGN OTA and comparator
cells should follow as offline structural fixtures. The VCO and MAGICAL examples
should remain expected-failure canaries until their specific dialect features are
implemented.
