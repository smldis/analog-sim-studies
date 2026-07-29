# Canonical Netlist Representation

The canonical netlist representation is an LLM-oriented structural view of an
Eldo or ngspice netlist. It complements the original netlist; it is not a
replacement for simulator input or a lossless serialization of every simulator
directive.

The representation gives two reciprocal views of circuit connectivity:

- the devices and pins incident on each net;
- the named nets connected to each device.

Subcircuit interfaces are represented separately so an instance can use formal
pin names instead of positional pin numbers.

## Tables

Each subcircuit has a one-column interface table. Pin order is the declaration
order from the original `.SUBCKT` statement, but numeric pin identifiers are not
introduced.

```text
SUBCKT INV
pin
A
Y
VDD
VSS
```

Each circuit, including `TOP`, has a net-incident table with one row per net.

```text
NET_INCIDENT_TABLE INV
net | incident pins
A   | M1.g, M2.g
Y   | M1.d, M2.d
VDD | M1.s, M1.b
VSS | M2.s, M2.b
```

An incident pin uses `instance.pin`. Primitive devices use semantic terminal
names such as `d`, `g`, `s`, and `b`. Subcircuit instances use the formal pin
names from the corresponding `SUBCKT` table.

Each circuit also has a device table.

```text
DEVICE_TABLE INV
name | type | connections | parameters
M1 | pmos | d=Y, g=A, s=VDD, b=VDD | model=PCH, W=2u, L=180n
M2 | nmos | d=Y, g=A, s=VSS, b=VSS | model=NCH, W=1u, L=180n
```

A subcircuit instance uses its subcircuit name as its type and maps formal pins
to nets by name.

```text
DEVICE_TABLE TOP
name | type | connections | parameters
X1 | INV | A=in, Y=out, VDD=vdd, VSS=0 |
```

The corresponding net rows are:

```text
NET_INCIDENT_TABLE TOP
net | incident pins
in  | X1.A
out | X1.Y
vdd | X1.VDD
0   | X1.VSS
```

## Top Level

The root circuit starts with a reserved marker:

```text
TOP_LEVEL TOP
```

It is followed by the root `NET_INCIDENT_TABLE` and `DEVICE_TABLE`. There is no
root pin table because a SPICE input deck has no declared external pin list.
`TOP_LEVEL` lets a reverse converter locate the root directly without traversing
subcircuit hierarchy or being told the root circuit's display name.
For a library file containing only subcircuit definitions, the marker and both
root tables are omitted; such a representation intentionally has no designated
simulation root.

## Connectivity Invariant

Every device connection has exactly one reciprocal net incident. If a device row
contains:

```text
X1 | INV | A=in |
```

then the `in` net row contains `X1.A`. The Python renderer derives the incident
table from parsed device connections so these views cannot diverge.

Subcircuit pins with no internal connection are still emitted as empty net rows.
This preserves the complete declared interface.

## Buses

Bus indices and ranges use angle brackets and retain the spelling from the source
netlist.

```text
SUBCKT REGISTER
pin
D<9:0>
Q<9:0>
CLK
VDD
VSS
```

Uniform whole-bus connectivity may remain compact:

```text
XREG | REGISTER | D<9:0>=DATA<9:0>, Q<9:0>=RESULT<9:0>, CLK=clk |
```

```text
DATA<9:0>   | XREG.D<9:0>
RESULT<9:0> | XREG.Q<9:0>
```

When bits have different connectivity, the source netlist should expose those
bits separately and the canonical form emits one row per bit:

```text
DATA<3> | XREG.D<3>, U1.Y
DATA<2> | XREG.D<2>, U2.Y
```

The extractor does not infer or expand bus semantics that are not present in the
source.

## Delimiters

The structural punctuation is deliberately small:

```text
|     separates table columns
,     separates items within a cell
.     separates an instance name from its pin
=     maps a pin to a net or a parameter to a value
:     is not a structural delimiter; it remains available for bus ranges
< >   enclose bus indices and ranges
```

A literal `|`, backslash, or newline inside a rendered cell is backslash-escaped.
Parameter expressions otherwise retain their source spelling.

## Annotations

The core form is structural. Information not explicitly encoded by ordinary
SPICE, such as pin direction or signal class, can be added later as columns:

```text
SUBCKT INV
pin | direction | class
A   | input     | signal
Y   | output    | signal
VDD | input     | power
VSS | input     | ground
```

Inferred annotations should carry provenance or confidence separately from the
structural extraction.

## Python Extractor

The implementation is in `spice_canonical.canonical_netlist`.

```python
from spice_canonical.canonical_netlist import from_file

netlist = from_file("input.spi", top_name="TOP", spice_format="eldo")
print(netlist.render())

for diagnostic in netlist.diagnostics:
    print(f"{diagnostic.source}:{diagnostic.line}: {diagnostic.message}")
```

The module also provides a command-line interface:

```bash
spice-canonical input.spi --output canonical.txt
spice-canonical input.spi --top-name CHIP
spice-canonical input.spi --strict
spice-canonical input.cir --format ngspice --strict
spice-canonical input.cir --device-type-map device-types.json
```

Without `--output`, the representation is written to standard output. Warnings
are written to standard error. `--strict` returns a failure when any statement
cannot be completely resolved.

Library primitives represented as opaque subcircuit instances can optionally be
normalized before rendering. The pass is activated explicitly with
`device_type_map` in the Python API or `--device-type-map` in the CLI. Its JSON
form maps source type names to canonical type names:

```json
{
  "sky130_fd_pr__nfet_01v8": "nmos",
  "sky130_fd_pr__pfet_01v8": "pmos"
}
```

Matching is case-insensitive. A normalized device retains its original library
name in the `source_type` parameter. With no map, extraction preserves existing
device types exactly as before.

## Supported Extraction

The parser handles:

- case-insensitive SPICE directives and names while preserving source spelling;
- `.SUBCKT`/`.ENDS`, declaration parameters, and named subcircuit calls;
- `.MODEL` declarations for device-type refinement;
- leading `+` continuation lines;
- full-line `*` and `//` comments and inline `$` or whitespace-delimited `//`
  comments;
- grouped quoted, parenthesized, bracketed, and braced expressions;
- common `R`, `C`, `L`, `V`, `I`, `B`, `D`, `M`, `J`, `Q`, `E`, `F`, `G`,
  `H`, `S`, `T`, `O`, `W`, `K`, and `X` devices.
- recursive `.INCLUDE` and `.INC` expansion when using `from_file` or the CLI.

Pass `spice_format="ngspice"` to the Python API, or `--format ngspice` to the
CLI, for ngspice decks. Ngspice mode additionally handles:

- the first physical line of the root deck as its title;
- semicolon end-of-line comments;
- `.CONTROL`/`.ENDC` blocks without treating control commands as devices;
- model-bin families such as `nch.1`, `nch.2`, instantiated as `nch`;
- `U` uniform distributed RC lines and `Z` MESFET devices.

The title rule applies only to the root deck. The first line of an included file
is retained because `.INCLUDE` has textual insertion semantics.

Unsupported proprietary device prefixes are retained in the device table as
`unresolved`, with their unparsed text in `raw` and a diagnostic. The extractor
does not invent terminal names because doing so would create false graph edges.
Variable-topology XSPICE code models and coupled multiconductor lines are
currently retained this way.

File-based extraction treats includes as textual insertion. Relative paths are
resolved from the directory containing each include directive. Quoted paths,
home-directory paths, and environment variables are supported. Nested includes
are expanded recursively in simulator order. As a result:

- top-level devices from included files are concatenated into the parent circuit;
- included `.SUBCKT` definitions receive their own canonical tables;
- included `.MODEL` declarations participate in device-type resolution;
- instances in any expanded file can resolve subcircuits declared in another;
- missing files and include cycles are skipped with source-qualified diagnostics.

Repeated non-cyclic includes are expanded each time, matching textual include
semantics. Duplicate resulting subcircuits or device names are therefore reported
as structural errors. `.LIB` section selection and simulator-specific library
search paths are not expanded.

`from_text` has no base directory and therefore leaves include directives
unexpanded. Use `from_file` when resolving a multi-file deck.

## Ngspice Corpus Verification

The repository includes a networked compatibility verifier:

```bash
python scripts/verify_ngspice_corpus.py
```

It downloads three checksum-pinned examples from the official ngspice repository,
runs each one through an installed `ngspice` in batch mode, then requires a strict,
diagnostic-free canonical extraction:

- [`gain_stage.cir`](https://github.com/ngspice/ngspice/blob/master/examples/various/gain_stage.cir)
- [`inv-meas-tran-control.sp`](https://github.com/ngspice/ngspice/blob/master/examples/measure/inv-meas-tran-control.sp)
- [`ltra1_1_line.sp`](https://github.com/ngspice/ngspice/blob/master/examples/TransmissionLines/ltra1_1_line.sp)

Normal unit tests remain offline. A small local integration test runs ngspice when
the executable is available and otherwise skips only that simulator invocation.

Analysis commands, options, model bodies, global parameters, and other simulator
directives are intentionally omitted from the structural representation. The
original Eldo or ngspice deck remains the authoritative source for simulation.
