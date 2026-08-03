"""Build an inspectable analog characterization plan without executing work."""

from __future__ import annotations

from ass_flow import artifact, flow, input_artifact, operation, parameter, plan


DESIGN = artifact("analog-design-description")
CORNER_METRICS = artifact("corner-metrics")
SUMMARY = artifact("characterization-summary")


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
    inputs={
        "nominal": CORNER_METRICS,
        "slow": CORNER_METRICS,
        "fast": CORNER_METRICS,
    },
    outputs={"summary": SUMMARY},
)
def reduce_characterization(nominal, slow, fast):
    """Describe fixed-shape fan-in over the three planned corner artifacts."""

    raise AssertionError("operation bodies must not execute while planning")


@flow(name="example.characterize_one_corner")
def characterize_one_corner(design, *, corner, temperature_c):
    """Reuse one operation declaration behind a visible per-corner boundary."""

    return estimate_corner_metrics(
        design,
        corner=corner,
        temperature_c=temperature_c,
    )


@flow(name="example.characterize_design")
def characterize_design(design, *, include_extremes):
    """Use ordinary Python to select a static graph, then reduce its results."""

    corners = {
        "tt": characterize_one_corner(
            design,
            corner="tt",
            temperature_c=27,
        )
    }
    if include_extremes:
        corners["ss"] = characterize_one_corner(
            design,
            corner="ss",
            temperature_c=125,
        )
        corners["ff"] = characterize_one_corner(
            design,
            corner="ff",
            temperature_c=-40,
        )
    else:
        # The current core has scalar artifact inputs. Reusing the nominal
        # handle keeps the reducer shape explicit when extremes are omitted.
        corners["ss"] = corners["tt"]
        corners["ff"] = corners["tt"]

    summary = reduce_characterization(
        nominal=corners["tt"],
        slow=corners["ss"],
        fast=corners["ff"],
    )
    return {"corners": corners, "summary": summary}


def build_characterization_plan(*, include_extremes: bool = True):
    """Return one validated plan containing the complete authored graph."""

    with plan() as draft:
        design = input_artifact(
            "inputs/two-stage-opamp.json",
            "analog-design-description",
        )
        outputs = characterize_design(
            design,
            include_extremes=include_extremes,
        )
    return draft.finish(outputs=outputs)


def main() -> None:
    print(build_characterization_plan().to_json())


if __name__ == "__main__":
    main()
