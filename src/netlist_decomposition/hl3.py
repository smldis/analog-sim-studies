"""Full differential pairs and hierarchy-level-3 blocks.

Implements the parts of Abel et al. (2021) that Algorithm 2 can recognize
without amplification stages (HL4):

- full differential pair (Eq. 13): two normal transistors of equal doping
  connected only at their sources, with a same-doping current-bias drain on
  the common source.  This runs against the pre-Eq.-19 current biases, as
  Algorithm 1 finds differential pairs before deleting irrelevant blocks;
- gate-connected couple (Eq. 14) and cascode differential pair (Eq. 15),
  with the folded/equal-doping subtypes of Eq. 16/17.  Couples are only
  tagged as constituents of a cascode pair; a standalone Eq. 14 match (for
  example the upper devices of a cascode current mirror) is not emitted;
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
  sit on a transconductance source.  Only Eq.-19-maximal current biases are
  used, matching Algorithm 2 running after Algorithm 1's deletion step;
- source follower (extension, not in the paper): a common-drain stage is
  a voltage buffer, not a transconductance stage, so it gets its own HL3
  kind instead of a stretched ``transconductance`` subtype.  A normal
  transistor outside every differential pair, drain on the doping-matching
  declared rail, with a same-doping maximal current bias sinking from its
  source to the opposite rail, is tagged as a ``source_follower``
  (``function=voltage_buffer``) plus a voltage-output ``stage_bias``;
  their composition is emitted as a ``source_follower_stage`` (HL4-level,
  but fully determined by its two HL3 parts, so it is resolved here).

The inverting transconductance (Eq. 23) and the paper's voltage-output
stage bias (Eq. 27) are NOT implemented: Algorithm 2 resolves their
bidirectional dependency inside the amplification-stage loop, so they
arrive with HL4.
"""

from __future__ import annotations

from dataclasses import dataclass

from spice_canonical.canonical_netlist import Device

from netlist_decomposition import mos
from netlist_decomposition.bias import _stack_views
from netlist_decomposition.engine import (
    HL1_NORMAL,
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
)


_RULE = "HL3 resolution (Alg. 2)"
_POLARITY = {"nmos": "n", "pmos": "p"}


@dataclass(frozen=True)
class _Pair:
    """Eq. 13 differential pair, inputs in circuit order."""

    names: tuple[str, str]
    gates: tuple[str, str]
    drains: tuple[str, str]
    source: str
    doping: str
    members: frozenset[str]


@dataclass(frozen=True)
class _Unit:
    """One transconductance unit: a pair, optionally cascoded (Eq. 15)."""

    pair: _Pair
    couple: tuple[str, str] | None
    outs: tuple[str, str]
    members: frozenset[str]


def resolve_hl3_blocks(graph: CircuitGraph, blocks: BlockIndex) -> None:
    """Add differential-pair and HL3 tags to ``blocks``."""

    normals = tuple(
        graph.devices[tag.devices_for("device")[0]]
        for tag in blocks.of_kind(HL1_NORMAL)
    )
    pairs = _differential_pairs(graph, blocks, normals)
    units = _cascode_units(graph, blocks, normals, pairs)
    transconductances = _transconductances(blocks, pairs, units)
    stacks = _stack_views(graph, blocks)
    maximal_cbs = _maximal(blocks.of_kind("current_bias"))
    for tc in transconductances:
        _load(graph, blocks, stacks, tc)
        _stage_bias(blocks, maximal_cbs, tc)
    _source_followers(graph, blocks, normals, pairs, maximal_cbs)


def _differential_pairs(
    graph: CircuitGraph, blocks: BlockIndex, normals: tuple[Device, ...]
) -> tuple[_Pair, ...]:
    bias_drains: dict[str, set[str]] = {"n": set(), "p": set()}
    for tag in blocks.of_kind("current_bias"):
        doping = _POLARITY[dict(tag.properties)["mos_type"]]
        bias_drains[doping].add(tag.net_for("drain") or "")

    pairs = []
    for position, left in enumerate(normals):
        for right in normals[position + 1 :]:
            if not mos.same_polarity(left, right):
                continue
            source = mos.pin_net(left, "s")
            gates = (mos.pin_net(left, "g"), mos.pin_net(right, "g"))
            drains = (mos.pin_net(left, "d"), mos.pin_net(right, "d"))
            doping = mos.mos_polarity(left)
            if (
                source is None
                or mos.pin_net(right, "s") != source
                or gates[0] == gates[1]
                or drains[0] == drains[1]
                or source not in bias_drains[doping]
            ):
                continue
            pair = _Pair(
                names=(left.name, right.name),
                gates=gates,
                drains=drains,
                source=source,
                doping=doping,
                members=frozenset({left.name, right.name}),
            )
            pairs.append(pair)
            blocks.add(
                BlockCandidate(
                    kind="differential_pair",
                    members=pair.members,
                    roles=(
                        ("input_1", (left.name,)),
                        ("input_2", (right.name,)),
                    ),
                    nets=(
                        ("input_1", gates[0]),
                        ("input_2", gates[1]),
                        ("output_1", drains[0]),
                        ("output_2", drains[1]),
                        ("common_source", source),
                    ),
                    properties=(("mos_type", left.type),),
                ),
                rule=_RULE,
            )
    return tuple(pairs)


def _cascode_units(
    graph: CircuitGraph,
    blocks: BlockIndex,
    normals: tuple[Device, ...],
    pairs: tuple[_Pair, ...],
) -> tuple[_Unit, ...]:
    """Emit gcc/vdp tags (Eq. 14-17) and return all transconductance units."""

    units = []
    cascoded: set[frozenset[str]] = set()
    for pair in pairs:
        uppers = [
            tuple(
                device
                for device in normals
                if device.name not in pair.members
                and mos.pin_net(device, "s") == drain
            )
            for drain in pair.drains
        ]
        for first in uppers[0]:
            for second in uppers[1]:
                gate = mos.pin_net(first, "g")
                outs = (mos.pin_net(first, "d"), mos.pin_net(second, "d"))
                if (
                    first.name == second.name
                    or not mos.same_polarity(first, second)
                    or mos.pin_net(second, "g") != gate
                    or outs[0] == outs[1]
                ):
                    continue
                # Eq. 15: pair source and gates must not touch couple
                # gate or drains.
                if {pair.source, *pair.gates} & {gate, *outs}:
                    continue
                couple = (first.name, second.name)
                members = pair.members | {first.name, second.name}
                variant = "cdp" if mos.mos_polarity(first) == pair.doping else "fcdp"
                blocks.add(
                    BlockCandidate(
                        kind="gate_connected_couple",
                        members=frozenset(couple),
                        roles=(("devices", couple),),
                        nets=(
                            ("gate", gate),
                            ("drain_1", outs[0]),
                            ("drain_2", outs[1]),
                        ),
                        properties=(("mos_type", first.type),),
                    ),
                    rule=_RULE,
                )
                blocks.add(
                    BlockCandidate(
                        kind="cascode_differential_pair",
                        members=members,
                        roles=(("pair", pair.names), ("couple", couple)),
                        nets=(
                            ("input_1", pair.gates[0]),
                            ("input_2", pair.gates[1]),
                            ("output_1", outs[0]),
                            ("output_2", outs[1]),
                            ("common_source", pair.source),
                        ),
                        properties=(
                            ("mos_type", _doping_type(pair.doping)),
                            ("variant", variant),
                        ),
                    ),
                    rule=_RULE,
                )
                cascoded.add(pair.members)
                units.append(
                    _Unit(pair=pair, couple=couple, outs=outs, members=members)
                )
    units.extend(
        _Unit(pair=pair, couple=None, outs=pair.drains, members=pair.members)
        for pair in pairs
        if pair.members not in cascoded
    )
    return tuple(units)


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
        types = {_doping_type(unit.pair.doping) for unit in tc_units}
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
            rule=_RULE,
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
        rule=_RULE,
    )


def _stage_bias(
    blocks: BlockIndex,
    maximal_cbs: tuple[BlockTag, ...],
    tc: _Transconductance,
) -> None:
    """Eq. 28/29: current biases driving the transconductance sources."""

    sources = {unit.pair.source for unit in tc.units}
    feeding = tuple(
        tag for tag in maximal_cbs if tag.net_for("drain") in sources
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
            ),
        ),
        rule=_RULE,
    )


def _source_followers(
    graph: CircuitGraph,
    blocks: BlockIndex,
    normals: tuple[Device, ...],
    pairs: tuple[_Pair, ...],
    maximal_cbs: tuple[BlockTag, ...],
) -> None:
    """Source-follower voltage buffer, stage bias, and stage (extension).

    The follower's drain sits on the rail its doping pulls towards
    (NMOS: vdd, PMOS: vss); the bias mirrors that on the opposite rail.
    Recognition requires the bias -- a rail-connected transistor alone is
    not a follower -- so nothing is found without declared rails.
    """

    drain_rails = {"n": graph.vdd_nets, "p": graph.vss_nets}
    bias_rails = {"n": graph.vss_nets, "p": graph.vdd_nets}
    paired = frozenset().union(*(pair.members for pair in pairs))
    for device in normals:
        doping = mos.mos_polarity(device)
        if doping is None or device.name in paired:
            continue
        drain = mos.pin_net(device, "d")
        source = mos.pin_net(device, "s")
        if drain not in drain_rails[doping]:
            continue
        feeding = tuple(
            tag
            for tag in maximal_cbs
            if tag.net_for("drain") == source
            and dict(tag.properties)["mos_type"] == device.type
            and tag.net_for("source") in bias_rails[doping]
            and device.name not in tag.members
        )
        if not feeding:
            continue
        gate = mos.pin_net(device, "g")
        bias_members = frozenset().union(*(tag.members for tag in feeding))
        bias_devices = tuple(
            name
            for tag in feeding
            for name in tag.devices_for("ordered_devices")
        )
        blocks.add(
            BlockCandidate(
                kind="source_follower",
                members=frozenset({device.name}),
                roles=(("devices", (device.name,)),),
                nets=(("input", gate), ("output", source), ("rail", drain)),
                properties=(
                    ("function", "voltage_buffer"),
                    ("mos_type", device.type),
                ),
            ),
            rule=_RULE,
        )
        blocks.add(
            BlockCandidate(
                kind="stage_bias",
                members=bias_members,
                roles=(
                    ("current_biases", bias_devices),
                    ("source_follower", (device.name,)),
                ),
                nets=(("output_1", source),),
                properties=(
                    ("output_type", "voltage"),
                    ("current_bias_count", str(len(feeding))),
                ),
            ),
            rule=_RULE,
        )
        blocks.add(
            BlockCandidate(
                kind="source_follower_stage",
                members=frozenset({device.name}) | bias_members,
                roles=(
                    ("follower", (device.name,)),
                    ("current_biases", bias_devices),
                ),
                nets=(("input", gate), ("output", source), ("rail", drain)),
                properties=(("mos_type", device.type),),
            ),
            rule=_RULE,
        )


def _maximal(tags: tuple[BlockTag, ...]) -> tuple[BlockTag, ...]:
    """Eq. 19 view: drop tags strictly contained in a same-kind tag."""

    return tuple(
        tag
        for tag in tags
        if not any(tag.members < other.members for other in tags)
    )


def _doping_type(doping: str) -> str:
    return {"n": "nmos", "p": "pmos"}[doping]
