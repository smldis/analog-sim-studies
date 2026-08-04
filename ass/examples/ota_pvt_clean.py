"""The OTA/PVT study reduced to the simulation path, with a written deliverable.

    python examples/ota_pvt_clean.py

`ota_pvt.py` carries the whole reference, structural analysis included. This is
the same study with SPICE Canonical and Netlist Decomposition removed, leaving
what a PVT sign-off actually is: render the corners, simulate them, measure
them, check them against limits, and hand someone a report.

Two things differ beyond the deletions.

**Sidecar fans out, not the flow.** The corners are not written here. They are
read from the edit file's own ``PARAM_SETS`` at authoring time, expanded through
sidecar's own ``expand_param_matrix``, and rendered by a *single* ``prepare``
invocation. The edit file is the one place a corner is declared; adding one
there adds it to the study.

The trade is real and worth stating: one invocation that renders every corner is
one unit of reuse. Editing a single corner's parameters re-renders all of them,
where `ota_pvt.py`'s per-corner prepare re-rendered only the corner that moved.
Simulation is where the time goes and that stays per corner either way, so this
is cheap here — but on a study whose rendering is expensive it would not be.

**It writes a deliverable.** ``report.md`` is the artifact a person is given:
the verdict, the corner table, the limits applied, and the provenance —
including each declared source's content fingerprint, so the report says which
inputs produced it rather than asserting a date.
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
    artifacts,
    codec,
    file,
    flow,
    input_artifact,
    local,
    materialization,
    operation,
    parameter,
    plan,
    returned,
    shell,
    study,
    sweep,
)
from sidecar_edits.render import (  # noqa: E402
    RenderPlan,
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

SIDE_CAR_BASE = artifact("sidecar-base-directory")
SIDE_CAR_EDITS = artifact("sidecar-edit-file")
PREPARED_RUNS = artifact("prepared-simulation-directory")
SIMULATOR_RAW = artifact("simulator-raw-results")
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


def jobs_of(render_plan: RenderPlan) -> list[dict[str, Any]]:
    """Every corner this edit file fans out to, by sidecar's own expansion.

    Param sets crossed with the param matrix, which is what ``sidecar-edits``
    means by a job. One definition, called twice: once while authoring, to name
    the invocations, and once while rendering, to produce them. If those two
    ever disagreed the study would simulate decks it never rendered, so they
    are not allowed to be two functions.
    """

    jobs: list[dict[str, Any]] = []
    for param_set in render_plan.param_sets:
        for case in expand_param_matrix(render_plan.param_matrix):
            name = param_set.name or "default"
            if case.suffix:
                name = f"{name}__{case.suffix}"
            jobs.append({"name": name, "params": {**param_set.params, **case.params}})
    return jobs


@operation(
    name="ota_pvt_clean.prepare",
    version="1",
    inputs={"base": SIDE_CAR_BASE, "edits": SIDE_CAR_EDITS},
    config={"jobs": parameter(list)},
    outputs={"runs": file("runs", kind="prepared-simulation-directory")},
)
def prepare(base, edits, out, *, jobs):
    """Render every corner in one go. Sidecar does the fan-out, not the flow.

    ``base`` is declared and not opened: the edit file reaches the base tree
    through its own ``BASE_DIR``, and declaring it is what makes editing the
    base netlist invalidate the study.

    ``jobs`` is config rather than something re-read here, so the Plan states
    exactly which corners will be rendered and with what — inspectable before
    anything is spent, and part of this invocation's identity.
    """

    del base  # reached through the edit file's own BASE_DIR; declared for identity
    render_plan = load_editfile(Path(edits))
    out.runs.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        render_job(render_plan, dict(job["params"]), out.runs / job["name"],
                   label=job["name"])


@operation(
    name="ota_pvt_clean.simulate_ac",
    version="1",
    inputs={"runs": PREPARED_RUNS},
    config={"point_id": parameter(str), "analysis": parameter(str)},
    outputs={"raw": file("ota_ac.raw", kind="simulator-raw-results")},
    # Give the site an `lsf` transport and this line places each corner on its
    # own job:  policy=lsf(cores=1, memory_mb=2048, licences={"ngspice": 1}),
    policy=local(),
)
def simulate_ac(runs, out, *, point_id, analysis):
    """A launcher: the ngspice run is what the placement places."""

    if analysis != "ac":
        raise NotImplementedError(f"only the 'ac' analysis is implemented: {analysis!r}")
    deck = Path(runs) / point_id / DECK_NAME
    if not deck.exists():
        raise FileNotFoundError(f"prepared deck not found at {deck} for {point_id}")
    return shell("ngspice", "-b", "-r", out.raw, deck)


@operation(
    name="ota_pvt_clean.measure_ac",
    version="1",
    inputs={"raw": SIMULATOR_RAW, "definition": MEASUREMENT_DEFINITION},
    config={"point_id": parameter(str)},
    outputs={"measurements": returned(kind="ota-point-measurements")},
)
def measure_ac(raw, definition, *, point_id):
    """Gain, GBW and phase margin from the real raw file, never transcribed."""

    declared = json.loads(Path(definition).read_text(encoding="utf-8"))
    expected = {item["name"] for item in declared["metrics"]}

    measured = measure_ac_metrics(read_ac_raw(Path(raw)))
    missing = expected - measured.keys()
    if missing:
        raise RawFileError(f"measurement definition names {sorted(missing)}; not computed")
    return {"point_id": point_id, **measured}


@operation(
    name="ota_pvt_clean.evaluate_pvt",
    version="1",
    inputs={
        "measurements": artifacts("ota-point-measurements"),
        "limits": SPEC_LIMITS,
    },
    config={"point_ids": parameter(list)},
    outputs={"evaluation": returned(kind="ota-pvt-evaluation")},
)
def evaluate_pvt(measurements, limits, *, point_ids):
    """Check every corner against the declared limits. Refuses no metric."""

    declared = json.loads(Path(limits).read_text(encoding="utf-8"))
    limit_map = declared["limits"]

    points: dict[str, Any] = {}
    overall_pass = True
    for point_id, measurement in zip(point_ids, measurements):
        checks: dict[str, Any] = {}
        point_pass = True
        for metric, limit in limit_map.items():
            value = measurement.get(metric)
            minimum = limit.get("minimum")
            ok = value is not None and minimum is not None and value >= minimum
            checks[metric] = {"value": value, "minimum": minimum, "pass": ok}
            point_pass = point_pass and ok
        points[point_id] = {
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


@flow(name="ota_pvt_clean.study", version="1")
def pvt_study(base, edits, definition, limits, jobs):
    """One render for every corner, then one simulation and measurement each."""

    prepared = prepare.options(key="prepare")(base, edits, jobs=jobs)

    measured = []
    for job in sweep(jobs, key=lambda item: item["name"]):
        raw = simulate_ac(prepared, point_id=job["name"], analysis="ac")
        measured.append(measure_ac(raw, definition, point_id=job["name"]))

    evaluation = evaluate_pvt.options(key="evaluate")(
        measured, limits, point_ids=[job["name"] for job in jobs]
    )
    return {"evaluation": evaluation.evaluation}


def build(edits_path: Path):
    """Author the study, with the corners read from the edit file itself.

    The edit file is opened here, while authoring, which is why the plan can
    name every corner before anything runs. Note what that costs: the author
    needs the address resolved before a `Site` exists to resolve it, so the
    locator is turned into a path twice — once here, once by the site. Worth
    knowing; not worth a mechanism yet.
    """

    jobs = jobs_of(load_editfile(edits_path))
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
            jobs,
        )
    return draft.finish(outputs=outputs)


# ---------------------------------------------------------------------------
# ngspice AC raw reading. No third-party dependency: a short ASCII header, then
# little-endian complex doubles, one (real, imag) pair per variable per point.
# ---------------------------------------------------------------------------

_BINARY_MARKER = b"Binary:\n"


class RawFileError(ValueError):
    """The raw file is not the AC/complex shape this reader expects.

    Refusing beats guessing: a measurement computed from misread bytes is worse
    than no measurement.
    """


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
    run,
    *,
    jobs: list[dict[str, Any]],
    fingerprints: Mapping[str, str],
    document: Mapping[str, Any],
) -> str:
    """Write what a person is handed: verdict, corners, limits, provenance.

    Ordinary post-processing over what ``submit`` already returned. It reads no
    result to decide what runs next, so it is not the result-dependent control
    the Plan is kept free of.
    """

    evaluation = run.value or {}
    points = evaluation.get("points", {})
    limits = evaluation.get("limits", {})
    verdict = "PASS" if evaluation.get("overall_pass") else "FAIL"

    lines = [
        "# OTA PVT sign-off",
        "",
        f"**Verdict: {verdict}** — {len(points)} corners, "
        f"{len(limits)} limits, status `{evaluation.get('status')}`.",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        "from a plan that named every corner before anything ran.",
        "",
        "## Corners",
        "",
    ]

    header = ["corner"] + [f"{label} ({unit})" for _, label, unit, _, _ in _METRICS]
    lines.append("| " + " | ".join(header + ["verdict"]) + " |")
    lines.append("|" + "---|" * (len(header) + 1))
    for job in jobs:
        name = job["name"]
        point = points.get(name, {})
        measured = point.get("measurements", {})
        cells = [f"`{name}`"]
        for key, _, _, scale, form in _METRICS:
            value = measured.get(key)
            cells.append(form.format(value / scale) if value is not None else "—")
        cells.append("pass" if point.get("pass") else "**fail**")
        lines.append("| " + " | ".join(cells) + " |")

    lines += ["", "## Limits applied", "", "| metric | minimum |", "|---|---|"]
    for metric, limit in sorted(limits.items()):
        lines.append(f"| `{metric}` | {limit.get('minimum')} |")

    lines += [
        "",
        "## Corner parameters",
        "",
        "Read from the edit file, not written into the study.",
        "",
    ]
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
        f"{len(document.get('sources', []))} declared sources.",
        "",
        "### Inputs, by content",
        "",
        "| source | fingerprint |",
        "|---|---|",
    ]
    for source in document.get("sources", []):
        locator = (source.get("address") or {}).get("locator", "?")
        digest = fingerprints.get(source["id"], "—")
        lines.append(f"| `{locator}` | `{digest}` |")

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

    work = _HERE / "_runs" / "ota-clean"
    site = Site(
        root=str(work / "attempts"),
        workspace_root=str(work / "work"),
        address_spaces={"repository-relative": str(_REPO)},
    )

    jobs = jobs_of(load_editfile(_REPO / PVT_EDITS_LOCATOR))
    print(f"{len(jobs)} corners from the edit file: "
          f"{', '.join(job['name'] for job in jobs)}\n")

    subject = study(build(_REPO / PVT_EDITS_LOCATOR))
    print(subject.summary(), "\n")

    document = subject.document
    run = subject.submit(site=site, watch=True)

    report = render_report(
        run, jobs=jobs, fingerprints=site.fingerprints(document), document=document
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
