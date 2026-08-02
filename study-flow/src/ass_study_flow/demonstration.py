"""Domain-neutral operations for the two-item reference experiment."""

from __future__ import annotations

from typing import Any

from .contracts import FlowSpec, OperationContext, OperationSpec, WorkItemSpec
from .operations import OperationCallable


def combine_inputs(
    context: OperationContext,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Combine the shared and per-item JSON values without interpreting them."""

    return {
        "combined": {
            "item_id": context.item_id,
            "shared": inputs["shared"],
            "item": inputs["item"],
        }
    }


def describe_output(
    context: OperationContext,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Describe the preceding generic object as a second visible operation."""

    combined = inputs["previous"]["combined"]
    return {
        "description": {
            "item_id": context.item_id,
            "shared_fields": sorted(combined["shared"]),
            "item_fields": sorted(combined["item"]),
        }
    }


def collect_outputs(
    context: OperationContext,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Collect the two mapped descriptions without imposing domain evaluation."""

    descriptions = [output["description"] for output in inputs["mapped"]]
    return {
        "collection": {
            "count": len(descriptions),
            "items": descriptions,
        }
    }


def demonstration_spec() -> FlowSpec:
    """Return the generic shared-input, two-item map/reduce example."""

    return FlowSpec(
        flow_id="two-item-collection",
        shared_inputs={"scope": "shared-context"},
        items=(
            WorkItemSpec(item_id="alpha", inputs={"value": "first"}),
            WorkItemSpec(item_id="beta", inputs={"value": "second"}),
        ),
        preparation=OperationSpec(
            operation_id="materialize-shared-input",
            input_ports=("authored",),
            output_ports=("shared",),
        ),
        map_operations=(
            OperationSpec(
                operation_id="combine-inputs",
                input_ports=("shared", "item"),
                output_ports=("combined",),
            ),
            OperationSpec(
                operation_id="describe-output",
                input_ports=("previous",),
                output_ports=("description",),
            ),
        ),
        reduction=OperationSpec(
            operation_id="collect-outputs",
            input_ports=("mapped",),
            output_ports=("collection",),
        ),
    )


def demonstration_operations() -> dict[str, OperationCallable]:
    """Bind operation identities to ordinary Python functions for the demo."""

    return {
        "combine-inputs": combine_inputs,
        "describe-output": describe_output,
        "collect-outputs": collect_outputs,
    }
