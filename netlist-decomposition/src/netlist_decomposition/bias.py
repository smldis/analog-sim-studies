"""HL2 voltage/current bias and current mirror recognition.

Implements Algorithm 1 of Abel et al. (2021) on top of the transistor-stack
tags: voltage bias and current bias (approximating Eq. 10 and 11 exactly the
way the paper's algorithm does), current mirrors (Eq. 12), and the deletion
of irrelevant same-type-contained blocks (Eq. 19).

This lives outside the monotone rule engine on purpose.  Eq. 11 contains a
negated existential (a stack is a current bias only while no same-doping
stack gate hangs on its drain) and Eq. 10/11 reference each other, so the
recognition needs the complete stack set and a dedicated fixed point, not an
add-only rule.  Following the paper:

- line 8's check stands in for Eq. 11's "no voltage bias on the drain";
- Eq. 10's last clause (every stack gate has exactly one gate-drain partner
  that belongs to some bias) is not checked, as the paper itself skips it
  for valid topologies;
- a current mirror is one voltage bias plus ONE current bias.  A structure
  with several outputs becomes several overlapping mirror tags sharing the
  voltage bias -- the paper's "current mirror bench" is that overlap, not a
  block type of its own;
- sub-stack biases and mirrors inside larger ones (a simple mirror inside a
  cascode mirror) are recognized and then pruned by Eq. 19.

Additionally, a voltage bias and a current bias pairing must not share a
device; the paper treats them as distinct blocks and a shared transistor
would double-assign within one mirror.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from netlist_decomposition import mos
from netlist_decomposition.engine import (
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
)


_RULE = "HL2 bias resolution (Alg. 1)"
_DOPING_TYPE = {"n": "nmos", "p": "pmos"}

#: Block kinds subject to Eq. 19 irrelevant-containment pruning.
PRUNED_KINDS = frozenset({"voltage_bias", "current_bias", "current_mirror"})


@dataclass(frozen=True)
class _Stack:
    """Bottom-to-top view of one transistor_stack tag."""

    names: tuple[str, ...]
    members: frozenset[str]
    gates: tuple[str, ...]
    gate_set: frozenset[str]
    drains: tuple[str, ...]
    source: str
    drain: str
    doping: str
    member_classes: str


def _stack_views(graph: CircuitGraph, blocks: BlockIndex) -> tuple[_Stack, ...]:
    views = []
    for tag in blocks.of_kind("transistor_stack"):
        names = tag.devices_for("ordered_devices")
        doping = mos.mos_polarity(graph.devices[names[0]])
        if doping is None:
            continue
        gates = tuple(
            mos.pin_net(graph.devices[name], "g") or "" for name in names
        )
        drains = tuple(
            mos.pin_net(graph.devices[name], "d") or "" for name in names
        )
        views.append(
            _Stack(
                names=names,
                members=tag.members,
                gates=gates,
                gate_set=frozenset(gates),
                drains=drains,
                source=tag.net_for("source") or "",
                drain=tag.net_for("drain") or "",
                doping=doping,
                member_classes=dict(tag.properties).get("member_classes", ""),
            )
        )
    return tuple(views)


def _bias_candidate(kind: str, stack: _Stack) -> BlockCandidate:
    return BlockCandidate(
        kind=kind,
        members=stack.members,
        roles=(("ordered_devices", stack.names),),
        nets=(("source", stack.source), ("drain", stack.drain)),
        properties=(
            ("length", str(len(stack.names))),
            ("mos_type", _DOPING_TYPE[stack.doping]),
            ("member_classes", stack.member_classes),
        ),
    )


def _is_current_mirror(vb: _Stack, cb: _Stack) -> bool:
    """Eq. 12 for one voltage-bias/current-bias pair (same doping assumed)."""

    if vb.members & cb.members:
        return False
    if vb.source != cb.source:
        return False
    if len(cb.gates) < len(vb.gates):
        return False
    if any(vb.gates[i] != cb.gates[i] for i in range(len(vb.gates))):
        return False
    if vb.drain not in cb.gate_set:
        return False
    drains = [*vb.drains, *cb.drains]
    return all(drains.count(gate) == 1 for gate in vb.gates[:-1])


def resolve_bias_blocks(graph: CircuitGraph, blocks: BlockIndex) -> None:
    """Add voltage_bias, current_bias, and current_mirror tags to ``blocks``."""

    stacks = _stack_views(graph, blocks)

    for doping in ("n", "p"):
        group = tuple(stack for stack in stacks if stack.doping == doping)
        if not group:
            continue
        # With one-device stacks present for every HL1 transistor, the union
        # of stack gate nets is the gate universe Alg. 1 line 8 tests against.
        gate_universe = frozenset(
            gate for stack in group for gate in stack.gate_set
        )

        vb: dict[tuple[str, ...], _Stack] = {}
        cb: dict[tuple[str, ...], _Stack] = {}
        changed = True
        while changed:
            changed = False
            for ts_k in group:
                if ts_k.names in vb or ts_k.names in cb:
                    continue
                for ts_l in group:
                    if ts_l.members & ts_k.members:
                        continue
                    # Line 7: drain-gate and complete gate-gate connection.
                    if ts_k.drain not in ts_l.gate_set:
                        continue
                    if not ts_k.gate_set <= ts_l.gate_set:
                        continue
                    # Line 8: ts_l has only the connections of a current
                    # bias, and nothing of this doping hangs on its drain.
                    if (
                        ts_l.gate_set <= ts_k.gate_set | {ts_k.drain}
                        and ts_l.drain not in gate_universe
                    ):
                        vb.setdefault(ts_k.names, ts_k)
                        if ts_l.names not in cb:
                            cb[ts_l.names] = ts_l
                        changed = True
                        continue
                    # Line 11: secondary voltage bias for a known current bias.
                    if ts_l.names in cb:
                        vb.setdefault(ts_k.names, ts_k)
                        changed = True

        for stack in vb.values():
            blocks.add(_bias_candidate("voltage_bias", stack), rule=_RULE)
        for stack in cb.values():
            blocks.add(_bias_candidate("current_bias", stack), rule=_RULE)

        for vb_stack in vb.values():
            for cb_stack in cb.values():
                if not _is_current_mirror(vb_stack, cb_stack):
                    continue
                variant = (
                    "scm"
                    if len(vb_stack.names) == 1 and len(cb_stack.names) == 1
                    else "unclassified"
                )
                blocks.add(
                    BlockCandidate(
                        kind="current_mirror",
                        members=vb_stack.members | cb_stack.members,
                        roles=(
                            ("voltage_bias", vb_stack.names),
                            ("current_bias", cb_stack.names),
                        ),
                        nets=(
                            ("common_source", vb_stack.source),
                            ("bias", vb_stack.drain),
                            ("output", cb_stack.drain),
                        ),
                        properties=(
                            ("mos_type", _DOPING_TYPE[doping]),
                            ("vb_length", str(len(vb_stack.names))),
                            ("cb_length", str(len(cb_stack.names))),
                            ("variant", variant),
                        ),
                    ),
                    rule=_RULE,
                )


def maximal(tags: Sequence[BlockTag]) -> tuple[BlockTag, ...]:
    """Eq. 19 view: drop tags strictly contained in a same-kind tag.

    Non-destructive counterpart of ``prune_irrelevant``, used inside HL2
    by recognizers that run after Algorithm 1 but before the level's
    closing deletion (the source follower must not accept a sub-stack
    current bias the deletion is about to remove).
    """

    return tuple(
        tag
        for tag in tags
        if not any(tag.members < other.members for other in tags)
    )


def prune_irrelevant(blocks: BlockIndex) -> None:
    """Delete irrelevant same-type-contained blocks per Eq. 19.

    A voltage bias, current bias, or current mirror whose member set is a
    strict subset of another block of the same kind adds no information
    (e.g. the simple mirror inside a cascode mirror, Fig. 10a) and is
    removed from the index.  All other kinds are left untouched.  As in
    the paper, this closes Algorithm 1's hierarchy level: it runs at the
    end of HL2, after the differential pairs (which Algorithm 1 finds
    against the pre-deletion current biases), so every later level reads
    the cleaned block set directly.
    """

    members_by_kind: dict[str, list[frozenset[str]]] = {}
    for tag in blocks:
        if tag.kind in PRUNED_KINDS:
            members_by_kind.setdefault(tag.kind, []).append(tag.members)

    blocks.discard(
        tag
        for tag in blocks
        if tag.kind in PRUNED_KINDS
        and any(tag.members < other for other in members_by_kind[tag.kind])
    )
