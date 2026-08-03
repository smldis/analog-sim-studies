"""Declare the plan-only OTA/PVT reference graph without executing work."""

from __future__ import annotations

from dataclasses import dataclass

from ass_flow import (
    ResourceContract,
    address,
    artifact,
    artifacts,
    codec,
    flow,
    input_artifact,
    materialization,
    named_policy,
    operation,
    parameter,
    plan,
)


@dataclass(frozen=True, slots=True)
class PVTPoint:
    """One ordered sentinel point local to this reference declaration."""

    key: str
    process: str
    vdd_v: float
    temp_c: int


PVT_POINTS = (
    PVTPoint("tt_1v80_27c", "tt", 1.80, 27),
    PVTPoint("ss_1v62_125c", "ss", 1.62, 125),
    PVTPoint("ff_1v98_m40c", "ff", 1.98, -40),
)

BASE_DIRECTORY_LOCATOR = "docs/reference/ota-pvt-plan/inputs/base"
PVT_EDITS_LOCATOR = "docs/reference/ota-pvt-plan/inputs/pvt_edits.py"
MEASUREMENT_DEFINITION_LOCATOR = (
    "docs/reference/ota-pvt-plan/inputs/measurement_definition.json"
)
SPEC_LIMITS_LOCATOR = "docs/reference/ota-pvt-plan/inputs/spec_limits.json"

SIDE_CAR_BASE = artifact("sidecar-base-directory")
SIDE_CAR_EDITS = artifact("sidecar-edit-file")
PREPARED_RUN = artifact("prepared-simulation-directory")
CANONICAL_NETLIST = artifact("canonical-netlist")
OTA_DECOMPOSITION = artifact("ota-functional-decomposition")
SIMULATOR_RAW = artifact("simulator-raw-results")
MEASUREMENT_DEFINITION = artifact("ota-measurement-definition")
POINT_MEASUREMENTS = artifact("ota-point-measurements")
SPEC_LIMITS = artifact("ota-specification-limits")
PVT_EVALUATION = artifact("ota-pvt-evaluation")

DIRECTORY_TREE_V1 = codec("directory-tree", version="1")
PYTHON_SOURCE_V1 = codec("python-source", version="1", encoding="utf-8")
JSON_V1 = codec("json", version="1", encoding="utf-8")
REPOSITORY_DIRECTORY_TREE = materialization(
    codec=DIRECTORY_TREE_V1,
    address_space="repository-relative",
    access_scope="repository-checkout",
)
REPOSITORY_PYTHON_SOURCE = materialization(
    codec=PYTHON_SOURCE_V1,
    address_space="repository-relative",
    access_scope="repository-checkout",
)
REPOSITORY_JSON = materialization(
    codec=JSON_V1,
    address_space="repository-relative",
    access_scope="repository-checkout",
)

PLAN_DECLARATION_POLICY = named_policy("reference.plan-only")(
    status="declaration-only"
)
SIMULATOR_BOUNDARY_POLICY = named_policy("reference.plan-only")(
    boundary="simulator-adapter",
    status="unimplemented",
)


@operation(
    name="reference.ota_pvt.prepare_run",
    version="1",
    inputs={"base": SIDE_CAR_BASE, "edits": SIDE_CAR_EDITS},
    config={
        "point_id": parameter(str),
        "param_set": parameter(str),
        "process": parameter(str),
        "vdd_v": parameter(float),
        "temp_c": parameter(int),
    },
    outputs={"run": PREPARED_RUN},
    resources=(ResourceContract("cpu_cores", 1, "count"),),
)
def prepare_run(base, edits, *, point_id, param_set, process, vdd_v, temp_c):
    """Proposed adapter boundary for a Sidecar Edits render operation."""

    raise NotImplementedError("plan declaration only; prepare_run is unimplemented")


@operation(
    name="reference.ota_pvt.canonicalize_deck",
    version="1",
    inputs={"run": PREPARED_RUN},
    config={
        "deck_relpath": parameter(str),
        "spice_format": parameter(str),
        "top_name": parameter(str),
    },
    outputs={"canonical": CANONICAL_NETLIST},
)
def canonicalize_deck(run, *, deck_relpath, spice_format, top_name):
    """Proposed adapter boundary for SPICE Canonical file extraction."""

    raise NotImplementedError(
        "plan declaration only; canonicalize_deck is unimplemented"
    )


@operation(
    name="reference.ota_pvt.decompose_ota",
    version="1",
    inputs={"canonical": CANONICAL_NETLIST},
    config={
        "circuit_name": parameter(str),
        "vdd_nets": parameter(list),
        "vss_nets": parameter(list),
        "max_level": parameter(int),
        "suppress_false_stacks": parameter(bool),
    },
    outputs={"decomposition": OTA_DECOMPOSITION},
    resources=(ResourceContract("cpu_cores", 1, "count"),),
)
def decompose_ota(
    canonical,
    *,
    circuit_name,
    vdd_nets,
    vss_nets,
    max_level,
    suppress_false_stacks,
):
    """Proposed adapter boundary for Netlist Decomposition calls."""

    raise NotImplementedError("plan declaration only; decompose_ota is unimplemented")


@operation(
    name="reference.ota_pvt.simulate_ac",
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
    outputs={"raw": SIMULATOR_RAW},
    resources=(
        ResourceContract("cpu_cores", 1, "count"),
        ResourceContract("memory_gib", 1, "GiB"),
    ),
    default_policy=SIMULATOR_BOUNDARY_POLICY,
)
def simulate_ac(
    run,
    *,
    point_id,
    process,
    vdd_v,
    temp_c,
    simulator_profile,
    analysis,
):
    """Declare an unimplemented simulator-adapter boundary."""

    raise NotImplementedError("plan declaration only; simulate_ac is unimplemented")


@operation(
    name="reference.ota_pvt.measure_ac",
    version="1",
    inputs={"raw": SIMULATOR_RAW, "definition": MEASUREMENT_DEFINITION},
    config={"point_id": parameter(str)},
    outputs={"measurements": POINT_MEASUREMENTS},
)
def measure_ac(raw, definition, *, point_id):
    """Declare an unimplemented waveform-measurement boundary."""

    raise NotImplementedError("plan declaration only; measure_ac is unimplemented")


@operation(
    name="reference.ota_pvt.evaluate_pvt",
    version="1",
    inputs={
        "measurements": artifacts("ota-point-measurements"),
        "decompositions": artifacts("ota-functional-decomposition"),
        "limits": SPEC_LIMITS,
    },
    config={"point_ids": parameter(list)},
    outputs={"evaluation": PVT_EVALUATION},
)
def evaluate_pvt(measurements, decompositions, limits, *, point_ids):
    """Declare an unimplemented PVT evaluation boundary."""

    raise NotImplementedError("plan declaration only; evaluate_pvt is unimplemented")


OPERATION_DECLARATIONS = (
    prepare_run,
    canonicalize_deck,
    decompose_ota,
    simulate_ac,
    measure_ac,
    evaluate_pvt,
)


@flow(name="reference.ota_pvt.point", version="1")
def plan_point(base, edits, measurement_definition, *, point):
    """Declare the independent structural and AC branches for one PVT point."""

    prepared = prepare_run.options(key="prepare-run")(
        base,
        edits,
        point_id=point.key,
        param_set=point.key,
        process=point.process,
        vdd_v=point.vdd_v,
        temp_c=point.temp_c,
    )
    canonical = canonicalize_deck.options(key="canonicalize-deck")(
        prepared,
        deck_relpath="ota_ac.cir",
        spice_format="ngspice",
        top_name="ota_pvt",
    )
    decomposition = decompose_ota.options(key="decompose-ota")(
        canonical,
        circuit_name="ota_core",
        vdd_nets=["vdd"],
        vss_nets=["vss"],
        max_level=4,
        suppress_false_stacks=True,
    )
    raw = simulate_ac.options(key="simulate-ac")(
        prepared,
        point_id=point.key,
        process=point.process,
        vdd_v=point.vdd_v,
        temp_c=point.temp_c,
        simulator_profile="ngspice-ac",
        analysis="ac",
    )
    measurements = measure_ac.options(key="measure-ac")(
        raw,
        measurement_definition,
        point_id=point.key,
    )
    return {
        "prepared": prepared,
        "canonical": canonical,
        "decomposition": decomposition,
        "raw": raw,
        "measurements": measurements,
    }


@flow(name="reference.ota_pvt.study", version="1")
def plan_study(base, edits, measurement_definition, limits, *, points):
    """Expand the ordered PVT tuple and declare its two ordered fan-ins."""

    point_outputs = {}
    measurements = []
    decompositions = []
    for point in points:
        outputs = plan_point.options(key=f"point-{point.key}")(
            base,
            edits,
            measurement_definition,
            point=point,
        )
        point_outputs[point.key] = outputs
        measurements.append(outputs["measurements"])
        decompositions.append(outputs["decomposition"])

    evaluation = evaluate_pvt.options(key="evaluate-pvt")(
        measurements,
        decompositions,
        limits,
        point_ids=[point.key for point in points],
    )
    return {"points": point_outputs, "evaluation": evaluation}


FLOW_DECLARATIONS = (plan_point, plan_study)


def build_plan():
    """Construct and validate the reference Plan without reading fixture files."""

    with plan(default_policy=PLAN_DECLARATION_POLICY) as draft:
        base = input_artifact(
            address("repository-relative", BASE_DIRECTORY_LOCATOR),
            artifact=SIDE_CAR_BASE,
            materialized_as=REPOSITORY_DIRECTORY_TREE,
        )
        edits = input_artifact(
            address("repository-relative", PVT_EDITS_LOCATOR),
            artifact=SIDE_CAR_EDITS,
            materialized_as=REPOSITORY_PYTHON_SOURCE,
        )
        measurement_definition = input_artifact(
            address(
                "repository-relative", MEASUREMENT_DEFINITION_LOCATOR
            ),
            artifact=MEASUREMENT_DEFINITION,
            materialized_as=REPOSITORY_JSON,
        )
        limits = input_artifact(
            address("repository-relative", SPEC_LIMITS_LOCATOR),
            artifact=SPEC_LIMITS,
            materialized_as=REPOSITORY_JSON,
        )
        outputs = plan_study.options(key="ota-pvt-study")(
            base,
            edits,
            measurement_definition,
            limits,
            points=PVT_POINTS,
        )
    return draft.finish(outputs=outputs)


def main() -> None:
    """Print canonical Plan JSON for inspection; no operation is submitted."""

    print(build_plan().to_json())


if __name__ == "__main__":
    main()
