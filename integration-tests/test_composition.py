from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Units are not installed; each one's tests name its siblings' source roots in
# its own pyproject, and integration tests reach across every unit, so they name
# all of them here.
for _unit in ("netlist-decomposition", "spice-canonical", "sidecar-edits"):
    sys.path.insert(0, str(ROOT / _unit / "src"))

import composition


DEVELOPMENT_STATE = re.compile(
    r"^\*\*Development state:\*\*\s*`([^`]+)`\s*$", re.MULTILINE
)


def walk_units(unit: composition.Unit):
    yield unit
    for child in unit.children:
        yield from walk_units(child)


def write_unit(
    root: Path,
    unit_id: str,
    *,
    children: tuple[str, ...] = (),
    test_command: tuple[str, ...] | None = None,
    docs: bool = False,
) -> None:
    root.mkdir(parents=True)
    (root / "ONTOLOME.md").write_text(f"# {unit_id}\n", encoding="utf-8")
    child_text = ", ".join(repr(child) for child in children)
    workflow = (
        f"\n[workflows]\ntest = {list(test_command)!r}\n" if test_command else ""
    )
    docs_contract = (
        '\n[docs]\nsource = "docs"\nindex = "index.md"\n' if docs else ""
    )
    (root / "unit.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "[unit]",
                f'id = "{unit_id}"',
                f'name = "{unit_id}"',
                'ontology = "ONTOLOME.md"',
                f"children = [{child_text}]",
                workflow,
                docs_contract,
            ]
        ),
        encoding="utf-8",
    )
    if docs:
        (root / "docs").mkdir()
        (root / "docs" / "index.md").write_text(
            f"# {unit_id}\n", encoding="utf-8"
        )


def test_discovery_is_deterministic_by_child_id(tmp_path: Path) -> None:
    write_unit(tmp_path / "root", "root", children=("z-dir", "a-dir"))
    write_unit(tmp_path / "root" / "z-dir", "bravo")
    write_unit(tmp_path / "root" / "a-dir", "alpha")

    unit = composition.load_unit(tmp_path / "root")

    assert [child.unit_id for child in unit.children] == ["alpha", "bravo"]
    assert composition.ontology_lines(unit) == [
        "root: ONTOLOME.md",
        "  alpha: ONTOLOME.md",
        "  bravo: ONTOLOME.md",
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


def test_a_declared_python_runs_under_the_composing_interpreter(tmp_path: Path) -> None:
    """`python` names an environment; the run must be the one composing."""

    recorded = tmp_path / "interpreter"
    write_unit(
        tmp_path / "root",
        "root",
        test_command=(
            "python",
            "-c",
            f"import sys; from pathlib import Path; "
            f"Path({str(recorded)!r}).write_text(sys.executable)",
        ),
    )

    assert composition.run_tests(composition.load_unit(tmp_path / "root")) == 0
    assert recorded.read_text() == sys.executable


def test_docs_stage_includes_nested_units_and_links_them(tmp_path: Path) -> None:
    root = tmp_path / "root"
    write_unit(root, "root", children=("parent",), docs=True)
    write_unit(
        root / "parent", "parent", children=("nested",), docs=True
    )
    write_unit(root / "parent" / "nested", "nested", docs=True)
    run_artifact = root / "parent" / "nested" / "docs" / "_runs" / "report.md"
    run_artifact.parent.mkdir()
    run_artifact.write_text("# Not documentation\n", encoding="utf-8")

    stage = tmp_path / "stage"
    composition.stage_docs(composition.load_unit(root), stage)

    assert (stage / "children" / "parent" / "docs" / "index.md").is_file()
    assert (stage / "children" / "nested" / "docs" / "index.md").is_file()
    assert not (stage / "children" / "nested" / "docs" / "_runs").exists()
    composed = (stage / "_composed-children.md").read_text(encoding="utf-8")
    assert "parent <children/parent/docs/index.md>" in composed
    assert "nested <children/nested/docs/index.md>" in composed


def test_staging_retargets_cross_unit_links_both_directions(tmp_path: Path) -> None:
    """A link authored where it resolves must still resolve where it is built.

    Staging moves a root page up out of `docs/` and a child page down into
    `children/<unit-id>/`, so the same relative link needs a different spelling
    in each tree. The authored one is the one that has to be right.
    """

    root = tmp_path / "root"
    write_unit(root, "root", children=("parent",), docs=True)
    write_unit(root / "parent", "parent", docs=True)
    (root / "docs" / "index.md").write_text(
        "# root\n\nSee [parent](../parent/docs/index.md#start).\n", encoding="utf-8"
    )
    (root / "parent" / "docs" / "index.md").write_text(
        "# parent\n\nBack to [root](../../docs/index.md).\n", encoding="utf-8"
    )

    stage = tmp_path / "stage"
    composition.stage_docs(composition.load_unit(root), stage)

    # Root page loses `docs/`; child page gains `children/parent/docs/`.
    assert "(children/parent/docs/index.md#start)" in (
        stage / "index.md"
    ).read_text(encoding="utf-8")
    assert "(../../../index.md)" in (
        stage / "children" / "parent" / "docs" / "index.md"
    ).read_text(encoding="utf-8")


def test_staging_moves_only_relative_links_to_staged_files(tmp_path: Path) -> None:
    """Everything that is not a relative link into a staged page is left alone.

    A link that is merely broken stays broken: the composer translates layouts,
    it does not invent targets, and a warning about a real dead link is worth
    keeping.
    """

    root = tmp_path / "root"
    write_unit(root, "root", children=("parent",), docs=True)
    write_unit(root / "parent", "parent", docs=True)
    (root / "docs" / "sibling.md").write_text("# sibling\n", encoding="utf-8")
    page = "\n".join(
        [
            "# root",
            "",
            "A [sibling](sibling.md) and an [anchor](#here) and a",
            "[url](https://example.invalid/parent/docs/index.md) and a",
            "[dead link](../parent/docs/missing.md).",
            "",
            "Prose about `[a link](../parent/docs/index.md)` stays prose.",
            "",
            "```markdown",
            "[fenced](../parent/docs/index.md)",
            "```",
            "",
            "But [`index.md`](../parent/docs/index.md) is a real link.",
            "",
        ]
    )
    (root / "docs" / "index.md").write_text(page, encoding="utf-8")

    stage = tmp_path / "stage"
    composition.stage_docs(composition.load_unit(root), stage)
    staged = (stage / "index.md").read_text(encoding="utf-8")

    assert "[sibling](sibling.md)" in staged
    assert "[anchor](#here)" in staged
    assert "[url](https://example.invalid/parent/docs/index.md)" in staged
    assert "[dead link](../parent/docs/missing.md)" in staged
    assert "`[a link](../parent/docs/index.md)`" in staged
    assert "[fenced](../parent/docs/index.md)" in staged
    # Code spans in the *text* of a link do not make it prose about a link.
    assert "[`index.md`](children/parent/docs/index.md)" in staged


def test_repository_tree_has_its_declared_units_and_no_root_src() -> None:
    unit = composition.load_unit(ROOT)

    # Sorted, not in declaration order: `hedloom` composes the three Hedloom units, and
    # the remaining three siblings supply real circuit work.
    assert [child.unit_id for child in unit.children] == [
        "hedloom",
        "netlist-decomposition",
        "sidecar-edits",
        "spice-canonical",
    ]
    hedloom = next(child for child in unit.children if child.unit_id == "hedloom")
    assert [child.unit_id for child in hedloom.children] == [
        "hedloom-exec",
        "hedloom-flow",
        "hedloom-run",
    ]
    assert not (ROOT / "src").exists()
    assert not (ROOT / "tests").exists()
    assert all(child.ontology.is_file() for child in unit.children)


def test_every_ontology_node_is_a_prototype_with_adjacent_agent_guidance() -> None:
    units = tuple(walk_units(composition.load_unit(ROOT)))

    for unit in units:
        ontology_text = unit.ontology.read_text(encoding="utf-8")
        match = DEVELOPMENT_STATE.search(ontology_text)
        assert match, f"{unit.ontology}: missing Development state marker"
        assert match.group(1) == "prototype", unit.ontology
        assert (unit.ontology.parent / "AGENTS.md").is_file(), unit.root


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
