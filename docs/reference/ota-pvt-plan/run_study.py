"""Run the OTA/PVT reference study for real, end to end, against ngspice.

``ota_pvt_plan.py`` stays exactly what it always was: a Plan declaration whose
operation bodies raise ``NotImplementedError``. That is the right shape for a
plan-only document, and this module does not touch it. What was still missing
is what ``ass-run``'s own README calls the other half: "The Plan declares
meaning; the run binds mechanism." This module is that binding, in the same
shape as ``ass-exec/examples/planned_characterization.py`` -- a separate
implementation for every operation name, handed to a transport, walked by
``ass_run.run_plan``.

Invariant this binding exists to hold: every declared output that a step
claims to produce is either a real file this process can point to afterward,
or an in-memory Python value handed directly to the next in-process step.
Nothing here invents a measurement, a passing spec check, or a materialized
file that does not exist -- a step that cannot honestly answer raises, and the
invocation is recorded as failed rather than papered over.

Two boundaries this script deliberately does not resolve for a caller:

* The four external sources (base directory, edit file, measurement
  definition, spec limits) are declared in the Plan as repository-relative
  addresses, but ``ass_run.binding.resolve`` only threads *output* references
  between invocations -- by design, source addresses are left to whatever
  reads them. This script reads them itself, from the same locators
  ``ota_pvt_plan.py`` authored, rather than trusting the (always ``None``)
  resolved input.
* The Plan's only declared policy is ``reference.plan-only`` (a documentation
  marker recorded by ``PLAN_DECLARATION_POLICY``/``SIMULATOR_BOUNDARY_POLICY``
  in ``ota_pvt_plan.py``, not a placement name). ``ass_run`` reads
  ``policy.name`` as the placement to route an invocation to, so this binding
  runs in single-transport mode (``transport=...``, not ``transports={...}``)
  rather than pretending a "local" placement was authored. See
  ``docs/vision/open-concepts.md`` for the finding this raised.

Usage, from the repository root, with every sibling source tree on the path::

    PYTHONPATH=ass-flow/src:ass-run/src:ass-exec/src:sidecar-edits/src:\\
spice-canonical/src:netlist-decomposition/src \\
      python docs/reference/ota-pvt-plan/run_study.py
"""

from __future__ import annotations

import cmath
import json
import math
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ass_exec.transport import InProcessTransport, Observation, SubmissionRefused
from ass_run import run_plan

from netlist_decomposition import BlockTag
from netlist_decomposition import decompose as decompose_blocks
from netlist_decomposition import suppress_false_stacks as suppress_false_stacks_fn
from sidecar_edits.render import load_editfile, render_job
from spice_canonical.canonical_netlist import (
    CanonicalNetlist,
    Circuit,
    Connection,
    Device,
    Parameter,
    from_file,
)

STUDY_DIR = Path(__file__).resolve().parent
REPO_ROOT = STUDY_DIR.parents[1]

PVT_EDITS_PATH = STUDY_DIR / "inputs" / "pvt_edits.py"
MEASUREMENT_DEFINITION_PATH = STUDY_DIR / "inputs" / "measurement_definition.json"
SPEC_LIMITS_PATH = STUDY_DIR / "inputs" / "spec_limits.json"

DEFAULT_ROOT = STUDY_DIR / "_runs" / "attempts"
DEFAULT_WORKSPACE_ROOT = STUDY_DIR / "_runs" / "work"
DEFAULT_REPORT_PATH = STUDY_DIR / "_runs" / "report.json"

PLAN_ID = "ota-pvt-study"

# Which declared outputs are real files this run should verify, and where each
# operation writes its result relative to its own attempt workdir.
DECLARED_OUTPUTS = {
    "reference.ota_pvt.prepare_run": {"run": {"path": "run"}},
    "reference.ota_pvt.simulate_ac": {"raw": {"path": "ota_ac.raw"}},
}


# --------------------------------------------------------------------------
# ngspice AC raw-file reading. No third-party dependency: the format is a
# short ASCII header followed by a binary block of little-endian complex
# doubles, one (real, imag) pair per variable per sweep point.
# --------------------------------------------------------------------------

_BINARY_MARKER = b"Binary:\n"


class RawFileError(ValueError):
    """The ngspice raw file is not the AC/complex shape this reader expects.

    Refusing here rather than guessing matters: a measurement silently
    computed from misread bytes would be worse than no measurement.
    """


def read_ac_raw(path: Path) -> dict[str, list[complex]]:
    """Read an ngspice ``-r`` AC-analysis raw file into named complex columns."""

    data = path.read_bytes()
    marker_at = data.find(_BINARY_MARKER)
    if marker_at == -1:
        raise RawFileError(f"{path}: no binary marker; not an ngspice -r raw file")

    header_lines = data[:marker_at].decode("ascii", errors="replace").splitlines()
    flags: str | None = None
    n_vars: int | None = None
    n_points: int | None = None
    variables: list[str] = []
    index = 0
    while index < len(header_lines):
        line = header_lines[index]
        if line.startswith("Flags:"):
            flags = line.split(":", 1)[1].strip()
        elif line.startswith("No. Variables:"):
            n_vars = int(line.split(":", 1)[1].strip())
        elif line.startswith("No. Points:"):
            n_points = int(line.split(":", 1)[1].strip())
        elif line.strip() == "Variables:" and n_vars is not None:
            for offset in range(1, n_vars + 1):
                variables.append(header_lines[index + offset].strip().split("\t")[1])
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
        point_base = point * n_vars * 16
        for var_index, name in enumerate(variables):
            real, imag = struct.unpack_from("<2d", body, point_base + var_index * 16)
            columns[name].append(complex(real, imag))
    return columns


def measure_ac_metrics(
    columns: Mapping[str, list[complex]],
    *,
    output_node: str = "v(out)",
    positive_input: str = "v(in_p)",
    negative_input: str = "v(in_n)",
) -> dict[str, float]:
    """Compute gain/GBW/phase-margin from a real AC sweep. Refuses, never guesses."""

    for name in (output_node, positive_input, negative_input, "frequency"):
        if name not in columns:
            raise RawFileError(f"raw file has no column {name!r}; have {sorted(columns)}")

    frequencies = [value.real for value in columns["frequency"]]
    gains_db: list[float] = []
    phases_deg: list[float] = []
    for out, pos, neg in zip(columns[output_node], columns[positive_input], columns[negative_input]):
        differential = pos - neg
        if differential == 0:
            raise RawFileError("zero differential AC excitation; cannot compute a gain")
        transfer = out / differential
        gains_db.append(20.0 * math.log10(abs(transfer)))
        phases_deg.append(math.degrees(cmath.phase(transfer)))

    dc_gain_db = gains_db[0]

    gain_bandwidth_hz: float | None = None
    phase_margin_deg: float | None = None
    for index in range(1, len(frequencies)):
        if gains_db[index - 1] > 0 >= gains_db[index]:
            log_f0, log_f1 = math.log10(frequencies[index - 1]), math.log10(frequencies[index])
            g0, g1 = gains_db[index - 1], gains_db[index]
            fraction = g0 / (g0 - g1)
            gain_bandwidth_hz = 10 ** (log_f0 + fraction * (log_f1 - log_f0))
            p0, p1 = phases_deg[index - 1], phases_deg[index]
            phase_margin_deg = 180.0 + (p0 + fraction * (p1 - p0))
            break

    if gain_bandwidth_hz is None:
        raise RawFileError("gain never crosses 0 dB across the swept band; cannot report GBW/PM")

    return {
        "dc_gain_db": dc_gain_db,
        "gain_bandwidth_hz": gain_bandwidth_hz,
        "phase_margin_deg": phase_margin_deg,
    }


# --------------------------------------------------------------------------
# Minimal JSON-safe serialization for the two in-memory sibling values that
# cross an invocation boundary: ``CanonicalNetlist``/``Circuit`` (SPICE
# Canonical) and the ``BlockTag`` tuple (Netlist Decomposition). Neither
# offers a portable representation today -- PLANNING.md records that as an
# explicit honest limitation. It turned out not to be optional: ``ass_run``
# always runs invocations at ``Durability.RECORDED``, and ``ass_exec``
# appends every observed result to a JSON journal line before an output is
# ever inspected, so an in-process return value that is not JSON-safe fails
# the invocation before this study's own logic ever sees it. Discovered by
# running this against real ngspice, not designed in advance -- see the
# report/open-concepts note this raised.
# --------------------------------------------------------------------------


def _serialize_circuit(circuit: Circuit) -> dict[str, Any]:
    return {
        "name": circuit.name,
        "pins": list(circuit.pins),
        "devices": [
            {
                "name": device.name,
                "type": device.type,
                "connections": [[c.pin, c.net] for c in device.connections],
                "parameters": [[p.name, p.value] for p in device.parameters],
            }
            for device in circuit.devices
        ],
    }


def _serialize_canonical(netlist: CanonicalNetlist) -> dict[str, Any]:
    return {
        "top": _serialize_circuit(netlist.top),
        "subcircuits": [_serialize_circuit(item) for item in netlist.subcircuits],
    }


def _deserialize_circuit(data: Mapping[str, Any]) -> Circuit:
    return Circuit(
        name=data["name"],
        pins=tuple(data["pins"]),
        devices=tuple(
            Device(
                name=item["name"],
                type=item["type"],
                connections=tuple(Connection(pin=c[0], net=c[1]) for c in item["connections"]),
                parameters=tuple(Parameter(name=p[0], value=p[1]) for p in item["parameters"]),
            )
            for item in data["devices"]
        ),
    )


def _serialize_block_tag(tag: BlockTag) -> dict[str, Any]:
    return {
        "id": tag.id,
        "kind": tag.kind,
        "members": sorted(tag.members),
        "roles": tag.roles,
        "nets": tag.nets,
        "properties": tag.properties,
        "rule": tag.rule,
        "level": tag.level,
    }


# --------------------------------------------------------------------------
# Real operation implementations, keyed by the Plan's operation names. Each
# accepts exactly the declared config and input names, plus an optional
# ``workdir`` this run's LocalTransport injects when it has one.
# --------------------------------------------------------------------------


def prepare_run_impl(
    base: Any,
    edits: Any,
    *,
    point_id: str,
    param_set: str,
    process: str,
    vdd_v: float,
    temp_c: int,
    workdir: str,
) -> str:
    """Real Sidecar Edits render: copy the base tree, apply the point's edits.

    ``base``/``edits`` arrive as ``None`` (see the module docstring); the real
    base directory and edit file are the same repository-relative locators
    ``ota_pvt_plan.py`` declared as sources. ``params`` is built from this
    call's own declared config -- the values that participate in this
    invocation's content-addressed identity -- not re-read from the edit
    file's own ``PARAM_SETS``, so that a config edit and a rerun agree on what
    changed.
    """

    del base, edits  # unresolved source references; read directly instead
    render_plan = load_editfile(PVT_EDITS_PATH)
    params = {
        "point_id": point_id,
        "param_set": param_set,
        "process": process,
        "vdd_v": vdd_v,
        "temp_c": temp_c,
    }
    output_dir = Path(workdir) / "run"
    render_job(render_plan, params, output_dir, label=point_id)
    return str(output_dir)


def canonicalize_deck_impl(
    run: str,
    *,
    deck_relpath: str,
    spice_format: str,
    top_name: str,
    workdir: str | None = None,
) -> dict[str, Any]:
    """Real SPICE Canonical extraction of the rendered corner's deck.

    Returns the JSON-safe serialization (see above), not the live
    ``CanonicalNetlist``: this invocation's result is journaled as JSON by
    ``ass_exec`` regardless of placement, and this is the first real,
    inspectable representation this artifact kind has had.
    """

    del workdir
    deck_path = Path(run) / deck_relpath
    netlist = from_file(deck_path, top_name=top_name, spice_format=spice_format)
    return _serialize_canonical(netlist)


def decompose_ota_impl(
    canonical: Mapping[str, Any],
    *,
    circuit_name: str,
    vdd_nets: Sequence[str],
    vss_nets: Sequence[str],
    max_level: int,
    suppress_false_stacks: bool,
    workdir: str | None = None,
) -> list[dict[str, Any]]:
    """Real Netlist Decomposition of the selected circuit.

    Reconstructs a real ``Circuit`` from ``canonicalize_deck``'s serialized
    output, decomposes it for real, and returns the JSON-safe tag list.
    """

    del workdir
    circuits = (canonical["top"], *canonical["subcircuits"])
    circuit_data = next((item for item in circuits if item["name"] == circuit_name), None)
    if circuit_data is None:
        raise ValueError(
            f"circuit {circuit_name!r} not found; have {[item['name'] for item in circuits]}"
        )
    circuit = _deserialize_circuit(circuit_data)
    tags = decompose_blocks(circuit, vdd_nets=vdd_nets, vss_nets=vss_nets, max_level=max_level)
    if suppress_false_stacks:
        tags = suppress_false_stacks_fn(tags)
    return [_serialize_block_tag(tag) for tag in tags]


def simulate_ac_impl(
    run: str,
    *,
    point_id: str,
    process: str,
    vdd_v: float,
    temp_c: int,
    simulator_profile: str,
    analysis: str,
    workdir: str,
) -> str:
    """Real ngspice batch invocation. A nonzero exit or a missing raw file refuses."""

    del process, vdd_v, temp_c, simulator_profile  # already baked into the rendered deck
    if analysis != "ac":
        raise NotImplementedError(f"only the 'ac' analysis is implemented; got {analysis!r}")

    deck_path = Path(run) / "ota_ac.cir"
    if not deck_path.exists():
        raise FileNotFoundError(f"prepared deck not found at {deck_path}")

    workdir_path = Path(workdir)
    raw_path = workdir_path / "ota_ac.raw"
    log_path = workdir_path / "ngspice.log"
    argv = ["ngspice", "-b", "-r", str(raw_path), str(deck_path)]
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    log_path.write_text(
        f"$ {' '.join(argv)}\n\n--- stdout ---\n{completed.stdout}\n"
        f"--- stderr ---\n{completed.stderr}\n",
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ngspice exited {completed.returncode} for {point_id}; see {log_path}"
        )
    if not raw_path.exists():
        raise RuntimeError(f"ngspice reported success but never wrote {raw_path}")
    return str(raw_path)


def measure_ac_impl(
    raw: str,
    definition: Any,
    *,
    point_id: str,
    workdir: str | None = None,
) -> dict[str, Any]:
    """Compute gain/GBW/phase-margin from the real raw file. Never transcribed."""

    del workdir
    del definition  # unresolved source reference; read directly instead
    declared = json.loads(MEASUREMENT_DEFINITION_PATH.read_text(encoding="utf-8"))
    expected_metrics = {item["name"] for item in declared["metrics"]}

    columns = read_ac_raw(Path(raw))
    measured = measure_ac_metrics(columns)

    missing = expected_metrics - measured.keys()
    if missing:
        raise RawFileError(f"measurement definition names {sorted(missing)}; not computed")

    return {"point_id": point_id, **measured}


def evaluate_pvt_impl(
    measurements: Sequence[Mapping[str, Any]],
    decompositions: Sequence[list[Mapping[str, Any]]],
    limits: Any,
    *,
    point_ids: Sequence[str],
    workdir: str | None = None,
) -> dict[str, Any]:
    """Check every point's measurements against the spec limits. Refuses no metric."""

    del workdir
    del limits  # unresolved source reference; read directly instead
    declared = json.loads(SPEC_LIMITS_PATH.read_text(encoding="utf-8"))
    limit_map = declared["limits"]

    points: dict[str, Any] = {}
    overall_pass = True
    for point_id, measurement, decomposition in zip(point_ids, measurements, decompositions):
        checks: dict[str, Any] = {}
        point_pass = True
        for metric, limit in limit_map.items():
            value = measurement.get(metric)
            minimum = limit.get("minimum")
            ok = value is not None and minimum is not None and value >= minimum
            checks[metric] = {"value": value, "minimum": minimum, "pass": ok}
            point_pass = point_pass and ok

        kind_counts: dict[str, int] = {}
        for tag in decomposition:
            kind_counts[tag["kind"]] = kind_counts.get(tag["kind"], 0) + 1

        points[point_id] = {
            "measurements": measurement,
            "checks": checks,
            "pass": point_pass,
            "decomposition_kinds": kind_counts,
        }
        overall_pass = overall_pass and point_pass

    return {
        "status": declared.get("status"),
        "points": points,
        "overall_pass": overall_pass,
    }


IMPLEMENTATIONS = {
    "reference.ota_pvt.prepare_run": prepare_run_impl,
    "reference.ota_pvt.canonicalize_deck": canonicalize_deck_impl,
    "reference.ota_pvt.decompose_ota": decompose_ota_impl,
    "reference.ota_pvt.simulate_ac": simulate_ac_impl,
    "reference.ota_pvt.measure_ac": measure_ac_impl,
    "reference.ota_pvt.evaluate_pvt": evaluate_pvt_impl,
}


class LocalTransport(InProcessTransport):
    """In-process execution that also hands each attempt its own workdir.

    Invariant: correct iff the callable receives exactly its declared config,
    the resolved values of its declared inputs, and -- only when this run
    declared a workspace -- the one directory this specific attempt, and no
    other attempt, may write into. It decides no readiness and owns no
    identity; both stay with ``ass_run``/``ass_exec`` exactly as for any other
    transport.
    """

    name = "local"

    def __init__(self, implementations: Mapping[str, Any]) -> None:
        super().__init__(implementations)
        # Wall-clock per invocation, keyed by the plan's invocation id rather
        # than the attempt identity: report-only instrumentation, kept out of
        # the journaled record entirely so it cannot affect identity or reuse.
        self.durations_s: dict[str, float] = {}

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        operation = bundle.get("operation")
        implementation = self._implementations.get(operation)
        if implementation is None:
            raise SubmissionRefused(f"no local implementation bound for operation {operation!r}")

        arguments = dict(bundle.get("arguments", {}))
        arguments.update(bundle.get("resolved_inputs", {}))
        workdir = bundle.get("workdir")
        if workdir is not None:
            arguments["workdir"] = workdir

        started = time.perf_counter()
        try:
            value = implementation(**arguments)
        except Exception as error:  # a failed corner is a recordable outcome
            self._results[identity] = Observation(
                "failed", {"error": f"{type(error).__name__}: {error}"}
            )
        else:
            self._results[identity] = Observation("succeeded", {"value": value})
        finally:
            invocation_id = bundle.get("invocation")
            if invocation_id:
                self.durations_s[invocation_id] = time.perf_counter() - started
        return {"transport": self.name, "identity": identity, "workdir": workdir}


def run_once(
    document: Mapping[str, Any],
    *,
    root: Path = DEFAULT_ROOT,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    on_event=None,
):
    """Execute one Plan document with the real local binding.

    Single-transport mode (``transport=``, not ``transports={...}``) is
    deliberate: this Plan's only declared policy is the ``reference.plan-only``
    documentation marker, not an authored placement name, so there is no
    "local" key to route on. See the module docstring.
    """

    transport = LocalTransport(IMPLEMENTATIONS)
    report = run_plan(
        document,
        transport,
        plan_id=PLAN_ID,
        root=str(root),
        workspace_root=str(workspace_root),
        outputs=DECLARED_OUTPUTS,
        on_event=on_event,
    )
    return report, transport.durations_s


def write_report(
    *,
    report,
    durations_s: Mapping[str, float],
    evaluation: Mapping[str, Any] | None,
    total_s: float,
    path: Path,
) -> None:
    """Materialize this run's results as a file. Stdout is diagnostics only.

    Not a Plan operation: adding one would change the reference's declared
    invocation/edge/output cardinality, which ``PLANNING.md`` reserves for
    coordinated review. This is ordinary post-processing in the binding
    script, over data ``run_plan`` already returned -- it does not read a
    result and decide what to run next, so it is not the result-dependent
    control ``ass-run`` is kept free of.
    """

    invocations = [
        {
            "authored_key": outcome.authored_key,
            "operation": outcome.operation,
            "disposition": outcome.disposition,
            "outcome": outcome.outcome,
            "duration_s": durations_s.get(outcome.invocation_id),
            "error": outcome.error,
        }
        for outcome in report.outcomes
    ]
    document = {
        "plan_id": PLAN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "succeeded": report.succeeded,
        "total_wall_clock_s": total_s,
        "invocations": invocations,
        "evaluation": evaluation,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, default=str), encoding="utf-8")
    if not path.exists():
        # Mirrors the declared-output rule this study holds every simulator
        # step to: a report that claims to exist and does not is a failure,
        # not a detail to shrug off.
        raise RuntimeError(f"wrote {path} but it is not there afterward")


def main() -> int:
    sys.path.insert(0, str(STUDY_DIR))
    import ota_pvt_plan  # noqa: E402  (path must be set up first)

    document = ota_pvt_plan.build_plan().to_data()
    started = time.perf_counter()
    report, durations_s = run_once(document)
    total_s = time.perf_counter() - started

    print(report.summary())
    print()
    for outcome in report.outcomes:
        elapsed = durations_s.get(outcome.invocation_id)
        tag = outcome.invocation_id.rsplit(":", 1)[-1][:8]
        label = f"{outcome.authored_key}[{tag}]"
        if elapsed is not None:
            print(f"  {label:<28} {elapsed * 1000:8.1f} ms  ({outcome.disposition})")
        else:
            print(f"  {label:<28} {'(reused)':>11}  ({outcome.disposition})")
    print(f"  {'total (wall clock)':<28} {total_s * 1000:8.1f} ms")
    print()
    evaluation = next(
        (outcome.value for outcome in report.outcomes if outcome.authored_key == "evaluate-pvt"),
        None,
    )
    if evaluation is not None:
        print(json.dumps(evaluation, indent=2, default=str))

    write_report(
        report=report,
        durations_s=durations_s,
        evaluation=evaluation,
        total_s=total_s,
        path=DEFAULT_REPORT_PATH,
    )
    print(f"\nreport written: {DEFAULT_REPORT_PATH}")

    return 0 if report.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
