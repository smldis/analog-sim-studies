"""Small, serializable contracts used by the study-flow experiment."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


_STABLE_ID = re.compile(r"^[a-z][a-z0-9-]*$")


def _require_stable_id(value: str, label: str) -> None:
    if not _STABLE_ID.fullmatch(value):
        raise ValueError(f"{label} must be a stable kebab-case identifier")


def _require_finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


@dataclass(frozen=True)
class CaseSpec:
    """One mapped case in the demonstration study."""

    case_id: str
    stimulus: float
    multiplier: float

    def __post_init__(self) -> None:
        _require_stable_id(self.case_id, "case_id")
        _require_finite(self.stimulus, "stimulus")
        _require_finite(self.multiplier, "multiplier")


@dataclass(frozen=True)
class StudySpec:
    """Authored intent for the bounded demonstration."""

    study_id: str
    reference: float
    cases: tuple[CaseSpec, ...]

    def __post_init__(self) -> None:
        _require_stable_id(self.study_id, "study_id")
        _require_finite(self.reference, "reference")
        if self.reference == 0:
            raise ValueError("reference must be non-zero")
        if not self.cases:
            raise ValueError("at least one case is required")
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case identifiers must be unique")


@dataclass(frozen=True)
class PreparedStudy:
    """The local dependency shared by every mapped basic flow."""

    run_id: str
    run_directory: Path
    spec_path: Path
    plan_path: Path
    artifact_path: Path
    reference: float
    cases: tuple[CaseSpec, ...]
    prepared_by_pid: int


@dataclass(frozen=True)
class SimulationAttempt:
    """A materialized attempt produced by the simulation placeholder."""

    run_id: str
    case_id: str
    attempt_id: str
    artifact_path: Path
    raw_response: float
    reference: float
    worker_address: str
    status: str = "completed"


@dataclass(frozen=True)
class MeasurementResult:
    """A named value derived from one simulation attempt."""

    run_id: str
    case_id: str
    value: float
    unit: str
    artifact_path: Path
    simulation_artifact: Path


@dataclass(frozen=True)
class StudySummary:
    """The reduction over all mapped measurement results."""

    run_id: str
    count: int
    minimum: float
    maximum: float
    mean: float
    artifact_path: Path
    measurements: tuple[MeasurementResult, ...]


def demonstration_spec() -> StudySpec:
    """Return the deliberately small two-case authored example."""

    return StudySpec(
        study_id="two-case-response",
        reference=1.0,
        cases=(
            CaseSpec(case_id="low", stimulus=0.9, multiplier=10.0),
            CaseSpec(case_id="high", stimulus=1.1, multiplier=10.0),
        ),
    )
