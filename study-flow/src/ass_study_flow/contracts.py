"""Domain-neutral contracts for the bounded map/reduce experiment."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_STABLE_ID = re.compile(r"^[a-z][a-z0-9-]*$")
_ATTEMPT_STATES = {"succeeded", "failed"}


def _require_stable_id(value: str, label: str) -> None:
    if not _STABLE_ID.fullmatch(value):
        raise ValueError(f"{label} must be a stable kebab-case identifier")


def _require_unique(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def require_json_object(value: Any, label: str) -> None:
    """Require a JSON object with finite numbers and string object keys."""

    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain JSON-compatible values") from exc


@dataclass(frozen=True)
class OperationSpec:
    """An engine-neutral operation identity and its visible port contract."""

    operation_id: str
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_stable_id(self.operation_id, "operation_id")
        if not self.output_ports:
            raise ValueError("an operation must declare at least one output port")
        for port in (*self.input_ports, *self.output_ports):
            _require_stable_id(port, "port")
        _require_unique(self.input_ports, "input ports")
        _require_unique(self.output_ports, "output ports")


@dataclass(frozen=True)
class WorkItemSpec:
    """One item mapped through the operation chain."""

    item_id: str
    inputs: dict[str, Any]

    def __post_init__(self) -> None:
        _require_stable_id(self.item_id, "item_id")
        require_json_object(self.inputs, "work item inputs")


@dataclass(frozen=True)
class FlowSpec:
    """Authored input for the bounded shared-input/map/reduce shape."""

    flow_id: str
    shared_inputs: dict[str, Any]
    items: tuple[WorkItemSpec, ...]
    preparation: OperationSpec
    map_operations: tuple[OperationSpec, ...]
    reduction: OperationSpec

    def __post_init__(self) -> None:
        _require_stable_id(self.flow_id, "flow_id")
        require_json_object(self.shared_inputs, "shared inputs")
        if not self.items:
            raise ValueError("at least one work item is required")
        if not self.map_operations:
            raise ValueError("at least one mapped operation is required")
        _require_unique(tuple(item.item_id for item in self.items), "item identifiers")
        operations = (self.preparation, *self.map_operations, self.reduction)
        _require_unique(
            tuple(operation.operation_id for operation in operations),
            "operation identifiers",
        )
        if self.preparation.input_ports != ("authored",):
            raise ValueError("preparation must consume the authored port")
        if self.preparation.output_ports != ("shared",):
            raise ValueError("preparation must publish the shared port")
        map_ports = {"shared", "item", "previous"}
        for index, operation in enumerate(self.map_operations):
            unsupported = set(operation.input_ports) - map_ports
            if unsupported:
                raise ValueError(
                    f"unsupported mapped input ports: {sorted(unsupported)}"
                )
            if index == 0 and "previous" in operation.input_ports:
                raise ValueError("the first mapped operation has no previous output")
            if index > 0 and "previous" not in operation.input_ports:
                raise ValueError("later mapped operations must consume previous")
        reduction_ports = {"shared", "items", "mapped"}
        unsupported = set(self.reduction.input_ports) - reduction_ports
        if unsupported:
            raise ValueError(
                f"unsupported reduction input ports: {sorted(unsupported)}"
            )
        if "mapped" not in self.reduction.input_ports:
            raise ValueError("reduction must consume mapped outputs")


@dataclass(frozen=True)
class PortBinding:
    """A resolved input port and the plan source that supplies it."""

    port: str
    source: str

    def __post_init__(self) -> None:
        _require_stable_id(self.port, "bound port")
        if not self.source:
            raise ValueError("port binding source must not be empty")


@dataclass(frozen=True)
class InvocationSpec:
    """One resolved operation in the inspectable derived plan."""

    invocation_id: str
    operation_id: str
    execution_role: str
    depends_on: tuple[str, ...]
    inputs: tuple[PortBinding, ...]
    outputs: tuple[str, ...]
    item_id: str | None = None

    def __post_init__(self) -> None:
        _require_stable_id(self.invocation_id, "invocation_id")
        _require_stable_id(self.operation_id, "operation_id")
        if self.item_id is not None:
            _require_stable_id(self.item_id, "item_id")


@dataclass(frozen=True)
class ArtifactRef:
    """Portable identity and retrieval information for one JSON artifact."""

    artifact_id: str
    kind: str
    path: Path
    media_type: str = "application/json"
    producer_invocation_id: str | None = None
    producer_attempt_id: str | None = None

    def __post_init__(self) -> None:
        _require_stable_id(self.artifact_id, "artifact_id")
        _require_stable_id(self.kind, "artifact kind")
        if self.producer_invocation_id is not None:
            _require_stable_id(
                self.producer_invocation_id, "producer_invocation_id"
            )


@dataclass(frozen=True)
class OperationContext:
    """Execution context supplied to a bound operation function."""

    run_id: str
    invocation_id: str
    attempt_id: str
    item_id: str | None
    work_directory: Path
    executor_address: str


@dataclass(frozen=True)
class AttemptRecord:
    """Append-only fact about trying one resolved invocation."""

    run_id: str
    invocation_id: str
    attempt_id: str
    status: str
    executor_address: str
    record_path: Path
    inputs: tuple[ArtifactRef, ...]
    outputs: tuple[ArtifactRef, ...]
    item_id: str | None = None
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        _require_stable_id(self.run_id, "run_id")
        _require_stable_id(self.invocation_id, "invocation_id")
        if self.status not in _ATTEMPT_STATES:
            raise ValueError(f"unsupported attempt status: {self.status}")


@dataclass(frozen=True)
class PreparedFlow:
    """The materialized plan and local dependency supplied to the executor."""

    run_id: str
    run_directory: Path
    spec: FlowSpec
    spec_ref: ArtifactRef
    plan_ref: ArtifactRef
    manifest_ref: ArtifactRef
    shared_ref: ArtifactRef
    preparation_attempt: AttemptRecord


@dataclass(frozen=True)
class CompletedFlow:
    """Durable references returned after all temporary executor handles resolve."""

    prepared: PreparedFlow
    attempts: tuple[AttemptRecord, ...]
    result: ArtifactRef


def validate_operation_output(
    operation: OperationSpec,
    value: Any,
) -> dict[str, Any]:
    """Validate a bound operation's JSON output against its declared ports."""

    require_json_object(value, f"{operation.operation_id} output")
    expected = set(operation.output_ports)
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{operation.operation_id} output ports do not match: "
            f"expected {sorted(expected)}, got {sorted(actual)}"
        )
    return value
