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

Three views, because they answer different questions:

* `render(...)` draws the Plan in the vocabulary it was authored in: one node
  per invocation, labelled with its authored key. It scales to whatever holds
  it, and lays out tall or wide on request, so one file reads on a monitor and
  on a phone.
* `render(..., view="dask")` draws the lowering instead — task keys, source
  thunks, output projections. What a scheduler would see, and not somewhere a
  corner can be found by name.
* `structure(...)` returns the same authored view as plain nodes and edges, for
  a renderer that has neither graphviz nor Dask.
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


def render(
    study: Any,
    path: str,
    *,
    view: str = "authored",
    rankdir: str = "TB",
    responsive: bool = True,
    **options: Any,
) -> str:
    """Draw the study to a file. Needs `graphviz` and a `dot` binary.

    ``view="authored"`` draws the Plan in the vocabulary it was written in: one
    node per invocation, labelled with its authored key, its operation beneath,
    its placement when that is not local. It also draws the plans the local
    lowering refuses, which is every plan bound for a farm.

    ``view="dask"`` draws the lowering instead — task keys, source thunks and
    output projections, the shape a scheduler would see. A different question,
    and much less legible: its nodes are named for the lowering's own key
    namespace, so a corner is not findable in it.

    ``rankdir`` is ``"TB"`` (tall, reads on a phone) or ``"LR"`` (wide, reads
    on a monitor). ``responsive`` drops the fixed pixel size graphviz writes
    onto the SVG and keeps its ``viewBox``, so one drawing scales to whatever
    element holds it instead of overflowing the small ones.
    """

    if view == "dask":
        import dask

        dask.visualize(*lower(study).outputs.values(), filename=path, **options)
        return path

    if view != "authored":
        raise ValueError(f"unknown view {view!r}; use 'authored' or 'dask'")

    from pathlib import Path as _Path

    target = _Path(path)
    fmt = target.suffix.lstrip(".") or "svg"
    rendered = _authored_digraph(
        structure(study), rankdir=rankdir, **options
    ).pipe(format=fmt)

    if fmt == "svg" and responsive:
        target.write_text(
            _scale_to_its_container(rendered.decode("utf-8")), encoding="utf-8"
        )
    else:
        target.write_bytes(rendered)
    return str(target)


# Opaque muted fills with dark ink, on no background at all. The drawing is
# embedded in pages this module does not control, and an opaque node reads
# against a light or a dark one where a white canvas reads against neither.
_SOURCE_FILL = "#dbe3ea"
_LOCAL_FILL = "#e8eef7"
_PLACED_FILL = "#f7ecd9"
_INK = "#1c2430"
_LINE = "#7c8899"


def _authored_digraph(shape: Mapping[str, Any], *, rankdir: str = "TB", **options: Any):
    """One node per declared thing, labelled the way the study named it."""

    import html

    import graphviz

    drawing = graphviz.Digraph("study", format="svg")
    drawing.attr(
        rankdir=rankdir,
        bgcolor="transparent",
        splines="spline",
        nodesep="0.28",
        ranksep="0.5",
        **options,
    )
    drawing.attr("node", fontname="Helvetica", fontsize="11", color=_LINE,
                 fontcolor=_INK, style="filled,rounded", penwidth="1")
    drawing.attr("edge", color=_LINE, arrowsize="0.7", penwidth="1")

    # Plan ids carry colons (`invoke:key:<digest>`, `source:0001`) and graphviz
    # reads a colon as a node:port separator, which silently drops every edge
    # and flattens the drawing onto one rank. Names here are opaque; the ids
    # stay in the labels, where they are for people rather than for dot.
    names = {node["id"]: f"n{index}" for index, node in enumerate(shape["nodes"])}

    for node in shape["nodes"]:
        label = html.escape(str(node["label"]))
        if node["kind"] == "source":
            caption = html.escape(str(node.get("artifact") or "source"))
            drawing.node(
                names[node["id"]],
                label=f'<<B>{label}</B><BR/><FONT POINT-SIZE="8.5">{caption}</FONT>>',
                shape="note",
                fillcolor=_SOURCE_FILL,
            )
            continue

        placement = node.get("placement") or "local"
        caption = html.escape(str(node.get("operation") or ""))
        if placement != "local":
            # Only when it is worth saying. A study that is entirely local
            # should not repeat the word on every node.
            caption += f'<BR/><FONT POINT-SIZE="8.5">@{html.escape(placement)}</FONT>'
        drawing.node(
            names[node["id"]],
            label=f'<<B>{label}</B><BR/><FONT POINT-SIZE="8.5">{caption}</FONT>>',
            shape="box",
            fillcolor=_LOCAL_FILL if placement == "local" else _PLACED_FILL,
        )

    for edge in shape["edges"]:
        drawing.edge(
            names[edge["source"]], names[edge["target"]],
            label=f'  {edge.get("input", "")}', fontsize="8.5", fontcolor=_LINE,
        )
    return drawing


def _scale_to_its_container(svg: str) -> str:
    """Let the drawing size itself to whatever holds it.

    Graphviz writes the size it computed, in points, onto the root element.
    That fixes the drawing at that size and overflows anything smaller — a
    phone, a split pane, a card in a launcher. Dropping width and height while
    keeping the viewBox is what makes an SVG scale, so one file reads on a
    monitor and on a handset without rendering it twice.
    """

    import re

    def rewrite(match: re.Match[str]) -> str:
        tag = match.group(0)
        if "viewBox" not in tag:  # nothing to scale against; leave it alone
            return tag
        tag = re.sub(r'\s(?:width|height)="[^"]*"', "", tag)
        return tag.replace(
            "<svg",
            '<svg style="width:100%;height:auto;max-width:100%;display:block"',
            1,
        )

    return re.sub(r"<svg\b[^>]*>", rewrite, svg, count=1)


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
