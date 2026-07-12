"""Manual check of the decomposition against the SKY130 OTA fixture.

Runs the real extraction pipeline from the sibling sky130-analog-workspace
(no rendered-text parsing) and verifies the expectations recorded in
design/functional-decomposition-abel2021.md:

    python scripts/verify_ota_decomposition.py [workspace-dir]

The workspace defaults to ../sky130-analog-workspace next to this repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from spice_canonical import canonical_netlist  # noqa: E402
from netlist_decomposition import decompose, suppress_false_stacks  # noqa: E402


def main() -> int:
    workspace = Path(
        sys.argv[1] if len(sys.argv) > 1 else REPO_ROOT.parent / "sky130-analog-workspace"
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
    tags = decompose(core)
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

    mirrors = of_kind("simple_current_mirror")
    check(
        "XM3/XM4 pmos simple mirror",
        any(
            tag.devices_for("reference") == ("XM3",)
            and tag.devices_for("outputs") == ("XM4",)
            for tag in mirrors
        ),
    )
    check(
        "XM8 -> XM5, XM7 nmos multi-output mirror",
        any(
            tag.devices_for("reference") == ("XM8",)
            and set(tag.devices_for("outputs")) == {"XM5", "XM7"}
            for tag in mirrors
        ),
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
