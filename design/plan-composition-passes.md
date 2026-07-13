# Plan: Tagging Sets + Composition Passes Refactor

Status: executed (2026-07-13).  Kept for the record; the current state is
described in design/functional-decomposition-abel2021.md.

## Constraints (standing, do not violate)

- NEVER run pytest or `scripts/verify_ota_decomposition.py`; the user runs
  them.  The only permitted check is `python -m py_compile` on every
  touched file.
- Do not render figures or PDF pages.  Paper text is already extracted at
  the session scratchpad if needed, but this plan is self-contained.
- Do not revert the `spice_canonical` refactor.

## Motivation

The current pipeline (`HIERARCHY_LEVELS`, one runnable stage per paper
hierarchy level 1-4) forces a 1:1 correspondence the paper does not have:
Abel et al. (2021) Section 7 recognizes blocks in THREE procedures (7.1
classification, 7.2 Algorithm 1, 7.3 Algorithm 2), and 7.3 deliberately
covers hierarchy levels 3 AND 4 because the inverting transconductance
(HL3, Eq. 23) and its stage bias (Eq. 27/28) are mutually dependent and
resolvable only through the amplification-stage loop.  Consequence today:
the stage named `hl4` emits HL3 kinds (`transconductance` tc_type=tcinv,
`stage_bias`), which reads as a level violation.

Agreed resolution: decouple taxonomy from computation.

- **Hierarchy levels become kind metadata** ("tagging sets"): every block
  kind belongs to a level per the paper's Fig. 15 (extensions get levels
  by analogy).  Queryable on each tag.
- **The pipeline becomes three composition passes** mirroring Section 7.
  Each pass declares which tagging sets (levels) it *completes*.  Pass 3
  completes levels 3 and 4 -- so emitting a level-3 kind there is the
  declared behavior, not an anomaly.
- **Membership/annotation contract**: a level's set membership is final
  once its completing pass ends (the Eq. 19 deletion runs inside pass 2,
  before completion -- unchanged).  Later passes may only *enrich*
  existing tags with properties, never add or remove tags of completed
  levels.  (No enrichment exists yet; the contract is documented now so
  future bias-dependent stack/mirror variant naming has a defined home.)

Decision taken (flagged during discussion, default chosen): pass 3 keeps
**Algorithm 2 verbatim** -- the tcinv trigger is "bottom gate driven by
the output of an already recognized stage".  The Eq. 23-literal widening
(trigger on any transconductance/load output, which additionally tags
tcinv in circuits whose driving stage never completed) is NOT implemented;
it is recorded as a documented option (see step 6).

## Target architecture

```python
# engine.py
KIND_LEVELS: dict[str, int] = {
    # level 1 (Eq. 7/8)
    "normal_transistor": 1, "diode_transistor": 1,
    # level 2 (Eq. 9-19 + extensions + legacy candidates)
    "transistor_stack": 2, "voltage_bias": 2, "current_bias": 2,
    "current_mirror": 2, "differential_pair": 2,
    "gate_connected_couple": 2, "cascode_differential_pair": 2,
    "analog_inverter": 2, "source_follower": 2,
    "differential_pair_candidate": 2, "cmos_inverter": 2,
    # level 3 (Eq. 20-29 + follower extension)
    "transconductance": 3, "load": 3, "stage_bias": 3,
    "source_follower_stage": 3,
    # level 4 (Eq. 30-39)
    "amplification_stage": 4, "circuit_bias": 4,
    "compensation_capacitor": 4, "load_capacitor": 4,
}

@dataclass(frozen=True)
class CompositionPass:
    number: int
    name: str
    completes: tuple[int, ...]   # tagging sets finalized by this pass
    run: PassRunner              # Callable[[CircuitGraph, BlockIndex, Sequence[Rule]], None]

COMPOSITION_PASSES = (
    CompositionPass(1, "classify", (1,), _run_classify),    # Section 7.1
    CompositionPass(2, "structure", (2,), _run_structure),  # Section 7.2, Alg. 1
    CompositionPass(3, "stages", (3, 4), _run_stages),      # Section 7.3, Alg. 2
)
```

- `BlockTag` gains `level: int | None = None` (last field, keyword
  construction only happens in `BlockIndex.add`).  `add` stamps it via
  `KIND_LEVELS.get(candidate.kind)`.  Unregistered custom kinds get
  `None`.  `_key()` unchanged (level is derived from kind).
- Monotone rules keep the `level` attribute with *improved* semantics:
  it is the hierarchy level of the kinds the rule emits (default 2).  A
  pass runs the rules whose level is in its `completes` tuple, to a fixed
  point, before its resolution passes:
  `_pass_rules(rules, completes) = tuple(r for r in rules if getattr(r, "level", 2) in completes)`.
- `decompose(circuit, rules, *, vdd_nets, vss_nets, max_level=4)` keeps
  its signature.  New semantics -- completion plus view:
  - run each pass unless `all(lvl > max_level for lvl in pass.completes)`
    (so max_level=1 runs pass 1; =2 runs 1-2; =3 and =4 run all three,
    because pass 3 is what completes level 3);
  - return `tuple(tag for tag in blocks.as_tuple() if tag.level is None or tag.level <= max_level)`.
  - Note for docs: at max_level=3 the level-4 work executes and is
    filtered from the returned view -- inherent to the paper's merged
    7.3.  This filter is a read view, not a destructive step; the index
    itself always holds the complete pass output (unlike Eq. 19, which
    is a real deletion inside pass 2).

## Steps

### 1. engine.py

- Add `KIND_LEVELS` (contents above) near the top, after the tag types.
- Add `level: int | None = None` to `BlockTag`; stamp in `BlockIndex.add`.
- Replace `HierarchyLevel`, `HIERARCHY_LEVELS`, `_run_hl1..4`,
  `_level_rules` with `CompositionPass`, `COMPOSITION_PASSES`,
  `_run_classify`, `_run_structure`, `_run_stages`, `_pass_rules`.
  Clean break: no aliases kept.
  - `_run_classify` = old `_run_hl1` body.
  - `_run_structure` = old `_run_hl2` body (engine fixed point on its
    rules, `bias.resolve_bias_blocks`, `hl2.resolve_hl2_blocks`,
    `bias.prune_irrelevant` closing the pass -- unchanged order).
  - `_run_stages` = engine fixed point on level-3/4 rules, then
    `stages.resolve_stage_blocks(graph, blocks)` (see step 2), lazy
    import as today.
- Rewrite `decompose` per the semantics above.
- Rewrite the pipeline block comment and `decompose`/`FunctionRule`
  docstrings: tagging sets vs passes, `completes` metadata, the
  membership/annotation contract, Section 7.1/7.2/7.3 mapping, the
  view-filter note.

### 2. Merge hl3.py + hl4.py into stages.py

One module for Section 7.3, killing the misleading hl3/hl4 module split.

- Create `src/netlist_decomposition/stages.py`:
  - module docstring: merge of the two current docstrings, reframed as
    "the stage composition pass (Alg. 2), completes tagging sets 3 and
    4"; keep the per-equation bullets, keep the note that tcinv and its
    stage bias are level-3 kinds emitted here because Alg. 2 resolves
    their mutual dependency, and that this is now the declared contract
    (`completes=(3, 4)`).
  - `resolve_stage_blocks(graph, blocks)` = old `resolve_hl3_blocks`
    body followed by old `resolve_hl4_blocks` body.
  - Move all functions from hl3.py (`_transconductances`, `_load`,
    `_stage_bias`, `_bias_doping`, `_follower_stages`, `_Transconductance`)
    and hl4.py (`_Stage`, `_prop`, `_stage_class`, `_noninverting_stages`,
    `_inverting_stages`, `_emit_inverting_stage`, `_symmetric_stage`,
    `_emit_symmetric_stage`, `_circuit_bias`, `_capacitors`,
    `_NONINVERTING`) unchanged except: single `_RULE`?  No -- keep TWO
    rule labels so tag provenance stays readable:
    `_RULE_HL3 = "HL3 resolution (Alg. 2)"` and
    `_RULE_HL4 = "HL4 resolution (Alg. 2)"`, used exactly where the old
    modules used theirs.
  - Imports consolidated: `hl2` (pair_views/unit_views/_DOPING_TYPE/
    _Pair/_Unit), `bias._stack_views`, `mos`, engine types.
- Delete hl3.py and hl4.py.
- hl2.py and bias.py are untouched by this step (their names still match
  the level of the kinds they emit; they are pass-2 helpers).

### 3. __init__.py

- Exports: remove `HIERARCHY_LEVELS`, `HierarchyLevel`; add
  `COMPOSITION_PASSES`, `CompositionPass`, `KIND_LEVELS`.  Keep the rest.

### 4. tests/test_netlist_decomposition.py

- No test imports `HIERARCHY_LEVELS`, so imports stay valid; add
  `KIND_LEVELS` to the package import only if used by new tests.
- `test_hierarchy_levels_stop_at_max_level` (SOURCE_FOLLOWER fixture):
  assertions still hold; rename to
  `test_max_level_completes_and_filters_tagging_sets` and keep body.
- `test_hl4_blocks_appear_only_at_level_four` (TWO_STAGE_MILLER): the
  meaning changes -- at max_level=3 pass 3 now RUNS and level-4 tags are
  filtered from the view.  Existing assertions still hold.  Rename to
  `test_max_level_three_returns_complete_level_three_view` and ADD the
  payoff assertion: at max_level=3 the tcinv transconductance IS present
  (`("tc_type", "tcinv")` among transconductance tags) -- previously
  impossible because hl4 never ran.
- New test `test_tags_carry_their_hierarchy_level`: on TWO_STAGE_MILLER,
  assert e.g. a `normal_transistor` tag has `level == 1`, `current_bias`
  2, `stage_bias` 3, `amplification_stage` 4.
- New test `test_unregistered_kind_gets_no_level_and_survives_filtering`:
  a custom `FunctionRule` emitting kind `"custom_probe"` (level attr
  default 2 so it runs in pass 2); assert its tag has `level is None`
  and appears in `decompose(..., max_level=1)` output?  NO -- max_level=1
  does not run pass 2.  Use `max_level=2`: assert the tag appears and
  `level is None`.  Keep the rule's matcher trivial (tag device M1).
- Do NOT run the tests.

### 5. scripts/verify_ota_decomposition.py

- No `HIERARCHY_LEVELS` usage; calls `decompose(...)` with defaults.  No
  change needed.  Re-read once to confirm after the refactor.

### 6. design/functional-decomposition-abel2021.md

- Rewrite the pipeline bullet: hierarchy levels are tagging sets (kind
  taxonomy per Fig. 15, stamped on every tag); the pipeline is
  `COMPOSITION_PASSES` mirroring Section 7 (7.1 classify, 7.2 structure/
  Alg. 1, 7.3 stages/Alg. 2 with `completes=(3, 4)`); the membership/
  annotation contract; `max_level` = run passes needed to complete the
  requested levels, return the filtered view (level-4 work runs and is
  view-filtered at max_level=3).
- State that pass 3 keeps Algorithm 2's stage-driven tcinv trigger, and
  record the Eq. 23-literal widening (trigger on any transconductance or
  load output; only differs on circuits whose driving stage never
  completed) under "Optional policies" as a possible future switch.
- In the unimplemented list, note that bias-dependent stack variant
  names (cp, mp1, mp2, vr1, vr2) and named mirror variants are now
  expressible as later-pass property enrichment under the annotation
  contract (still unimplemented).
- Grep the doc for stale phrases: "HIERARCHY_LEVELS", "HL4 runs",
  "levels can be run individually", "max_level=1|2|3|4" and align them.

### 7. Verification (only this)

```bash
python -m py_compile src/netlist_decomposition/{__init__,engine,mos,bias,hl2,stages}.py \
    tests/test_netlist_decomposition.py scripts/verify_ota_decomposition.py
grep -rn "hl3\|hl4\|HIERARCHY_LEVELS\|HierarchyLevel" src/ tests/ scripts/ design/functional-decomposition-abel2021.md
```

The grep must show no remaining references to the deleted modules/names
(design-doc prose describing the paper's HL3/HL4 *taxonomy* is fine and
expected; module references are not).  Report results; the user runs
pytest and the OTA script themselves.

## Out of scope (recorded follow-ups)

- Eq. 23-literal tcinv trigger widening (one condition in
  `_inverting_stages`: driver check against known tc/load outputs
  instead of stage outputs).
- An annotation API on `BlockIndex` (property enrichment of completed
  tags) -- add only together with its first real user (stack/mirror
  variant refinement).
- Everything already listed as unimplemented in the design doc (op-amp
  classification above HL4, cascoded followers, tcc/tccmfb over cascoded
  pairs, Eq. 24/25/26).
