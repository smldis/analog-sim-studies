"""Looking at a study is not a second way to run one.

The lowering exists so a Plan can be drawn. What these hold is that it stays
that: the shape is real, the bindings are not, and asking it for a number
refuses instead of inventing one.
"""

import pytest

from hedloom import artifact, file, flow, local, operation, parameter, plan, returned, study, sweep
from hedloom.visualize import RefusedComputation, lower, structure

TEXT = artifact("text-file")


@operation(config={"word": parameter(str)},
           outputs={"note": file("note.txt", kind="text-file")})
def write_note(out, *, word: str) -> None:
    out.note.write_text(word)


@operation(inputs={"note": TEXT}, outputs={"size": returned(kind="count")})
def measure(note) -> int:
    raise AssertionError("must not run")


@flow
def notes(words):
    last = None
    for word in sweep(words, key=lambda item: item):
        last = measure(write_note(word=word))
    return {"sizes": last}


def build(words=("ab", "cde")):
    with plan(default_policy=local()) as draft:
        outputs = notes.options(key="notes")(words)
    return draft.finish(outputs=outputs)


def test_the_plan_lowers_to_a_graph_with_the_shape_it_declared():
    lowering = lower(study(build()))

    assert len(lowering.invocations) == 4
    assert list(lowering.outputs) == ["sizes"]


def test_computing_a_lowering_refuses_instead_of_answering():
    """The whole reason this is safe to expose."""

    dask = pytest.importorskip("dask")
    lowering = lower(study(build()))

    with pytest.raises(Exception) as raised:
        dask.compute(*lowering.outputs.values())
    causes = []
    error = raised.value
    while error is not None:
        causes.append(type(error))
        error = error.__cause__
    assert RefusedComputation in causes, causes


def test_structure_speaks_the_vocabulary_the_study_was_authored_in():
    shape = structure(study(build()))

    labels = {node["label"] for node in shape["nodes"]}
    assert {"ab:write_note", "ab:measure", "cde:write_note", "cde:measure"} <= labels
    assert shape["outputs"] == ["sizes"]
    assert all(node["placement"] == "local" for node in shape["nodes"]
               if node["kind"] == "invocation")


def test_every_edge_joins_two_declared_nodes():
    shape = structure(study(build()))

    known = {node["id"] for node in shape["nodes"]}
    assert shape["edges"], "a plan with inputs must have edges"
    for edge in shape["edges"]:
        assert edge["source"] in known, edge
        assert edge["target"] in known, edge


def test_structure_needs_neither_dask_nor_graphviz(monkeypatch):
    """It reads the Plan, so it works for plans the local lowering refuses."""

    import sys

    monkeypatch.setitem(sys.modules, "graphviz", None)
    assert structure(study(build()))["nodes"]


def test_a_drawing_sizes_itself_to_whatever_holds_it():
    """Graphviz fixes the size it computed; a phone has a different one.

    Needs no graphviz: this is the string rewrite that makes one file read on
    a monitor and a handset, so it is worth holding on its own.
    """

    from hedloom.visualize import _scale_to_its_container

    given = (
        '<?xml version="1.0"?>\n<svg width="1101pt" height="374pt"\n'
        ' viewBox="0.00 0.00 1101.00 374.00" xmlns="http://www.w3.org/2000/svg">'
        '<g><title>study</title></g></svg>'
    )
    scaled = _scale_to_its_container(given)

    assert 'width="1101pt"' not in scaled
    assert 'height="374pt"' not in scaled
    assert 'viewBox="0.00 0.00 1101.00 374.00"' in scaled
    assert "width:100%" in scaled
    assert "<title>study</title>" in scaled, "only the root element is rewritten"


def test_a_drawing_with_nothing_to_scale_against_is_left_alone():
    from hedloom.visualize import _scale_to_its_container

    given = '<svg width="10pt" height="10pt"></svg>'
    assert _scale_to_its_container(given) == given


def test_the_drawing_is_labelled_the_way_the_study_was_authored():
    """The reason this view exists: a corner has to be findable in it."""

    pytest.importorskip("graphviz")
    from hedloom.visualize import _authored_digraph, structure

    body = _authored_digraph(structure(study(build())), rankdir="TB").source

    for authored in ("ab:write_note", "cde:measure"):
        assert authored in body, authored
    # Plan ids carry colons, which dot reads as node:port. Names must not.
    assert "invoke:key:" not in body.replace("<B>", "").split("label=")[0]


def test_an_unknown_view_is_refused_rather_than_guessed(tmp_path):
    from hedloom.visualize import render

    with pytest.raises(ValueError, match="authored"):
        render(study(build()), str(tmp_path / "x.svg"), view="sideways")
