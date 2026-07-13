from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from netlist_decomposition.dependencies import (  # noqa: E402
    BLOCK_RULE_DEPENDENCIES,
    EXTERNAL_INPUTS,
    default_output_path,
    pass_metadata,
    produced_passes,
    render_dependency_table,
)
from netlist_decomposition.engine import COMPOSITION_PASSES, KIND_LEVELS  # noqa: E402


def test_generated_dependency_table_is_current() -> None:
    assert default_output_path().read_text(encoding="utf-8") == render_dependency_table()


def test_dependency_catalog_is_closed_and_available_by_its_composition_pass() -> None:
    passes = pass_metadata()
    kind_passes = produced_passes()

    for rule in BLOCK_RULE_DEPENDENCIES:
        assert rule.dependencies
        assert rule.produces in KIND_LEVELS
        target_pass = passes[rule.composition_pass][0]
        for dependency in rule.dependencies:
            if dependency.kind in EXTERNAL_INPUTS:
                continue
            assert dependency.kind in KIND_LEVELS
            assert any(number <= target_pass for number in kind_passes[dependency.kind])


def test_catalog_uses_the_runtime_taxonomy_and_composition_passes() -> None:
    assert {rule.produces for rule in BLOCK_RULE_DEPENDENCIES} == set(KIND_LEVELS)
    assert set(pass_metadata()) == {item.name for item in COMPOSITION_PASSES}


def test_every_literal_block_kind_emitted_by_the_pipeline_is_cataloged() -> None:
    emitted = set()
    for relative in (
        "src/netlist_decomposition/engine.py",
        "src/netlist_decomposition/bias.py",
        "src/netlist_decomposition/hl2.py",
        "src/netlist_decomposition/stages.py",
    ):
        tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if (
                    keyword.arg == "kind"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    emitted.add(keyword.value.value)

    cataloged = {rule.produces for rule in BLOCK_RULE_DEPENDENCIES}
    assert emitted <= cataloged


def test_table_keeps_taxonomy_and_execution_dependencies_separate() -> None:
    rendered = render_dependency_table()

    assert "same HL" in rendered
    assert "HL1 → HL2" in rendered
    assert "HL2 → HL3" in rendered
    # Algorithm 2 has an upward taxonomy dependency resolved within pass 3.
    assert "HL4 → HL3" in rendered
    assert "same pass" in rendered
    assert "| 3 | `stages` | HL3, HL4 |" in rendered
