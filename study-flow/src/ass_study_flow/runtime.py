"""Submit and complete the bounded flow through Dask."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from distributed import Client, Future, LocalCluster

from .clusters import LsfClusterSettings, create_lsf_cluster
from .contracts import PreparedStudy, StudySpec, StudySummary, demonstration_spec
from .operations import (
    measure_placeholder,
    reduce_measurements,
    simulate_placeholder,
)
from .planning import prepare_study


@dataclass(frozen=True)
class WorkflowHandles:
    """Temporary Dask handles for one materialized plan."""

    prepared: PreparedStudy
    simulations: tuple[Future, ...]
    measurements: tuple[Future, ...]
    summary: Future


@dataclass(frozen=True)
class CompletedDemo:
    """Durable result references returned after Dask completion."""

    prepared: PreparedStudy
    summary: StudySummary


def submit_prepared(client: Client, prepared: PreparedStudy) -> WorkflowHandles:
    """Map two basic flows and reduce them without hiding their dependencies."""

    cases = list(prepared.cases)
    simulations = tuple(
        client.map(
            simulate_placeholder,
            [prepared] * len(cases),
            cases,
            key=f"{prepared.run_id}-simulate",
            pure=False,
        )
    )
    measurements = tuple(
        client.map(
            measure_placeholder,
            simulations,
            key=f"{prepared.run_id}-measure",
            pure=False,
        )
    )
    summary = client.submit(
        reduce_measurements,
        prepared,
        list(measurements),
        key=f"{prepared.run_id}-reduce",
        pure=False,
    )
    return WorkflowHandles(
        prepared=prepared,
        simulations=simulations,
        measurements=measurements,
        summary=summary,
    )


def complete(handles: WorkflowHandles) -> CompletedDemo:
    """Wait for the reduction and return only durable result references."""

    return CompletedDemo(prepared=handles.prepared, summary=handles.summary.result())


def run_local_demo(
    output_root: Path,
    spec: StudySpec | None = None,
) -> CompletedDemo:
    """Run the reference flow with two local threaded Dask workers."""

    prepared = prepare_study(spec or demonstration_spec(), output_root)
    with LocalCluster(
        n_workers=2,
        threads_per_worker=1,
        processes=False,
        scheduler_port=0,
        dashboard_address=None,
    ) as cluster:
        with Client(cluster) as client:
            return complete(submit_prepared(client, prepared))


def run_lsf_demo(
    output_root: Path,
    settings: LsfClusterSettings,
    spec: StudySpec | None = None,
) -> CompletedDemo:
    """Run the same flow on Dask workers allocated through LSF.

    The output root and package environment must be visible from every worker.
    This function intentionally keeps cluster creation separate from the
    authored plan and persists the generated worker job script for inspection.
    """

    prepared = prepare_study(spec or demonstration_spec(), output_root)
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
            return complete(submit_prepared(client, prepared))
    finally:
        cluster.close()
