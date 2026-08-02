"""Run the two-item generic reference flow without a batch scheduler."""

from pathlib import Path

from ass_study_flow import run_local_demo


completed = run_local_demo(Path("build/example-local"))
print(completed.result.path)
