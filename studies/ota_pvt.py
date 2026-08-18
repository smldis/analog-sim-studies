"""The OTA/PVT reference study, as one file, against real ngspice.

    python studies/ota_pvt.py

This is the study that used to be two: ``ota_pvt_plan.py`` declared what the
work meant and every body raised ``NotImplementedError``; ``run_study.py`` then
supplied six hundred lines of implementations, command lines, output paths and
source locators whose only job was to agree with the first file. Every seam
between them was a place the study could run as something other than what was
authored.

Here the declaration and the body are the same statement. What that buys, in
the order you meet it below:

* ``@operation`` bodies really run, so nothing restates them elsewhere.
* Declared outputs are ``file(...)``/``returned(...)`` on the operation, so the
  path a body writes and the path the executor checks are one declaration.
* The four external inputs are ``input_artifact`` sources and arrive as real
  paths. ``run_study.py`` could not receive them -- it read them from
  module-level constants and wrote ``del base, edits  # unresolved source
  reference`` three times.
* ``simulate_ac`` returns ``shell(...)`` rather than calling a subprocess, so
  the ngspice run is the thing a placement places. Locally that is a child
  process bound to this one's lifetime; give the site an ``lsf`` transport and
  swap this operation's policy for ``lsf(cores=1, memory_mb=2048,
  licences={"ngspice": 1})`` and the same study puts each corner on its own job.
* ``sweep`` keys every call inside a point, so three operations across three
  points do not need nine hand-written keys.

Everything measured is measured: gain, GBW and phase margin come out of a real
ngspice AC sweep, and a step that cannot answer honestly raises rather than
inventing a number.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
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
    _REPO / "spice-canonical" / "src",
    _REPO / "netlist-decomposition" / "src",
):
    sys.path.insert(0, str(_source))

from hedloom import (  # noqa: E402
    Site,
    address,
    artifact,
    artifacts,
    file,
    flow,
    input_artifact,
    local,
    operation,
    parameter,
    returned,
    shell,
    study,
    sweep,
)
from netlist_decomposition import BlockTag  # noqa: E402
from netlist_decomposition import decompose as decompose_blocks  # noqa: E402
from netlist_decomposition import suppress_false_stacks as _suppress  # noqa: E402
from sidecar_edits.render import load_editfile, render_job  # noqa: E402
from spice_canonical.canonical_netlist import (  # noqa: E402
    CanonicalNetlist,
    Circuit,
    Connection,
    Device,
    Parameter,
    from_file,
)


class PVTPoint:
    """One ordered sentinel point. Plain, so the sweep key is an attribute."""

    __slots__ = ("key", "process", "vdd_v", "temp_c")

    def __init__(self, key: str, process: str, vdd_v: float, temp_c: int) -> None:
        self.key = key
        self.process = process
        self.vdd_v = vdd_v
        self.temp_c = temp_c


PVT_POINTS = (
    PVTPoint("tt_1v80_27c", "tt", 1.80, 27),
    PVTPoint("ss_1v62_125c", "ss", 1.62, 125),
    PVTPoint("ff_1v98_m40c", "ff", 1.98, -40),
)

# The same repository-relative locators the reference plan always declared.
# They are addresses, not paths: the site says what the address space means.
INPUTS = "docs/reference/ota-pvt-plan/inputs"
BASE_DIRECTORY_LOCATOR = f"{INPUTS}/base"
PVT_EDITS_LOCATOR = f"{INPUTS}/pvt_edits.py"
MEASUREMENT_DEFINITION_LOCATOR = f"{INPUTS}/measurement_definition.json"
SPEC_LIMITS_LOCATOR = f"{INPUTS}/spec_limits.json"

SIDE_CAR_BASE = artifact("sidecar-base-directory")
SIDE_CAR_EDITS = artifact("sidecar-edit-file")
PREPARED_RUN = artifact("prepared-simulation-directory")
CANONICAL_NETLIST = artifact("canonical-netlist")
OTA_DECOMPOSITION = artifact("ota-functional-decomposition")
SIMULATOR_RAW = artifact("simulator-raw-results")
MEASUREMENT_DEFINITION = artifact("ota-measurement-definition")
POINT_MEASUREMENTS = artifact("ota-point-measurements")
SPEC_LIMITS = artifact("ota-specification-limits")



# ---------------------------------------------------------------------------
# Operations. Each body is what the Plan names; nothing restates it elsewhere.
# ---------------------------------------------------------------------------


@operation(
    name="ota_pvt.prepare_run",
    version="1",
    inputs={"base": SIDE_CAR_BASE, "edits": SIDE_CAR_EDITS},
    config={
        "point_id": parameter(str),
        "param_set": parameter(str),
        "process": parameter(str),
        "vdd_v": parameter(float),
        "temp_c": parameter(int),
    },
    outputs={"run": file("run", kind="prepared-simulation-directory")},
)
def prepare_run(base, edits, out, *, point_id, param_set, process, vdd_v, temp_c):
    """Render this point's deck with Sidecar Edits, into this attempt's own dir.

    ``edits`` is the declared edit file, now delivered as a real path rather
    than read from a constant. ``base`` is declared and not opened here: the
    edit file reaches the base tree through its own ``BASE_DIR``, and declaring
    it is what makes editing the base netlist invalidate every point.

    ``params`` is built from this call's own declared config -- the values that
    are in this invocation's identity -- rather than re-read from the edit
    file's ``PARAM_SETS``, so a config edit and a rerun agree on what changed.
    """

    del base  # reached through the edit file's own BASE_DIR; declared for identity
    render_job(
        load_editfile(Path(edits)),
        {
            "point_id": point_id,
            "param_set": param_set,
            "process": process,
            "vdd_v": vdd_v,
            "temp_c": temp_c,
        },
        out.run,
        label=point_id,
    )


@operation(
    name="ota_pvt.canonicalize_deck",
    version="1",
    inputs={"run": PREPARED_RUN},
    config={
        "deck_relpath": parameter(str),
        "spice_format": parameter(str),
        "top_name": parameter(str),
    },
    outputs={"canonical": returned(kind="canonical-netlist")},
)
def canonicalize_deck(run, *, deck_relpath, spice_format, top_name):
    """Real SPICE Canonical extraction of the rendered corner's deck."""

    netlist = from_file(
        Path(run) / deck_relpath, top_name=top_name, spice_format=spice_format
    )
    return _serialize_canonical(netlist)


@operation(
    name="ota_pvt.decompose_ota",
    version="1",
    inputs={"canonical": CANONICAL_NETLIST},
    config={
        "circuit_name": parameter(str),
        "vdd_nets": parameter(list),
        "vss_nets": parameter(list),
        "max_level": parameter(int),
        "suppress_false_stacks": parameter(bool),
    },
    outputs={"decomposition": returned(kind="ota-functional-decomposition")},
)
def decompose_ota(
    canonical, *, circuit_name, vdd_nets, vss_nets, max_level, suppress_false_stacks
):
    """Real Netlist Decomposition of the selected circuit."""

    circuits = (canonical["top"], *canonical["subcircuits"])
    found = next((item for item in circuits if item["name"] == circuit_name), None)
    if found is None:
        raise ValueError(
            f"circuit {circuit_name!r} not found; "
            f"have {[item['name'] for item in circuits]}"
        )
    tags = decompose_blocks(
        _deserialize_circuit(found),
        vdd_nets=vdd_nets,
        vss_nets=vss_nets,
        max_level=max_level,
    )
    if suppress_false_stacks:
        tags = _suppress(tags)
    return [_serialize_block_tag(tag) for tag in tags]


@operation(
    name="ota_pvt.simulate_ac",
    version="1",
    inputs={"run": PREPARED_RUN},
    config={
        "point_id": parameter(str),
        "process": parameter(str),
        "vdd_v": parameter(float),
        "temp_c": parameter(int),
        "simulator_profile": parameter(str),
        "analysis": parameter(str),
    },
    outputs={"raw": file("ota_ac.raw", kind="simulator-raw-results")},
    # On a site with an LSF transport this line is the whole difference:
    #   policy=lsf(queue="normal", cores=1, memory_mb=2048,
    #              licences={"ngspice": 1}),
    policy=local(),
)
def simulate_ac(
    run, out, *, point_id, process, vdd_v, temp_c, simulator_profile, analysis
):
    """A launcher: the ngspice run is what the placement places.

    The declared output is the contract. If ngspice exits nonzero the attempt
    fails; if it exits clean without writing the raw file, reconciliation
    refuses -- neither can be papered over into a measurement.
    """

    del process, vdd_v, temp_c, simulator_profile  # already rendered into the deck
    if analysis != "ac":
        raise NotImplementedError(f"only the 'ac' analysis is implemented: {analysis!r}")

    deck = Path(run) / "ota_ac.cir"
    if not deck.exists():
        raise FileNotFoundError(f"prepared deck not found at {deck} for {point_id}")
    return shell("ngspice", "-b", "-r", out.raw, deck)


@operation(
    name="ota_pvt.measure_ac",
    version="1",
    inputs={"raw": SIMULATOR_RAW, "definition": MEASUREMENT_DEFINITION},
    config={"point_id": parameter(str)},
    outputs={"measurements": returned(kind="ota-point-measurements")},
)
def measure_ac(raw, definition, *, point_id):
    """Gain, GBW and phase margin computed from the real raw file.

    ``definition`` is the declared measurement definition, delivered as a path.
    A metric it names and this cannot compute is refused, not omitted.
    """

    declared = json.loads(Path(definition).read_text(encoding="utf-8"))
    expected = {item["name"] for item in declared["metrics"]}

    measured = measure_ac_metrics(read_ac_raw(Path(raw)))
    missing = expected - measured.keys()
    if missing:
        raise RawFileError(f"measurement definition names {sorted(missing)}; not computed")
    return {"point_id": point_id, **measured}


@operation(
    name="ota_pvt.evaluate_pvt",
    version="1",
    inputs={
        "measurements": artifacts("ota-point-measurements"),
        "decompositions": artifacts("ota-functional-decomposition"),
        "limits": SPEC_LIMITS,
    },
    config={"point_ids": parameter(list)},
    outputs={"evaluation": returned(kind="ota-pvt-evaluation")},
)
def evaluate_pvt(measurements, decompositions, limits, *, point_ids):
    """Check every point against the declared spec limits."""

    declared = json.loads(Path(limits).read_text(encoding="utf-8"))
    limit_map = declared["limits"]

    points: dict[str, Any] = {}
    overall_pass = True
    for point_id, measurement, decomposition in zip(
        point_ids, measurements, decompositions
    ):
        checks: dict[str, Any] = {}
        point_pass = True
        for metric, limit in limit_map.items():
            value = measurement.get(metric)
            minimum = limit.get("minimum")
            ok = value is not None and minimum is not None and value >= minimum
            checks[metric] = {"value": value, "minimum": minimum, "pass": ok}
            point_pass = point_pass and ok

        kinds: dict[str, int] = {}
        for tag in decomposition:
            kinds[tag["kind"]] = kinds.get(tag["kind"], 0) + 1

        points[point_id] = {
            "measurements": measurement,
            "checks": checks,
            "pass": point_pass,
            "decomposition_kinds": kinds,
        }
        overall_pass = overall_pass and point_pass

    return {
        "status": declared.get("status"),
        "points": points,
        "overall_pass": overall_pass,
    }


@flow(name="ota_pvt.study", version="1")
def ota_pvt_study(base, edits, definition, limits, points):
    """Two independent branches per point, then two ordered fan-ins."""

    measurements = []
    decompositions = []
    for point in sweep(points, key=lambda item: item.key):
        prepared = prepare_run(
            base,
            edits,
            point_id=point.key,
            param_set=point.key,
            process=point.process,
            vdd_v=point.vdd_v,
            temp_c=point.temp_c,
        )
        canonical = canonicalize_deck(
            prepared, deck_relpath="ota_ac.cir", spice_format="ngspice",
            top_name="ota_pvt",
        )
        decompositions.append(
            decompose_ota(
                canonical,
                circuit_name="ota_core",
                vdd_nets=["vdd"],
                vss_nets=["vss"],
                max_level=4,
                suppress_false_stacks=True,
            )
        )
        raw = simulate_ac(
            prepared,
            point_id=point.key,
            process=point.process,
            vdd_v=point.vdd_v,
            temp_c=point.temp_c,
            simulator_profile="ngspice-ac",
            analysis="ac",
        )
        measurements.append(measure_ac(raw, definition, point_id=point.key))

    evaluation = evaluate_pvt.named("evaluate-pvt")(
        measurements,
        decompositions,
        limits,
        point_ids=[point.key for point in points],
    )
    return {"evaluation": evaluation.evaluation}


@study(default_policy=local())
def pvt(points=PVT_POINTS):
    """The study: every declared input, then the flow that consumes them."""

    return ota_pvt_study.named("ota-pvt-study")(
        input_artifact(
            address("repository-relative", BASE_DIRECTORY_LOCATOR),
            artifact=SIDE_CAR_BASE,
        ),
        input_artifact(
            address("repository-relative", PVT_EDITS_LOCATOR),
            artifact=SIDE_CAR_EDITS,
        ),
        input_artifact(
            address("repository-relative", MEASUREMENT_DEFINITION_LOCATOR),
            artifact=MEASUREMENT_DEFINITION,
        ),
        input_artifact(
            address("repository-relative", SPEC_LIMITS_LOCATOR),
            artifact=SPEC_LIMITS,
        ),
        points,
    )


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
# JSON-safe forms for the two sibling values that cross an invocation boundary.
# Not optional: every result is journaled as JSON before an output is inspected,
# so a return value that will not serialize fails the invocation.
# ---------------------------------------------------------------------------


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
                connections=tuple(
                    Connection(pin=c[0], net=c[1]) for c in item["connections"]
                ),
                parameters=tuple(
                    Parameter(name=p[0], value=p[1]) for p in item["parameters"]
                ),
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


# ---------------------------------------------------------------------------
# Running it.
# ---------------------------------------------------------------------------


def write_report(run, path: Path) -> None:
    """Materialize this run's results as a file; stdout stays diagnostics.

    Ordinary post-processing over what ``submit`` already returned. It reads no
    result to decide what runs next, so it is not the result-dependent control
    the Plan is kept free of.
    """

    document = {
        "plan_id": "ota-pvt-study",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "succeeded": run.succeeded,
        "invocations": [
            {
                "authored_key": outcome.authored_key,
                "operation": outcome.operation,
                "placement": outcome.placement,
                "disposition": outcome.disposition,
                "outcome": outcome.outcome,
                "reused": outcome.reused,
                "error": outcome.error,
            }
            for outcome in run.report.outcomes
        ],
        "evaluation": run.value,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, default=str), encoding="utf-8")
    if not path.exists():
        # The rule every simulator step is held to: a declared result that
        # claims to exist and does not is a failure, not a detail.
        raise RuntimeError(f"wrote {path} but it is not there afterward")


def main() -> int:
    if shutil.which("ngspice") is None:
        print("ngspice is not on PATH; this study needs a real simulator")
        return 1

    work = _HERE / "_runs" / "ota"
    site = Site(
        root=str(work / "attempts"),
        workspace_root=str(work / "work"),
        address_spaces={"repository-relative": str(_REPO)},
    )

    subject = pvt()
    print(subject.summary(), "\n")

    run = subject.submit(site=site, watch=True)

    evaluation = run.value
    if evaluation is not None:
        print()
        print(json.dumps(evaluation, indent=2, default=str))

    report_path = work / "report.json"
    write_report(run, report_path)
    print(f"\nreport written: {report_path}")
    return 0 if run.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
