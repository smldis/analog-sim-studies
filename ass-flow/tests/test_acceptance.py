import json

import pytest

import ass_flow
from ass_flow import (
    AuthoringError,
    BindingError,
    PlanningScopeError,
    artifact,
    flow,
    input_artifact,
    operation,
    parameter,
    plan,
    submit,
)
from examples import characterization


DESIGN = artifact("analog-design-description")
CORNER_METRICS = artifact("corner-metrics")
SUMMARY = artifact("characterization-summary")


def test_characterization_example_is_one_valid_inspectable_graph(capsys):
    normalized = characterization.build_characterization_plan()
    nominal_only = characterization.build_characterization_plan(
        include_extremes=False
    )

    assert normalized.validate() is normalized
    assert len(normalized.sources) == 1
    assert len(normalized.invocations) == 4
    assert len(normalized.edges) == 3
    assert len(normalized.boundaries) == 4
    roots = [
        boundary for boundary in normalized.boundaries if boundary.parent_id is None
    ]
    assert len(roots) == 1
    assert {
        boundary.parent_id
        for boundary in normalized.boundaries
        if boundary.parent_id is not None
    } == {roots[0].id}
    assert {output.name for output in normalized.outputs} == {
        "corners__ff",
        "corners__ss",
        "corners__tt",
        "summary",
    }
    assert json.loads(normalized.to_json()) == normalized.to_data()
    assert nominal_only.validate() is nominal_only
    assert len(nominal_only.invocations) == 2
    assert len(nominal_only.boundaries) == 2
    assert [
        binding.value
        for invocation in nominal_only.invocations
        for binding in invocation.config
        if binding.name == "corner"
    ] == ["tt"]

    characterization.main()
    printed = capsys.readouterr().out.strip()
    assert printed == normalized.to_json()


def test_same_example_inputs_reconstruct_identical_data_and_ids():
    first = characterization.build_characterization_plan(include_extremes=True)
    second = characterization.build_characterization_plan(include_extremes=True)

    assert first.to_data() == second.to_data()
    assert first.to_json() == second.to_json()
    for field in ("sources", "invocations", "edges", "boundaries"):
        assert [item.id for item in getattr(first, field)] == [
            item.id for item in getattr(second, field)
        ]


def test_example_operation_bodies_are_never_executed():
    # Both public operation bodies raise unconditionally. Reaching a valid plan
    # is direct evidence that flow authoring recorded calls without running them.
    normalized = characterization.build_characterization_plan()

    assert len(normalized.invocations) == 4


def test_nested_flow_failure_rolls_back_graph_and_all_id_counters():
    @operation(
        name="acceptance.estimate",
        inputs={"design": DESIGN},
        outputs={"metrics": CORNER_METRICS},
    )
    def estimate(design):
        raise AssertionError("must not run")

    @operation(
        name="acceptance.summarize",
        inputs={"metrics": CORNER_METRICS},
        outputs={"summary": SUMMARY},
    )
    def summarize(metrics):
        raise AssertionError("must not run")

    @flow(name="acceptance.failing_nested")
    def failing_nested(design):
        summarize(estimate(design))
        raise RuntimeError("authored nested-flow failure")

    @flow(name="acceptance.successful_nested")
    def successful_nested(design):
        return summarize(estimate(design))

    @flow(name="acceptance.rollback_study")
    def rollback_study(design):
        with pytest.raises(RuntimeError, match="nested-flow failure"):
            failing_nested(design)
        return successful_nested(design)

    with plan() as draft:
        result = rollback_study(
            input_artifact("inputs/design.json", "analog-design-description")
        )
    normalized = draft.finish(outputs={"summary": result})

    assert [item.id for item in normalized.invocations] == [
        "invoke:0001",
        "invoke:0002",
    ]
    assert [item.id for item in normalized.edges] == ["edge:0001"]
    assert {item.id for item in normalized.boundaries} == {
        "flow:0001",
        "flow:0002",
    }
    assert {item.identity.name for item in normalized.flows} == {
        "acceptance.rollback_study",
        "acceptance.successful_nested",
    }
    assert normalized.validate() is normalized


def test_foreign_source_only_and_incompatible_values_fail_before_finish_returns():
    @operation(
        inputs={"design": DESIGN},
        outputs={"metrics": CORNER_METRICS},
    )
    def estimate(design):
        raise AssertionError("must not run")

    @operation(inputs={"metrics": CORNER_METRICS}, outputs={"summary": SUMMARY})
    def summarize(metrics):
        raise AssertionError("must not run")

    with plan() as foreign_draft:
        foreign_result = estimate(
            input_artifact("inputs/foreign.json", "analog-design-description")
        )
    foreign_draft.finish(outputs={"metrics": foreign_result})

    with plan() as local_draft:
        local_source = input_artifact(
            "inputs/local.json", "analog-design-description"
        )
        with pytest.raises(BindingError, match="different plan"):
            summarize(foreign_result)
        with pytest.raises(BindingError, match="expects artifact kind"):
            summarize(local_source)
        with pytest.raises(BindingError, match="artifact inputs must be"):
            summarize("results/corner.json")
        local_result = estimate(local_source)

    with pytest.raises(BindingError, match="different plan"):
        local_draft.finish(outputs={"metrics": foreign_result})
    with pytest.raises(AuthoringError, match="not an input source"):
        local_draft.finish(outputs={"design": local_source})

    normalized = local_draft.finish(outputs={"metrics": local_result})
    assert len(normalized.invocations) == 1
    assert normalized.invocations[0].id == "invoke:0001"


def test_no_run_or_ambient_execution_surface_and_submit_is_explicit():
    assert not hasattr(ass_flow, "run")
    assert not hasattr(characterization.characterize_design, "run")
    assert not hasattr(characterization.estimate_corner_metrics, "run")

    with pytest.raises(PlanningScopeError, match="active plan"):
        characterization.characterize_design(object(), include_extremes=True)
    with pytest.raises(PlanningScopeError, match="active plan"):
        input_artifact("inputs/design.json", "analog-design-description")
    with pytest.raises(NotImplementedError, match="outside this planning spike"):
        submit(characterization.build_characterization_plan())


def _mapping_order_plan(*, reverse_inputs):
    @operation(
        name="acceptance.mapping_order.estimate",
        inputs={"design": DESIGN},
        config={"corner": parameter(str)},
        outputs={"metrics": CORNER_METRICS},
    )
    def estimate(design, *, corner):
        raise AssertionError("must not run")

    reducer_inputs = (
        {"right": CORNER_METRICS, "left": CORNER_METRICS}
        if reverse_inputs
        else {"left": CORNER_METRICS, "right": CORNER_METRICS}
    )

    @operation(
        name="acceptance.mapping_order.reduce",
        inputs=reducer_inputs,
        outputs={"summary": SUMMARY},
    )
    def reduce(left, right):
        raise AssertionError("must not run")

    with plan() as draft:
        design = input_artifact(
            "inputs/design.json", "analog-design-description"
        )
        left = estimate(design, corner="ss")
        right = estimate(design, corner="ff")
        summary = reduce(left=left, right=right)
    return draft.finish(outputs={"summary": summary})


def test_name_keyed_declaration_order_is_semantically_irrelevant():
    assert _mapping_order_plan(reverse_inputs=False).to_data() == _mapping_order_plan(
        reverse_inputs=True
    ).to_data()
