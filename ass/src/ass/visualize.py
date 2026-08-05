"""Looking at a study before running it.

`ass_flow.experimental.local_dask` lowers a Plan to Dask `Delayed` values. It
was written as an instrument and left unreexported, because lowering a Plan to
a second execution path is exactly the kind of thing that quietly becomes a
second way to run work. It is still not that. This module gives it the one use
that needs no execution at all: a picture.

The distinction is kept by construction. Lowering here binds every operation to
a stand-in that **refuses to run**, so the graph can be drawn, walked, and
counted, and computing it raises rather than producing a number nobody
simulated. Computing one surfaces as the lowerer's own
`InvocationExecutionError`, naming the invocation, with `RefusedComputation` as
its cause. `submit()` remains the only way a study runs.

Two views, because they answer different questions:

* `render(...)` draws the Dask graph the lowering produces — task keys,
  projections, the shape a scheduler would see.
* `structure(...)` reads the Plan itself into nodes and edges: authored keys,
  operations and placements, as plain data any renderer can take. No graphviz,
  no Dask.
"""

from __future__ import annotations

from typing import Any, Mapping
import sys

from ass_flow.model import OperationIdentity

__all__ = ["RefusedComputation", "lower", "render", "structure"]


class RefusedComputation(RuntimeError):
    """A lowering meant for looking at was asked to produce a result."""


def _stand_in(identity: OperationIdentity):
    """A body that exists to be drawn, and says so if anyone computes it."""

    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise RefusedComputation(
            f"{identity.name!r} was lowered for inspection, not execution. "
            "This graph binds no implementations; run the study with submit()."
        )

    refuse.__name__ = identity.name.replace(".", "_")
    return refuse


def lower(study: Any) -> Any:
    """Lower a study's Plan to Dask Delayed values, bound to nothing.

    Returns `ass_flow.experimental.local_dask.DelayedLowering`, whose
    `invocations`, `outputs` and `invocation_keys` are ordinary Dask
    collections — so anything Dask can do to a graph works here.

    The lowering refuses a plan it cannot represent rather than approximating
    one: an invocation with a non-`local` placement, a placement carrying
    options, or an operation declaring resources is rejected by name. That is
    the honest limit of a local lowering, and a study bound for LSF will say so
    instead of drawing something it is not.
    """

    from ass_flow.experimental.local_dask import lower_delayed

    plan = study.plan
    return lower_delayed(
        plan,
        operations={
            definition.identity: _stand_in(definition.identity)
            for definition in plan.operations
        },
        # Inert placeholders. A source's *value* is never part of the shape,
        # and reading one to draw a picture would be spending to look.
        sources={source.id: None for source in plan.sources},
    )


def render(study: Any, path: str, **options: Any) -> Any:
    """Draw the lowered graph to a file. Needs `graphviz` and a `dot` binary.

    The extension chooses the format, as it does for `dask.visualize`; `.svg`
    embeds anywhere without a second file.
    """

    import dask

    lowering = lower(study)
    return dask.visualize(
        *lowering.outputs.values(), filename=path, **options
    )


def structure(study: Any) -> dict[str, Any]:
    """The Plan as nodes and edges, for a renderer that has neither.

    Read from the Plan document rather than from the lowering, because this is
    the view an operator asks for: which corner, which operation, which
    placement — the vocabulary the study was authored in, not the vocabulary a
    scheduler sees. It also works for plans the local lowering refuses, which
    is every plan bound for a farm.
    """

    document = study.document
    definitions = {
        item["identity"]["name"]: item for item in document.get("operations", [])
    }

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []

    for source in document.get("sources", []):
        nodes.append(
            {
                "id": source["id"],
                "kind": "source",
                "label": (source.get("address") or {}).get("locator", source["id"]),
                "artifact": (source.get("artifact") or {}).get("kind"),
            }
        )

    for invocation in document.get("invocations", []):
        name = invocation["operation"]["name"]
        definition = definitions.get(name) or {}
        nodes.append(
            {
                "id": invocation["id"],
                "kind": "invocation",
                "label": invocation.get("authored_key") or invocation["id"],
                "operation": name,
                "placement": (invocation.get("policy") or {}).get("name", "local"),
                "boundary": invocation.get("boundary_id"),
                "outputs": [
                    item["name"] for item in definition.get("outputs", [])
                ],
                "implementation": (definition.get("implementation") or {}).get(
                    "entry_point"
                ),
            }
        )
        for binding in invocation.get("inputs", []):
            references = (
                [binding["reference"]]
                if "reference" in binding
                else binding.get("references", [])
            )
            for reference in references:
                origin = (
                    reference.get("invocation_id")
                    if reference.get("type") == "output"
                    else reference.get("source_id")
                )
                if origin:
                    edges.append(
                        {
                            "source": origin,
                            "target": invocation["id"],
                            "input": binding["name"],
                        }
                    )

    return {
        "schema_version": document.get("schema_version"),
        "outputs": [item["name"] for item in document.get("outputs", [])],
        "nodes": nodes,
        "edges": edges,
    }


def _main(argv: list[str]) -> int:  # pragma: no cover - operator convenience
    """`python -m ass.visualize <module> <out.svg>` for a module exposing build()."""

    import importlib
    import json

    if not argv:
        print(__doc__)
        return 2
    module = importlib.import_module(argv[0])
    from ass import study as _study

    subject = _study(module.build())
    if len(argv) > 1:
        render(subject, argv[1])
        print(f"wrote {argv[1]}")
    else:
        print(json.dumps(structure(subject), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main(sys.argv[1:]))
