"""The same sign-off with the fan-out *inside* the graph, and what that costs.

    python examples/ota_pvt_clean_nested.py

`ota_pvt_clean.py` reads the edit file while authoring: `load_editfile` and
`jobs_of` run on the submitting machine, before a Plan exists, so the Plan can
name one simulation per corner. This study moves both into the graph, as the
first two operations of a higher-level flow whose third member is the study
itself:

    described = load_edit_file(edits)        # operation 1
    jobs      = expand_jobs(described)       # operation 2
    result    = corners(..., jobs, ...)      # a nested flow -- the study

That is a real improvement in one respect: nothing about the corners is known
outside the graph any more. The edit file is read once, by a recorded
invocation, and every downstream digest depends on what that invocation
produced. There is no second reading to drift.

It is also the boundary this project keeps naming, met head-on. **A Plan states
what will run before anything runs.** The moment the corner list is a *result*,
the graph cannot name one invocation per corner — it does not know how many
there are. So the fan-out has to move inside the operations, and the plan
becomes a fixed six invocations whatever the edit file says.

What that trades away, concretely:

* **Placement.** `simulate_all` runs every ngspice itself. It cannot return
  `shell(...)`, because a body returns one command and this needs N. So no
  corner can take its own LSF job, its own licence, or its own core count.
  `ota_pvt_clean.py` places each corner; this places the whole sweep.
* **Reuse.** One invocation covers every simulation, so editing one corner
  reruns all of them. Simulation is where the time goes, which makes this the
  expensive version of the trade `ota_pvt_clean.py` only made for rendering.
* **Observability.** `watch=True` shows six rows regardless of corner count. A
  sweep of two hundred corners reports as one line that is either running or
  not.

Both files run the same corners against the same simulator and agree on the
numbers. Which is right depends on whether the corner set is knowable before
the study runs. Here it is — the edit file is right there — so `ota_pvt_clean.py`
is the better shape, and this one exists to show what the graph gives up when a
result decides its shape.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import cmath
import json
import math
import shutil
import struct
import sys

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
sys.path.insert(0, str(_HERE.parent / "src"))
for _unit in ("ass-flow", "ass-exec", "ass-run", "sidecar-edits"):
    sys.path.insert(0, str(_REPO / _unit / "src"))

from ass import (  # noqa: E402
    Site,
    address,
    artifact,
    codec,
    file,
    flow,
    input_artifact,
    local,
    materialization,
    operation,
    plan,
    returned,
    study,
)
from ass_exec.lsf import SubprocessRunner  # noqa: E402
from sidecar_edits.render import (  # noqa: E402
    expand_param_matrix,
    load_editfile,
    render_job,
)

INPUTS = "docs/reference/ota-pvt-plan/inputs"
BASE_DIRECTORY_LOCATOR = f"{INPUTS}/base"
PVT_EDITS_LOCATOR = f"{INPUTS}/pvt_edits.py"
MEASUREMENT_DEFINITION_LOCATOR = f"{INPUTS}/measurement_definition.json"
SPEC_LIMITS_LOCATOR = f"{INPUTS}/spec_limits.json"

DECK_NAME = "ota_ac.cir"
RAW_NAME = "ota_ac.raw"

SIDE_CAR_BASE = artifact("sidecar-base-directory")
SIDE_CAR_EDITS = artifact("sidecar-edit-file")
RENDER_PLAN = artifact("sidecar-render-plan")
SIDECAR_JOBS = artifact("sidecar-jobs")
PREPARED_RUNS = artifact("prepared-simulation-directory")
SIMULATOR_RAWS = artifact("simulator-raw-results")
MEASUREMENT_DEFINITION = artifact("ota-measurement-definition")
POINT_MEASUREMENTS = artifact("ota-point-measurements")
SPEC_LIMITS = artifact("ota-specification-limits")

REPOSITORY_DIRECTORY_TREE = materialization(
    codec=codec("directory-tree", version="1"),
    address_space="repository-relative",
    access_scope="repository-checkout",
)
REPOSITORY_PYTHON_SOURCE = materialization(
    codec=codec("python-source", version="1", encoding="utf-8"),
    address_space="repository-relative",
    access_scope="repository-checkout",
)
REPOSITORY_JSON = materialization(
    codec=codec("json", version="1", encoding="utf-8"),
    address_space="repository-relative",
    access_scope="repository-checkout",
)


# ---------------------------------------------------------------------------
# The two operations that used to run while authoring.
# ---------------------------------------------------------------------------


@operation(
    name="ota_pvt_nested.load_edit_file",
    version="1",
    inputs={"edits": SIDE_CAR_EDITS},
    outputs={"described": returned(kind="sidecar-render-plan")},
)
def load_edit_file(edits):
    """Read the edit file into a JSON-safe description of what it declares.

    Returned rather than kept: every result is journaled as JSON before an
    output is inspected, so a live `RenderPlan` could not cross this boundary.
    What crosses is what the next operation needs — the param sets and the
    matrix — and the edit file's own path, since rendering re-opens it.
    """

    render_plan = load_editfile(Path(edits))
    return {
        "editfile": str(render_plan.editfile_path),
        "base_dir": str(render_plan.base_dir),
        "param_sets": [
            {
                "name": item.name,
                "description": item.description,
                "params": dict(item.params),
            }
            for item in render_plan.param_sets
        ],
        "param_matrix": {
            key: list(values) for key, values in render_plan.param_matrix.items()
        },
    }


@operation(
    name="ota_pvt_nested.expand_jobs",
    version="1",
    inputs={"described": RENDER_PLAN},
    outputs={"jobs": returned(kind="sidecar-jobs")},
)
def expand_jobs(described):
    """Sidecar's own fan-out: param sets crossed with the param matrix.

    In `ota_pvt_clean.py` this is `jobs_of`, called while authoring so the Plan
    can name a simulation per corner. Here it is an invocation, so nothing
    downstream can be named per corner — the count is not known until this has
    run. That is the whole difference between the two studies.
    """

    jobs: list[dict[str, Any]] = []
    for param_set in described["param_sets"]:
        for case in expand_param_matrix(described["param_matrix"]):
            name = param_set["name"] or "default"
            if case.suffix:
                name = f"{name}__{case.suffix}"
            jobs.append(
                {"name": name, "params": {**param_set["params"], **case.params}}
            )
    return jobs


# ---------------------------------------------------------------------------
# The study. Each operation covers every corner, because the graph cannot name
# them one at a time.
# ---------------------------------------------------------------------------


@operation(
    name="ota_pvt_nested.prepare_all",
    version="1",
    inputs={"base": SIDE_CAR_BASE, "edits": SIDE_CAR_EDITS, "jobs": SIDECAR_JOBS},
    outputs={"runs": file("runs", kind="prepared-simulation-directory")},
)
def prepare_all(base, edits, jobs, out):
    """Render every corner. `base` is declared for identity, opened by sidecar."""

    del base  # reached through the edit file's own BASE_DIR; declared for identity
    render_plan = load_editfile(Path(edits))
    out.runs.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        render_job(render_plan, dict(job["params"]), out.runs / job["name"],
                   label=job["name"])


@operation(
    name="ota_pvt_nested.simulate_all",
    version="1",
    inputs={"runs": PREPARED_RUNS, "jobs": SIDECAR_JOBS},
    outputs={"raws": file("raws", kind="simulator-raw-results")},
)
def simulate_all(runs, jobs, out):
    """Every ngspice run, in this one invocation.

    This is what the nesting costs. A body returning `shell(...)` hands one
    command to its placement; N commands cannot be handed to N placements from
    one invocation, so this runs them itself. `SubprocessRunner` is the runner
    `ass_exec` uses for `bsub`, so each child still dies with this process --
    but no corner has its own queue, licence or core count any more.
    """

    runner = SubprocessRunner()
    out.raws.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        deck = Path(runs) / job["name"] / DECK_NAME
        if not deck.exists():
            raise FileNotFoundError(f"prepared deck not found at {deck}")
        target = out.raws / job["name"]
        target.mkdir(parents=True, exist_ok=True)
        result = runner(
            ["ngspice", "-b", "-r", str(target / RAW_NAME), str(deck)],
            cwd=str(target),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ngspice exited {result.returncode} for {job['name']}: "
                f"{result.stderr[-800:]}"
            )
        if not (target / RAW_NAME).exists():
            raise RuntimeError(
                f"ngspice reported success but never wrote {target / RAW_NAME}"
            )


@operation(
    name="ota_pvt_nested.measure_all",
    version="1",
    inputs={
        "raws": SIMULATOR_RAWS,
        "definition": MEASUREMENT_DEFINITION,
        "jobs": SIDECAR_JOBS,
    },
    outputs={"measurements": returned(kind="ota-point-measurements")},
)
def measure_all(raws, definition, jobs):
    """Gain, GBW and phase margin for every corner. Refuses no declared metric."""

    declared = json.loads(Path(definition).read_text(encoding="utf-8"))
    expected = {item["name"] for item in declared["metrics"]}

    measured = []
    for job in jobs:
        columns = read_ac_raw(Path(raws) / job["name"] / RAW_NAME)
        metrics = measure_ac_metrics(columns)
        missing = expected - metrics.keys()
        if missing:
            raise RawFileError(
                f"measurement definition names {sorted(missing)}; not computed"
            )
        measured.append({"point_id": job["name"], **metrics})
    return measured


@operation(
    name="ota_pvt_nested.evaluate_pvt",
    version="1",
    inputs={"measurements": POINT_MEASUREMENTS, "limits": SPEC_LIMITS},
    outputs={"evaluation": returned(kind="ota-pvt-evaluation")},
)
def evaluate_pvt(measurements, limits):
    """Check every corner against the declared limits."""

    declared = json.loads(Path(limits).read_text(encoding="utf-8"))
    limit_map = declared["limits"]

    points: dict[str, Any] = {}
    overall_pass = True
    for measurement in measurements:
        checks: dict[str, Any] = {}
        point_pass = True
        for metric, limit in limit_map.items():
            value = measurement.get(metric)
            minimum = limit.get("minimum")
            ok = value is not None and minimum is not None and value >= minimum
            checks[metric] = {"value": value, "minimum": minimum, "pass": ok}
            point_pass = point_pass and ok
        points[measurement["point_id"]] = {
            "measurements": measurement,
            "checks": checks,
            "pass": point_pass,
        }
        overall_pass = overall_pass and point_pass

    return {
        "status": declared.get("status"),
        "limits": limit_map,
        "points": points,
        "overall_pass": overall_pass,
    }


@flow(name="ota_pvt_nested.corners", version="1")
def corners(base, edits, jobs, definition, limits):
    """The study proper, once the corners exist as a value."""

    runs = prepare_all.options(key="prepare")(base, edits, jobs)
    raws = simulate_all.options(key="simulate")(runs, jobs)
    measured = measure_all.options(key="measure")(raws, definition, jobs)
    return {
        "evaluation": evaluate_pvt.options(key="evaluate")(measured, limits).evaluation
    }


@flow(name="ota_pvt_nested.study", version="1")
def pvt_study(base, edits, definition, limits):
    """Three members: read the edit file, expand it, then run what it says."""

    described = load_edit_file.options(key="load")(edits)
    jobs = expand_jobs.options(key="expand")(described)
    return corners.options(key="corners")(base, edits, jobs, definition, limits)


def build():
    """Nothing is read here. Every fact about the corners comes from the graph."""

    with plan(default_policy=local()) as draft:
        outputs = pvt_study.options(key="ota-pvt")(
            input_artifact(
                address("repository-relative", BASE_DIRECTORY_LOCATOR),
                artifact=SIDE_CAR_BASE,
                materialized_as=REPOSITORY_DIRECTORY_TREE,
            ),
            input_artifact(
                address("repository-relative", PVT_EDITS_LOCATOR),
                artifact=SIDE_CAR_EDITS,
                materialized_as=REPOSITORY_PYTHON_SOURCE,
            ),
            input_artifact(
                address("repository-relative", MEASUREMENT_DEFINITION_LOCATOR),
                artifact=MEASUREMENT_DEFINITION,
                materialized_as=REPOSITORY_JSON,
            ),
            input_artifact(
                address("repository-relative", SPEC_LIMITS_LOCATOR),
                artifact=SPEC_LIMITS,
                materialized_as=REPOSITORY_JSON,
            ),
        )
    return draft.finish(outputs=outputs)


# ---------------------------------------------------------------------------
# ngspice AC raw reading. No third-party dependency: a short ASCII header, then
# little-endian complex doubles, one (real, imag) pair per variable per point.
# ---------------------------------------------------------------------------

_BINARY_MARKER = b"Binary:\n"


class RawFileError(ValueError):
    """The raw file is not the AC/complex shape this reader expects."""


def read_ac_raw(path: Path) -> dict[str, list[complex]]:
    """Read an ngspice ``-r`` AC raw file into named complex columns."""

    data = path.read_bytes()
    marker_at = data.find(_BINARY_MARKER)
    if marker_at == -1:
        raise RawFileError(f"{path}: no binary marker; not an ngspice -r raw file")

    header = data[:marker_at].decode("ascii", errors="replace").splitlines()
    flags: str | None = None
    n_vars: int | None = None
    n_points: int | None = None
    variables: list[str] = []
    index = 0
    while index < len(header):
        line = header[index]
        if line.startswith("Flags:"):
            flags = line.split(":", 1)[1].strip()
        elif line.startswith("No. Variables:"):
            n_vars = int(line.split(":", 1)[1].strip())
        elif line.startswith("No. Points:"):
            n_points = int(line.split(":", 1)[1].strip())
        elif line.strip() == "Variables:" and n_vars is not None:
            for offset in range(1, n_vars + 1):
                variables.append(header[index + offset].strip().split("\t")[1])
            index += n_vars
        index += 1

    if flags != "complex" or n_vars is None or n_points is None:
        raise RawFileError(
            f"{path}: expected a complex AC raw file (flags={flags!r}, "
            f"variables={n_vars!r}, points={n_points!r})"
        )

    body = data[marker_at + len(_BINARY_MARKER) :]
    expected_bytes = n_vars * n_points * 16
    if len(body) < expected_bytes:
        raise RawFileError(
            f"{path}: truncated binary section ({len(body)} of {expected_bytes} bytes)"
        )

    columns: dict[str, list[complex]] = {name: [] for name in variables}
    for point in range(n_points):
        base = point * n_vars * 16
        for var_index, name in enumerate(variables):
            real, imag = struct.unpack_from("<2d", body, base + var_index * 16)
            columns[name].append(complex(real, imag))
    return columns


def measure_ac_metrics(
    columns: Mapping[str, list[complex]],
    *,
    output_node: str = "v(out)",
    positive_input: str = "v(in_p)",
    negative_input: str = "v(in_n)",
) -> dict[str, float]:
    """Gain, GBW and phase margin from a real AC sweep. Refuses, never guesses."""

    for name in (output_node, positive_input, negative_input, "frequency"):
        if name not in columns:
            raise RawFileError(f"raw file has no column {name!r}; have {sorted(columns)}")

    frequencies = [value.real for value in columns["frequency"]]
    gains_db: list[float] = []
    phases_deg: list[float] = []
    for out, pos, neg in zip(
        columns[output_node], columns[positive_input], columns[negative_input]
    ):
        differential = pos - neg
        if differential == 0:
            raise RawFileError("zero differential AC excitation; cannot compute a gain")
        transfer = out / differential
        gains_db.append(20.0 * math.log10(abs(transfer)))
        phases_deg.append(math.degrees(cmath.phase(transfer)))

    gain_bandwidth_hz: float | None = None
    phase_margin_deg: float | None = None
    for index in range(1, len(frequencies)):
        if gains_db[index - 1] > 0 >= gains_db[index]:
            log_f0 = math.log10(frequencies[index - 1])
            log_f1 = math.log10(frequencies[index])
            g0, g1 = gains_db[index - 1], gains_db[index]
            fraction = g0 / (g0 - g1)
            gain_bandwidth_hz = 10 ** (log_f0 + fraction * (log_f1 - log_f0))
            p0, p1 = phases_deg[index - 1], phases_deg[index]
            phase_margin_deg = 180.0 + (p0 + fraction * (p1 - p0))
            break

    if gain_bandwidth_hz is None:
        raise RawFileError(
            "gain never crosses 0 dB across the swept band; cannot report GBW/PM"
        )

    return {
        "dc_gain_db": gains_db[0],
        "gain_bandwidth_hz": gain_bandwidth_hz,
        "phase_margin_deg": phase_margin_deg,
    }


# ---------------------------------------------------------------------------
# The deliverable.
# ---------------------------------------------------------------------------

_METRICS = (
    ("dc_gain_db", "DC gain", "dB", 1e0, "{:.1f}"),
    ("gain_bandwidth_hz", "GBW", "MHz", 1e6, "{:.2f}"),
    ("phase_margin_deg", "Phase margin", "deg", 1e0, "{:.1f}"),
)


def render_report(
    run, *, fingerprints: Mapping[str, str], document: Mapping[str, Any]
) -> str:
    """The deliverable, built from what the graph produced rather than re-read.

    The corner list comes out of the `expand` invocation, which is the point of
    this variant: the report cannot disagree with the study about which corners
    were run, because it is reading the same value the study ran on.
    """

    evaluation = run.value or {}
    points = evaluation.get("points", {})
    limits = evaluation.get("limits", {})
    jobs = run["expand"].value or []
    verdict = "PASS" if evaluation.get("overall_pass") else "FAIL"

    lines = [
        "# OTA PVT sign-off",
        "",
        f"**Verdict: {verdict}** — {len(points)} corners, "
        f"{len(limits)} limits, status `{evaluation.get('status')}`.",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "The corner set was produced by the graph, not read alongside it.",
        "",
        "## Corners",
        "",
    ]

    header = ["corner"] + [f"{label} ({unit})" for _, label, unit, _, _ in _METRICS]
    lines.append("| " + " | ".join(header + ["verdict"]) + " |")
    lines.append("|" + "---|" * (len(header) + 1))
    for job in jobs:
        point = points.get(job["name"], {})
        measured = point.get("measurements", {})
        cells = [f"`{job['name']}`"]
        for key, _, _, scale, form in _METRICS:
            value = measured.get(key)
            cells.append(form.format(value / scale) if value is not None else "—")
        cells.append("pass" if point.get("pass") else "**fail**")
        lines.append("| " + " | ".join(cells) + " |")

    lines += ["", "## Limits applied", "", "| metric | minimum |", "|---|---|"]
    for metric, limit in sorted(limits.items()):
        lines.append(f"| `{metric}` | {limit.get('minimum')} |")

    if jobs:
        lines += ["", "## Corner parameters", "",
                  "Expanded by the `expand` invocation, from the edit file.", ""]
        keys = sorted({key for job in jobs for key in job["params"]})
        lines.append("| corner | " + " | ".join(f"`{key}`" for key in keys) + " |")
        lines.append("|" + "---|" * (len(keys) + 1))
        for job in jobs:
            values = [str(job["params"].get(key, "—")) for key in keys]
            lines.append(f"| `{job['name']}` | " + " | ".join(values) + " |")

    lines += [
        "",
        "## Provenance",
        "",
        f"Plan schema {document.get('schema_version')}, "
        f"{len(document.get('invocations', []))} invocations, "
        f"{len(document.get('sources', []))} declared sources. The invocation "
        "count does not depend on the corner count: the fan-out is inside the "
        "operations, so this plan has the same shape for three corners or three "
        "hundred.",
        "",
        "### Inputs, by content",
        "",
        "| source | fingerprint |",
        "|---|---|",
    ]
    for source in document.get("sources", []):
        locator = (source.get("address") or {}).get("locator", "?")
        lines.append(f"| `{locator}` | `{fingerprints.get(source['id'], '—')}` |")

    lines += [
        "",
        "### What ran",
        "",
        "| invocation | operation | placement | outcome | |",
        "|---|---|---|---|---|",
    ]
    for outcome in run.report.outcomes:
        lines.append(
            f"| `{outcome.authored_key}` | `{outcome.operation}` | "
            f"{outcome.placement or '—'} | {outcome.outcome} | "
            f"{'reused' if outcome.reused else 'ran'} |"
        )
    if not run.succeeded:
        lines += ["", "### Failures", ""]
        for outcome in run.report.outcomes:
            if outcome.error:
                lines.append(f"- `{outcome.authored_key}`: {outcome.error}")

    return "\n".join(lines) + "\n"


def main() -> int:
    if shutil.which("ngspice") is None:
        print("ngspice is not on PATH; this study needs a real simulator")
        return 1

    work = _HERE / "_runs" / "ota-nested"
    site = Site(
        root=str(work / "attempts"),
        workspace_root=str(work / "work"),
        address_spaces={"repository-relative": str(_REPO)},
    )

    subject = study(build())
    print(subject.summary(), "\n")
    print("Note: no corner appears above. The plan cannot name them, because\n"
          "the corner list is a result rather than a declaration.\n")

    document = subject.document
    run = subject.submit(site=site, watch=True)

    report = render_report(
        run, fingerprints=site.fingerprints(document), document=document
    )
    work.mkdir(parents=True, exist_ok=True)
    (work / "report.md").write_text(report, encoding="utf-8")
    (work / "report.json").write_text(
        json.dumps(run.value, indent=2, default=str), encoding="utf-8"
    )

    print()
    print(report)
    print(f"deliverable: {work / 'report.md'}")
    return 0 if run.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
