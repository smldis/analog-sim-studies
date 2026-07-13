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
- **Voltage and current bias (Section 4.1/4.2 via Algorithm 1).**
  `netlist_decomposition.bias` implements the paper's Algorithm 1 rather than
  raw Eq. 10/11, which are mutually recursive and contain a negated
  existential no monotone rule can express: per doping, stacks are paired
  into primary voltage/current biases (drain-to-gate plus complete gate-gate
  connection, the current bias carrying no other gate connections and no
  same-doping stack gate on its drain), then secondary voltage biases of
  already-known current biases are added until a fixed point.  As in the
  paper, Eq. 10's last clause (each stack gate has exactly one gate-drain
  partner belonging to some bias) is not checked, and line 8's stack-gate
  test stands in for Eq. 11's "no voltage bias on the drain".  One extra
  guard beyond the paper: a bias pairing must be device-disjoint.
- **Current mirror (Eq. 12).** One voltage bias plus exactly one current
  bias: equal doping, connected stack sources, index-aligned gate-gate
  connections up to the voltage-bias length, voltage-bias drain on a
  current-bias gate, and every non-uppermost voltage-bias gate on exactly
  one member drain.  Multi-output structures produce several overlapping
  pairwise mirror tags sharing the voltage bias -- the paper's
  "current-mirror bench" is that overlap, not a block type.  The `variant`
  property is `scm` only for the one-plus-one composition (the paper's
  simple current mirror); everything else is `unclassified`.
- **Irrelevant multiple assignments (Eq. 19).** Voltage biases, current
  biases, and current mirrors whose member set is a strict subset of
  another block of the same kind are deleted (the simple mirror inside a
  cascode mirror, Fig. 10a).  Other kinds, including stacks, are never
  pruned.  As in the paper, the deletion closes hierarchy level 2: it is
  physically removed from the block index at the end of the HL2 stage --
  after the differential pairs, which Algorithm 1 finds against the
  pre-deletion current biases -- so HL3 and every caller read the cleaned
  set directly.
- **Differential pair, gate-connected couple, cascode pair (Eq. 13-17).**
  `netlist_decomposition.hl2` recognizes the full `differential_pair` (two
  normal transistors, equal doping, connected only at their sources, with a
  same-doping current-bias drain on the common source), the
  `gate_connected_couple`, and the `cascode_differential_pair` with its
  `fcdp`/`cdp` doping subtypes.  Matching Algorithm 1's ordering, pairs are
  found against the pre-Eq.-19 current biases.  Couples are only tagged as
  constituents of a cascode pair; standalone Eq. 14 matches (e.g. the upper
  devices of a cascode mirror) are not emitted.  Eq. 13 has no bulk
  condition, unlike the legacy `differential_pair_candidate`, which stays
  as a cheap tag for netlists without recognizable biases.
- **Non-inverting transconductance (Eq. 20-22).** `tcs` (one pair or one
  cascode pair with no gate connection to any other pair), `tcc` (two
  simple pairs, opposite doping, both gates connected), `tccmfb` (two
  simple pairs, equal doping, exactly one shared gate).  Complementary and
  CMFB types over cascoded pairs are not built.
- **Load (Algorithm 3, deliberately not Eq. 24/25).** The paper recommends
  its Algorithm 3 because it works when the load is biased externally: for
  each transconductance output net, same-doping stacks whose drain sits on
  the net and whose source reaches the doping-matching declared rail or
  another transconductance output form the NMOS/PMOS load parts.  Stacks
  sharing a device with the transconductance are excluded; without that
  guard the Section 4.6 false stacks (tail plus input device) would be
  recognized as loads.  Rail-connected load parts require declared
  supplies.
- **Current-output stage bias (Eq. 28/29).** The Eq.-19-maximal current
  biases whose drains sit on a transconductance source, one `stage_bias`
  tag per transconductance.  The voltage-output stage bias (Eq. 26/27) is
  not implemented: Algorithm 2 resolves it, together with the inverting
  transconductance (Eq. 23), inside the amplification-stage loop, i.e.
  with HL4.
- **Source follower (extension, not a paper rule).** The paper's
  transconductance types do not cover a transistor whose voltage output is
  its own source: the non-inverting types are built on differential pairs
  and the inverting type (Eq. 23) outputs at a stack drain.  A
  common-drain stage is a voltage buffer, not a transconductance stage,
  so the extension introduces new kinds instead of stretching the paper's
  taxonomy.  Following the paper's abstraction boundaries, the follower
  is split across levels: at HL2 (justified by the paper's own precedent
  -- the analog inverter Eq. 18 uses rail knowledge at HL2, and the
  mirror Eq. 12 composes other HL2 blocks), a normal transistor outside
  every differential pair, drain on the doping-matching declared rail
  (NMOS: vdd, PMOS: vss), with a same-doping Eq.-19-maximal current bias
  from its source to the opposite rail, becomes a `source_follower` with
  `function=voltage_buffer`.  At HL3, the bias becomes a `stage_bias`
  with `output_type=voltage` (the Eq. 26/27 flavor, though not their
  formulation) and the composition is emitted as a
  `source_follower_stage` -- a buffer stage, deliberately not an HL4
  amplification stage.  Recognition requires both the declared rails and
  the bias -- a rail-connected transistor alone is never a follower.  The
  underlying bias-plus-follower Eq. 9 stack remains tagged; the stack is
  the structure, the stage is its function.
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
  excludes drain-source-shorted devices per Eq. 8.  The former grouped
  `simple_current_mirror` kind was replaced by pairwise `current_mirror`
  tags built from resolved biases.
- **Supply nets are declared, never inferred.**
  `decompose(circuit, vdd_nets=..., vss_nets=...)` stores the rails on the
  `CircuitGraph` (positive rails and ground rails separately, as
  Algorithm 3 and Eq. 18 are doping-specific); no name-based guessing.
  Without declared rails, loads are only found in folded arrangements.
- **The pipeline is explicit hierarchy levels** (`HIERARCHY_LEVELS`,
  matching the paper's numbering): HL1 classifies transistors (Eq. 7/8);
  HL2 runs the monotone structural rules (stacks, candidates), then
  Algorithm 1 (biases, mirrors), then the Eq. 13-17 pairs and the source
  follower, and closes with the Eq. 19 deletion, mirroring Algorithm 1;
  HL3 resolves transconductances, loads, stage biases, and stages per
  Algorithm 2.  Every level leaves the index in its complete post-level
  state, so destructive normalization happens at the earliest point where
  no later consumer needs the removed blocks.  The resolution passes need
  complete block sets and negative conditions, so they cannot
  be ordinary monotone rules; monotone rules carry a `level` attribute
  (default 2) selecting the level whose fixed point runs them.
  `decompose(..., max_level=1|2|3)` stops after the given level, and each
  `HierarchyLevel.run(graph, blocks, rules)` can be applied individually
  to a caller-owned index, provided the lower levels ran before.

## Exact versus candidate names

- Exact per the paper: `normal_transistor`, `diode_transistor`,
  `transistor_stack` (Eq. 7/8/9 as above); `voltage_bias`, `current_bias`,
  and `current_mirror` to the fidelity of the paper's own Algorithm 1
  (with the documented Eq. 10/11 approximations the paper itself makes);
  `differential_pair`, `gate_connected_couple`,
  `cascode_differential_pair` (Eq. 13-17); `transconductance` for the
  non-inverting types (Eq. 20-22); `load` per Algorithm 3; `stage_bias`
  for the current-output type (Eq. 28/29).
- Extensions with no paper counterpart: `source_follower` (the
  common-drain transistor itself, `function=voltage_buffer`), the
  `output_type=voltage` stage bias produced with it, and
  `source_follower_stage`.  `transconductance` remains exclusively the
  paper's types.
- Stack `structural_variant` labels are composition-only, derived from the
  bottom-to-top `member_classes` (`nt`/`dt`) sequence: `single_normal`,
  `single_diode`, `all_normal`, `diode_pair` (the paper's dip), `all_diode`,
  `mixed_pair_diode_bottom`, `mixed_pair_diode_top`, `mixed`. The paper's
  cascode pair (cp) and mixed pairs mp1/mp2 additionally require the
  enclosing HL2 voltage/current bias (Fig. 4 and 5), and vr1/vr2 require
  specific gate connections; none of those names are claimed.
- `differential_pair_candidate` and `cmos_inverter` predate this alignment
  and do not implement the paper's full HL2 definitions (Eq. 13-18); the
  differential pair is explicitly a candidate.

## Unimplemented paper rules

- Bias-dependent stack variant names (cp, mp1, mp2, vr1, vr2) and the named
  current-mirror examples beyond scm (ccm, 4cm, wcm, wscm, iwcm from
  Fig. 6): mirrors with longer stacks carry `variant=unclassified`.
- Full analog inverter (Eq. 18), inverting transconductance (Eq. 23), and
  the paper's voltage-output stage bias (Eq. 26/27): Algorithm 2
  recognizes these inside the amplification-stage loop, so they belong to
  the HL4 step.  (The follower's voltage-output stage bias above is a
  separate extension, not an Eq. 26/27 implementation.)
- Cascoded source followers (follower reaching the rail through a stack)
  and followers biased by unrecognized structures.
- All of HL4-HL5: amplification stages (Eq. 30-33), circuit bias,
  compensation/load capacitors, op-amp classification.
- Complementary/CMFB transconductances over cascoded pairs.
- Section 4.6 false-stack suppression beyond the differential-pair case
  listed above (Algorithm 1's ordering, where inverters are recognized last
  to avoid false positives inside differential pairs, becomes relevant once
  the full inverter exists).

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
