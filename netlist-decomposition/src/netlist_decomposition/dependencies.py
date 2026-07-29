"""Machine-readable functional-block dependency catalog.

Hierarchy levels are tagging sets (the taxonomy in Abel et al. Figure 15),
whereas composition passes describe recognition order (Section 7).  The catalog
keeps those axes separate and is the source for the generated Markdown table.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from netlist_decomposition.engine import COMPOSITION_PASSES, KIND_LEVELS


EXTERNAL_INPUTS = {
    "canonical_device": "Canonical devices and their named terminal nets",
    "declared_supply_nets": "Caller-declared VDD and VSS net sets",
}


@dataclass(frozen=True)
class Dependency:
    kind: str
    use: str


@dataclass(frozen=True)
class BlockRuleDependency:
    """One producer, assigned to a composition pass and tagging-set kind."""

    rule: str
    produces: str
    composition_pass: str
    implementation: str
    dependencies: tuple[Dependency, ...]
    status: str = "exact"


def _rule(
    rule: str,
    produces: str,
    composition_pass: str,
    implementation: str,
    *dependencies: tuple[str, str],
    status: str = "exact",
) -> BlockRuleDependency:
    return BlockRuleDependency(
        rule,
        produces,
        composition_pass,
        implementation,
        tuple(Dependency(*item) for item in dependencies),
        status,
    )


BLOCK_RULE_DEPENDENCIES = (
    _rule(
        "Normal transistor (Eq. 7)", "normal_transistor", "classify",
        "engine._hl1_transistors",
        ("canonical_device", "classify distinct drain, gate, and source nets"),
    ),
    _rule(
        "Diode transistor (Eq. 8)", "diode_transistor", "classify",
        "engine._hl1_transistors",
        ("canonical_device", "classify the drain-gate self-connection"),
    ),
    _rule(
        "Transistor stack (Eq. 9)", "transistor_stack", "structure",
        "engine.transistor_stack_rule",
        ("normal_transistor", "eligible stack member"),
        ("diode_transistor", "eligible stack member"),
    ),
    _rule(
        "Differential-pair candidate", "differential_pair_candidate", "structure",
        "engine._differential_pairs",
        ("canonical_device", "legacy source-coupled structural match"),
        status="candidate",
    ),
    _rule(
        "CMOS inverter candidate", "cmos_inverter", "structure",
        "engine._cmos_inverters",
        ("canonical_device", "legacy common-gate/common-drain match"),
        status="candidate",
    ),
    _rule(
        "Voltage bias (Algorithm 1)", "voltage_bias", "structure",
        "bias.resolve_bias_blocks",
        ("transistor_stack", "candidate voltage-producing stack"),
        ("current_bias", "same-pass fixed-point partner"),
    ),
    _rule(
        "Current bias (Algorithm 1)", "current_bias", "structure",
        "bias.resolve_bias_blocks",
        ("transistor_stack", "candidate current-producing stack"),
        ("voltage_bias", "same-pass fixed-point partner"),
    ),
    _rule(
        "Current mirror (Eq. 12)", "current_mirror", "structure",
        "bias.resolve_bias_blocks",
        ("voltage_bias", "reference branch"),
        ("current_bias", "one output branch"),
    ),
    _rule(
        "Differential pair (Eq. 13)", "differential_pair", "structure",
        "hl2._differential_pairs",
        ("normal_transistor", "two source-coupled input devices"),
        ("current_bias", "tail-bias connection"),
    ),
    _rule(
        "Gate-connected couple (Eq. 14)", "gate_connected_couple", "structure",
        "hl2._cascode_pairs",
        ("normal_transistor", "gate-connected upper devices"),
        ("differential_pair", "emitted as a cascode-pair constituent"),
    ),
    _rule(
        "Cascode differential pair (Eq. 15-17)", "cascode_differential_pair",
        "structure", "hl2._cascode_pairs",
        ("differential_pair", "lower differential pair"),
        ("gate_connected_couple", "upper gate-connected couple"),
    ),
    _rule(
        "Analog inverter (Eq. 18)", "analog_inverter", "structure",
        "hl2._analog_inverters",
        ("transistor_stack", "opposite-polarity all-normal halves"),
        ("differential_pair", "exclude false pair-crossing stacks"),
        ("declared_supply_nets", "verify each stack source rail"),
    ),
    _rule(
        "Source follower", "source_follower", "structure",
        "hl2._source_followers",
        ("normal_transistor", "common-drain signal device"),
        ("current_bias", "output-node bias"),
        ("declared_supply_nets", "verify the two rail connections"),
        status="extension",
    ),
    _rule(
        "Non-inverting transconductance (Eq. 20-22)", "transconductance", "stages",
        "stages._transconductances",
        ("differential_pair", "simple, complementary, or CMFB unit"),
        ("cascode_differential_pair", "optional cascoded unit"),
    ),
    _rule(
        "Inverting transconductance (Eq. 23)", "transconductance", "stages",
        "stages._inverting_stages",
        ("analog_inverter", "select the signal-side stack"),
        ("amplification_stage", "preceding-stage output drives its gate"),
        ("current_bias", "opposite inverter half biases the output"),
    ),
    _rule(
        "Load (Algorithm 3)", "load", "stages", "stages._load",
        ("transconductance", "defines searched output nets"),
        ("transistor_stack", "load-part candidates"),
        ("declared_supply_nets", "recognize rail-connected load parts"),
    ),
    _rule(
        "Current-output stage bias (Eq. 28-29)", "stage_bias", "stages",
        "stages._stage_bias",
        ("transconductance", "defines the biased source nets"),
        ("current_bias", "current-output bias branches"),
    ),
    _rule(
        "Voltage-output stage bias (Eq. 27)", "stage_bias", "stages",
        "stages._symmetric_stage",
        ("transconductance", "defines the biased output"),
        ("voltage_bias", "single voltage-output bias"),
        ("amplification_stage", "resolved inside the stage loop"),
    ),
    _rule(
        "Follower voltage-output stage bias", "stage_bias", "stages",
        "stages._follower_stages",
        ("source_follower", "defines the buffered output net"),
        ("current_bias", "voltage-output bias branch"),
        status="extension",
    ),
    _rule(
        "Source-follower stage", "source_follower_stage", "stages",
        "stages._follower_stages",
        ("source_follower", "voltage-buffer signal block"),
        ("stage_bias", "voltage-output stage bias"),
        status="extension",
    ),
    _rule(
        "Non-inverting amplification stage (Eq. 30-33)", "amplification_stage",
        "stages", "stages._noninverting_stages",
        ("transconductance", "non-inverting signal block"),
        ("load", "current-to-voltage load"),
        ("stage_bias", "current-output stage bias"),
    ),
    _rule(
        "Current-biased inverting stage (Eq. 34-35)", "amplification_stage",
        "stages", "stages._inverting_stages",
        ("analog_inverter", "candidate stage structure"),
        ("amplification_stage", "preceding stage and fixed-point chain"),
        ("transconductance", "inverting signal block emitted in-loop"),
        ("stage_bias", "current-output bias emitted in-loop"),
    ),
    _rule(
        "Symmetrical-OTA inverting stage (Eq. 36)", "amplification_stage",
        "stages", "stages._symmetric_stage",
        ("amplification_stage", "known first and current-biased stages"),
        ("transistor_stack", "fresh all-normal signal stack"),
        ("voltage_bias", "load and voltage-output bias structures"),
        ("transconductance", "inverting signal block emitted in-loop"),
        ("stage_bias", "voltage-output bias emitted in-loop"),
    ),
    _rule(
        "Circuit bias (Eq. 37)", "circuit_bias", "stages", "stages._circuit_bias",
        ("voltage_bias", "unclaimed voltage-bias branches"),
        ("current_bias", "unclaimed current-bias branches"),
        ("amplification_stage", "exclude stage-owned biases"),
        ("source_follower_stage", "exclude follower-owned biases"),
    ),
    _rule(
        "Compensation capacitor (Eq. 38)", "compensation_capacitor", "stages",
        "stages._capacitors",
        ("canonical_device", "capacitor terminals"),
        ("amplification_stage", "two distinct stage outputs"),
    ),
    _rule(
        "Load capacitor (Eq. 39)", "load_capacitor", "stages",
        "stages._capacitors",
        ("canonical_device", "capacitor terminals"),
        ("amplification_stage", "highest-stage output"),
        ("declared_supply_nets", "ground terminal"),
    ),
)


def pass_metadata() -> dict[str, tuple[int, tuple[int, ...]]]:
    return {
        item.name: (item.number, item.completes) for item in COMPOSITION_PASSES
    }


def produced_passes(
    rules: Iterable[BlockRuleDependency] = BLOCK_RULE_DEPENDENCIES,
) -> dict[str, frozenset[int]]:
    passes = pass_metadata()
    result: dict[str, set[int]] = {}
    for rule in rules:
        result.setdefault(rule.produces, set()).add(passes[rule.composition_pass][0])
    return {kind: frozenset(numbers) for kind, numbers in result.items()}


def taxonomy_scope(dependency: str, produced: str) -> str:
    if dependency in EXTERNAL_INPUTS:
        return "external input"
    source, target = KIND_LEVELS[dependency], KIND_LEVELS[produced]
    return "same HL" if source == target else f"HL{source} → HL{target}"


def execution_scope(
    dependency: str,
    target_pass: int,
    kind_passes: dict[str, frozenset[int]],
) -> str:
    if dependency in EXTERNAL_INPUTS:
        return "external input"
    sources = kind_passes[dependency]
    if target_pass in sources:
        return "same pass"
    earlier = max(number for number in sources if number < target_pass)
    return f"pass {earlier} → {target_pass}"


def render_dependency_table(
    rules: Iterable[BlockRuleDependency] = BLOCK_RULE_DEPENDENCIES,
) -> str:
    rules = tuple(rules)
    passes = pass_metadata()
    kind_passes = produced_passes(rules)
    lines = [
        "# Functional Decomposition Rule Dependencies",
        "",
        "<!-- Generated by scripts/generate_decomposition_dependencies.py; do not edit by hand. -->",
        "",
        "This is the Markdown-table counterpart of Figure 15 in Abel et al. (2021).",
        "Hierarchy level is block taxonomy; composition pass is recognition order.",
        "A same-pass cycle records the bidirectional/fixed-point dependencies that",
        "prevent the paper's dependency graph from being a simple DAG.",
        "",
        "| Tag HL | Pass | Pass completes | Produced block | Recognition rule | Depends on | Taxonomy edge | Execution edge | Use | Status | Implementation |",
        "|---:|---:|---|---|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(
        rules,
        key=lambda item: (
            passes[item.composition_pass][0], KIND_LEVELS[item.produces],
            item.produces, item.rule,
        ),
    )
    for rule in ordered:
        pass_number, completes = passes[rule.composition_pass]
        for dependency in rule.dependencies:
            lines.append(
                "| " + " | ".join((
                    str(KIND_LEVELS[rule.produces]),
                    str(pass_number),
                    ", ".join(f"HL{level}" for level in completes),
                    f"`{rule.produces}`",
                    rule.rule,
                    f"`{dependency.kind}`",
                    taxonomy_scope(dependency.kind, rule.produces),
                    execution_scope(dependency.kind, pass_number, kind_passes),
                    dependency.use,
                    rule.status,
                    f"`{rule.implementation}`",
                )) + " |"
            )
    lines += [
        "", "## Composition passes", "",
        "| Pass | Name | Completes tagging sets |", "|---:|---|---|",
        *(
            f"| {item.number} | `{item.name}` | "
            + ", ".join(f"HL{level}" for level in item.completes) + " |"
            for item in COMPOSITION_PASSES
        ),
        "", "## External inputs", "", "| Input | Meaning |", "|---|---|",
        *(f"| `{name}` | {meaning} |" for name, meaning in EXTERNAL_INPUTS.items()),
        "",
    ]
    return "\n".join(lines)


def default_output_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "design"
        / "functional-decomposition-dependencies.md"
    )
