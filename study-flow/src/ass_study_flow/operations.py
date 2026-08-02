"""Mapped basic operations and their reduction."""

from __future__ import annotations

import os
from pathlib import Path
from statistics import fmean
from uuid import uuid4

from distributed import get_worker

from .artifacts import read_json, write_json
from .contracts import (
    CaseSpec,
    MeasurementResult,
    PreparedStudy,
    SimulationAttempt,
    StudySummary,
)


def _worker_address() -> str:
    try:
        return str(get_worker().address)
    except ValueError:
        return f"local-process://{os.getpid()}"


def simulate_placeholder(
    prepared: PreparedStudy,
    case: CaseSpec,
) -> SimulationAttempt:
    """Stand in for an external simulator while preserving attempt shape."""

    preparation = read_json(prepared.artifact_path)
    if preparation["run_id"] != prepared.run_id:
        raise ValueError("prepared artifact does not describe this run")

    attempt_id = uuid4().hex
    raw_response = case.stimulus * case.multiplier
    attempt_directory = (
        prepared.run_directory / "attempts" / case.case_id / attempt_id
    )
    artifact_path = attempt_directory / "simulation.json"
    attempt = SimulationAttempt(
        run_id=prepared.run_id,
        case_id=case.case_id,
        attempt_id=attempt_id,
        artifact_path=artifact_path,
        raw_response=raw_response,
        reference=prepared.reference,
        worker_address=_worker_address(),
    )
    write_json(
        artifact_path,
        {
            "kind": "simulation-attempt",
            "attempt": attempt,
            "warning": "Arithmetic placeholder; no simulator was invoked.",
        },
    )
    return attempt


def measure_placeholder(attempt: SimulationAttempt) -> MeasurementResult:
    """Turn one simulation placeholder result into a named measurement."""

    simulation = read_json(attempt.artifact_path)
    recorded = simulation["attempt"]
    if recorded["attempt_id"] != attempt.attempt_id:
        raise ValueError("simulation artifact does not describe this attempt")

    value = attempt.raw_response / attempt.reference
    artifact_path = attempt.artifact_path.with_name("measurement.json")
    measurement = MeasurementResult(
        run_id=attempt.run_id,
        case_id=attempt.case_id,
        value=value,
        unit="normalized-response",
        artifact_path=artifact_path,
        simulation_artifact=attempt.artifact_path,
    )
    write_json(
        artifact_path,
        {
            "kind": "measurement-result",
            "measurement": measurement,
            "validated_input": attempt.artifact_path,
        },
    )
    return measurement


def reduce_measurements(
    prepared: PreparedStudy,
    measurements: list[MeasurementResult],
) -> StudySummary:
    """Reduce the mapped basic-flow results into one durable summary."""

    if not measurements:
        raise ValueError("cannot reduce an empty measurement collection")
    ordered = tuple(sorted(measurements, key=lambda item: item.case_id))
    expected = {case.case_id for case in prepared.cases}
    actual = {measurement.case_id for measurement in ordered}
    if actual != expected:
        raise ValueError("reduction inputs do not match the prepared cases")
    for measurement in ordered:
        published = read_json(measurement.artifact_path)
        if published["measurement"]["case_id"] != measurement.case_id:
            raise ValueError("measurement artifact has inconsistent identity")

    values = tuple(measurement.value for measurement in ordered)
    artifact_path = prepared.run_directory / "summary.json"
    summary = StudySummary(
        run_id=prepared.run_id,
        count=len(values),
        minimum=min(values),
        maximum=max(values),
        mean=fmean(values),
        artifact_path=artifact_path,
        measurements=ordered,
    )
    write_json(
        artifact_path,
        {
            "kind": "study-summary",
            "summary": summary,
            "source_plan": prepared.plan_path,
        },
    )
    return summary
