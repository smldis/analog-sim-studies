from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from spice_canonical import canonical_netlist  # noqa: E402
from netlist_decomposition import (  # noqa: E402
    DEFAULT_RULES,
    decompose,
    suppress_false_stacks,
    transistor_stack_rule,
)
from netlist_decomposition.engine import (  # noqa: E402
    _cmos_inverters,
    _current_mirrors,
    _differential_pairs,
    _hl1_transistors,
    FunctionRule,
)


MODELS = ".MODEL N NMOS\n.MODEL P PMOS\n"


def _decompose_devices(devices: str, rules=DEFAULT_RULES):
    netlist = canonical_netlist.from_text(MODELS + devices)
    assert not netlist.diagnostics
    return decompose(netlist.top, rules)


def _of_kind(tags, kind: str):
    return tuple(tag for tag in tags if tag.kind == kind)


def _stack_orders(tags):
    return {
        tag.devices_for("ordered_devices")
        for tag in _of_kind(tags, "transistor_stack")
    }


def _stack(tags, ordered_devices: tuple[str, ...]):
    return next(
        tag
        for tag in _of_kind(tags, "transistor_stack")
        if tag.devices_for("ordered_devices") == ordered_devices
    )


# --- HL1 classification and one-device stacks ---------------------------------


def test_normal_mos_is_normal_transistor_and_one_device_stack() -> None:
    tags = _decompose_devices("M1 d g s b N\n")

    normals = _of_kind(tags, "normal_transistor")
    assert [tag.members for tag in normals] == [frozenset({"M1"})]
    assert normals[0].net_for("drain") == "d"
    assert normals[0].net_for("source") == "s"
    assert ("mos_type", "nmos") in normals[0].properties
    assert not _of_kind(tags, "diode_transistor")

    stack = _stack(tags, ("M1",))
    assert stack.net_for("source") == "s"
    assert stack.net_for("drain") == "d"
    assert ("length", "1") in stack.properties
    assert ("member_classes", "nt") in stack.properties
    assert ("structural_variant", "single_normal") in stack.properties


def test_diode_connected_mos_is_diode_transistor_and_one_device_stack() -> None:
    tags = _decompose_devices("M1 dg dg s b N\n")

    diodes = _of_kind(tags, "diode_transistor")
    assert [tag.members for tag in diodes] == [frozenset({"M1"})]
    assert diodes[0].net_for("gate_drain") == "dg"
    assert not _of_kind(tags, "normal_transistor")

    stack = _stack(tags, ("M1",))
    assert ("member_classes", "dt") in stack.properties
    assert ("structural_variant", "single_diode") in stack.properties


def test_fully_shorted_or_gate_source_shorted_mos_has_no_hl1_tag() -> None:
    tags = _decompose_devices(
        "M1 x x x b N\n"  # d, g, s all on one net: neither Eq. 7 nor Eq. 8
        "M2 d gs gs b N\n"  # gate-source connection violates Eq. 7
    )

    assert not _of_kind(tags, "normal_transistor")
    assert not _of_kind(tags, "diode_transistor")
    assert not _of_kind(tags, "transistor_stack")


# --- Equation 9 stacks ---------------------------------------------------------


def test_two_device_all_normal_stack_is_ordered_source_to_drain() -> None:
    tags = _decompose_devices(
        "M1 top g1 mid b N\n"
        "M2 mid g2 bot b N\n"
    )

    stack = _stack(tags, ("M2", "M1"))
    assert stack.net_for("source") == "bot"
    assert stack.net_for("drain") == "top"
    assert ("length", "2") in stack.properties
    assert ("mos_type", "nmos") in stack.properties
    assert ("structural_variant", "all_normal") in stack.properties
    assert ("internal_nets", "mid") in stack.properties
    # One-device sub-stacks remain valid overlapping tags.
    assert _stack_orders(tags) == {("M1",), ("M2",), ("M2", "M1")}


def test_three_device_stack_and_its_sub_stacks() -> None:
    tags = _decompose_devices(
        "M1 top g1 mid2 b N\n"
        "M2 mid2 g2 mid1 b N\n"
        "M3 mid1 g3 bot b N\n"
    )

    stack = _stack(tags, ("M3", "M2", "M1"))
    assert ("length", "3") in stack.properties
    assert ("internal_nets", "mid1,mid2") in stack.properties
    assert _stack_orders(tags) == {
        ("M1",),
        ("M2",),
        ("M3",),
        ("M2", "M1"),
        ("M3", "M2"),
        ("M3", "M2", "M1"),
    }


def test_mixed_polarity_chain_is_not_a_stack() -> None:
    tags = _decompose_devices(
        "M1 top g1 mid b P\n"
        "M2 mid g2 bot b N\n"
    )

    assert _stack_orders(tags) == {("M1",), ("M2",)}


def test_generic_mosfet_forms_only_one_device_stacks() -> None:
    netlist = canonical_netlist.from_text(
        "M1 top g1 mid b UNKNOWN\nM2 mid g2 bot b UNKNOWN\n"
    )
    tags = decompose(netlist.top)

    assert {tag.members for tag in _of_kind(tags, "normal_transistor")} == {
        frozenset({"M1"}),
        frozenset({"M2"}),
    }
    assert _stack_orders(tags) == {("M1",), ("M2",)}


def test_higher_gate_on_lower_drain_rejects_three_device_stack() -> None:
    # M1's gate touches M3's drain (mid1): the pair stacks stay valid, the
    # full three-device chain is a forbidden cross connection.
    tags = _decompose_devices(
        "M1 top mid1 mid2 b N\n"
        "M2 mid2 g2 mid1 b N\n"
        "M3 mid1 g3 bot b N\n"
    )

    orders = _stack_orders(tags)
    assert ("M3", "M2", "M1") not in orders
    assert ("M2", "M1") in orders
    assert ("M3", "M2") in orders


def test_higher_drain_on_lower_source_rejects_candidate() -> None:
    # M1.d returns to M2.s: a two-device ring satisfies the drain-source
    # adjacency in both directions but is rejected by Eq. 9.
    tags = _decompose_devices(
        "M1 bot g1 mid b N\n"
        "M2 mid g2 bot b N\n"
    )

    assert _stack_orders(tags) == {("M1",), ("M2",)}


def test_three_device_ring_reuses_no_transistor_and_is_rejected() -> None:
    tags = _decompose_devices(
        "M1 net1 g1 net3 b N\n"
        "M2 net2 g2 net1 b N\n"
        "M3 net3 g3 net2 b N\n"
    )

    # Every two-device arc of the ring closes drain-to-source against its
    # lower member's source only at length three, so pairs survive and the
    # ring (which would need to reuse its bottom transistor to close) does
    # not appear at any length.
    orders = _stack_orders(tags)
    assert all(len(order) <= 2 for order in orders)
    assert len({order for order in orders if len(order) == 1}) == 3


def test_stacks_are_enumerated_once_without_reversed_duplicates() -> None:
    tags = _decompose_devices(
        "M1 top g1 mid b N\n"
        "M2 mid g2 bot b N\n"
    )

    stacks = _of_kind(tags, "transistor_stack")
    orders = [tag.devices_for("ordered_devices") for tag in stacks]
    assert len(orders) == len(set(orders))
    assert ("M1", "M2") not in orders


def test_diode_pair_and_mixed_pair_structural_variants() -> None:
    tags = _decompose_devices(
        # Diode pair: both members drain-gate connected.
        "M1 top top mid b N\n"
        "M2 mid mid bot b N\n"
        # Mixed pair, diode on top.
        "M3 t2 t2 m2 b N\n"
        "M4 m2 g4 b2 b N\n"
        # Mixed pair, diode at bottom.
        "M5 t3 g5 m3 b N\n"
        "M6 m3 m3 b3 b N\n"
    )

    assert ("member_classes", "dt,dt") in _stack(tags, ("M2", "M1")).properties
    assert ("structural_variant", "diode_pair") in _stack(
        tags, ("M2", "M1")
    ).properties
    assert ("structural_variant", "mixed_pair_diode_top") in _stack(
        tags, ("M4", "M3")
    ).properties
    assert ("structural_variant", "mixed_pair_diode_bottom") in _stack(
        tags, ("M6", "M5")
    ).properties


def test_exclusive_internal_nets_policy_drops_branching_stacks() -> None:
    # A tail device feeding two source-coupled devices: the internal net
    # carries three MOS drain/source terminals.
    devices = (
        "MTAIL tail bias vss b N\n"
        "MIN1 left in1 tail b N\n"
        "MIN2 right in2 tail b N\n"
    )
    default_tags = _decompose_devices(devices)
    exclusive_rules = (
        FunctionRule("HL1 transistors", _hl1_transistors),
        transistor_stack_rule(exclusive_internal_nets=True),
    )
    exclusive_tags = _decompose_devices(devices, exclusive_rules)

    assert ("MTAIL", "MIN1") in _stack_orders(default_tags)
    assert ("MTAIL", "MIN2") in _stack_orders(default_tags)
    assert _stack_orders(exclusive_tags) == {("MTAIL",), ("MIN1",), ("MIN2",)}


def test_suppress_false_stacks_drops_stacks_through_differential_pair() -> None:
    tags = _decompose_devices(
        "MTAIL tail bias vss b N\n"
        "MIN1 left in1 tail b N\n"
        "MIN2 right in2 tail b N\n"
        "M1 top g1 mid b N\n"
        "M2 mid g2 bot b N\n"
    )

    kept = suppress_false_stacks(tags)
    orders = _stack_orders(kept)
    assert ("MTAIL", "MIN1") not in orders
    assert ("MTAIL", "MIN2") not in orders
    # Unrelated stacks, one-device stacks, and all non-stack tags survive.
    assert ("M2", "M1") in orders
    assert {("MTAIL",), ("MIN1",), ("MIN2",)} <= orders
    assert _of_kind(kept, "differential_pair_candidate")
    assert len(_of_kind(kept, "normal_transistor")) == 5


# --- Dependent rules on a small OTA-like fixture -------------------------------


NETLIST = MODELS + """\
.SUBCKT EXAMPLE in_p in_n out vdd vss
MREF bias bias vss vss N
MOUT tail bias vss vss N
MIN1 left in_p tail vss N
MIN2 right in_n tail vss N
MSTACK1 out cascode middle vss N
MSTACK2 middle drive vss vss N
MPINV out inv_in vdd vdd P
MNINV out inv_in vss vss N
.ENDS EXAMPLE
"""


def _tags(kind: str):
    circuit = canonical_netlist.from_text(NETLIST).subcircuits[0]
    return tuple(tag for tag in decompose(circuit) if tag.kind == kind)


def test_tags_a_diode_connected_reference_and_mirror() -> None:
    diode = _tags("diode_transistor")
    mirrors = _tags("simple_current_mirror")

    assert [tag.members for tag in diode] == [frozenset({"MREF"})]
    assert len(mirrors) == 1
    assert mirrors[0].devices_for("reference") == ("MREF",)
    assert mirrors[0].devices_for("outputs") == ("MOUT",)
    assert mirrors[0].net_for("bias") == "bias"


def test_tags_multi_output_current_mirror() -> None:
    netlist = MODELS + (
        "MREF bias bias vss vss N\n"
        "MOUT1 o1 bias vss vss N\n"
        "MOUT2 o2 bias vss vss N\n"
    )
    tags = decompose(canonical_netlist.from_text(netlist).top)
    mirrors = _of_kind(tags, "simple_current_mirror")

    assert len(mirrors) == 1
    assert mirrors[0].devices_for("outputs") == ("MOUT1", "MOUT2")
    assert ("output_count", "2") in mirrors[0].properties


def test_tags_differential_pair_candidate() -> None:
    pairs = _tags("differential_pair_candidate")

    assert any(tag.members == frozenset({"MIN1", "MIN2"}) for tag in pairs)


def test_tags_oriented_transistor_stack() -> None:
    stacks = _tags("transistor_stack")

    stack = next(
        tag
        for tag in stacks
        if tag.members == frozenset({"MSTACK1", "MSTACK2"})
    )
    assert stack.devices_for("ordered_devices") == ("MSTACK2", "MSTACK1")
    assert stack.net_for("source") == "vss"
    assert stack.net_for("drain") == "out"
    assert ("length", "2") in stack.properties


def test_tags_cmos_inverter() -> None:
    inverters = _tags("cmos_inverter")

    assert len(inverters) == 1
    assert inverters[0].members == frozenset({"MPINV", "MNINV"})
    assert inverters[0].net_for("input") == "inv_in"
    assert inverters[0].net_for("output") == "out"


def test_dependent_rules_reject_unknown_polarity() -> None:
    netlist = (
        "MREF bias bias vss vss UNKNOWN\n"
        "MOUT o1 bias vss vss UNKNOWN\n"
        "MIN1 l inp tail vss UNKNOWN\n"
        "MIN2 r inn tail vss UNKNOWN\n"
    )
    rules = (
        FunctionRule("HL1 transistors", _hl1_transistors),
        FunctionRule("simple current mirrors", _current_mirrors),
        FunctionRule("differential-pair candidates", _differential_pairs),
        FunctionRule("CMOS inverters", _cmos_inverters),
    )
    tags = decompose(canonical_netlist.from_text(netlist).top, rules)

    assert not _of_kind(tags, "simple_current_mirror")
    assert not _of_kind(tags, "differential_pair_candidate")
