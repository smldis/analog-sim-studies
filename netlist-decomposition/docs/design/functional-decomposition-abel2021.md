# Functional Decomposition: Abel et al. (2021) Alignment

Scope note for `src/netlist_decomposition/`. The reference is Abel, Neuner,
Graeb (2021), *A Functional Block Decomposition Method for Automatic Op-Amp
Design*. Only the parts listed below are implemented; this is not the full
paper decomposition.

The current rule dependencies are structured metadata rendered in
[functional-decomposition-dependencies.md](functional-decomposition-dependencies.md),
the Markdown-table counterpart of Figure 15. The generated table deliberately
separates hierarchy levels (tag taxonomy) from composition passes (recognition
order). Regenerate or verify it with:

```bash
python scripts/generate_decomposition_dependencies.py
python scripts/generate_decomposition_dependencies.py --check
```

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
  physically removed from the block index at the end of the structure
  pass -- after the differential pairs, which Algorithm 1 finds against
  the pre-deletion current biases -- so the stage pass and every caller
  read the cleaned set directly.
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
- **Analog inverter (Eq. 18).** Two all-normal-transistor stacks of
  opposite doping joined at their drains, each source on the
  doping-matching declared rail, with no gate-gate, gate-drain, or
  source-source connection between any two member transistors -- which
  also excludes the gate-coupled digital CMOS inverter (that stays the
  legacy `cmos_inverter` tag).  Recognized last within the structure pass, as
  Algorithm 1 line 19 prescribes; stacks sharing a device with an Eq. 13
  differential pair are skipped, implementing the Section 4.6
  false-stack suppression that avoids false inverters.
- **Current-output stage bias (Eq. 28/29).** The Eq.-19-maximal current
  biases whose drains sit on a transconductance source, one `stage_bias`
  tag per transconductance.
- **Amplification stages (Eq. 30-36 via Algorithm 2).**
  `netlist_decomposition.stages` composes each non-inverting
  transconductance with its load and current-output stage bias into an
  `amplification_stage` (Eq. 30; the connectivity conditions hold by
  construction) classified per Eq. 31-33 (`stage_class` of `as`, `ac`,
  `acmfb`, or generic `aninv` when the doping pattern matches none).
  The inverting-stage loop (Alg. 2 lines 8-26) then iterates over the
  analog inverters: a stack gate-driven by a recognized stage output
  whose partner stack is a current bias yields the `tcinv`
  transconductance (Eq. 23), its Eq. 28 stage bias, and an `ainvc`
  stage (Eq. 34/35), repeated to a fixed point so stage chains number
  themselves (`stage_index`).  The symmetrical-OTA branch (Eq. 36,
  Alg. 2 lines 17-23) runs while exactly one `ainvc` exists and a
  simple first stage has a single load part containing two voltage
  biases; its stage bias is one voltage bias on the tcinv drain --
  exactly the Eq. 27 voltage-output stage bias.  The tcinv tags and
  their stage biases are level-3 kinds emitted by the stage pass, which
  declares `completes=(3, 4)` -- matching the paper, which recognizes
  HL3-4 in one algorithm because of that bidirectional dependency.
- **Circuit bias (Eq. 37).** One `circuit_bias` tag collecting the
  voltage and current biases claimed by no amplification stage (nor, in
  line with the follower extension, by a `source_follower_stage`).  Its
  Eq. 26 voltage-output structure is not verified.
- **Compensation and load capacitors (Eq. 38/39).** A capacitor between
  the outputs of two different amplification stages is a
  `compensation_capacitor`; a capacitor between an output of the
  highest stage and a declared ground rail is a `load_capacitor`.
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
- **Hierarchy levels are tagging sets; the pipeline is composition
  passes.**  The paper's levels 1-4 are a kind taxonomy (Fig. 15), not a
  computation order: `KIND_LEVELS` assigns every kind its level
  (extensions by analogy), and each `BlockTag` carries it as `level`
  (`None` for unregistered custom kinds, which are never filtered).
  Recognition runs as `COMPOSITION_PASSES`, mirroring the paper's own
  Section 7 "Functional Block Analysis": pass 1 `classify` (7.1,
  Eq. 7/8, completes level 1); pass 2 `structure` (7.2) runs the
  monotone structural rules (stacks, candidates), then Algorithm 1
  (biases, mirrors), then the Eq. 13-17 pairs, the source follower, and
  the Eq. 18 inverters, and closes level 2 with the Eq. 19 deletion;
  pass 3 `stages` (7.3) runs Algorithm 2 and completes levels 3 AND 4
  together, because tcinv (Eq. 23) and its stage bias (Eq. 27/28) are
  mutually dependent with the amplification stages -- emitting level-3
  kinds there is the declared `completes=(3, 4)` contract.
  **Membership/annotation contract:** a level's set membership is final
  once its completing pass ends (Eq. 19 runs inside pass 2, before
  completion); later passes may only enrich existing tags with
  properties, never add or remove tags of completed levels.  No
  enrichment exists yet; it is the defined home for future
  bias-dependent variant naming (see unimplemented list).  The
  resolution steps need complete block sets and negative conditions, so
  they cannot be ordinary monotone rules; monotone rules carry a
  `level` attribute (default 2) naming the level of the kinds they
  emit, and run in the pass whose `completes` contains it.
  `decompose(..., max_level=1|2|3|4)` has completion-plus-view
  semantics: every pass completing a level `<= max_level` runs, then
  the returned tags are filtered to `level <= max_level` (or `None`).
  At `max_level=3` the level-4 work therefore executes and is
  view-filtered -- inherent to the paper's merged 7.3; the filter is a
  read view, not a deletion, unlike Eq. 19.  Each
  `CompositionPass.run(graph, blocks, rules)` can be applied
  individually to a caller-owned index, provided the earlier passes ran
  before.

## Exact versus candidate names

- Exact per the paper: `normal_transistor`, `diode_transistor`,
  `transistor_stack` (Eq. 7/8/9 as above); `voltage_bias`, `current_bias`,
  and `current_mirror` to the fidelity of the paper's own Algorithm 1
  (with the documented Eq. 10/11 approximations the paper itself makes);
  `differential_pair`, `gate_connected_couple`,
  `cascode_differential_pair` (Eq. 13-17); `analog_inverter` (Eq. 18);
  `transconductance` for the non-inverting types (Eq. 20-22) and, via
  the Algorithm 2 loop, the inverting type (Eq. 23); `load` per
  Algorithm 3; `stage_bias` for the current-output type (Eq. 28/29) and
  the single-voltage-bias Eq. 27 type produced with the `ainvv` stage;
  `amplification_stage` (Eq. 30-36), `circuit_bias` (Eq. 37, structure
  unverified), `compensation_capacitor`/`load_capacitor` (Eq. 38/39).
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
  Under the membership/annotation contract these are now expressible as
  later-pass property enrichment of the completed level-2 tags (still
  unimplemented).
- The exact load definitions Eq. 24/25 (Algorithm 3 is used instead, on
  the paper's own recommendation) and the multi-bias Eq. 26 bias-with-
  voltage-output structure (the emitted `circuit_bias` does not verify
  it; the Eq. 27 single-voltage-bias stage bias is implemented).
- Op-amp classification above HL4 (the paper's final composition level).
- Cascoded source followers (follower reaching the rail through a stack)
  and followers biased by unrecognized structures.
- Complementary/CMFB transconductances over cascoded pairs.
- Section 4.6 false-stack suppression beyond the differential-pair cases
  listed above (the Eq. 13 pair guard inside the inverter recognition,
  and the candidate-based `suppress_false_stacks` output filter).

## Optional policies

`transistor_stack_rule(exclusive_internal_nets=True)` restores the old
conservative behavior that every stack-internal net must carry exactly two
MOS drain/source terminals. This is not a paper rule (default off); it
over-approximates Section 4.6 by dropping every branching stack, including
paper-valid ones.

The stage pass keeps Algorithm 2's tcinv trigger verbatim: an analog
inverter enters the loop only when one stack is gate-driven by the output
of an already recognized stage.  Eq. 23's own condition is wider (gate on
any transconductance or load output); a literal-Eq. 23 switch would
additionally tag tcinv in circuits whose driving stage never completed
(e.g. a first stage without a recognized stage bias).  Not implemented;
recorded here as a possible future policy.

## Manual verification

Against the SKY130 OTA in the sibling workspace (uses the real extraction
pipeline with the workspace's device type map, no rendered-text parsing):

```bash
python scripts/verify_ota_decomposition.py
```
