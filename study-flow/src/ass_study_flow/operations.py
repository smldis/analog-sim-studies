"""Executor-facing wrappers that publish generic operation attempts."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from distributed import get_worker

from .artifacts import read_json, write_json
from .contracts import (
    ArtifactRef,
    AttemptRecord,
    FlowSpec,
    OperationContext,
    OperationSpec,
    PreparedFlow,
    WorkItemSpec,
    require_json_object,
    validate_operation_output,
)


OperationCallable = Callable[[OperationContext, dict[str, Any]], dict[str, Any]]


def _executor_address() -> str:
    try:
        return str(get_worker().address)
    except ValueError:
        return f"local-process://{os.getpid()}"


def read_artifact_payload(reference: ArtifactRef) -> dict[str, Any]:
    """Read and identity-check the JSON payload referenced by an artifact."""

    published = read_json(reference.path)
    if published.get("artifact", {}).get("artifact_id") != reference.artifact_id:
        raise ValueError(f"artifact identity mismatch: {reference.path}")
    payload = published.get("payload")
    require_json_object(payload, f"{reference.artifact_id} payload")
    return payload


def _record_attempt(attempt: AttemptRecord) -> None:
    write_json(
        attempt.record_path,
        {"kind": "attempt-record", "attempt": attempt},
    )


def _failed_attempt(
    *,
    prepared: PreparedFlow,
    invocation_id: str,
    attempt_id: str,
    executor_address: str,
    record_path: Path,
    inputs: tuple[ArtifactRef, ...],
    item_id: str | None,
    error: Exception,
) -> AttemptRecord:
    attempt = AttemptRecord(
        run_id=prepared.run_id,
        invocation_id=invocation_id,
        attempt_id=attempt_id,
        status="failed",
        executor_address=executor_address,
        record_path=record_path,
        inputs=inputs,
        outputs=(),
        item_id=item_id,
        diagnostic=f"{type(error).__name__}: {error}",
    )
    _record_attempt(attempt)
    return attempt


def execute_mapped_operation(
    prepared: PreparedFlow,
    item: WorkItemSpec,
    operation: OperationSpec,
    function: OperationCallable,
    previous: AttemptRecord | None,
) -> AttemptRecord:
    """Execute one bound map operation and publish its output and attempt."""

    invocation_id = f"{operation.operation_id}-{item.item_id}"
    attempt_id = uuid4().hex
    attempt_directory = (
        prepared.run_directory
        / "attempts"
        / item.item_id
        / operation.operation_id
        / attempt_id
    )
    record_path = attempt_directory / "attempt.json"
    executor_address = _executor_address()
    context = OperationContext(
        run_id=prepared.run_id,
        invocation_id=invocation_id,
        attempt_id=attempt_id,
        item_id=item.item_id,
        work_directory=attempt_directory,
        executor_address=executor_address,
    )
    attempt_directory.mkdir(parents=True)
    input_references = [prepared.spec_ref, prepared.shared_ref]
    try:
        shared = read_artifact_payload(prepared.shared_ref)[
            prepared.spec.preparation.output_ports[0]
        ]
        available: dict[str, Any] = {
            "shared": shared,
            "item": item.inputs,
        }
        if previous is not None:
            if previous.status != "succeeded" or len(previous.outputs) != 1:
                raise ValueError("previous operation did not publish one output")
            input_references.append(previous.outputs[0])
            available["previous"] = read_artifact_payload(previous.outputs[0])
        inputs = {port: available[port] for port in operation.input_ports}
        output = validate_operation_output(operation, function(context, inputs))
        output_ref = ArtifactRef(
            artifact_id=(
                f"{operation.operation_id}-{item.item_id}-output-{attempt_id[:12]}"
            ),
            kind="operation-output",
            path=attempt_directory / "output.json",
            producer_invocation_id=invocation_id,
            producer_attempt_id=attempt_id,
        )
        write_json(
            output_ref.path,
            {
                "kind": output_ref.kind,
                "artifact": output_ref,
                "payload": output,
            },
        )
    except Exception as exc:
        _failed_attempt(
            prepared=prepared,
            invocation_id=invocation_id,
            attempt_id=attempt_id,
            executor_address=executor_address,
            record_path=record_path,
            inputs=tuple(input_references),
            item_id=item.item_id,
            error=exc,
        )
        raise

    attempt = AttemptRecord(
        run_id=prepared.run_id,
        invocation_id=invocation_id,
        attempt_id=attempt_id,
        status="succeeded",
        executor_address=executor_address,
        record_path=record_path,
        inputs=tuple(input_references),
        outputs=(output_ref,),
        item_id=item.item_id,
    )
    _record_attempt(attempt)
    return attempt


def execute_reduction(
    prepared: PreparedFlow,
    operation: OperationSpec,
    function: OperationCallable,
    mapped_attempts: list[AttemptRecord],
) -> AttemptRecord:
    """Reduce the final mapped outputs through the same operation contract."""

    expected_items = tuple(item.item_id for item in prepared.spec.items)
    by_item = {attempt.item_id: attempt for attempt in mapped_attempts}
    if (
        len(mapped_attempts) != len(expected_items)
        or None in by_item
        or set(by_item) != set(expected_items)
    ):
        raise ValueError("mapped attempts do not match the authored work items")
    ordered = tuple(by_item[item_id] for item_id in expected_items)
    if any(attempt.status != "succeeded" for attempt in ordered):
        raise ValueError("cannot reduce unsuccessful mapped attempts")

    attempt_id = uuid4().hex
    attempt_directory = (
        prepared.run_directory
        / "attempts"
        / "reduce"
        / operation.operation_id
        / attempt_id
    )
    record_path = attempt_directory / "attempt.json"
    executor_address = _executor_address()
    context = OperationContext(
        run_id=prepared.run_id,
        invocation_id="reduce",
        attempt_id=attempt_id,
        item_id=None,
        work_directory=attempt_directory,
        executor_address=executor_address,
    )
    attempt_directory.mkdir(parents=True)
    mapped_refs = tuple(attempt.outputs[0] for attempt in ordered)
    input_references = (prepared.spec_ref, prepared.shared_ref, *mapped_refs)
    try:
        shared = read_artifact_payload(prepared.shared_ref)[
            prepared.spec.preparation.output_ports[0]
        ]
        available = {
            "shared": shared,
            "items": [item.inputs for item in prepared.spec.items],
            "mapped": [read_artifact_payload(reference) for reference in mapped_refs],
        }
        inputs = {port: available[port] for port in operation.input_ports}
        output = validate_operation_output(operation, function(context, inputs))
        output_ref = ArtifactRef(
            artifact_id="flow-result",
            kind="operation-output",
            path=prepared.run_directory / "result.json",
            producer_invocation_id="reduce",
            producer_attempt_id=attempt_id,
        )
        write_json(
            output_ref.path,
            {
                "kind": output_ref.kind,
                "artifact": output_ref,
                "payload": output,
            },
        )
    except Exception as exc:
        _failed_attempt(
            prepared=prepared,
            invocation_id="reduce",
            attempt_id=attempt_id,
            executor_address=executor_address,
            record_path=record_path,
            inputs=input_references,
            item_id=None,
            error=exc,
        )
        raise

    attempt = AttemptRecord(
        run_id=prepared.run_id,
        invocation_id="reduce",
        attempt_id=attempt_id,
        status="succeeded",
        executor_address=executor_address,
        record_path=record_path,
        inputs=input_references,
        outputs=(output_ref,),
    )
    _record_attempt(attempt)
    return attempt


def required_operation_ids(spec: FlowSpec) -> set[str]:
    """Return the operation bindings required after local preparation."""

    operation_ids = {
        operation.operation_id for operation in spec.map_operations
    }
    operation_ids.add(spec.reduction.operation_id)
    return operation_ids
