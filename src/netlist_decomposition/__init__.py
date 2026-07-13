"""Structural functional-block tagging for canonical circuit netlists."""

from netlist_decomposition.engine import (
    COMPOSITION_PASSES,
    DEFAULT_RULES,
    HL1_DIODE,
    HL1_NORMAL,
    KIND_LEVELS,
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
    CompositionPass,
    DecompositionEngine,
    FunctionRule,
    Rule,
    decompose,
    suppress_false_stacks,
    transistor_stack_rule,
)

__all__ = [
    "COMPOSITION_PASSES",
    "DEFAULT_RULES",
    "HL1_DIODE",
    "HL1_NORMAL",
    "KIND_LEVELS",
    "BlockCandidate",
    "BlockIndex",
    "BlockTag",
    "CircuitGraph",
    "CompositionPass",
    "DecompositionEngine",
    "FunctionRule",
    "Rule",
    "decompose",
    "suppress_false_stacks",
    "transistor_stack_rule",
]
