"""Structural functional-block tagging for canonical circuit netlists."""

from netlist_decomposition.engine import (
    DEFAULT_RULES,
    HL1_DIODE,
    HL1_NORMAL,
    BlockCandidate,
    BlockIndex,
    BlockTag,
    CircuitGraph,
    DecompositionEngine,
    FunctionRule,
    Rule,
    decompose,
    suppress_false_stacks,
    transistor_stack_rule,
)

__all__ = [
    "DEFAULT_RULES",
    "HL1_DIODE",
    "HL1_NORMAL",
    "BlockCandidate",
    "BlockIndex",
    "BlockTag",
    "CircuitGraph",
    "DecompositionEngine",
    "FunctionRule",
    "Rule",
    "decompose",
    "suppress_false_stacks",
    "transistor_stack_rule",
]
