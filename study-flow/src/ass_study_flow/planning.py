"""Materialize a neutral plan and run its sole controller-side dependency."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from .artifacts import write_json
from .contracts import (
    ArtifactRef,
    AttemptRecord,
    FlowSpec,
    InvocationSpec,
    PortBinding,
    PreparedFlow,
    _require_stable_id,
)


def _plan_nodes(spec: FlowSpec) -> tuple[InvocationSpec, ...]:
    nodes: list[InvocationSpec] = [
        InvocationSpec(
            invocation_id="prepare",
            operation_id=spec.preparation.operation_id,
            execution_role="local-controller",
            depends_on=(),
            inputs=tuple(
                PortBinding(port=port, source="flow-spec:shared-inputs")
                for port in spec.preparation.input_ports
            ),
            outputs=spec.preparation.output_ports,
        )
    ]
    final_item_nodes: list[InvocationSpec] = []
    for item in spec.items:
        previous = nodes[0]
        for index, operation in enumerate(spec.map_operations):
            invocation_id = f"{operation.operation_id}-{item.item_id}"
            sources = {
                "shared": "prepare:shared",
                "item": f"flow-spec:items.{item.item_id}",
                "previous": f"{previous.invocation_id}:outputs",
            }
            node = InvocationSpec(
                invocation_id=invocation_id,
                operation_id=operation.operation_id,
                execution_role="mapped-worker",
                depends_on=(previous.invocation_id,),
                inputs=tuple(
                    PortBinding(port=port, source=sources[port])
                    for port in operation.input_ports
                ),
                outputs=operation.output_ports,
                item_id=item.item_id,
            )
            if index == 0:
                node = InvocationSpec(
                    invocation_id=node.invocation_id,
                    operation_id=node.operation_id,
                    execution_role=node.execution_role,
                    depends_on=("prepare",),
                    inputs=node.inputs,
                    outputs=node.outputs,
                    item_id=node.item_id,
                )
            nodes.append(node)
            previous = node
        final_item_nodes.append(previous)

    reducer_sources = {
        "shared": "prepare:shared",
        "items": "flow-spec:items",
        "mapped": ",".join(
            f"{node.invocation_id}:outputs" for node in final_item_nodes
        ),
    }
    nodes.append(
        InvocationSpec(
            invocation_id="reduce",
            operation_id=spec.reduction.operation_id,
            execution_role="reduction-worker",
            depends_on=tuple(node.invocation_id for node in final_item_nodes),
            inputs=tuple(
                PortBinding(port=port, source=reducer_sources[port])
                for port in spec.reduction.input_ports
            ),
            outputs=spec.reduction.output_ports,
        )
    )
    return tuple(nodes)


def prepare_flow(
    spec: FlowSpec,
    output_root: Path,
    *,
    run_id: str | None = None,
) -> PreparedFlow:
    """Materialize the plan, then publish and record its local dependency."""

    resolved_run_id = run_id or f"{spec.flow_id}-{uuid4().hex[:12]}"
    _require_stable_id(resolved_run_id, "run_id")
    run_directory = (output_root / resolved_run_id).resolve()
    try:
        run_directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(f"run already exists: {run_directory}") from exc

    spec_path = write_json(
        run_directory / "flow-spec.json",
        {"kind": "flow-spec", "spec": spec},
    )
    spec_ref = ArtifactRef(
        artifact_id="flow-spec",
        kind="authored-input",
        path=spec_path,
    )
    plan_path = write_json(
        run_directory / "plan.json",
        {
            "kind": "derived-plan",
            "run_id": resolved_run_id,
            "source": spec_ref,
            "invocations": _plan_nodes(spec),
            "note": (
                "Operation identity and dependencies are engine-neutral; "
                "execution roles are placement constraints, not domain meaning."
            ),
        },
    )
    plan_ref = ArtifactRef(
        artifact_id="derived-plan",
        kind="derived-plan",
        path=plan_path,
        producer_invocation_id="derive-plan",
    )

    attempt_id = uuid4().hex
    attempt_directory = run_directory / "attempts" / "prepare" / attempt_id
    shared_ref = ArtifactRef(
        artifact_id="shared-input",
        kind="operation-output",
        path=run_directory / "shared-input.json",
        producer_invocation_id="prepare",
        producer_attempt_id=attempt_id,
    )
    write_json(
        shared_ref.path,
        {
            "kind": shared_ref.kind,
            "artifact": shared_ref,
            "payload": {spec.preparation.output_ports[0]: spec.shared_inputs},
        },
    )
    preparation_attempt = AttemptRecord(
        run_id=resolved_run_id,
        invocation_id="prepare",
        attempt_id=attempt_id,
        status="succeeded",
        executor_address=f"local-process://{os.getpid()}",
        record_path=attempt_directory / "attempt.json",
        inputs=(spec_ref,),
        outputs=(shared_ref,),
    )
    write_json(
        preparation_attempt.record_path,
        {"kind": "attempt-record", "attempt": preparation_attempt},
    )

    manifest_path = run_directory / "prepared.json"
    manifest_ref = ArtifactRef(
        artifact_id="prepared-flow",
        kind="prepared-manifest",
        path=manifest_path,
        producer_invocation_id="prepare",
        producer_attempt_id=attempt_id,
    )
    write_json(
        manifest_path,
        {
            "kind": manifest_ref.kind,
            "run_id": resolved_run_id,
            "source": spec_ref,
            "plan": plan_ref,
            "shared_input": shared_ref,
            "preparation_attempt": preparation_attempt.record_path,
        },
    )
    return PreparedFlow(
        run_id=resolved_run_id,
        run_directory=run_directory,
        spec=spec,
        spec_ref=spec_ref,
        plan_ref=plan_ref,
        manifest_ref=manifest_ref,
        shared_ref=shared_ref,
        preparation_attempt=preparation_attempt,
    )
