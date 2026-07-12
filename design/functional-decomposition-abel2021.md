# Functional Decomposition: Abel et al. (2021) Alignment

Scope note for `src/netlist_decomposition/`. The reference is Abel, Neuner,
Graeb (2021), *A Functional Block Decomposition Method for Automatic Op-Amp
Design*. Only the parts listed below are implemented; this is not the full
paper decomposition.

## Implemented paper rules

- **Hierarchy level 1 (Section 3, Eq. 7 and 8).**
  `normal_transistor`: a supported MOS whose drain, gate, and source sit on
  three distinct nets (no self connections). `diode_transistor`: drain and
  gate share a net, drain and source do not. A device with a gate-source or
  drain-source short is neither. Connectivity is net identity in the canonical
  netlist; the equations' negated connection operators (overbarred arrows in
  the PDF) are implemented as "different net".
- **Transistor stacks (Section 4 introduction, Eq. 9).**
  Stacks of length 1-3 are built from the HL1 tags, not from raw devices.
  Multi-device stacks require equal known polarity (`nmos`/`pmos`); adjacent
  members connect lower drain to higher source; a higher member's gate must
  not touch a lower member's drain, and a higher member's drain must not
  touch a lower member's source; no transistor is reused within one stack.
  Eq. 9 states the two exclusions for adjacent members only, while the
  prose ("higher transistor gates are not allowed to be connected to drains
  of lower transistors...") quantifies over all lower/higher pairs. The
  implementation uses the stricter all-pairs prose reading; the readings
  differ only for non-adjacent members of three-device stacks, where the
  all-pairs form also rejects degenerate three-device rings. For two-device
  stacks the gate exclusion is already implied by HL1: a higher gate on the
  internal net would be a gate-source self connection.
- **Section 4.6 false stacks (partial).** `suppress_false_stacks` removes
  stacks whose internal net is the common source of a
  `differential_pair_candidate` and that include one of the pair's devices
  (tail-plus-input false stacks, the paper's Fig. 8/10b case).

## Conventions

- **Member ordering** is bottom-to-top, i.e. source end to drain end,
  matching the paper's `x_{k,1} .. x_{k,n}` numbering: the role
  `ordered_devices[0]` provides the stack `source` net, the last member the
  stack `drain` net.
- **Drain/source orientation is assumed canonical.** The engine never swaps
  or infers drain/source (or bulk) roles.
- **Tags overlap and are not a partition.** One device is typically a
  `normal_transistor`, a one-device `transistor_stack`, and possibly part of
  larger stacks, mirrors, or pair candidates at the same time. Sub-chains of
  a three-device stack are themselves reported as stacks, as Eq. 9 admits.
- **Polarity comes only from canonical device types.** `nmos`/`pmos` are the
  polarity classes. Generic `mosfet` devices are classified on HL1 and form
  one-device stacks, but are excluded from every same-doping comparison
  (multi-device stacks, mirrors, pair candidates). Device names are never
  used to infer polarity.
- The former `diode_connected_mos` tag kind was replaced by
  `diode_transistor` (no alias is kept); the new predicate additionally
  excludes drain-source-shorted devices per Eq. 8.

## Exact versus candidate names

- Exact per the paper: `normal_transistor`, `diode_transistor`,
  `transistor_stack` (Eq. 7/8/9 as above).
- Stack `structural_variant` labels are composition-only, derived from the
  bottom-to-top `member_classes` (`nt`/`dt`) sequence: `single_normal`,
  `single_diode`, `all_normal`, `diode_pair` (the paper's dip), `all_diode`,
  `mixed_pair_diode_bottom`, `mixed_pair_diode_top`, `mixed`. The paper's
  cascode pair (cp) and mixed pairs mp1/mp2 additionally require the
  enclosing HL2 voltage/current bias (Fig. 4 and 5), and vr1/vr2 require
  specific gate connections; none of those names are claimed.
- `simple_current_mirror`, `differential_pair_candidate`, and
  `cmos_inverter` predate this alignment and do not implement the paper's
  full HL2 definitions (Eq. 10-15): the mirror rule consumes
  `diode_transistor` references but does not build the paper's voltage/
  current bias pair, and the differential pair is explicitly a candidate.

## Unimplemented paper rules

- HL2 voltage bias and current bias (Eq. 10 and 11) and therefore all
  bias-dependent stack variant names (cp, mp1, mp2, vr1, vr2).
- The paper's current mirror (Eq. 12) built from vb/cb, and every HL2+ block
  beyond the simple candidates above; all of HL3-HL5.
- Section 4.6 beyond the false-stack case listed above: irrelevant same-type
  containment (Eq. 19) and bias-informed suppression. Extend
  `suppress_false_stacks` when the HL2 blocks exist.

## Optional policies

`transistor_stack_rule(exclusive_internal_nets=True)` restores the old
conservative behavior that every stack-internal net must carry exactly two
MOS drain/source terminals. This is not a paper rule (default off); it
over-approximates Section 4.6 by dropping every branching stack, including
paper-valid ones.

## Manual verification

Against the SKY130 OTA in the sibling workspace (uses the real extraction
pipeline with the workspace's device type map, no rendered-text parsing):

```bash
python scripts/verify_ota_decomposition.py
```
