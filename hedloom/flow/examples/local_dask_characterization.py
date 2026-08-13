"""Compute the public characterization Plan through the local Dask experiment."""

from __future__ import annotations

import json

import characterization
import dask

from hedloom_flow.experimental.local_dask import lower_delayed


DECODED_DESIGN = {
    "name": "two-stage-opamp",
    "source": "injected-decoded-value",
}


def _estimate_corner_metrics_identity(
    design, *, corner: str, temperature_c: int
):
    """Provide the explicit runtime binding for the authored estimate identity."""

    return {
        "metrics": {
            "corner": corner,
            "design": design["name"],
            "temperature_c": temperature_c,
        }
    }


def _reduce_characterization_identity(*, measurements):
    """Preserve the Plan's significant TT/SS/FF collection order."""

    return {
        "summary": {
            "corner_count": len(measurements),
            "corner_order": [measurement["corner"] for measurement in measurements],
            "temperatures_c": [
                measurement["temperature_c"] for measurement in measurements
            ],
        }
    }


def build_result():
    """Lower and explicitly compute one deterministic semantic result record."""

    normalized = characterization.build_characterization_plan()
    source_id = normalized.sources[0].id
    estimate_identity = characterization.estimate_corner_metrics.identity
    reduce_identity = characterization.reduce_characterization.identity
    lowered = lower_delayed(
        normalized,
        operations={
            estimate_identity: _estimate_corner_metrics_identity,
            reduce_identity: _reduce_characterization_identity,
        },
        sources={source_id: DECODED_DESIGN},
    )

    output_names = tuple(output.name for output in normalized.outputs)
    computed = dask.compute(
        *(lowered.outputs[name] for name in output_names),
        scheduler="synchronous",
        optimize_graph=False,
    )
    return {
        "plan": {
            "counts": {
                "boundaries": len(normalized.boundaries),
                "edges": len(normalized.edges),
                "flows": len(normalized.flows),
                "invocations": len(normalized.invocations),
                "operations": len(normalized.operations),
                "outputs": len(normalized.outputs),
                "sources": len(normalized.sources),
            },
            "ids": {
                "boundaries": [item.id for item in normalized.boundaries],
                "edges": [item.id for item in normalized.edges],
                "invocations": [item.id for item in normalized.invocations],
                "sources": [item.id for item in normalized.sources],
            },
            "schema_version": normalized.schema_version,
        },
        "results": dict(zip(output_names, computed, strict=True)),
    }


def main() -> None:
    print(json.dumps(build_result(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
