"""Illustrative LSF entry point; replace the site-specific values."""

from pathlib import Path

from ass_study_flow import LsfClusterSettings, run_lsf_demo


settings = LsfClusterSettings(
    queue="replace-with-site-queue",
    project="replace-with-site-project",
    worker_jobs=2,
    cores_per_job=1,
    memory="1GB",
    walltime="00:15",
    interface="replace-with-reachable-interface",
)
completed = run_lsf_demo(Path("/replace/with/shared/path"), settings)
print(completed.summary.artifact_path)
