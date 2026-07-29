from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import composition


def write_unit(
    root: Path,
    unit_id: str,
    *,
    children: tuple[str, ...] = (),
    test_command: tuple[str, ...] | None = None,
) -> None:
    root.mkdir(parents=True)
    (root / "ONTOLOGY.md").write_text(f"# {unit_id}\n", encoding="utf-8")
    child_text = ", ".join(repr(child) for child in children)
    workflow = (
        f"\n[workflows]\ntest = {list(test_command)!r}\n" if test_command else ""
    )
    (root / "unit.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "[unit]",
                f'id = "{unit_id}"',
                f'name = "{unit_id}"',
                'ontology = "ONTOLOGY.md"',
                f"children = [{child_text}]",
                workflow,
            ]
        ),
        encoding="utf-8",
    )


def test_discovery_is_deterministic_by_child_id(tmp_path: Path) -> None:
    write_unit(tmp_path / "root", "root", children=("z-dir", "a-dir"))
    write_unit(tmp_path / "root" / "z-dir", "bravo")
    write_unit(tmp_path / "root" / "a-dir", "alpha")

    unit = composition.load_unit(tmp_path / "root")

    assert [child.unit_id for child in unit.children] == ["alpha", "bravo"]
    assert composition.ontology_lines(unit) == [
        "root: ONTOLOGY.md",
        "  alpha: ONTOLOGY.md",
        "  bravo: ONTOLOGY.md",
    ]


def test_missing_child_declaration_fails_clearly(tmp_path: Path) -> None:
    write_unit(tmp_path / "root", "root", children=("missing",))

    with pytest.raises(composition.CompositionError, match="missing child directory"):
        composition.load_unit(tmp_path / "root")


def test_malformed_child_declaration_fails_clearly(tmp_path: Path) -> None:
    write_unit(tmp_path / "root", "root", children=("child",))
    (tmp_path / "root" / "child").mkdir()
    (tmp_path / "root" / "child" / "unit.toml").write_text(
        "this is not valid TOML = [", encoding="utf-8"
    )

    with pytest.raises(composition.CompositionError, match="malformed"):
        composition.load_unit(tmp_path / "root")


def test_child_command_failure_propagates_and_stops_parent(tmp_path: Path) -> None:
    marker = tmp_path / "parent-ran"
    write_unit(
        tmp_path / "root",
        "root",
        children=("child",),
        test_command=(
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).touch()",
        ),
    )
    write_unit(
        tmp_path / "root" / "child",
        "child",
        test_command=(sys.executable, "-c", "raise SystemExit(7)"),
    )

    assert composition.run_tests(composition.load_unit(tmp_path / "root")) == 7
    assert not marker.exists()


def test_repository_tree_has_three_direct_units_and_no_root_src() -> None:
    unit = composition.load_unit(ROOT)

    assert [child.unit_id for child in unit.children] == [
        "netlist-decomposition",
        "sidecar-edits",
        "spice-canonical",
    ]
    assert not (ROOT / "src").exists()
    assert not (ROOT / "tests").exists()
    assert all(child.ontology.is_file() for child in unit.children)


def test_netlist_decomposition_consumes_canonical_contract() -> None:
    from netlist_decomposition import decompose
    from spice_canonical.canonical_netlist import from_text

    netlist = from_text(
        """\
.subckt pair in_p in_n out vdd vss
M1 out in_p tail vss nch
M2 out in_n tail vss nch
.ends pair
""",
        top_name="pair",
    )

    assert callable(decompose)
    assert netlist.subcircuits[0].name == "pair"
