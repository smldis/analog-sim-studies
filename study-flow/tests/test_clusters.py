from __future__ import annotations

import sys
from stat import S_IMODE

import pytest

from ass_study_flow import (
    LsfClusterSettings,
    create_lsf_cluster,
    lsf_cluster_kwargs,
)


def test_lsf_translation_is_isolated_and_secure_by_default(tmp_path) -> None:
    settings = LsfClusterSettings(
        queue="normal",
        project="analog",
        worker_jobs=2,
        cores_per_job=2,
        processes_per_job=1,
        memory="4GB",
        walltime="01:30",
        interface="eth0",
        job_script_prologue=("module load python",),
        shared_temp_directory=str(tmp_path / "control"),
        local_directory=str(tmp_path / "workers"),
        log_directory=str(tmp_path / "logs"),
    )

    kwargs = lsf_cluster_kwargs(settings)

    assert kwargs["queue"] == "normal"
    assert kwargs["project"] == "analog"
    assert kwargs["cores"] == 2
    assert kwargs["processes"] == 1
    assert kwargs["python"] == sys.executable
    assert kwargs["security"] is True
    assert kwargs["n_workers"] == 0
    assert kwargs["scheduler_options"] == {
        "port": 0,
        "dashboard_address": "127.0.0.1:0",
    }
    assert kwargs["job_script_prologue"] == ["module load python"]
    assert kwargs["shared_temp_directory"] == str(tmp_path / "control")


def test_lsf_settings_reject_impossible_process_layout() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        LsfClusterSettings(
            queue="normal", cores_per_job=1, processes_per_job=2
        )


def test_cluster_factory_requires_shared_tls_storage() -> None:
    with pytest.raises(ValueError, match="TLS credentials"):
        create_lsf_cluster(LsfClusterSettings(queue="normal"))


def test_lsf_job_script_renders_with_tls_without_submitting(tmp_path) -> None:
    settings = LsfClusterSettings(
        queue="normal",
        interface="lo",
        shared_temp_directory=str(tmp_path),
    )

    cluster = create_lsf_cluster(settings)
    try:
        script = cluster.job_script()
    finally:
        cluster.close()

    assert "#BSUB -q normal" in script
    assert "distributed.cli.dask_worker tls://" in script
    assert "--tls-ca-file" in script
    assert "--tls-cert" in script
    assert "--tls-key" in script
    credentials = tuple(tmp_path.glob(".dask-jobqueue*"))
    assert len(credentials) == 3
    assert all(S_IMODE(path.stat().st_mode) == 0o600 for path in credentials)
