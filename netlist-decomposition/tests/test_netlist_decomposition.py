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
    _differential_pairs,
    _hl1_transistors,
    BlockCandidate,
    CircuitGraph,
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


def test_tags_a_diode_reference_as_bias_pair_and_simple_mirror() -> None:
    diode = _tags("diode_transistor")
    mirrors = _tags("current_mirror")

    assert [tag.members for tag in diode] == [frozenset({"MREF"})]
    assert [tag.devices_for("ordered_devices") for tag in _tags("voltage_bias")] == [
        ("MREF",)
    ]
    assert [tag.devices_for("ordered_devices") for tag in _tags("current_bias")] == [
        ("MOUT",)
    ]
    assert len(mirrors) == 1
    assert mirrors[0].devices_for("voltage_bias") == ("MREF",)
    assert mirrors[0].devices_for("current_bias") == ("MOUT",)
    assert mirrors[0].net_for("bias") == "bias"
    assert mirrors[0].net_for("output") == "tail"
    assert ("variant", "scm") in mirrors[0].properties


def test_multi_output_structure_becomes_pairwise_overlapping_mirrors() -> None:
    netlist = MODELS + (
        "MREF bias bias vss vss N\n"
        "MOUT1 o1 bias vss vss N\n"
        "MOUT2 o2 bias vss vss N\n"
    )
    tags = decompose(canonical_netlist.from_text(netlist).top)
    mirrors = _of_kind(tags, "current_mirror")

    # One voltage bias shared by two overlapping pairwise mirrors: the
    # paper's current-mirror bench is this overlap, not an aggregate tag.
    assert {tag.members for tag in mirrors} == {
        frozenset({"MREF", "MOUT1"}),
        frozenset({"MREF", "MOUT2"}),
    }
    assert all(tag.devices_for("voltage_bias") == ("MREF",) for tag in mirrors)
    assert {tag.net_for("output") for tag in mirrors} == {"o1", "o2"}


def test_cascode_mirror_prunes_contained_simple_mirror() -> None:
    tags = _decompose_devices(
        "MA n1 n1 vss b N\n"
        "MB n2 n2 n1 b N\n"
        "MC m1 n1 vss b N\n"
        "MD out n2 m1 b N\n"
    )

    # The inner MA/MC simple mirror and all one-device biases are irrelevant
    # per Eq. 19: same kind, strictly contained in the cascode blocks.
    assert [tag.members for tag in _of_kind(tags, "voltage_bias")] == [
        frozenset({"MA", "MB"})
    ]
    assert [tag.members for tag in _of_kind(tags, "current_bias")] == [
        frozenset({"MC", "MD"})
    ]
    mirrors = _of_kind(tags, "current_mirror")
    assert len(mirrors) == 1
    assert mirrors[0].devices_for("voltage_bias") == ("MA", "MB")
    assert mirrors[0].devices_for("current_bias") == ("MC", "MD")
    assert mirrors[0].net_for("output") == "out"
    assert ("variant", "unclassified") in mirrors[0].properties


def test_current_bias_rejected_when_drain_drives_same_doping_gate() -> None:
    # MOUT's drain feeds MLOAD's gate: per Alg. 1 line 8 (Eq. 11's negated
    # existential) MOUT cannot be a current bias, so no mirror is formed.
    tags = _decompose_devices(
        "MREF bias bias vss b N\n"
        "MOUT o1 bias vss b N\n"
        "MLOAD x o1 vss b N\n"
    )

    assert not _of_kind(tags, "voltage_bias")
    assert not _of_kind(tags, "current_bias")
    assert not _of_kind(tags, "current_mirror")


def test_supply_nets_are_declared_not_inferred() -> None:
    circuit = canonical_netlist.from_text(MODELS + "M1 d g s b N\n").top

    assert CircuitGraph(circuit).supply_nets == frozenset()
    graph = CircuitGraph(circuit, vdd_nets=("vdd",), vss_nets=("vss", "gnd"))
    assert graph.vdd_nets == frozenset({"vdd"})
    assert graph.vss_nets == frozenset({"vss", "gnd"})
    assert graph.supply_nets == frozenset({"vdd", "vss", "gnd"})
    assert decompose(circuit, vdd_nets=("vdd",), vss_nets=("vss",))


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
        transistor_stack_rule(),
        FunctionRule("differential-pair candidates", _differential_pairs),
        FunctionRule("CMOS inverters", _cmos_inverters),
    )
    tags = decompose(canonical_netlist.from_text(netlist).top, rules)

    assert not _of_kind(tags, "current_mirror")
    assert not _of_kind(tags, "differential_pair_candidate")


# --- Full differential pairs and HL3 blocks ------------------------------------


FIVE_TRANSISTOR_OTA = (
    "MREF bias bias vss vss N\n"
    "MTAIL tail bias vss vss N\n"
    "MIN1 outn in_p tail vss N\n"
    "MIN2 outp in_n tail vss N\n"
    "MLP1 outn outn vdd vdd P\n"
    "MLP2 outp outn vdd vdd P\n"
)


def test_full_differential_pair_requires_current_bias_tail() -> None:
    tags = _decompose_devices(FIVE_TRANSISTOR_OTA)
    pairs = _of_kind(tags, "differential_pair")

    assert [tag.members for tag in pairs] == [frozenset({"MIN1", "MIN2"})]
    assert pairs[0].net_for("common_source") == "tail"
    assert pairs[0].net_for("output_1") == "outn"

    # Source-coupled devices without a recognized current bias on the common
    # source stay candidates only (Eq. 13's existential is not met).
    tail_less = _decompose_devices(
        "MIN1 left in1 tail b N\n"
        "MIN2 right in2 tail b N\n"
    )
    assert not _of_kind(tail_less, "differential_pair")
    assert _of_kind(tail_less, "differential_pair_candidate")


def test_five_transistor_ota_decomposes_into_tc_load_stage_bias() -> None:
    netlist = canonical_netlist.from_text(MODELS + FIVE_TRANSISTOR_OTA)
    tags = decompose(netlist.top, vdd_nets=("vdd",), vss_nets=("vss",))

    tc = _of_kind(tags, "transconductance")
    assert len(tc) == 1
    assert tc[0].members == frozenset({"MIN1", "MIN2"})
    assert ("tc_type", "tcs") in tc[0].properties
    assert tc[0].net_for("out_1") == "outn"
    assert tc[0].net_for("out_2") == "outp"

    loads = _of_kind(tags, "load")
    assert len(loads) == 1
    assert loads[0].members == frozenset({"MLP1", "MLP2"})
    assert loads[0].devices_for("part_pmos") == ("MLP1", "MLP2")
    assert loads[0].devices_for("part_nmos") == ()
    assert loads[0].devices_for("transconductance") == ("MIN1", "MIN2")

    stage_bias = _of_kind(tags, "stage_bias")
    assert len(stage_bias) == 1
    assert stage_bias[0].members == frozenset({"MTAIL"})
    assert stage_bias[0].net_for("output_1") == "tail"
    assert ("output_type", "current") in stage_bias[0].properties


def test_load_needs_declared_rails_for_rail_connected_stacks() -> None:
    # Same OTA without declared supplies: Algorithm 3 cannot see that the
    # PMOS load sources sit on a rail, so no load is recognized.
    tags = _decompose_devices(FIVE_TRANSISTOR_OTA)

    assert not _of_kind(tags, "load")
    assert _of_kind(tags, "transconductance")


def test_cascode_differential_pair_forms_one_cascode_transconductance() -> None:
    tags = _decompose_devices(
        "MREF bias bias vss b N\n"
        "MTAIL tail bias vss b N\n"
        "MIN1 d1 inp tail b N\n"
        "MIN2 d2 inn tail b N\n"
        "MC1 o1 cas d1 b N\n"
        "MC2 o2 cas d2 b N\n"
    )

    couples = _of_kind(tags, "gate_connected_couple")
    assert [tag.members for tag in couples] == [frozenset({"MC1", "MC2"})]

    cascode = _of_kind(tags, "cascode_differential_pair")
    assert len(cascode) == 1
    assert cascode[0].devices_for("pair") == ("MIN1", "MIN2")
    assert cascode[0].devices_for("couple") == ("MC1", "MC2")
    assert ("variant", "cdp") in cascode[0].properties
    assert cascode[0].net_for("output_1") == "o1"

    tc = _of_kind(tags, "transconductance")
    assert len(tc) == 1
    assert tc[0].members == frozenset({"MIN1", "MIN2", "MC1", "MC2"})
    assert tc[0].devices_for("cascode_devices") == ("MC1", "MC2")
    assert tc[0].net_for("out_1") == "o1"


def test_complementary_transconductance_from_opposite_doping_pairs() -> None:
    tags = _decompose_devices(
        "MREFN biasn biasn vss b N\n"
        "MTN tailn biasn vss b N\n"
        "MN1 x1 ina tailn b N\n"
        "MN2 x2 inb tailn b N\n"
        "MREFP biasp biasp vdd b P\n"
        "MTP tailp biasp vdd b P\n"
        "MP1 y1 ina tailp b P\n"
        "MP2 y2 inb tailp b P\n"
    )

    tc = _of_kind(tags, "transconductance")
    assert len(tc) == 1
    assert ("tc_type", "tcc") in tc[0].properties
    assert ("mos_type", "mixed") in tc[0].properties
    assert tc[0].members == frozenset({"MN1", "MN2", "MP1", "MP2"})


def test_cmfb_transconductance_from_single_shared_gate() -> None:
    tags = _decompose_devices(
        "MREF bias bias vss b N\n"
        "MT1 tail1 bias vss b N\n"
        "MT2 tail2 bias vss b N\n"
        "MA1 a1 ga tail1 b N\n"
        "MA2 a2 shared tail1 b N\n"
        "MB1 b1 shared tail2 b N\n"
        "MB2 b2 gc tail2 b N\n"
    )

    tc = _of_kind(tags, "transconductance")
    assert len(tc) == 1
    assert ("tc_type", "tccmfb") in tc[0].properties
    assert tc[0].members == frozenset({"MA1", "MA2", "MB1", "MB2"})


SOURCE_FOLLOWER = (
    "MREF bias bias vss vss N\n"
    "MSINK out bias vss vss N\n"
    "MFOL vdd in out vss N\n"
)


def test_source_follower_stage_from_rail_transistor_and_biased_output() -> None:
    netlist = canonical_netlist.from_text(MODELS + SOURCE_FOLLOWER)
    tags = decompose(netlist.top, vdd_nets=("vdd",), vss_nets=("vss",))

    followers = _of_kind(tags, "source_follower")
    assert len(followers) == 1
    assert followers[0].members == frozenset({"MFOL"})
    assert ("function", "voltage_buffer") in followers[0].properties
    assert followers[0].net_for("input") == "in"
    assert followers[0].net_for("output") == "out"
    # A follower is a voltage buffer, not a transconductance stage.
    assert not _of_kind(tags, "transconductance")

    stage_bias = _of_kind(tags, "stage_bias")
    assert len(stage_bias) == 1
    assert stage_bias[0].members == frozenset({"MSINK"})
    assert ("output_type", "voltage") in stage_bias[0].properties
    assert stage_bias[0].net_for("output_1") == "out"
    assert stage_bias[0].devices_for("source_follower") == ("MFOL",)

    stages = _of_kind(tags, "source_follower_stage")
    assert len(stages) == 1
    assert stages[0].members == frozenset({"MFOL", "MSINK"})
    assert stages[0].devices_for("follower") == ("MFOL",)
    assert stages[0].devices_for("current_biases") == ("MSINK",)
    assert stages[0].net_for("input") == "in"
    assert stages[0].net_for("output") == "out"


def test_pmos_source_follower_is_symmetric() -> None:
    netlist = canonical_netlist.from_text(
        MODELS
        + "MREF bias bias vdd vdd P\n"
        + "MSRC out bias vdd vdd P\n"
        + "MFOL vss in out vdd P\n"
    )
    tags = decompose(netlist.top, vdd_nets=("vdd",), vss_nets=("vss",))

    stages = _of_kind(tags, "source_follower_stage")
    assert len(stages) == 1
    assert stages[0].members == frozenset({"MFOL", "MSRC"})
    assert ("mos_type", "pmos") in stages[0].properties


def test_max_level_completes_and_filters_tagging_sets() -> None:
    netlist = canonical_netlist.from_text(MODELS + SOURCE_FOLLOWER)
    rails = {"vdd_nets": ("vdd",), "vss_nets": ("vss",)}

    hl1 = decompose(netlist.top, max_level=1, **rails)
    assert {tag.kind for tag in hl1} == {"normal_transistor", "diode_transistor"}

    hl2_kinds = {tag.kind for tag in decompose(netlist.top, max_level=2, **rails)}
    assert "source_follower" in hl2_kinds
    assert "current_mirror" in hl2_kinds
    assert not hl2_kinds & {"stage_bias", "source_follower_stage"}

    full_kinds = {tag.kind for tag in decompose(netlist.top, **rails)}
    assert {"stage_bias", "source_follower_stage"} <= full_kinds


def test_source_follower_needs_declared_rails() -> None:
    # Without rails the follower drain cannot be recognized as
    # rail-connected, so no follower blocks appear.
    tags = _decompose_devices(SOURCE_FOLLOWER)

    assert not _of_kind(tags, "source_follower_stage")
    assert not _of_kind(tags, "stage_bias")
    assert not _of_kind(tags, "source_follower")


# --- Analog inverters and HL4 stages --------------------------------------------


RAILS = {"vdd_nets": ("vdd",), "vss_nets": ("vss",)}

TWO_STAGE_MILLER = (
    FIVE_TRANSISTOR_OTA
    + "MP2 out outp vdd vdd P\n"
    + "MN2 out bias vss vss N\n"
    + "CC outp out 1p\n"
    + "CL out vss 5p\n"
)


def _decompose_with_rails(devices: str, **kwargs):
    netlist = canonical_netlist.from_text(MODELS + devices)
    assert not netlist.diagnostics
    return decompose(netlist.top, **RAILS, **kwargs)


def test_gate_coupled_cmos_pair_is_not_an_analog_inverter() -> None:
    # Eq. 18 forbids gate-gate connections between the stacks: the digital
    # CMOS inverter stays the legacy cmos_inverter tag only.
    tags = _decompose_with_rails(
        "MP out in vdd vdd P\n"
        "MN out in vss vss N\n"
    )

    assert not _of_kind(tags, "analog_inverter")
    assert _of_kind(tags, "cmos_inverter")


def test_differential_pair_false_stacks_do_not_form_analog_inverters() -> None:
    tags = _decompose_with_rails(FIVE_TRANSISTOR_OTA)

    # The MTAIL/MIN2 false stack (Section 4.6) must not pair with the MLP2
    # load transistor into an inverter.
    assert not _of_kind(tags, "analog_inverter")

    # The five-transistor OTA is one simple first stage (Eq. 30/31).
    stages = _of_kind(tags, "amplification_stage")
    assert len(stages) == 1
    assert stages[0].members == frozenset(
        {"MIN1", "MIN2", "MLP1", "MLP2", "MTAIL"}
    )
    assert ("stage_class", "as") in stages[0].properties
    assert ("inverting", "false") in stages[0].properties
    assert stages[0].net_for("out_1") == "outn"

    # Eq. 37: the reference diode is the only bias outside the stage.
    circuit_bias = _of_kind(tags, "circuit_bias")
    assert len(circuit_bias) == 1
    assert circuit_bias[0].members == frozenset({"MREF"})


def test_two_stage_miller_recognizes_inverting_stage_and_capacitors() -> None:
    tags = _decompose_with_rails(TWO_STAGE_MILLER)

    inverters = _of_kind(tags, "analog_inverter")
    assert len(inverters) == 1
    assert inverters[0].members == frozenset({"MP2", "MN2"})
    assert inverters[0].devices_for("stack_pmos") == ("MP2",)
    assert inverters[0].net_for("output") == "out"

    stages = {
        dict(tag.properties)["stage_class"]: tag
        for tag in _of_kind(tags, "amplification_stage")
    }
    assert set(stages) == {"as", "ainvc"}
    assert ("stage_index", "1") in stages["as"].properties
    second = stages["ainvc"]
    assert second.members == frozenset({"MP2", "MN2"})
    assert ("stage_index", "2") in second.properties
    assert ("inverting", "true") in second.properties
    assert second.net_for("in_1") == "outp"
    assert second.net_for("out_1") == "out"

    # Algorithm 2 emits the HL3 tcinv and its Eq. 28 stage bias with the
    # stage.
    tcinv = [
        tag
        for tag in _of_kind(tags, "transconductance")
        if ("tc_type", "tcinv") in tag.properties
    ]
    assert len(tcinv) == 1
    assert tcinv[0].members == frozenset({"MP2"})
    assert tcinv[0].net_for("in_1") == "outp"
    second_bias = [
        tag
        for tag in _of_kind(tags, "stage_bias")
        if tag.devices_for("transconductance") == ("MP2",)
    ]
    assert len(second_bias) == 1
    assert second_bias[0].members == frozenset({"MN2"})
    assert ("output_type", "current") in second_bias[0].properties

    circuit_bias = _of_kind(tags, "circuit_bias")
    assert len(circuit_bias) == 1
    assert circuit_bias[0].members == frozenset({"MREF"})

    # Eq. 38: CC bridges the outputs of stage 1 and stage 2; Eq. 39: CL
    # hangs from the highest-stage output to the declared ground rail.
    comp = _of_kind(tags, "compensation_capacitor")
    assert [tag.members for tag in comp] == [frozenset({"CC"})]
    load_caps = _of_kind(tags, "load_capacitor")
    assert [tag.members for tag in load_caps] == [frozenset({"CL"})]
    assert load_caps[0].net_for("output") == "out"
    assert ("stage_index", "2") in load_caps[0].properties


SYMMETRICAL_OTA = (
    "MREF bias bias vss vss N\n"
    "MTAIL tail bias vss vss N\n"
    "MIN1 outn in_p tail vss N\n"
    "MIN2 outp in_n tail vss N\n"
    "MLP1 outn outn vdd vdd P\n"
    "MLP2 outp outp vdd vdd P\n"
    "MP3 outa outn vdd vdd P\n"
    "MP4 outb outp vdd vdd P\n"
    "MN3 outa outa vss vss N\n"
    "MN4 outb outa vss vss N\n"
)


def test_symmetrical_ota_second_stages_are_ainvc_and_ainvv() -> None:
    tags = _decompose_with_rails(SYMMETRICAL_OTA)

    classes = {
        dict(tag.properties)["stage_class"]: tag
        for tag in _of_kind(tags, "amplification_stage")
    }
    assert set(classes) == {"as", "ainvc", "ainvv"}
    assert classes["ainvc"].members == frozenset({"MP4", "MN4"})
    assert classes["ainvv"].members == frozenset({"MP3", "MN3"})
    assert ("stage_index", "2") in classes["ainvc"].properties
    assert ("stage_index", "2") in classes["ainvv"].properties

    # Eq. 27: the ainvv stage bias is one voltage bias on the tcinv drain.
    voltage_stage_bias = [
        tag
        for tag in _of_kind(tags, "stage_bias")
        if ("output_type", "voltage") in tag.properties
    ]
    assert len(voltage_stage_bias) == 1
    assert voltage_stage_bias[0].members == frozenset({"MN3"})
    assert voltage_stage_bias[0].devices_for("voltage_biases") == ("MN3",)

    tcinv_members = {
        tag.members
        for tag in _of_kind(tags, "transconductance")
        if ("tc_type", "tcinv") in tag.properties
    }
    assert tcinv_members == {frozenset({"MP3"}), frozenset({"MP4"})}

    assert _of_kind(tags, "circuit_bias")[0].members == frozenset({"MREF"})


def test_max_level_three_returns_complete_level_three_view() -> None:
    netlist = canonical_netlist.from_text(MODELS + TWO_STAGE_MILLER)
    level4_kinds = {
        "amplification_stage",
        "circuit_bias",
        "compensation_capacitor",
        "load_capacitor",
    }

    level3_view = decompose(netlist.top, max_level=3, **RAILS)
    level3_kinds = {tag.kind for tag in level3_view}
    assert "analog_inverter" in level3_kinds  # a level-2 kind
    assert not level3_kinds & level4_kinds
    # The stages pass completes levels 3 and 4 together, so the level-3
    # view already holds the tcinv transconductance Algorithm 2 emits
    # inside the amplification-stage loop.
    assert any(
        ("tc_type", "tcinv") in tag.properties
        for tag in level3_view
        if tag.kind == "transconductance"
    )

    full_kinds = {tag.kind for tag in decompose(netlist.top, **RAILS)}
    assert level4_kinds <= full_kinds


def test_tags_carry_their_hierarchy_level() -> None:
    netlist = canonical_netlist.from_text(MODELS + TWO_STAGE_MILLER)
    tags = decompose(netlist.top, **RAILS)
    levels = {tag.kind: tag.level for tag in tags}

    assert levels["normal_transistor"] == 1
    assert levels["current_bias"] == 2
    assert levels["stage_bias"] == 3
    assert levels["amplification_stage"] == 4


def test_unregistered_kind_gets_no_level_and_survives_filtering() -> None:
    def probe(graph, blocks):
        return [BlockCandidate(kind="custom_probe", members=frozenset({"M1"}))]

    netlist = canonical_netlist.from_text(MODELS + "M1 d g s b N\n")
    tags = decompose(
        netlist.top,
        DEFAULT_RULES + (FunctionRule("custom probe", probe),),
        max_level=2,
    )

    probes = _of_kind(tags, "custom_probe")
    assert len(probes) == 1
    assert probes[0].level is None
