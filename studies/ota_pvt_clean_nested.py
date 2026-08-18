"""The corner set is a result — and the corners are still invocations.

    python studies/ota_pvt_clean_nested.py

`ota_pvt_clean.py` reads the edit file while authoring, so the Plan can name one
simulation per corner. Moving that read into the graph makes the corner list a
*result*, and a Plan states what will run before anything runs — so the outer
plan cannot name them.

The way out is not to give up the fan-out. It is to stop assuming one plan:

    described = load_edit_file(edits)     # operation 1
    jobs      = expand_jobs(described)    # operation 2
    result    = run_corner_study(jobs, …) # operation 3 — authors a Plan and runs it

`run_corner_study` is one invocation of the outer plan. Inside it, the jobs are
an ordinary Python value, so it authors a second Plan that names one prepare,
one simulate and one measure *per corner*, and submits it. Per-corner identity,
placement, reuse and observability all come back — they belong to the inner
plan, which is complete and inspectable before it spends anything, exactly like
the outer one.

Nothing here is result-dependent control. No plan branches on its own results.
Plans are *staged*: each one is fully determined at the moment it is authored,
and the later stage is authored after the earlier stage has produced its
values. The invariant holds per plan, which is where it was always stated.

What this buys over collapsing the fan-out into monolithic operations:

* each corner is its own attempt. Tightening a spec limit reruns the outer
  `corners` invocation, which re-authors stage two — and stage two then reuses
  nine of its ten invocations, running only the evaluation. Every simulation
  survives a change to the thing that judges simulations.
* each corner can take its own placement, because `simulate_ac` returns
  `shell(...)` again and the inner run binds it;
* the inner plan document is a declared output of the outer invocation, so what
  the second stage decided to run is recorded rather than inferred.

What it does *not* buy, measured rather than assumed: **adding a corner still
reruns every corner.** `prepare_corner` declares the edit file as an input, a
source is fingerprinted whole, and that file carries two independent things —
which corners exist, and how every corner is edited. Adding a corner changes the
fingerprint, so the system correctly concludes that every corner's render might
have changed. It is right; the declaration is too coarse.

The staged shape is where that becomes fixable, which is worth noticing. `load_
edit_file` already separates the param sets from the rest of the file. If
stage two's corners depended on the *edit recipe* rather than on the file that
carries it, adding a corner would leave the others alone. Nothing here does that
yet — it needs a way to declare "this part of that source", which does not
exist.

The wart, stated rather than hidden: the inner records root arrives as config,
which puts a machine path into the outer plan's identity. An operation that
runs a study needs to know its site, and today the only way to tell it is to
author the answer. See `docs/vision/open-concepts.md`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from hashlib import blake2b
import cmath
import json
import math
import shutil
import struct
import sys

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "hedloom" / "src"))
for _source in (
    _REPO / "hedloom" / "flow" / "src",
    _REPO / "hedloom" / "exec" / "src",
    _REPO / "hedloom" / "run" / "src",
    _REPO / "sidecar-edits" / "src",
):
    sys.path.insert(0, str(_source))

from hedloom import (  # noqa: E402
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
    returned,
    shell,
    study,
    sweep,
)
from hedloom_run.site import fingerprint_file  # noqa: E402
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

SIDE_CAR_BASE = artifact("sidecar-base-directory")
SIDE_CAR_EDITS = artifact("sidecar-edit-file")
RENDER_PLAN = artifact("sidecar-render-plan")
SIDECAR_JOBS = artifact("sidecar-jobs")
PREPARED_RUN = artifact("prepared-simulation-directory")
SIMULATOR_RAW = artifact("simulator-raw-results")
MEASUREMENT_DEFINITION = artifact("ota-measurement-definition")
POINT_MEASUREMENTS = artifact("ota-point-measurements")
SPEC_LIMITS = artifact("ota-specification-limits")
STUDY_RESULT = artifact("ota-pvt-study-result")

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

_SOURCES = (
    ("base", BASE_DIRECTORY_LOCATOR, SIDE_CAR_BASE, REPOSITORY_DIRECTORY_TREE),
    ("edits", PVT_EDITS_LOCATOR, SIDE_CAR_EDITS, REPOSITORY_PYTHON_SOURCE),
    ("definition", MEASUREMENT_DEFINITION_LOCATOR, MEASUREMENT_DEFINITION,
     REPOSITORY_JSON),
    ("limits", SPEC_LIMITS_LOCATOR, SPEC_LIMITS, REPOSITORY_JSON),
)


def _declare_sources():
    """The four external inputs, declared identically in both stages."""

    return {
        name: input_artifact(
            address("repository-relative", locator),
            artifact=kind,
            materialized_as=how,
        )
        for name, locator, kind, how in _SOURCES
    }


# ---------------------------------------------------------------------------
# Stage one: read the edit file, expand it. Both are recorded invocations, so
# nothing about the corners is known outside the graph.
# ---------------------------------------------------------------------------


@operation(
    name="ota_pvt_nested.load_edit_file",
    version="1",
    inputs={"edits": SIDE_CAR_EDITS},
    outputs={"described": returned(kind="sidecar-render-plan")},
)
def load_edit_file(edits):
    """Read the edit file into a JSON-safe description of what it declares.

    Returned rather than kept whole: every result is journaled as JSON before an
    output is inspected, so a live `RenderPlan` could not cross this boundary.
    """

    render_plan = load_editfile(Path(edits))
    return {
        "editfile": str(render_plan.editfile_path),
        "param_sets": [
            {"name": item.name, "description": item.description,
             "params": dict(item.params)}
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
    """Sidecar's own fan-out: param sets crossed with the param matrix."""

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
# Stage two's operations. Ordinary per-corner work — the same shape
# `ota_pvt_clean.py` authors directly, authored here one stage later.
# ---------------------------------------------------------------------------


@operation(
    name="ota_pvt_nested.prepare_corner",
    version="1",
    inputs={"base": SIDE_CAR_BASE, "edits": SIDE_CAR_EDITS},
    config={"name": parameter(str), "params": parameter(dict)},
    outputs={"run": file("run", kind="prepared-simulation-directory")},
)
def prepare_corner(base, edits, out, *, name, params):
    """Render one corner. Its own invocation, so its own unit of reuse."""

    del base  # reached through the edit file's own BASE_DIR; declared for identity
    render_job(load_editfile(Path(edits)), dict(params), out.run, label=name)


@operation(
    name="ota_pvt_nested.simulate_ac",
    version="1",
    inputs={"run": PREPARED_RUN},
    config={"point_id": parameter(str), "analysis": parameter(str)},
    outputs={"raw": file("ota_ac.raw", kind="simulator-raw-results")},
    # Per corner again, so this is placeable:
    #   policy=lsf(cores=1, memory_mb=2048, licences={"ngspice": 1}),
    policy=local(),
)
def simulate_ac(run, out, *, point_id, analysis):
    """A launcher: the ngspice run is what the placement places."""

    if analysis != "ac":
        raise NotImplementedError(f"only the 'ac' analysis is implemented: {analysis!r}")
    deck = Path(run) / DECK_NAME
    if not deck.exists():
        raise FileNotFoundError(f"prepared deck not found at {deck} for {point_id}")
    return shell("ngspice", "-b", "-r", out.raw, deck)


@operation(
    name="ota_pvt_nested.measure_ac",
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
    name="ota_pvt_nested.evaluate_pvt",
    version="1",
    inputs={"measurements": artifacts("ota-point-measurements"), "limits": SPEC_LIMITS},
    config={"point_ids": parameter(list)},
    outputs={"evaluation": returned(kind="ota-pvt-evaluation")},
)
def evaluate_pvt(measurements, limits, *, point_ids):
    """Check every corner against the declared limits."""

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
            "measurements": measurement, "checks": checks, "pass": point_pass
        }
        overall_pass = overall_pass and point_pass

    return {
        "status": declared.get("status"),
        "limits": limit_map,
        "points": points,
        "overall_pass": overall_pass,
    }


@flow(name="ota_pvt_nested.corners", version="1")
def corner_sweep(base, edits, definition, limits, jobs):
    """One prepare, simulate and measure per corner, then one evaluation."""

    measured = []
    for job in sweep(jobs, key=lambda item: item["name"]):
        run = prepare_corner(base, edits, name=job["name"], params=job["params"])
        raw = simulate_ac(run, point_id=job["name"], analysis="ac")
        measured.append(measure_ac(raw, definition, point_id=job["name"]))

    evaluation = evaluate_pvt.named("evaluate")(
        measured, limits, point_ids=[job["name"] for job in jobs]
    )
    return {"evaluation": evaluation.evaluation}


@study(default_policy=local())
def corner_study(jobs: list[dict[str, Any]]):
    """Stage two. Ordinary authoring — the jobs are just a value here."""

    sources = _declare_sources()
    return corner_sweep.named("corners")(
        sources["base"], sources["edits"], sources["definition"],
        sources["limits"], jobs,
    )


# ---------------------------------------------------------------------------
# The third member of the outer flow: an invocation that authors a Plan.
# ---------------------------------------------------------------------------


@operation(
    name="ota_pvt_nested.run_corner_study",
    version="1",
    inputs={
        "base": SIDE_CAR_BASE,
        "edits": SIDE_CAR_EDITS,
        "definition": MEASUREMENT_DEFINITION,
        "limits": SPEC_LIMITS,
        "jobs": SIDECAR_JOBS,
    },
    config={"records_root": parameter(str), "workspace_root": parameter(str)},
    outputs={
        # One returned output, not two: a body returns one object, and every
        # value-bound output would be handed all of it. So this carries the
        # whole of what stage two produced, and is named for that.
        "result": returned(kind="ota-pvt-study-result"),
        "plan": file("corner-plan.json", kind="hedloom-plan-document"),
    },
)
def run_corner_study(
    base, edits, definition, limits, jobs, out, *, records_root, workspace_root
):
    """Author the corner plan from the jobs, run it, and answer with its result.

    This is the whole point. `jobs` is a value here, so authoring a Plan over it
    is ordinary authoring: the inner plan names one prepare, one simulate and
    one measure per corner, and is complete and inspectable before it spends
    anything, exactly like the plan that contains this invocation.

    The inner records live at `records_root`, which is *outside* this attempt's
    workspace on purpose. Put them inside and every inner attempt would be
    thrown away whenever this invocation's own digest moved — which it does the
    moment a corner is added. Kept outside, adding a corner re-authors the inner
    plan, and the corners that did not change are found by content and reused.

    The inner plan document is a declared output, so what the second stage
    decided to run is recorded rather than inferred from what happened.
    """

    inner = corner_study(list(jobs))
    out.plan.write_text(
        json.dumps(inner.document, indent=2, default=str), encoding="utf-8"
    )

    # The inner site resolves the same address space the outer one does. The
    # repository root is recovered from a delivered path and the locator it was
    # delivered for: the executor hands a body its inputs, not its site.
    repository = _root_of(Path(edits), PVT_EDITS_LOCATOR)
    site = Site(
        root=records_root,
        workspace_root=workspace_root,
        address_spaces={"repository-relative": str(repository)},
    )

    run = inner.submit(
        site=site,
        on_event=lambda outcome: print(
            f"      inner | {outcome.authored_key:28} "
            f"{'reused' if outcome.reused else 'ran   '}  {outcome.outcome}"
        ),
    )
    if not run.succeeded:
        raise RuntimeError(f"the corner study failed:\n{run.summary()}")

    return {
        "evaluation": run.value,
        "invocations": [
            {
                "authored_key": outcome.authored_key,
                "operation": outcome.operation,
                "placement": outcome.placement,
                "outcome": outcome.outcome,
                "reused": outcome.reused,
            }
            for outcome in run.report.outcomes
        ],
    }


def _root_of(delivered: Path, locator: str) -> Path:
    """Recover the address space root a delivered path was resolved under."""

    depth = len(Path(locator).parts)
    return delivered.resolve().parents[depth - 1]


@operation(
    name="ota_pvt_nested.report",
    version="1",
    inputs={
        "result": STUDY_RESULT,
        "jobs": SIDECAR_JOBS,
        "base": SIDE_CAR_BASE,
        "edits": SIDE_CAR_EDITS,
        "definition": MEASUREMENT_DEFINITION,
        "limits": SPEC_LIMITS,
    },
    outputs={
        "report": file("report.md", kind="ota-pvt-report"),
        "verdict": returned(kind="ota-pvt-verdict"),
    },
)
def report(result, jobs, base, edits, definition, limits, out):
    """The deliverable, as work rather than as an afterthought.

    Being an operation changes what the report *is*. It has an identity, so the
    same evidence produces the same report and a rerun that changes nothing
    reuses it rather than regenerating it with a new date. It declares the four
    sources as inputs, so it cannot describe inputs the study did not use. And
    it is a declared artifact of the study, not a side effect of the script that
    launched it.

    Two consequences, both deliberate:

    * **It cannot say what was reused.** Dispositions are the run's own
      bookkeeping, and an operation that read them would produce a different
      result on a rerun than on a reuse — the report would stop being a
      function of the evidence. Stage two's dispositions *are* here, because
      they travelled as data through `result`.
    * **A reused report keeps its original date.** That is right: the date says
      when this evidence was produced, and nothing about it has changed.

    It also recomputes the source fingerprints, which its own identity already
    depends on. An operation cannot see the identity of its own inputs, so the
    one number that says which inputs produced this report has to be derived a
    second time. Worth naming; nothing to do about it here.
    """

    evaluation = result.get("evaluation") or {}
    text = _render_report(
        evaluation=evaluation,
        jobs=list(jobs),
        inner=result.get("invocations") or [],
        sources={
            BASE_DIRECTORY_LOCATOR: base,
            PVT_EDITS_LOCATOR: edits,
            MEASUREMENT_DEFINITION_LOCATOR: definition,
            SPEC_LIMITS_LOCATOR: limits,
        },
    )
    out.report.write_text(text, encoding="utf-8")
    return {
        "overall_pass": bool(evaluation.get("overall_pass")),
        "corners": len(evaluation.get("points") or {}),
        "status": evaluation.get("status"),
    }


@flow(name="ota_pvt_nested.study", version="1")
def pvt_study(base, edits, definition, limits, *, records_root, workspace_root):
    """Read the edit file, expand it, plan and run it, and write the report."""

    described = load_edit_file.named("load")(edits)
    jobs = expand_jobs.named("expand")(described)
    result = run_corner_study.named("corners")(
        base, edits, definition, limits, jobs,
        records_root=records_root, workspace_root=workspace_root,
    )
    written = report.named("report")(
        result.result, jobs, base, edits, definition, limits
    )
    return {"report": written.report, "verdict": written.verdict}


@study(default_policy=local())
def pvt(*, records_root: str, workspace_root: str):
    """Stage one. Nothing about the corners is read here."""

    sources = _declare_sources()
    return pvt_study.named("ota-pvt")(
        sources["base"], sources["edits"], sources["definition"],
        sources["limits"],
        records_root=records_root,
        workspace_root=workspace_root,
    )


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


def _fingerprint(path: Path) -> str:
    """Identify one declared input by content, as the site does when planning."""

    if path.is_dir():
        digest = blake2b(digest_size=16)
        for item in sorted(path.rglob("*")):
            if item.is_file():
                digest.update(str(item.relative_to(path)).encode())
                digest.update(fingerprint_file(item).encode())
        return f"tree:{digest.hexdigest()}"
    return fingerprint_file(path)


def _render_report(
    *,
    evaluation: Mapping[str, Any],
    jobs: list[dict[str, Any]],
    inner: list[Mapping[str, Any]],
    sources: Mapping[str, str],
) -> str:
    """The deliverable, built from what the two stages produced."""

    points = evaluation.get("points", {})
    limits = evaluation.get("limits", {})
    verdict = "PASS" if evaluation.get("overall_pass") else "FAIL"

    lines = [
        "# OTA PVT sign-off",
        "",
        f"**Verdict: {verdict}** — {len(points)} corners, "
        f"{len(limits)} limits, status `{evaluation.get('status')}`.",
        "",
        f"Evidence produced {datetime.now(timezone.utc).isoformat(timespec='seconds')}. "
        "The corner set was produced by the graph; the corners were then planned "
        "and run as a study of their own; this report is an operation of that "
        "same study, so it is reused rather than rewritten when nothing changed.",
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
        "Every input below is declared by the operation that wrote this report, "
        "so it cannot describe an input the study did not use.",
        "",
        "### Inputs, by content",
        "",
        "| source | fingerprint |",
        "|---|---|",
    ]
    for locator, delivered in sources.items():
        lines.append(f"| `{locator}` | `{_fingerprint(Path(delivered))}` |")

    lines += [
        "",
        "### What stage two ran",
        "",
        "Stage one's own dispositions are absent deliberately: they are the "
        "run's bookkeeping, and a report that read them would say something "
        "different on a rerun than on a reuse.",
        "",
        "| invocation | operation | placement | outcome | |",
        "|---|---|---|---|---|",
    ]
    for item in inner:
        lines.append(
            f"| `{item['authored_key']}` | `{item['operation']}` | "
            f"{item['placement'] or '—'} | {item['outcome']} | "
            f"{'reused' if item['reused'] else 'ran'} |"
        )

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

    subject = pvt(
        records_root=str(work / "corner-attempts"),
        workspace_root=str(work / "corner-work"),
    )
    print(subject.summary(), "\n")
    print("No corner appears above: stage one cannot name them, because the\n"
          "corner list is a result. `corners` authors stage two, which can.\n")

    run = subject.submit(site=site, watch=True)
    if not run.succeeded:
        print(run.summary())
        return 1

    # The deliverable is an artifact of the study, not something this script
    # produced afterwards. All that is left to do is say where it is.
    written = Path(run["report"].artifacts["report"]["address"])
    print()
    print(written.read_text(encoding="utf-8"))
    print(f"verdict:     {run.value}")
    print(f"deliverable: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
