from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from spice_canonical import canonical_netlist  # noqa: E402


INVERTER_NETLIST = """\
* Common Eldo/SPICE inverter
.MODEL PCH PMOS LEVEL=1
.MODEL NCH NMOS LEVEL=1
.SUBCKT INV A Y VDD VSS PARAMS: WP=2u
M1 Y A VDD VDD PCH W=2u L=180n
M2 Y A VSS VSS NCH
+ W=1u L=180n $ continued instance parameters
.ENDS INV

VDD1 vdd 0 DC 1.8
VIN in 0 PULSE(0 1.8 0 1n 1n 5n 10n)
X1 in out vdd 0 INV
CL out 0 10f
"""


def test_render_inverter_with_named_subcircuit_pins() -> None:
    netlist = canonical_netlist.from_text(INVERTER_NETLIST)

    assert netlist.diagnostics == ()
    assert netlist.render() == (
        "TOP_LEVEL TOP\n"
        "\n"
        "NET_INCIDENT_TABLE TOP\n"
        "net | incident pins\n"
        "vdd | VDD1.p, X1.VDD\n"
        "0 | VDD1.n, VIN.n, X1.VSS, CL.n\n"
        "in | VIN.p, X1.A\n"
        "out | X1.Y, CL.p\n"
        "\n"
        "DEVICE_TABLE TOP\n"
        "name | type | connections | parameters\n"
        "VDD1 | vsource | p=vdd, n=0 | dc=1.8\n"
        "VIN | vsource | p=in, n=0 | waveform=PULSE(0 1.8 0 1n 1n 5n 10n)\n"
        "X1 | INV | A=in, Y=out, VDD=vdd, VSS=0 | \n"
        "CL | capacitor | p=out, n=0 | value=10f\n"
        "\n"
        "SUBCKT INV\n"
        "pin\n"
        "A\n"
        "Y\n"
        "VDD\n"
        "VSS\n"
        "\n"
        "NET_INCIDENT_TABLE INV\n"
        "net | incident pins\n"
        "A | M1.g, M2.g\n"
        "Y | M1.d, M2.d\n"
        "VDD | M1.s, M1.b\n"
        "VSS | M2.s, M2.b\n"
        "\n"
        "DEVICE_TABLE INV\n"
        "name | type | connections | parameters\n"
        "M1 | pmos | d=Y, g=A, s=VDD, b=VDD | model=PCH, W=2u, L=180n\n"
        "M2 | nmos | d=Y, g=A, s=VSS, b=VSS | model=NCH, W=1u, L=180n\n"
    )


def test_subcircuit_only_library_has_no_top_level_marker_or_tables() -> None:
    netlist = canonical_netlist.from_text(
        ".SUBCKT INV A Y\nR1 A Y 1k\n.ENDS INV\n"
    )

    rendered = netlist.render()

    assert not rendered.startswith("TOP_LEVEL")
    assert "NET_INCIDENT_TABLE TOP" not in rendered
    assert "DEVICE_TABLE TOP" not in rendered
    assert rendered.startswith("SUBCKT INV\npin\nA\nY\n")


def test_bus_names_keep_colon_for_ranges_only() -> None:
    netlist = canonical_netlist.from_text(
        ".SUBCKT REGISTER D<9:0> Q<9:0> CLK VDD VSS\n"
        "Rhold Q<9:0> VSS 10meg\n"
        ".ENDS REGISTER\n"
        "XREG DATA<9:0> RESULT<9:0> clk vdd 0 REGISTER\n"
    )

    rendered = netlist.render()

    assert "D<9:0>\nQ<9:0>\nCLK" in rendered
    assert (
        "XREG | REGISTER | D<9:0>=DATA<9:0>, Q<9:0>=RESULT<9:0>, "
        "CLK=clk, VDD=vdd, VSS=0 | "
    ) in rendered
    assert "DATA<9:0> | XREG.D<9:0>" in rendered
    assert "RESULT<9:0> | XREG.Q<9:0>" in rendered


def test_subcircuit_matching_is_case_insensitive_and_preserves_declared_names() -> None:
    netlist = canonical_netlist.from_text(
        ".subckt Buffer In Out\n"
        "R1 In Out 1k\n"
        ".ends buffer\n"
        "xbuf source load BUFFER\n"
    )

    device = netlist.top.devices[0]

    assert device.type == "Buffer"
    assert device.connections == (
        canonical_netlist.Connection("In", "source"),
        canonical_netlist.Connection("Out", "load"),
    )


def test_explicit_device_type_normalization_preserves_source_type() -> None:
    netlist = canonical_netlist.from_text(
        ".SUBCKT CELL d g s b\n"
        ".ENDS CELL\n"
        "X1 out bias 0 0 CELL W=2\n",
        device_type_map={"cell": "nmos"},
    )

    device = netlist.top.devices[0]
    assert device.type == "nmos"
    assert device.parameters == (
        canonical_netlist.Parameter("W", "2"),
        canonical_netlist.Parameter("source_type", "CELL"),
    )


def test_device_type_normalization_is_opt_in() -> None:
    netlist = canonical_netlist.from_text(
        ".SUBCKT CELL d g s b\n.ENDS CELL\nX1 out bias 0 0 CELL\n"
    )

    assert netlist.top.devices[0].type == "CELL"


def test_spaced_parameter_assignment_is_not_mistaken_for_a_subcircuit_pin() -> None:
    netlist = canonical_netlist.from_text(
        ".SUBCKT LOAD P N PARAMS: R = 1k\n"
        "R1 P N R ={R}\n"
        ".ENDS LOAD\n"
    )

    assert netlist.subcircuits[0].pins == ("P", "N")
    assert netlist.subcircuits[0].devices[0].parameters == (
        canonical_netlist.Parameter("R", "{R}"),
    )


def test_unconnected_subcircuit_pin_still_has_a_net_row() -> None:
    netlist = canonical_netlist.from_text(
        ".SUBCKT EMPTY A Y\n"
        ".ENDS EMPTY\n"
    )

    assert "A | \nY | \n\nDEVICE_TABLE EMPTY" in netlist.render()


def test_known_subcircuit_pin_count_mismatch_is_an_error() -> None:
    with pytest.raises(
        canonical_netlist.CanonicalParseError,
        match=r"X1 connects 1 nets.*INV.*2 pins",
    ):
        canonical_netlist.from_text(
            ".SUBCKT INV A Y\n"
            ".ENDS INV\n"
            "X1 in INV\n"
        )


def test_undefined_subcircuit_is_retained_with_a_diagnostic() -> None:
    netlist = canonical_netlist.from_text("X1 in out EXTERNAL gain=2\n")

    assert len(netlist.diagnostics) == 1
    assert "undefined subcircuit 'EXTERNAL'" in netlist.diagnostics[0].message
    assert (
        "X1 | EXTERNAL |  | unresolved_nets=in out, gain=2" in netlist.render()
    )


def test_unsupported_device_is_retained_without_inventing_connections() -> None:
    netlist = canonical_netlist.from_text("Z1 a b vendor_specific foo=1\n")

    assert netlist.top.devices == (
        canonical_netlist.Device(
            name="Z1",
            type="unresolved",
            connections=(),
            parameters=(
                canonical_netlist.Parameter("raw", "a b vendor_specific foo=1"),
            ),
        ),
    )
    assert "unsupported device prefix 'Z'" in netlist.diagnostics[0].message


def test_duplicate_device_names_are_rejected_case_insensitively() -> None:
    with pytest.raises(canonical_netlist.CanonicalParseError, match="repeats device"):
        canonical_netlist.from_text("R1 a b 1k\nr1 c d 2k\n")


def test_file_extraction_resolves_nested_includes_and_subcircuit_instances(
    tmp_path: Path,
) -> None:
    library = tmp_path / "cell library"
    library.mkdir()
    (library / "models.inc").write_text(
        ".MODEL PCH PMOS\n.MODEL NCH NMOS\n",
        encoding="utf-8",
    )
    (library / "inverter.inc").write_text(
        ".include models.inc\n"
        ".SUBCKT INV A Y VDD VSS\n"
        "M1 Y A VDD VDD PCH W=2u\n"
        "M2 Y A VSS VSS NCH W=1u\n"
        ".ENDS INV\n",
        encoding="utf-8",
    )
    top = tmp_path / "top.sp"
    top.write_text(
        "VDD1 vdd 0 1.8\n"
        '.INCLUDE "cell library/inverter.inc"\n'
        "X1 in out vdd 0 INV\n",
        encoding="utf-8",
    )

    netlist = canonical_netlist.from_file(top)

    assert netlist.diagnostics == ()
    assert [circuit.name for circuit in netlist.subcircuits] == ["INV"]
    assert netlist.top.devices[1].connections == (
        canonical_netlist.Connection("A", "in"),
        canonical_netlist.Connection("Y", "out"),
        canonical_netlist.Connection("VDD", "vdd"),
        canonical_netlist.Connection("VSS", "0"),
    )
    assert [device.type for device in netlist.subcircuits[0].devices] == [
        "pmos",
        "nmos",
    ]


def test_included_top_level_devices_are_concatenated_at_include_position(
    tmp_path: Path,
) -> None:
    fragment = tmp_path / "loads.inc"
    fragment.write_text("Cload out 0 2p\nRload out 0 10k\n", encoding="utf-8")
    top = tmp_path / "top.sp"
    top.write_text(
        "V1 out 0 1.2\n"
        ".inc loads.inc\n"
        "I1 out 0 DC 1u\n",
        encoding="utf-8",
    )

    netlist = canonical_netlist.from_file(top)

    assert [device.name for device in netlist.top.devices] == [
        "V1",
        "Cload",
        "Rload",
        "I1",
    ]
    assert "out | V1.p, Cload.p, Rload.p, I1.p" in netlist.render()


def test_missing_include_is_reported_but_available_circuit_is_still_rendered(
    tmp_path: Path,
) -> None:
    top = tmp_path / "top.sp"
    top.write_text(
        ".include missing.inc\nR1 in out 1k\n",
        encoding="utf-8",
    )

    netlist = canonical_netlist.from_file(top)

    assert [device.name for device in netlist.top.devices] == ["R1"]
    assert len(netlist.diagnostics) == 1
    assert netlist.diagnostics[0].source == top.resolve()
    assert "included file was not found" in netlist.diagnostics[0].message


def test_include_cycle_is_skipped_with_source_provenance(tmp_path: Path) -> None:
    first = tmp_path / "first.sp"
    second = tmp_path / "second.inc"
    first.write_text("R1 a b 1k\n.include second.inc\n", encoding="utf-8")
    second.write_text("C1 b 0 1p\n.include first.sp\n", encoding="utf-8")

    netlist = canonical_netlist.from_file(first)

    assert [device.name for device in netlist.top.devices] == ["R1", "C1"]
    assert len(netlist.diagnostics) == 1
    assert netlist.diagnostics[0].source == second.resolve()
    assert "include cycle skipped" in netlist.diagnostics[0].message


def test_include_boundary_uses_external_named_pin_signature(tmp_path: Path) -> None:
    models = tmp_path / "vendor-models.inc"
    models.write_text("Xinternal a b UNKNOWN\n", encoding="utf-8")
    top = tmp_path / "top.sp"
    top.write_text(
        ".include vendor-models.inc\nX1 out in 0 0 nch\n",
        encoding="utf-8",
    )

    netlist = canonical_netlist.from_file(
        top,
        stop_include=["vendor-*.inc"],
        external_subcircuits={"nch": ["d", "g", "s", "b"]},
    )

    assert netlist.diagnostics == ()
    assert [device.name for device in netlist.top.devices] == ["X1"]
    assert netlist.top.devices[0].connections == (
        canonical_netlist.Connection("d", "out"),
        canonical_netlist.Connection("g", "in"),
        canonical_netlist.Connection("s", "0"),
        canonical_netlist.Connection("b", "0"),
    )


def test_lib_directive_is_an_opaque_boundary(tmp_path: Path) -> None:
    top = tmp_path / "top.sp"
    top.write_text('.lib "models.lib" tt\nR1 a 0 1k\n', encoding="utf-8")

    netlist = canonical_netlist.from_file(top)

    assert netlist.diagnostics == ()
    assert [device.name for device in netlist.top.devices] == ["R1"]


def test_cli_writes_output_and_strict_mode_rejects_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_path = tmp_path / "input.sp"
    output_path = tmp_path / "canonical.txt"
    input_path.write_text(INVERTER_NETLIST, encoding="utf-8")

    result = canonical_netlist.main(
        [str(input_path), "--output", str(output_path), "--top-name", "CHIP"]
    )

    assert result == 0
    assert output_path.read_text(encoding="utf-8").startswith(
        "TOP_LEVEL CHIP\n\nNET_INCIDENT_TABLE CHIP\n"
    )
    assert capsys.readouterr().err == ""

    input_path.write_text("Z1 a b proprietary\n", encoding="utf-8")
    result = canonical_netlist.main([str(input_path), "--strict"])

    captured = capsys.readouterr()
    assert result == 2
    assert "warning: Z1: unsupported device prefix 'Z'" in captured.err
    assert captured.out == ""
