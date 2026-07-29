from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from spice_canonical import canonical_netlist  # noqa: E402


def test_ngspice_skips_title_control_block_and_semicolon_comments() -> None:
    netlist = canonical_netlist.from_text(
        "Rtitle would look like a resistor 1k\n"
        "V1 in 0 1 ; semicolon comment\n"
        ".control\n"
        "run\n"
        "Rcontrol must not become a device 2k\n"
        ".endc\n"
        "R1 in out 1k ; load\n"
        ".end\n",
        spice_format="ngspice",
    )

    assert netlist.diagnostics == ()
    assert [device.name for device in netlist.top.devices] == ["V1", "R1"]
    assert "semicolon" not in netlist.render()
    assert "Rcontrol" not in netlist.render()


def test_ngspice_resolves_parameterized_subcircuit_and_model_bins() -> None:
    netlist = canonical_netlist.from_text(
        "Parameterized inverter\n"
        ".model nch.1 nmos (level=54 lmin=0.1u lmax=1u)\n"
        ".model nch.2 nmos (level=54 lmin=1u lmax=10u)\n"
        ".subckt inv in out w=1u\n"
        "M1 out in 0 0 nch W={w} L=0.18u\n"
        ".ends inv\n"
        "X1 source load inv w=2u\n"
        ".end\n",
        spice_format="ngspice",
    )

    assert netlist.diagnostics == ()
    assert netlist.subcircuits[0].devices[0].type == "nmos"
    assert netlist.top.devices[0].connections == (
        canonical_netlist.Connection("in", "source"),
        canonical_netlist.Connection("out", "load"),
    )


def test_ngspice_does_not_treat_included_fragment_first_line_as_a_title(
    tmp_path: Path,
) -> None:
    child = tmp_path / "cell.inc"
    child.write_text(
        ".subckt FILTER IN OUT\n"
        "R1 IN OUT 1k\n"
        ".ends FILTER\n",
        encoding="utf-8",
    )
    top = tmp_path / "top.cir"
    top.write_text(
        "ngspice include example\n"
        ".include cell.inc\n"
        "X1 source load FILTER\n"
        ".end\n",
        encoding="utf-8",
    )

    netlist = canonical_netlist.from_file(top, spice_format="ngspice")

    assert netlist.diagnostics == ()
    assert [subckt.name for subckt in netlist.subcircuits] == ["FILTER"]
    assert netlist.top.devices[0].connections[0] == canonical_netlist.Connection(
        "IN", "source"
    )


def test_ngspice_mesfet_uses_named_terminals() -> None:
    netlist = canonical_netlist.from_text(
        "MESFET example\n"
        ".model zmod nmf (vto=-2 beta=1m)\n"
        "Z1 drain gate source zmod\n"
        ".end\n",
        spice_format="ngspice",
    )

    assert netlist.top.devices == (
        canonical_netlist.Device(
            name="Z1",
            type="nmf",
            connections=(
                canonical_netlist.Connection("d", "drain"),
                canonical_netlist.Connection("g", "gate"),
                canonical_netlist.Connection("s", "source"),
            ),
            parameters=(canonical_netlist.Parameter("model", "zmod"),),
        ),
    )


def test_ngspice_uniform_rc_line_uses_named_terminals() -> None:
    netlist = canonical_netlist.from_text(
        "Uniform RC line\n"
        ".model urcmod urc(rperl=1k cperl=1n)\n"
        "U1 input output 0 urcmod L=1\n"
        ".end\n",
        spice_format="ngspice",
    )

    device = netlist.top.devices[0]

    assert device.type == "urc"
    assert device.connections == (
        canonical_netlist.Connection("p", "input"),
        canonical_netlist.Connection("n", "output"),
        canonical_netlist.Connection("common", "0"),
    )


def test_unknown_spice_format_is_rejected() -> None:
    with pytest.raises(canonical_netlist.CanonicalParseError, match="unsupported SPICE"):
        canonical_netlist.from_text("title\n.end\n", spice_format="hspice")  # type: ignore[arg-type]


def test_cli_selects_ngspice_format(tmp_path: Path) -> None:
    input_path = tmp_path / "input.cir"
    output_path = tmp_path / "canonical.txt"
    input_path.write_text(
        "Rtitle is the title not a resistor 1k\n"
        "V1 in 0 1\n"
        ".end\n",
        encoding="utf-8",
    )

    result = canonical_netlist.main(
        [
            str(input_path),
            "--format",
            "ngspice",
            "--strict",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    rendered = output_path.read_text(encoding="utf-8")
    assert "V1 | vsource" in rendered
    assert "Rtitle" not in rendered


def test_cli_can_activate_device_type_normalization(tmp_path: Path) -> None:
    input_path = tmp_path / "input.cir"
    interfaces_path = tmp_path / "interfaces.json"
    types_path = tmp_path / "device_types.json"
    output_path = tmp_path / "canonical.txt"
    input_path.write_text(
        "normalization example\nX1 out gate 0 0 SKY_NMOS W=2\n.end\n",
        encoding="utf-8",
    )
    interfaces_path.write_text(
        '{"SKY_NMOS": ["d", "g", "s", "b"]}', encoding="utf-8"
    )
    types_path.write_text('{"sky_nmos": "nmos"}', encoding="utf-8")

    result = canonical_netlist.main(
        [
            str(input_path),
            "--format",
            "ngspice",
            "--external-subcircuits",
            str(interfaces_path),
            "--device-type-map",
            str(types_path),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert (
        "X1 | nmos | d=out, g=gate, s=0, b=0 | "
        "W=2, source_type=SKY_NMOS"
    ) in output_path.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice is not installed")
def test_ngspice_accepts_the_local_dialect_fixture(tmp_path: Path) -> None:
    input_path = tmp_path / "divider.cir"
    log_path = tmp_path / "ngspice.log"
    input_path.write_text(
        "ngspice voltage divider\n"
        "V1 in 0 1 ; source\n"
        "R1 in out 1k\n"
        "R2 out 0 2k\n"
        ".op\n"
        ".print dc v(out)\n"
        ".end\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["ngspice", "-b", "-o", str(log_path), str(input_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    canonical = canonical_netlist.from_file(input_path, spice_format="ngspice")

    assert result.returncode == 0, log_path.read_text(encoding="utf-8")
    assert canonical.diagnostics == ()
    assert [device.name for device in canonical.top.devices] == ["V1", "R1", "R2"]
