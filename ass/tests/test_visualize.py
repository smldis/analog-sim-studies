"""Looking at a study is not a second way to run one.

The lowering exists so a Plan can be drawn. What these hold is that it stays
that: the shape is real, the bindings are not, and asking it for a number
refuses instead of inventing one.
"""

import pytest

from ass import artifact, file, flow, local, operation, parameter, plan, returned, study, sweep
from ass.visualize import RefusedComputation, lower, structure

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
