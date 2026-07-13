"""Hierarchy-level-3 blocks: transconductance, load, stage bias, stages.

Implements the parts of Abel et al. (2021) Algorithm 2 that do not need the
HL4 amplification-stage loop, reading the HL2 tags produced by
``netlist_decomposition.bias`` (Algorithm 1) and ``netlist_decomposition.hl2``:

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
  current biases here, since HL2 closes with Algorithm 1's deletion step;
- source-follower stage (extension, not in the paper): each HL2
  ``source_follower`` yields a voltage-output ``stage_bias`` (the
  Eq. 26/27 flavor, though not their formulation) and the composed
  ``source_follower_stage``.

The inverting transconductance (Eq. 23) and the paper's voltage-output
stage bias (Eq. 27) are NOT implemented: Algorithm 2 resolves their
bidirectional dependency inside the amplification-stage loop, so they
arrive with HL4.
"""

from __future__ import annotations

from dataclasses import dataclass

from netlist_decomposition import hl2
from netlist_decomposition.bias import _stack_views
from netlist_decomposition.engine import (
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
)
from netlist_decomposition.hl2 import _DOPING_TYPE, _Pair, _Unit


_RULE = "HL3 resolution (Alg. 2)"


def resolve_hl3_blocks(graph: CircuitGraph, blocks: BlockIndex) -> None:
    """Add transconductance, load, stage-bias, and stage tags to ``blocks``."""

    pairs = hl2.pair_views(blocks)
    units = hl2.unit_views(blocks, pairs)
    transconductances = _transconductances(blocks, pairs, units)
    stacks = _stack_views(graph, blocks)
    # HL2 closed with the Eq. 19 deletion, so these are already maximal.
    current_biases = blocks.of_kind("current_bias")
    for tc in transconductances:
        _load(graph, blocks, stacks, tc)
        _stage_bias(blocks, current_biases, tc)
    _follower_stages(graph, blocks, current_biases)


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
            ),
        ),
        rule=_RULE,
    )


def _follower_stages(
    graph: CircuitGraph,
    blocks: BlockIndex,
    current_biases: tuple[BlockTag, ...],
) -> None:
    """Voltage-output stage bias and stage for each HL2 source follower."""

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
                nets=(
                    ("input", follower.net_for("input") or ""),
                    ("output", output),
                    ("rail", follower.net_for("rail") or ""),
                ),
                properties=(("mos_type", device.type),),
            ),
            rule=_RULE,
        )
