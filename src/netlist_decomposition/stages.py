"""The stage composition pass (Algorithm 2): completes tagging sets 3 and 4.

Implements Abel et al. (2021) Section 7.3 on top of the pass-2 tags
produced by ``netlist_decomposition.bias`` (Algorithm 1) and
``netlist_decomposition.hl2``.  The level-3 kinds (transconductance,
load, stage bias, follower stage) and the level-4 kinds (amplification
stage, circuit bias, capacitors) are recognized in this one pass because
the inverting transconductance (Eq. 23) and its stage bias (Eq. 27/28)
are mutually dependent with the amplification stages and resolvable only
inside the stage loop -- the pass declares ``completes=(3, 4)``, so
emitting level-3 kinds here is the contract, not a level violation.

Level-3 recognition:

- non-inverting transconductance (Eq. 20-22): simple (``tcs``),
  complementary (``tcc``), and common-mode feedback (``tccmfb``).  A
  cascode differential pair forms a simple transconductance as one unit;
  complementary and CMFB types are built from simple pairs only;
- load via Algorithm 3, which the paper recommends over Eq. 24/25 because
  it does not require the load stacks to be recognized biases: for every
  transconductance output net, same-doping stacks whose drain sits on the
  net and whose source reaches the doping-matching declared rail (or
  another transconductance output, for folded arrangements) form the NMOS/
  PMOS load parts.  Stacks sharing a device with the transconductance are
  excluded -- without this guard the Section 4.6 false stacks (tail plus
  input device) would be picked up as loads;
- current-output stage bias (Eq. 28/29): the current biases whose drains
  sit on a transconductance source.  The index only holds Eq.-19-maximal
  current biases here, since pass 2 closes with Algorithm 1's deletion
  step;
- source-follower stage (extension, not in the paper): each pass-2
  ``source_follower`` yields a voltage-output ``stage_bias`` (the
  Eq. 26/27 flavor, though not their formulation) and the composed
  ``source_follower_stage``.

Level-4 recognition:

- non-inverting amplification stage (Eq. 30): a non-inverting
  transconductance together with its Algorithm 3 load and its
  current-output stage bias.  The connectivity conditions of Eq. 30 hold
  by construction, since load and stage bias are recognized per
  transconductance.  Stages are classified per Eq. 31-33 into the simple
  first stage ``as``, the complementary first stage ``ac``, and the CMFB
  stage ``acmfb`` by the doping of their parts; unmatched doping
  combinations keep the generic class ``aninv``;
- inverting amplification stage (Alg. 2 lines 8-26): iterating over the
  pass-2 analog inverters resolves the bidirectional dependency between
  the inverting transconductance (Eq. 23) and its stage bias.  An
  inverter with one stack gate-driven by the output of an already
  recognized stage and the other stack a current bias yields the
  ``tcinv`` transconductance, its current-output stage bias (Eq. 28),
  and an ``ainvc`` stage (Eq. 34/35).  The loop repeats until no stage
  is added, so multi-stage chains number themselves;
- symmetrical-OTA inverting stage (Eq. 36, Alg. 2 lines 17-23): searched
  only while exactly one ``ainvc`` stage exists and a simple first stage
  has a single load part containing two voltage biases.  Its stage bias
  is one voltage bias whose drain sits on the transconductance output --
  exactly the Eq. 27 voltage-output stage bias;
- circuit bias (Eq. 37): the voltage and current biases claimed by no
  amplification stage (nor, matching the follower extension, by a
  ``source_follower_stage``).  Its Eq. 26 voltage-output structure is
  not verified;
- compensation capacitor (Eq. 38): a capacitor between the outputs of
  two different amplification stages; load capacitor (Eq. 39): a
  capacitor between an output of the highest stage and a declared
  ground rail.

The amplification-stage tags carry ``stage_index`` (1 for non-inverting
first stages, n for the nth stage of a chain) and ``stage_class``
(``as``/``ac``/``acmfb``/``aninv``/``ainvc``/``ainvv``).
"""

from __future__ import annotations

from dataclasses import dataclass

from netlist_decomposition import hl2, mos
from netlist_decomposition.bias import _stack_views
from netlist_decomposition.engine import (
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
)
from netlist_decomposition.hl2 import _DOPING_TYPE, _Pair, _Unit


_RULE_HL3 = "HL3 resolution (Alg. 2)"
_RULE_HL4 = "HL4 resolution (Alg. 2)"

_NONINVERTING = frozenset({"tcs", "tcc", "tccmfb"})


def resolve_stage_blocks(graph: CircuitGraph, blocks: BlockIndex) -> None:
    """Run Algorithm 2: complete the level-3 and level-4 tagging sets."""

    pairs = hl2.pair_views(blocks)
    units = hl2.unit_views(blocks, pairs)
    transconductances = _transconductances(blocks, pairs, units)
    stacks = _stack_views(graph, blocks)
    # Pass 2 closed with the Eq. 19 deletion, so these are already maximal.
    current_biases = blocks.of_kind("current_bias")
    for tc in transconductances:
        _load(graph, blocks, stacks, tc)
        _stage_bias(blocks, current_biases, tc)
    _follower_stages(graph, blocks, current_biases)

    stages: list[_Stage] = []
    _noninverting_stages(blocks, stages)
    _inverting_stages(graph, blocks, stages)
    _circuit_bias(blocks, stages)
    _capacitors(graph, blocks, stages)


@dataclass(frozen=True)
class _Transconductance:
    tc_type: str
    units: tuple[_Unit, ...]
    members: frozenset[str]


def _transconductances(
    blocks: BlockIndex, pairs: tuple[_Pair, ...], units: tuple[_Unit, ...]
) -> tuple[_Transconductance, ...]:
    found = []

    def emit(tc_type: str, *tc_units: _Unit) -> None:
        members = frozenset().union(*(unit.members for unit in tc_units))
        nets = []
        for index, unit in enumerate(tc_units):
            offset = 2 * index
            nets += [
                (f"in_{offset + 1}", unit.pair.gates[0]),
                (f"in_{offset + 2}", unit.pair.gates[1]),
                (f"out_{offset + 1}", unit.outs[0]),
                (f"out_{offset + 2}", unit.outs[1]),
                (f"source_{index + 1}", unit.pair.source),
            ]
        roles = [("inputs", tuple(n for u in tc_units for n in u.pair.names))]
        couples = tuple(
            name for u in tc_units if u.couple for name in u.couple
        )
        if couples:
            roles.append(("cascode_devices", couples))
        types = {_DOPING_TYPE[unit.pair.doping] for unit in tc_units}
        blocks.add(
            BlockCandidate(
                kind="transconductance",
                members=members,
                roles=tuple(roles),
                nets=tuple(nets),
                properties=(
                    ("tc_type", tc_type),
                    ("mos_type", types.pop() if len(types) == 1 else "mixed"),
                ),
            ),
            rule=_RULE_HL3,
        )
        found.append(
            _Transconductance(tc_type=tc_type, units=tc_units, members=members)
        )

    # Eq. 20: a single pair with no gate connection to any other pair.
    for unit in units:
        other_gates = {
            gate
            for pair in pairs
            if pair.members != unit.pair.members
            for gate in pair.gates
        }
        if not (set(unit.pair.gates) & other_gates):
            emit("tcs", unit)

    # Eq. 21/22 over simple (uncascoded) pairs.
    simple = tuple(unit for unit in units if unit.couple is None)
    for position, first in enumerate(simple):
        for second in simple[position + 1 :]:
            if first.members & second.members:
                continue
            one, two = first.pair, second.pair
            matched_both = set(one.gates) == set(two.gates)
            shared = {gate for gate in one.gates if gate in two.gates}
            if one.doping != two.doping and matched_both:
                emit("tcc", first, second)
            elif one.doping == two.doping and len(shared) == 1 and not matched_both:
                emit("tccmfb", first, second)

    return tuple(found)


def _load(
    graph: CircuitGraph,
    blocks: BlockIndex,
    stacks,
    tc: _Transconductance,
) -> None:
    """Algorithm 3 for one non-inverting transconductance."""

    out_nets = tuple(dict.fromkeys(out for unit in tc.units for out in unit.outs))
    rails = {"n": graph.vss_nets, "p": graph.vdd_nets}
    parts: dict[str, set[str]] = {"n": set(), "p": set()}
    for stack in stacks:
        if stack.drain not in out_nets or stack.members & tc.members:
            continue
        if stack.source in rails[stack.doping] or stack.source in out_nets:
            parts[stack.doping].update(stack.members)
    if not (parts["n"] or parts["p"]):
        return
    blocks.add(
        BlockCandidate(
            kind="load",
            members=frozenset(parts["n"] | parts["p"]),
            roles=(
                ("part_nmos", tuple(sorted(parts["n"]))),
                ("part_pmos", tuple(sorted(parts["p"]))),
                ("transconductance", tuple(sorted(tc.members))),
            ),
            nets=tuple(
                (f"out_{index + 1}", net) for index, net in enumerate(out_nets)
            ),
            properties=(("recognition", "algorithm_3"),),
        ),
        rule=_RULE_HL3,
    )


def _stage_bias(
    blocks: BlockIndex,
    current_biases: tuple[BlockTag, ...],
    tc: _Transconductance,
) -> None:
    """Eq. 28/29: current biases driving the transconductance sources."""

    sources = {unit.pair.source for unit in tc.units}
    feeding = tuple(
        tag for tag in current_biases if tag.net_for("drain") in sources
    )
    if not feeding:
        return
    members = frozenset().union(*(tag.members for tag in feeding))
    blocks.add(
        BlockCandidate(
            kind="stage_bias",
            members=members,
            roles=(
                (
                    "current_biases",
                    tuple(
                        name
                        for tag in feeding
                        for name in tag.devices_for("ordered_devices")
                    ),
                ),
                ("transconductance", tuple(sorted(tc.members))),
            ),
            nets=tuple(
                (f"output_{index + 1}", net)
                for index, net in enumerate(sorted(sources))
            ),
            properties=(
                ("output_type", "current"),
                ("current_bias_count", str(len(feeding))),
                ("mos_type", _bias_doping(feeding)),
            ),
        ),
        rule=_RULE_HL3,
    )


def _bias_doping(feeding: tuple[BlockTag, ...]) -> str:
    types = {dict(tag.properties)["mos_type"] for tag in feeding}
    return types.pop() if len(types) == 1 else "mixed"


def _follower_stages(
    graph: CircuitGraph,
    blocks: BlockIndex,
    current_biases: tuple[BlockTag, ...],
) -> None:
    """Voltage-output stage bias and stage for each pass-2 source follower."""

    for follower in blocks.of_kind("source_follower"):
        device = graph.devices[follower.devices_for("devices")[0]]
        feeding = hl2.follower_biases(graph, current_biases, device)
        if not feeding:
            continue
        output = follower.net_for("output") or ""
        bias_members = frozenset().union(*(tag.members for tag in feeding))
        bias_devices = tuple(
            name
            for tag in feeding
            for name in tag.devices_for("ordered_devices")
        )
        blocks.add(
            BlockCandidate(
                kind="stage_bias",
                members=bias_members,
                roles=(
                    ("current_biases", bias_devices),
                    ("source_follower", (device.name,)),
                ),
                nets=(("output_1", output),),
                properties=(
                    ("output_type", "voltage"),
                    ("current_bias_count", str(len(feeding))),
                    ("mos_type", _bias_doping(feeding)),
                ),
            ),
            rule=_RULE_HL3,
        )
        blocks.add(
            BlockCandidate(
                kind="source_follower_stage",
                members=frozenset({device.name}) | bias_members,
                roles=(
                    ("follower", (device.name,)),
                    ("current_biases", bias_devices),
                ),
                nets=(
                    ("input", follower.net_for("input") or ""),
                    ("output", output),
                    ("rail", follower.net_for("rail") or ""),
                ),
                properties=(("mos_type", device.type),),
            ),
            rule=_RULE_HL3,
        )


@dataclass(frozen=True)
class _Stage:
    """One recognized amplification stage, for the Alg. 2 loop."""

    index: int
    stage_class: str
    members: frozenset[str]
    outs: tuple[str, ...]
    load_parts: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())
    bias_gates: tuple[str, ...] = ()


def _prop(tag: BlockTag, name: str) -> str:
    return dict(tag.properties).get(name, "")


def _stage_class(
    tc_type: str, tc_doping: str, bias_doping: str, load_doping: str
) -> str:
    """Eq. 31-33 classification of a non-inverting stage."""

    single = tc_doping in ("nmos", "pmos")
    if (
        tc_type == "tcs"
        and single
        and bias_doping == tc_doping
        and load_doping != tc_doping
    ):
        return "as"
    if tc_type == "tcc" and tc_doping == bias_doping == load_doping == "mixed":
        return "ac"
    if (
        tc_type == "tccmfb"
        and single
        and bias_doping == tc_doping
        and load_doping in ("nmos", "pmos")
        and load_doping != tc_doping
    ):
        return "acmfb"
    return "aninv"


def _noninverting_stages(blocks: BlockIndex, stages: list[_Stage]) -> None:
    """Eq. 30-33: transconductance plus load plus current-output stage bias."""

    loads = {
        tag.devices_for("transconductance"): tag for tag in blocks.of_kind("load")
    }
    biases = {
        tag.devices_for("transconductance"): tag
        for tag in blocks.of_kind("stage_bias")
        if _prop(tag, "output_type") == "current"
    }
    for tc in blocks.of_kind("transconductance"):
        if _prop(tc, "tc_type") not in _NONINVERTING:
            continue
        key = tuple(sorted(tc.members))
        load, bias_tag = loads.get(key), biases.get(key)
        if load is None or bias_tag is None:
            continue
        parts = (load.devices_for("part_nmos"), load.devices_for("part_pmos"))
        load_doping = (
            "mixed" if parts[0] and parts[1] else ("nmos" if parts[0] else "pmos")
        )
        stage_class = _stage_class(
            _prop(tc, "tc_type"),
            _prop(tc, "mos_type"),
            _prop(bias_tag, "mos_type"),
            load_doping,
        )
        ins = tuple(net for name, net in tc.nets if name.startswith("in_"))
        outs = tuple(net for name, net in load.nets if name.startswith("out_"))
        members = tc.members | load.members | bias_tag.members
        blocks.add(
            BlockCandidate(
                kind="amplification_stage",
                members=members,
                roles=(
                    ("transconductance", key),
                    ("load", tuple(sorted(load.members))),
                    ("stage_bias", tuple(sorted(bias_tag.members))),
                ),
                nets=(
                    *((f"in_{i + 1}", net) for i, net in enumerate(ins)),
                    *((f"out_{i + 1}", net) for i, net in enumerate(outs)),
                ),
                properties=(
                    ("inverting", "false"),
                    ("stage_class", stage_class),
                    ("stage_index", "1"),
                ),
            ),
            rule=_RULE_HL4,
        )
        stages.append(
            _Stage(
                index=1,
                stage_class=stage_class,
                members=members,
                outs=outs,
                load_parts=parts,
            )
        )


def _inverting_stages(
    graph: CircuitGraph, blocks: BlockIndex, stages: list[_Stage]
) -> None:
    """Alg. 2 lines 8-26: the inverting-stage loop over the analog inverters."""

    current_biases = {
        tag.devices_for("ordered_devices"): tag
        for tag in blocks.of_kind("current_bias")
    }
    consumed: set[frozenset[str]] = set()
    changed = True
    while changed:
        changed = False
        for inverter in blocks.of_kind("analog_inverter"):
            if inverter.members in consumed:
                continue
            for tc_role, bias_role in (
                ("stack_pmos", "stack_nmos"),
                ("stack_nmos", "stack_pmos"),
            ):
                tc_names = inverter.devices_for(tc_role)
                gate = graph.pin_net(graph.devices[tc_names[0]], "g") or ""
                driver = next(
                    (stage for stage in stages if gate in stage.outs), None
                )
                bias = current_biases.get(inverter.devices_for(bias_role))
                if driver is None or bias is None:
                    continue
                _emit_inverting_stage(
                    graph,
                    blocks,
                    stages,
                    tc_names=tc_names,
                    gate=gate,
                    output=inverter.net_for("output") or "",
                    bias=bias,
                    index=driver.index + 1,
                )
                consumed.add(inverter.members)
                changed = True
                break
        changed |= _symmetric_stage(graph, blocks, stages)


def _emit_inverting_stage(
    graph: CircuitGraph,
    blocks: BlockIndex,
    stages: list[_Stage],
    *,
    tc_names: tuple[str, ...],
    gate: str,
    output: str,
    bias: BlockTag,
    index: int,
) -> None:
    """Emit tcinv (Eq. 23), its Eq. 28 stage bias, and the ainvc stage."""

    bottom = graph.devices[tc_names[0]]
    tc_key = tuple(sorted(tc_names))
    blocks.add(
        BlockCandidate(
            kind="transconductance",
            members=frozenset(tc_names),
            roles=(("ordered_devices", tc_names),),
            nets=(
                ("in_1", gate),
                ("out_1", output),
                ("source_1", graph.pin_net(bottom, "s") or ""),
            ),
            properties=(("tc_type", "tcinv"), ("mos_type", bottom.type)),
        ),
        rule=_RULE_HL4,
    )
    blocks.add(
        BlockCandidate(
            kind="stage_bias",
            members=bias.members,
            roles=(
                ("current_biases", bias.devices_for("ordered_devices")),
                ("transconductance", tc_key),
            ),
            nets=(("output_1", output),),
            properties=(
                ("output_type", "current"),
                ("current_bias_count", "1"),
                ("mos_type", _prop(bias, "mos_type")),
            ),
        ),
        rule=_RULE_HL4,
    )
    members = frozenset(tc_names) | bias.members
    blocks.add(
        BlockCandidate(
            kind="amplification_stage",
            members=members,
            roles=(
                ("transconductance", tc_key),
                ("stage_bias", tuple(sorted(bias.members))),
            ),
            nets=(("in_1", gate), ("out_1", output)),
            properties=(
                ("inverting", "true"),
                ("stage_class", "ainvc"),
                ("stage_index", str(index)),
            ),
        ),
        rule=_RULE_HL4,
    )
    stages.append(
        _Stage(
            index=index,
            stage_class="ainvc",
            members=members,
            outs=(output,),
            bias_gates=tuple(
                graph.pin_net(graph.devices[name], "g") or ""
                for name in bias.devices_for("ordered_devices")
            ),
        )
    )


def _symmetric_stage(
    graph: CircuitGraph, blocks: BlockIndex, stages: list[_Stage]
) -> bool:
    """Alg. 2 lines 17-23 (Eq. 36): the symmetrical-OTA second stage.

    Searched only while exactly one ainvc stage exists.  A simple first
    stage must have a single load part containing two voltage biases; a
    fresh all-normal stack gate-driven by one of those biases, with a
    voltage bias of opposite doping on its drain whose gates align with
    the known inverting stage's bias, forms the ainvv stage.  That
    voltage bias is the Eq. 27 stage bias: exactly one voltage bias,
    drain on the inverting transconductance output.
    """

    inverting = [stage for stage in stages if stage.stage_class == "ainvc"]
    if len(inverting) != 1 or any(
        stage.stage_class == "ainvv" for stage in stages
    ):
        return False
    known = inverting[0]
    voltage_biases = blocks.of_kind("voltage_bias")
    claimed = frozenset().union(*(stage.members for stage in stages))
    rails = {"n": graph.vss_nets, "p": graph.vdd_nets}
    for first in stages:
        if first.stage_class != "as":
            continue
        parts = [part for part in first.load_parts if part]
        if len(parts) != 1:
            continue
        part = frozenset(parts[0])
        load_vbs = [tag for tag in voltage_biases if tag.members <= part]
        if len(load_vbs) < 2:
            continue
        mirror_gates = {
            graph.pin_net(
                graph.devices[tag.devices_for("ordered_devices")[0]], "g"
            )
            for tag in load_vbs
        }
        for stack in _stack_views(graph, blocks):
            if (
                any(item != "nt" for item in stack.member_classes.split(","))
                or stack.source not in rails[stack.doping]
                or stack.gates[0] not in mirror_gates
                or stack.members & claimed
                or not mos.decoupled(
                    tuple(graph.devices[name] for name in stack.names)
                )
            ):
                continue
            for vb in voltage_biases:
                vb_names = vb.devices_for("ordered_devices")
                vb_gates = tuple(
                    graph.pin_net(graph.devices[name], "g") or ""
                    for name in vb_names
                )
                if (
                    vb.net_for("drain") != stack.drain
                    or _prop(vb, "mos_type") == _DOPING_TYPE[stack.doping]
                    or len(vb_gates) > len(known.bias_gates)
                    or any(
                        vb_gates[q] != known.bias_gates[q]
                        for q in range(len(vb_gates))
                    )
                ):
                    continue
                _emit_symmetric_stage(
                    blocks,
                    stages,
                    stack=stack,
                    vb=vb,
                    vb_names=vb_names,
                    vb_gates=vb_gates,
                    index=first.index + 1,
                )
                return True
    return False


def _emit_symmetric_stage(
    blocks: BlockIndex,
    stages: list[_Stage],
    *,
    stack,
    vb: BlockTag,
    vb_names: tuple[str, ...],
    vb_gates: tuple[str, ...],
    index: int,
) -> None:
    gate = stack.gates[0] or ""
    output = stack.drain
    tc_key = tuple(sorted(stack.members))
    blocks.add(
        BlockCandidate(
            kind="transconductance",
            members=stack.members,
            roles=(("ordered_devices", stack.names),),
            nets=(("in_1", gate), ("out_1", output), ("source_1", stack.source)),
            properties=(
                ("tc_type", "tcinv"),
                ("mos_type", _DOPING_TYPE[stack.doping]),
            ),
        ),
        rule=_RULE_HL4,
    )
    blocks.add(
        BlockCandidate(
            kind="stage_bias",
            members=vb.members,
            roles=(
                ("voltage_biases", vb_names),
                ("transconductance", tc_key),
            ),
            nets=(("output_1", vb_gates[0]),),
            properties=(
                ("output_type", "voltage"),
                ("voltage_bias_count", "1"),
                ("mos_type", _prop(vb, "mos_type")),
            ),
        ),
        rule=_RULE_HL4,
    )
    members = stack.members | vb.members
    blocks.add(
        BlockCandidate(
            kind="amplification_stage",
            members=members,
            roles=(
                ("transconductance", tc_key),
                ("stage_bias", tuple(sorted(vb.members))),
            ),
            nets=(("in_1", gate), ("out_1", output)),
            properties=(
                ("inverting", "true"),
                ("stage_class", "ainvv"),
                ("stage_index", str(index)),
            ),
        ),
        rule=_RULE_HL4,
    )
    stages.append(
        _Stage(
            index=index,
            stage_class="ainvv",
            members=members,
            outs=(output,),
        )
    )


def _circuit_bias(blocks: BlockIndex, stages: list[_Stage]) -> None:
    """Eq. 37: the biases claimed by no stage form the circuit bias."""

    claimed = frozenset().union(
        *(stage.members for stage in stages),
        *(tag.members for tag in blocks.of_kind("source_follower_stage")),
    )
    remaining = [
        tag
        for kind in ("voltage_bias", "current_bias")
        for tag in blocks.of_kind(kind)
        if not (tag.members & claimed)
    ]
    if not remaining:
        return

    def devices_of(kind: str) -> tuple[str, ...]:
        return tuple(
            name
            for tag in remaining
            if tag.kind == kind
            for name in tag.devices_for("ordered_devices")
        )

    blocks.add(
        BlockCandidate(
            kind="circuit_bias",
            members=frozenset().union(*(tag.members for tag in remaining)),
            roles=(
                ("voltage_biases", devices_of("voltage_bias")),
                ("current_biases", devices_of("current_bias")),
            ),
            properties=(("output_type", "voltage"),),
        ),
        rule=_RULE_HL4,
    )


def _capacitors(
    graph: CircuitGraph, blocks: BlockIndex, stages: list[_Stage]
) -> None:
    """Eq. 38/39: compensation and load capacitors."""

    if not stages:
        return
    highest = max(stage.index for stage in stages)
    highest_outs = frozenset(
        net for stage in stages if stage.index == highest for net in stage.outs
    )
    for device in graph.circuit.devices:
        if device.type != "capacitor":
            continue
        nets = (
            graph.pin_net(device, "p") or "",
            graph.pin_net(device, "n") or "",
        )
        owners = [
            frozenset(
                position
                for position, stage in enumerate(stages)
                if net in stage.outs
            )
            for net in nets
        ]
        if any(first != second for first in owners[0] for second in owners[1]):
            blocks.add(
                BlockCandidate(
                    kind="compensation_capacitor",
                    members=frozenset({device.name}),
                    roles=(("device", (device.name,)),),
                    nets=(("terminal_1", nets[0]), ("terminal_2", nets[1])),
                ),
                rule=_RULE_HL4,
            )
        for out_net, ground in (nets, nets[::-1]):
            if out_net in highest_outs and ground in graph.vss_nets:
                blocks.add(
                    BlockCandidate(
                        kind="load_capacitor",
                        members=frozenset({device.name}),
                        roles=(("device", (device.name,)),),
                        nets=(("output", out_net), ("ground", ground)),
                        properties=(("stage_index", str(highest)),),
                    ),
                    rule=_RULE_HL4,
                )
                break
