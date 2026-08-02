"""Dask cluster configuration boundaries for the prototype."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LsfClusterSettings:
    """Small, explicit subset of Dask Jobqueue's LSF configuration."""

    queue: str
    project: str | None = None
    worker_jobs: int = 2
    cores_per_job: int = 1
    processes_per_job: int = 1
    memory: str = "1GB"
    walltime: str = "00:15"
    interface: str | None = None
    python_executable: str = field(default_factory=lambda: sys.executable)
    job_script_prologue: tuple[str, ...] = ()
    shared_temp_directory: str | None = None
    local_directory: str | None = None
    log_directory: str | None = None

    def __post_init__(self) -> None:
        if not self.queue.strip():
            raise ValueError("queue must not be empty")
        if self.worker_jobs < 1:
            raise ValueError("worker_jobs must be positive")
        if self.cores_per_job < 1:
            raise ValueError("cores_per_job must be positive")
        if self.processes_per_job < 1:
            raise ValueError("processes_per_job must be positive")
        if self.processes_per_job > self.cores_per_job:
            raise ValueError("processes_per_job cannot exceed cores_per_job")


def lsf_cluster_kwargs(settings: LsfClusterSettings) -> dict[str, Any]:
    """Translate the ASS-facing settings into Dask Jobqueue arguments.

    Random ports prevent accidental clashes. Per-cluster mutual TLS is enabled
    unconditionally because a reachable Dask scheduler can execute Python code.
    """

    kwargs: dict[str, Any] = {
        "queue": settings.queue,
        "n_workers": 0,
        "cores": settings.cores_per_job,
        "processes": settings.processes_per_job,
        "memory": settings.memory,
        "walltime": settings.walltime,
        "python": settings.python_executable,
        "security": True,
        "scheduler_options": {
            "port": 0,
            "dashboard_address": "127.0.0.1:0",
        },
    }
    optional = {
        "project": settings.project,
        "interface": settings.interface,
        "shared_temp_directory": settings.shared_temp_directory,
        "local_directory": settings.local_directory,
        "log_directory": settings.log_directory,
    }
    kwargs.update({key: value for key, value in optional.items() if value})
    if settings.job_script_prologue:
        kwargs["job_script_prologue"] = list(settings.job_script_prologue)
    return kwargs


def create_lsf_cluster(settings: LsfClusterSettings):
    """Create, but do not scale, an LSF-backed Dask cluster."""

    from dask_jobqueue import LSFCluster

    if settings.shared_temp_directory is None:
        raise ValueError(
            "shared_temp_directory is required for TLS credentials; "
            "run_lsf_demo creates a private run-scoped directory automatically"
        )
    return LSFCluster(**lsf_cluster_kwargs(settings))
