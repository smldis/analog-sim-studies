"""Command line entry point for the study-flow experiment."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .clusters import LsfClusterSettings
from .deferred import DEFERRED_CAPABILITIES
from .runtime import run_local_demo, run_lsf_demo


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/study-flow-demo"),
        help="Shared root under which a unique run directory is created.",
    )
    parser.add_argument("--backend", choices=("local", "lsf"), default="local")
    parser.add_argument("--queue", help="LSF queue; required for --backend lsf.")
    parser.add_argument("--project", help="Optional LSF project.")
    parser.add_argument("--interface", help="Network interface visible to workers.")
    parser.add_argument("--worker-jobs", type=int, default=2)
    parser.add_argument("--cores-per-job", type=int, default=1)
    parser.add_argument("--memory", default="1GB")
    parser.add_argument("--walltime", default="00:15")
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable visible on the LSF workers.",
    )
    parser.add_argument(
        "--job-prologue",
        action="append",
        default=[],
        help="Setup command added before the Dask worker; may be repeated.",
    )
    parser.add_argument(
        "--list-deferred",
        action="store_true",
        help="Print explicit future seams without running the demo.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.list_deferred:
        print(json.dumps([asdict(item) for item in DEFERRED_CAPABILITIES], indent=2))
        return 0

    if args.backend == "local":
        completed = run_local_demo(args.output)
    else:
        if not args.queue:
            parser.error("--queue is required for --backend lsf")
        settings = LsfClusterSettings(
            queue=args.queue,
            project=args.project,
            worker_jobs=args.worker_jobs,
            cores_per_job=args.cores_per_job,
            memory=args.memory,
            walltime=args.walltime,
            interface=args.interface,
            python_executable=args.python_executable,
            job_script_prologue=tuple(args.job_prologue),
        )
        completed = run_lsf_demo(args.output, settings)

    print(
        json.dumps(
            {
                "run_id": completed.prepared.run_id,
                "plan": str(completed.prepared.plan_path),
                "summary": str(completed.summary.artifact_path),
                "count": completed.summary.count,
                "mean": completed.summary.mean,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0
