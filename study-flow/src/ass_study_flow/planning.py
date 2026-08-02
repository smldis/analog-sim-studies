"""Local authoring and plan materialization for the demonstration."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from .artifacts import write_json
from .contracts import PreparedStudy, StudySpec, _require_stable_id


def _plan_nodes(spec: StudySpec) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = [
        {
            "id": "prepare",
            "operation": "prepare-study",
            "execution_role": "local-controller",
            "depends_on": [],
        }
    ]
    measurement_ids: list[str] = []
    for case in spec.cases:
        simulation_id = f"simulate-{case.case_id}"
        measurement_id = f"measure-{case.case_id}"
        nodes.extend(
            [
                {
                    "id": simulation_id,
                    "operation": "simulation-placeholder",
                    "execution_role": "mapped-worker",
                    "depends_on": ["prepare"],
                    "case_id": case.case_id,
                },
                {
                    "id": measurement_id,
                    "operation": "measurement-placeholder",
                    "execution_role": "mapped-worker",
                    "depends_on": [simulation_id],
                    "case_id": case.case_id,
                },
            ]
        )
        measurement_ids.append(measurement_id)
    nodes.append(
        {
            "id": "reduce",
            "operation": "reduce-measurements",
            "execution_role": "reduction-worker",
            "depends_on": measurement_ids,
        }
    )
    return nodes


def prepare_study(
    spec: StudySpec,
    output_root: Path,
    *,
    run_id: str | None = None,
) -> PreparedStudy:
    """Run the sole local dependency and publish its derived plan.

    This function is intentionally synchronous and is called before a Dask
    cluster receives work. Its artifact must live on storage visible to every
    selected worker.
    """

    resolved_run_id = run_id or f"{spec.study_id}-{uuid4().hex[:12]}"
    _require_stable_id(resolved_run_id, "run_id")
    run_directory = (output_root / resolved_run_id).resolve()
    try:
        run_directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise FileExistsError(f"run already exists: {run_directory}") from exc

    prepared_by_pid = os.getpid()
    spec_path = write_json(
        run_directory / "study-spec.json",
        {
            "kind": "authored-study-spec-snapshot",
            "spec": spec,
        },
    )
    artifact_path = write_json(
        run_directory / "prepared.json",
        {
            "kind": "prepared-study",
            "run_id": resolved_run_id,
            "reference": spec.reference,
            "cases": spec.cases,
            "prepared_by_pid": prepared_by_pid,
            "source_spec": spec_path,
        },
    )
    plan_path = write_json(
        run_directory / "plan.json",
        {
            "kind": "derived-plan",
            "run_id": resolved_run_id,
            "source_spec": spec_path,
            "nodes": _plan_nodes(spec),
            "note": (
                "This plan is inspectable derived data and names execution "
                "roles rather than an authoritative engine; Dask Futures are "
                "temporary handles."
            ),
        },
    )
    return PreparedStudy(
        run_id=resolved_run_id,
        run_directory=run_directory,
        spec_path=spec_path,
        plan_path=plan_path,
        artifact_path=artifact_path,
        reference=spec.reference,
        cases=spec.cases,
        prepared_by_pid=prepared_by_pid,
    )
