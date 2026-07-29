"""Manual check of the decomposition against the SKY130 OTA fixture.

Runs the real extraction pipeline from the sibling sky130-analog-workspace
(no rendered-text parsing) and verifies the expectations recorded in
docs/design/functional-decomposition-abel2021.md:

    python scripts/verify_ota_decomposition.py [workspace-dir]

The workspace defaults to ../sky130-analog-workspace next to this repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


UNIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(UNIT_ROOT / "src"))

from spice_canonical import canonical_netlist  # noqa: E402
from netlist_decomposition import decompose, suppress_false_stacks  # noqa: E402


def main() -> int:
    workspace = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else UNIT_ROOT.parents[1] / "sky130-analog-workspace"
    )
    netlist = canonical_netlist.from_file(
        workspace / "circuits" / "analog_frontend_hier_op.spice",
        spice_format="ngspice",
        stop_include=("sky130_1v8_tt.inc",),
        external_subcircuits=json.loads(
            (workspace / "canonical" / "sky130_external_subcircuits.json").read_text()
        ),
        device_type_map=json.loads(
            (workspace / "canonical" / "sky130_device_types.json").read_text()
        ),
        top_name="analog_frontend_hier_op",
    )
    core = next(c for c in netlist.subcircuits if c.name == "ota_core")
    tags = decompose(core, vdd_nets=("vdd",), vss_nets=("vss",))
    kept = suppress_false_stacks(tags)

    def of_kind(kind, source=tags):
        return [tag for tag in source if tag.kind == kind]

    def stack_orders(source):
        return {
            tag.devices_for("ordered_devices")
            for tag in of_kind("transistor_stack", source)
        }

    failures = []

    def check(label, ok):
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
        if not ok:
            failures.append(label)

    diodes = {next(iter(tag.members)) for tag in of_kind("diode_transistor")}
    check("XM3 and XM8 are diode transistors", diodes == {"XM3", "XM8"})

    normals = {next(iter(tag.members)) for tag in of_kind("normal_transistor")}
    check(
        "XM1, XM2 are normal transistors",
        {"XM1", "XM2"} <= normals and not {"XM3", "XM8"} & normals,
    )
    check(
        "XM1/XM2 differential-pair candidate",
        any(
            tag.members == frozenset({"XM1", "XM2"})
            for tag in of_kind("differential_pair_candidate")
        ),
    )

    check(
        "XM3 and XM8 are voltage biases; XM4, XM5, XM7 are current biases",
        {t.members for t in of_kind("voltage_bias")}
        == {frozenset({"XM3"}), frozenset({"XM8"})}
        and {t.members for t in of_kind("current_bias")}
        == {frozenset({"XM4"}), frozenset({"XM5"}), frozenset({"XM7"})},
    )
    pairs = {
        (tag.devices_for("voltage_bias"), tag.devices_for("current_bias"))
        for tag in of_kind("current_mirror")
    }
    check(
        "pairwise mirrors: XM3/XM4, and XM8 shared by XM5 and XM7",
        pairs == {(("XM3",), ("XM4",)), (("XM8",), ("XM5",)), (("XM8",), ("XM7",))},
    )

    check(
        "XM1/XM2 is a full Eq. 13 differential pair (tail is a current bias)",
        any(
            tag.members == frozenset({"XM1", "XM2"})
            for tag in of_kind("differential_pair")
        ),
    )
    tcs = of_kind("transconductance")
    check(
        "XM1/XM2 form the only transconductance (tcs)",
        len(tcs) == 1
        and tcs[0].members == frozenset({"XM1", "XM2"})
        and ("tc_type", "tcs") in tcs[0].properties,
    )
    followers = of_kind("source_follower")
    check(
        "XM6 is a source follower (voltage buffer)",
        len(followers) == 1
        and followers[0].members == frozenset({"XM6"})
        and ("function", "voltage_buffer") in followers[0].properties,
    )
    loads = of_kind("load")
    check(
        "XM3/XM4 mirror is the first-stage load (Alg. 3)",
        len(loads) == 1 and loads[0].members == frozenset({"XM3", "XM4"}),
    )
    biases = {
        dict(tag.properties)["output_type"]: tag for tag in of_kind("stage_bias")
    }
    check(
        "XM5 is the current-output stage bias of the first stage",
        len(biases) == 2
        and biases.get("current") is not None
        and biases["current"].members == frozenset({"XM5"}),
    )
    check(
        "XM7 is the voltage-output stage bias of the follower",
        biases.get("voltage") is not None
        and biases["voltage"].members == frozenset({"XM7"}),
    )
    stages = of_kind("source_follower_stage")
    check(
        "XM6/XM7 form the source-follower output stage",
        len(stages) == 1
        and stages[0].members == frozenset({"XM6", "XM7"})
        and stages[0].devices_for("follower") == ("XM6",),
    )
    stages_a = of_kind("amplification_stage")
    check(
        "tc + XM3/XM4 load + XM5 bias form one simple first stage (as)",
        len(stages_a) == 1
        and stages_a[0].members == frozenset({"XM1", "XM2", "XM3", "XM4", "XM5"})
        and ("stage_class", "as") in stages_a[0].properties
        and ("stage_index", "1") in stages_a[0].properties,
    )
    check("no analog inverter in ota_core", not of_kind("analog_inverter"))
    circuit_bias = of_kind("circuit_bias")
    check(
        "XM8 alone remains as the circuit bias (Eq. 37)",
        len(circuit_bias) == 1
        and circuit_bias[0].members == frozenset({"XM8"}),
    )
    check(
        "XM7/XM6 stack is Eq. 9 valid (bottom-to-top XM7, XM6)",
        ("XM7", "XM6") in stack_orders(tags),
    )
    check(
        "tail false stacks exist before suppression",
        {("XM5", "XM1"), ("XM5", "XM2")} <= stack_orders(tags),
    )
    check(
        "suppress_false_stacks removes tail stacks, keeps XM7/XM6",
        not {("XM5", "XM1"), ("XM5", "XM2")} & stack_orders(kept)
        and ("XM7", "XM6") in stack_orders(kept),
    )

    print(f"\n{len(tags)} tags in ota_core, {len(kept)} after false-stack suppression")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
