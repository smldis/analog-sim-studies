"""HL2 differential pairs, cascode pairs, and source followers.

Implements the hierarchy-level-2 blocks of Abel et al. (2021) that need the
resolved biases (and therefore run after Algorithm 1, outside the monotone
rule engine):

- full differential pair (Eq. 13): two normal transistors of equal doping
  connected only at their sources, with a same-doping current-bias drain on
  the common source.  This runs against the pre-Eq.-19 current biases, as
  Algorithm 1 finds differential pairs before deleting irrelevant blocks;
- gate-connected couple (Eq. 14) and cascode differential pair (Eq. 15),
  with the folded/equal-doping subtypes of Eq. 16/17.  Couples are only
  tagged as constituents of a cascode pair; a standalone Eq. 14 match (for
  example the upper devices of a cascode current mirror) is not emitted;
- analog inverter (Eq. 18): two all-normal stacks of opposite doping
  joined at their drains, each source on the doping-matching declared
  rail, with no gate-gate, gate-drain, or source-source connection
  between any two member transistors.  Recognized last, as Algorithm 1
  line 19 prescribes;
- source follower (extension, not in the paper): a normal transistor
  outside every differential pair, drain on the doping-matching declared
  rail (NMOS: vdd, PMOS: vss), with a same-doping Eq.-19-maximal current
  bias sinking from its source to the opposite rail.  Rail knowledge at
  HL2 follows the paper's own analog inverter (Eq. 18), and composing
  other HL2 blocks follows its current mirror (Eq. 12).  The follower's
  stage bias and the composed ``source_follower_stage`` are level-3 kinds
  (see ``netlist_decomposition.stages``).

``pair_views``/``unit_views`` rebuild the recognition data from the emitted
tags so the stage composition pass can run separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from spice_canonical.canonical_netlist import Device

from netlist_decomposition import mos
from netlist_decomposition.bias import _stack_views, maximal
from netlist_decomposition.engine import (
    HL1_NORMAL,
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
)


_RULE = "HL2 pair/follower resolution"
_POLARITY = {"nmos": "n", "pmos": "p"}
_DOPING_TYPE = {"n": "nmos", "p": "pmos"}


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


def resolve_hl2_blocks(graph: CircuitGraph, blocks: BlockIndex) -> None:
    """Add differential-pair, cascode-pair, follower, and inverter tags."""

    normals = tuple(
        graph.devices[tag.devices_for("device")[0]]
        for tag in blocks.of_kind(HL1_NORMAL)
    )
    pairs = _differential_pairs(graph, blocks, normals)
    _cascode_pairs(graph, blocks, normals, pairs)
    maximal_cbs = maximal(blocks.of_kind("current_bias"))
    _source_followers(graph, blocks, normals, pairs, maximal_cbs)
    # Algorithm 1 line 19: inverters are the last HL2 recognition, after
    # the differential pairs whose false stacks they must not pick up.
    _analog_inverters(graph, blocks, pairs)


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


def _cascode_pairs(
    graph: CircuitGraph,
    blocks: BlockIndex,
    normals: tuple[Device, ...],
    pairs: tuple[_Pair, ...],
) -> None:
    """Emit gcc/vdp tags per Eq. 14-17."""

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
                            ("mos_type", _DOPING_TYPE[pair.doping]),
                            ("variant", variant),
                        ),
                    ),
                    rule=_RULE,
                )


def follower_biases(
    graph: CircuitGraph,
    maximal_cbs: tuple[BlockTag, ...],
    device: Device,
) -> tuple[BlockTag, ...]:
    """Maximal current biases sinking the follower output to the opposite rail."""

    rails = {"n": graph.vss_nets, "p": graph.vdd_nets}
    doping = mos.mos_polarity(device)
    output = mos.pin_net(device, "s")
    if doping is None or output is None:
        return ()
    return tuple(
        tag
        for tag in maximal_cbs
        if tag.net_for("drain") == output
        and dict(tag.properties)["mos_type"] == device.type
        and tag.net_for("source") in rails[doping]
        and device.name not in tag.members
    )


def _source_followers(
    graph: CircuitGraph,
    blocks: BlockIndex,
    normals: tuple[Device, ...],
    pairs: tuple[_Pair, ...],
    maximal_cbs: tuple[BlockTag, ...],
) -> None:
    """Source-follower recognition (extension, not a paper rule).

    The follower's drain sits on the rail its doping pulls towards
    (NMOS: vdd, PMOS: vss); the bias mirrors that on the opposite rail.
    Recognition requires the bias -- a rail-connected transistor alone is
    not a follower -- so nothing is found without declared rails.
    """

    drain_rails = {"n": graph.vdd_nets, "p": graph.vss_nets}
    paired = frozenset().union(*(pair.members for pair in pairs))
    for device in normals:
        doping = mos.mos_polarity(device)
        if doping is None or device.name in paired:
            continue
        if mos.pin_net(device, "d") not in drain_rails[doping]:
            continue
        if not follower_biases(graph, maximal_cbs, device):
            continue
        blocks.add(
            BlockCandidate(
                kind="source_follower",
                members=frozenset({device.name}),
                roles=(("devices", (device.name,)),),
                nets=(
                    ("input", mos.pin_net(device, "g") or ""),
                    ("output", mos.pin_net(device, "s") or ""),
                    ("rail", mos.pin_net(device, "d") or ""),
                ),
                properties=(
                    ("function", "voltage_buffer"),
                    ("mos_type", device.type),
                ),
            ),
            rule=_RULE,
        )


def _analog_inverters(
    graph: CircuitGraph, blocks: BlockIndex, pairs: tuple[_Pair, ...]
) -> None:
    """Eq. 18 analog inverters, recognized last per Algorithm 1 line 19.

    Two all-normal-transistor stacks of opposite doping share their drain
    net; each stack source sits on the doping-matching declared rail (so
    nothing is found without declared rails).  No gate-gate, gate-drain,
    or source-source connection may exist between any two member
    transistors -- which also excludes the gate-coupled digital CMOS
    inverter (that remains the legacy ``cmos_inverter`` tag).  Stacks
    sharing a device with an Eq. 13 differential pair are skipped: those
    are the Section 4.6 false stacks (tail plus input device) whose
    suppression the paper prescribes exactly to avoid false inverters.
    """

    paired = frozenset().union(*(pair.members for pair in pairs))
    rails = {"p": graph.vdd_nets, "n": graph.vss_nets}
    halves: dict[str, list] = {"p": [], "n": []}
    for stack in _stack_views(graph, blocks):
        if (
            all(item == "nt" for item in stack.member_classes.split(","))
            and stack.source in rails[stack.doping]
            and not (stack.members & paired)
        ):
            halves[stack.doping].append(stack)
    for upper in halves["p"]:
        for lower in halves["n"]:
            if upper.drain != lower.drain:
                continue
            devices = tuple(
                graph.devices[name] for name in (*upper.names, *lower.names)
            )
            if not mos.decoupled(devices, sources=True):
                continue
            blocks.add(
                BlockCandidate(
                    kind="analog_inverter",
                    members=upper.members | lower.members,
                    roles=(
                        ("stack_pmos", upper.names),
                        ("stack_nmos", lower.names),
                    ),
                    nets=(
                        ("output", upper.drain),
                        ("input_pmos", upper.gates[0]),
                        ("input_nmos", lower.gates[0]),
                    ),
                    properties=(
                        ("pmos_length", str(len(upper.names))),
                        ("nmos_length", str(len(lower.names))),
                    ),
                ),
                rule=_RULE,
            )


def pair_views(blocks: BlockIndex) -> tuple[_Pair, ...]:
    """Rebuild the Eq. 13 pairs from the differential_pair tags."""

    return tuple(
        _Pair(
            names=(
                tag.devices_for("input_1")[0],
                tag.devices_for("input_2")[0],
            ),
            gates=(tag.net_for("input_1") or "", tag.net_for("input_2") or ""),
            drains=(
                tag.net_for("output_1") or "",
                tag.net_for("output_2") or "",
            ),
            source=tag.net_for("common_source") or "",
            doping=_POLARITY[dict(tag.properties)["mos_type"]],
            members=tag.members,
        )
        for tag in blocks.of_kind("differential_pair")
    )


def unit_views(blocks: BlockIndex, pairs: tuple[_Pair, ...]) -> tuple[_Unit, ...]:
    """Rebuild the transconductance units: cascoded and simple pairs."""

    by_names = {pair.names: pair for pair in pairs}
    units = []
    cascoded: set[frozenset[str]] = set()
    for tag in blocks.of_kind("cascode_differential_pair"):
        pair = by_names[tag.devices_for("pair")]
        units.append(
            _Unit(
                pair=pair,
                couple=tag.devices_for("couple"),
                outs=(
                    tag.net_for("output_1") or "",
                    tag.net_for("output_2") or "",
                ),
                members=tag.members,
            )
        )
        cascoded.add(pair.members)
    units.extend(
        _Unit(pair=pair, couple=None, outs=pair.drains, members=pair.members)
        for pair in pairs
        if pair.members not in cascoded
    )
    return tuple(units)
