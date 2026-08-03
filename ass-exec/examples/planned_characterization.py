"""Author a flow, plan it, execute it, edit one input, and rerun.

This is the first end-to-end slice across both units: ASS Flow authors and
normalizes a static Plan, ASS Exec derives content-addressed bundles from that
Plan document and executes them with durable records.

The point of the demonstration is the second run. Change one corner's
temperature and rerun: that corner and the reduction downstream of it recompute,
the untouched corners are reused from their published manifests, and the
superseded result is still on disk and nameable rather than overwritten.

Run it from the unit directory with both source trees on the path:

    PYTHONPATH=src:../ass-flow/src python examples/planned_characterization.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile

try:
    from ass_flow import (
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
except ModuleNotFoundError:  # pragma: no cover - guidance, not logic
    sys.exit(
        "ass_flow is required for this example.\n"
        "Run: PYTHONPATH=src:../ass-flow/src python "
        "examples/planned_characterization.py"
    )

from ass_exec.durability import Durability, execute
from ass_exec.planned import plan_bundles
from ass_exec.reuse import describe_staleness, stale_attempts
from ass_exec.transport import InProcessTransport

PLAN_ID = "characterization"
CORNERS = {"tt": 27, "ss": 125, "ff": -40}


@operation(
    inputs={"design": artifact("design")},
    config={"corner": parameter(str), "temperature_c": parameter(int)},
    outputs={"metrics": artifact("corner-metrics")},
)
def estimate(design, *, corner, temperature_c):
    raise AssertionError("operation bodies do not run during planning")


@operation(
    inputs={"measurements": artifacts("corner-metrics")},
    outputs={"summary": artifact("summary")},
)
def summarize(measurements):
    raise AssertionError("operation bodies do not run during planning")


@flow
def characterize(design, *, corners):
    results = [
        estimate.options(key=f"corner-{name}")(
            design, corner=name, temperature_c=temperature
        )
        for name, temperature in corners.items()
    ]
    return summarize.options(key="summary")(results)


def build_plan(corners):
    with plan() as draft:
        design = input_artifact(
            address("repository-relative", "inputs/opamp.json"),
            artifact=artifact("design"),
            materialized_as=materialization(
                address_space="repository-relative",
                codec=codec("json", encoding="utf-8"),
                access_scope="repository-checkout",
            ),
        )
        result = characterize(design, corners=corners)
    normalized = draft.finish(outputs={"summary": result})
    normalized.validate()
    return normalized.to_data()


# Implementations. Deliberately arithmetic rather than a simulator: the slice
# under demonstration is identity and reuse, not analog meaning.
def estimate_impl(*, corner, temperature_c, design=None):
    return {"corner": corner, "gain_db": 60.0 - 0.05 * temperature_c}


def summarize_impl(*, measurements=None):
    values = [item["gain_db"] for item in (measurements or [])]
    return {"worst_gain_db": min(values), "corners": len(values)}


def run(document, root, label):
    transport = InProcessTransport(
        {"__main__.estimate": estimate_impl, "__main__.summarize": summarize_impl}
    )
    values: dict[str, object] = {}
    print(f"\n{label}")

    for item in plan_bundles(document):
        bundle = dict(item.bundle)
        resolved: dict[str, object] = {}
        for name, reference in item.bundle["inputs"].items():
            if isinstance(reference, list):
                resolved[name] = [values.get(entry) for entry in reference]
            elif reference.startswith("output:"):
                resolved[name] = values.get(reference)
        bundle["resolved_inputs"] = resolved

        result = execute(
            transport,
            bundle,
            durability=Durability.RECORDED,
            root=root,
            plan_id=PLAN_ID,
            invocation_id=item.invocation_id,
        )
        verb = "reused " if result.disposition == "completed" else "ran    "
        print(f"  {verb} {item.authored_key:<12} {item.input_digest[:12]}")

        for output in ("metrics", "summary"):
            values[f"output:{item.input_digest}:{output}"] = result.value

    return values


def main():
    root = tempfile.mkdtemp(prefix="ass-exec-example-")
    try:
        first = build_plan(CORNERS)
        run(first, root, "First run — nothing is published yet")
        run(first, root, "Second run — unchanged inputs, nothing recomputes")

        edited = dict(CORNERS, ss=150)
        second = build_plan(edited)
        values = run(second, root, "Third run — ss retuned to 150C")

        summary = [value for key, value in values.items() if "summary" in key]
        print(f"\n  final summary: {summary[-1] if summary else None}")

        superseded = [
            record
            for item in plan_bundles(second)
            for record in stale_attempts(
                root,
                plan_id=PLAN_ID,
                invocation_id=item.invocation_id,
                current_digest=item.input_digest,
            )
        ]
        print("\n  superseded but retained:")
        print("   " + describe_staleness(superseded).replace("\n", "\n   "))
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
