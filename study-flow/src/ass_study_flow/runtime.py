"""Submit the neutral map/reduce plan through Dask."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from distributed import Client, Future, LocalCluster

from .clusters import LsfClusterSettings, create_lsf_cluster
from .contracts import AttemptRecord, CompletedFlow, FlowSpec, PreparedFlow
from .demonstration import demonstration_operations, demonstration_spec
from .operations import (
    OperationCallable,
    execute_mapped_operation,
    execute_reduction,
    required_operation_ids,
)
from .planning import prepare_flow


@dataclass(frozen=True)
class DaskExecutionHandles:
    """Temporary Dask Futures kept outside the durable flow contracts."""

    prepared: PreparedFlow
    stages: tuple[tuple[Future, ...], ...]
    reduction: Future


def _validate_bindings(
    spec: FlowSpec,
    operations: Mapping[str, OperationCallable],
) -> None:
    missing = required_operation_ids(spec) - set(operations)
    if missing:
        raise ValueError(f"missing operation bindings: {sorted(missing)}")


def submit_prepared(
    client: Client,
    prepared: PreparedFlow,
    operations: Mapping[str, OperationCallable],
) -> DaskExecutionHandles:
    """Map the operation chain over every item and submit one reduction."""

    _validate_bindings(prepared.spec, operations)
    items = list(prepared.spec.items)
    previous: list[Future | None] = [None] * len(items)
    stages: list[tuple[Future, ...]] = []
    for operation in prepared.spec.map_operations:
        futures = tuple(
            client.map(
                execute_mapped_operation,
                [prepared] * len(items),
                items,
                [operation] * len(items),
                [operations[operation.operation_id]] * len(items),
                previous,
                key=f"{prepared.run_id}-{operation.operation_id}",
                pure=False,
            )
        )
        stages.append(futures)
        previous = list(futures)

    reduction = client.submit(
        execute_reduction,
        prepared,
        prepared.spec.reduction,
        operations[prepared.spec.reduction.operation_id],
        previous,
        key=f"{prepared.run_id}-{prepared.spec.reduction.operation_id}",
        pure=False,
    )
    return DaskExecutionHandles(
        prepared=prepared,
        stages=tuple(stages),
        reduction=reduction,
    )


def complete(handles: DaskExecutionHandles) -> CompletedFlow:
    """Resolve temporary Futures and return only durable records and artifacts."""

    reduction: AttemptRecord = handles.reduction.result()
    mapped_by_id = {
        attempt.invocation_id: attempt
        for attempt in (
            future.result() for stage in handles.stages for future in stage
        )
    }
    mapped = tuple(
        mapped_by_id[f"{operation.operation_id}-{item.item_id}"]
        for item in handles.prepared.spec.items
        for operation in handles.prepared.spec.map_operations
    )
    if len(reduction.outputs) != 1:
        raise ValueError("reduction did not publish exactly one flow result")
    return CompletedFlow(
        prepared=handles.prepared,
        attempts=(handles.prepared.preparation_attempt, *mapped, reduction),
        result=reduction.outputs[0],
    )


def run_local_flow(
    output_root: Path,
    spec: FlowSpec,
    operations: Mapping[str, OperationCallable],
) -> CompletedFlow:
    """Run a prepared flow with two local threaded Dask workers."""

    prepared = prepare_flow(spec, output_root)
    with LocalCluster(
        n_workers=2,
        threads_per_worker=1,
        processes=False,
        scheduler_port=0,
        dashboard_address=None,
    ) as cluster:
        with Client(cluster) as client:
            return complete(submit_prepared(client, prepared, operations))


def run_local_demo(output_root: Path) -> CompletedFlow:
    """Run the domain-neutral reference bindings on a local cluster."""

    return run_local_flow(
        output_root,
        demonstration_spec(),
        demonstration_operations(),
    )


def run_lsf_flow(
    output_root: Path,
    settings: LsfClusterSettings,
    spec: FlowSpec,
    operations: Mapping[str, OperationCallable],
) -> CompletedFlow:
    """Run the same neutral contract on Dask workers allocated through LSF."""

    prepared = prepare_flow(spec, output_root)
    if settings.shared_temp_directory is None:
        shared_temp_directory = prepared.run_directory / ".dask-control"
        shared_temp_directory.mkdir(mode=0o700)
        settings = replace(
            settings, shared_temp_directory=str(shared_temp_directory)
        )
    else:
        Path(settings.shared_temp_directory).mkdir(parents=True, exist_ok=True)

    cluster = create_lsf_cluster(settings)
    try:
        (prepared.run_directory / "lsf-worker-job.sh").write_text(
            cluster.job_script(), encoding="utf-8"
        )
        cluster.scale(jobs=settings.worker_jobs)
        with cluster.get_client() as client:
            return complete(submit_prepared(client, prepared, operations))
    finally:
        cluster.close()


def run_lsf_demo(
    output_root: Path,
    settings: LsfClusterSettings,
) -> CompletedFlow:
    """Run the domain-neutral reference bindings through Dask Jobqueue."""

    return run_lsf_flow(
        output_root,
        settings,
        demonstration_spec(),
        demonstration_operations(),
    )
