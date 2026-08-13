"""Build an inspectable analog characterization plan without executing work."""

from __future__ import annotations

from hedloom_flow import (
    address,
    artifact,
    artifacts,
    codec,
    flow,
    input_artifact,
    materialization,
    operation,
    parameter,
    plan,
)


DESIGN = artifact("analog-design-description")
CORNER_METRICS = artifact("corner-metrics")
SUMMARY = artifact("characterization-summary")
JSON_V1 = codec("json", version="1", encoding="utf-8")
REPOSITORY_JSON = materialization(
    codec=JSON_V1,
    address_space="repository-relative",
    access_scope="repository-checkout",
)


@operation(
    name="example.estimate_corner_metrics",
    inputs={"design": DESIGN},
    config={"corner": parameter(str), "temperature_c": parameter(int)},
    outputs={"metrics": CORNER_METRICS},
)
def estimate_corner_metrics(design, *, corner, temperature_c):
    """Describe analytical work; planning must never call this body."""

    raise AssertionError("operation bodies must not execute while planning")


@operation(
    name="example.reduce_characterization",
    inputs={"measurements": artifacts("corner-metrics")},
    outputs={"summary": SUMMARY},
)
def reduce_characterization(measurements):
    """Describe ordered fan-in over the planned corner artifacts."""

    raise AssertionError("operation bodies must not execute while planning")


@flow(name="example.characterize_one_corner")
def characterize_one_corner(design, *, corner, temperature_c):
    """Reuse one operation declaration behind a visible per-corner boundary."""

    return estimate_corner_metrics.options(key="estimate-corner-metrics")(
        design,
        corner=corner,
        temperature_c=temperature_c,
    )


@flow(name="example.characterize_design")
def characterize_design(design, *, include_extremes):
    """Use ordinary Python to select a static graph, then reduce its results."""

    corners = {}
    measurements = []

    nominal = characterize_one_corner.options(key="corner-tt")(
        design,
        corner="tt",
        temperature_c=27,
    )
    corners["tt"] = nominal
    measurements.append(nominal)

    if include_extremes:
        slow = characterize_one_corner.options(key="corner-ss")(
            design,
            corner="ss",
            temperature_c=125,
        )
        fast = characterize_one_corner.options(key="corner-ff")(
            design,
            corner="ff",
            temperature_c=-40,
        )
        corners["ss"] = slow
        corners["ff"] = fast
        measurements.extend((slow, fast))

    summary = reduce_characterization.options(key="reduce-characterization")(
        measurements
    )
    return {"corners": corners, "summary": summary}


def build_characterization_plan(*, include_extremes: bool = True):
    """Return one validated plan containing the complete authored graph."""

    with plan() as draft:
        design = input_artifact(
            address(
                "repository-relative", "inputs/two-stage-opamp.json"
            ),
            artifact=DESIGN,
            materialized_as=REPOSITORY_JSON,
        )
        outputs = characterize_design.options(key="characterize-design")(
            design,
            include_extremes=include_extremes,
        )
    return draft.finish(outputs=outputs)


def main() -> None:
    print(build_characterization_plan().to_json())


if __name__ == "__main__":
    main()
