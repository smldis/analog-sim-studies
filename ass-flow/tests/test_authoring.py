from dataclasses import FrozenInstanceError

import pytest

from ass_flow import (
    AuthoringError,
    BindingError,
    PlanningScopeError,
    artifact,
    flow,
    input_artifact,
    local,
    named_policy,
    operation,
    parameter,
    plan,
    submit,
)


DECK = artifact("spice-deck")
RAW = artifact("simulation-raw")
REPORT = artifact("measurement-report")


def test_calls_outside_scope_are_actionable_and_operation_body_does_not_run():
    calls = []

    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def simulate(deck):
        calls.append(deck)

    @flow
    def study(deck):
        return simulate(deck)

    with pytest.raises(PlanningScopeError, match="with plan"):
        simulate(object())
    with pytest.raises(PlanningScopeError, match="with plan"):
        study(object())

    with plan() as draft:
        result = study(input_artifact("input.spice", "spice-deck"))
    normalized = draft.finish(outputs={"raw": result})

    assert calls == []
    assert len(normalized.invocations) == 1
    assert len(normalized.boundaries) == 1


def test_options_are_immutable_and_policy_precedence_is_explicit():
    lsf = named_policy("lsf")
    operation_default = lsf(queue="operation")
    plan_default = lsf(queue="plan")
    override = lsf(queue="call")

    @operation(
        inputs={"deck": DECK},
        outputs={"raw": RAW},
        default_policy=operation_default,
    )
    def simulate(deck):
        raise AssertionError("must not run")

    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def inherited(deck):
        raise AssertionError("must not run")

    call_view = simulate.options(policy=override)
    assert call_view is not simulate
    assert simulate.definition.default_policy is operation_default
    with pytest.raises(FrozenInstanceError):
        call_view.policy = plan_default

    with plan(default_policy=plan_default) as draft:
        deck = input_artifact("input.spice", "spice-deck")
        call_view(deck)
        simulate(deck)
        inherited(deck)
    normalized = draft.finish(outputs={})

    assert [item.policy for item in normalized.invocations] == [
        override,
        operation_default,
        plan_default,
    ]

    with plan() as local_draft:
        deck = input_artifact("input.spice", "spice-deck")
        inherited(deck)
    local_plan = local_draft.finish(outputs={})
    assert local_plan.invocations[0].policy == local()


def test_repeated_planning_has_stable_source_invocation_edge_and_boundary_ids():
    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def simulate(deck):
        raise AssertionError("must not run")

    @operation(inputs={"raw": RAW}, outputs={"report": REPORT})
    def measure(raw):
        raise AssertionError("must not run")

    @flow
    def study(deck):
        return measure(simulate(deck))

    def build():
        with plan() as draft:
            result = study(input_artifact("input.spice", "spice-deck"))
        return draft.finish(outputs={"report": result})

    first = build()
    second = build()

    assert first.to_data() == second.to_data()
    assert [item.id for item in first.sources] == ["source:0001"]
    assert [item.id for item in first.invocations] == [
        "invoke:0001",
        "invoke:0002",
    ]
    assert [item.id for item in first.edges] == ["edge:0001"]
    assert [item.id for item in first.boundaries] == ["flow:0001"]


def test_name_keyed_declaration_order_does_not_change_normalized_plan():
    def build(*, reversed_declarations):
        @operation(
            name="authoring.mapping_order.produce",
            inputs={"deck": DECK},
            config={"corner": parameter(str)},
            outputs={"raw": RAW},
        )
        def produce(deck, *, corner):
            raise AssertionError("must not run")

        input_items = [("left", RAW), ("right", RAW)]
        config_items = [("label", str), ("corner", str)]
        output_items = [("raw", RAW), ("report", REPORT)]
        if reversed_declarations:
            input_items.reverse()
            config_items.reverse()
            output_items.reverse()

        @operation(
            name="authoring.mapping_order.combine",
            inputs=dict(input_items),
            config={name: parameter(value_type) for name, value_type in config_items},
            outputs=dict(output_items),
        )
        def combine(left, right, *, label, corner):
            raise AssertionError("must not run")

        with plan() as draft:
            deck = input_artifact("input.spice", "spice-deck")
            left = produce(deck, corner="ss")
            right = produce(deck, corner="ff")
            combined = combine(
                right=right,
                left=left,
                label="comparison",
                corner="all",
            )
        return draft.finish(outputs={"raw": combined.raw, "report": combined.report})

    forward = build(reversed_declarations=False)
    reverse = build(reversed_declarations=True)

    assert forward.to_data() == reverse.to_data()
    assert [edge.id for edge in forward.edges] == ["edge:0001", "edge:0002"]
    combine = next(
        definition
        for definition in forward.operations
        if definition.identity.name == "authoring.mapping_order.combine"
    )
    assert [contract.name for contract in combine.inputs] == ["left", "right"]
    assert [contract.name for contract in combine.config] == ["corner", "label"]
    assert [contract.name for contract in combine.outputs] == ["raw", "report"]


def test_nested_static_branch_and_fan_in_normalize_to_one_plan():
    @operation(
        inputs={"deck": DECK},
        config={"corner": parameter(str)},
        outputs={"raw": RAW},
    )
    def simulate(deck, *, corner):
        raise AssertionError("must not run")

    @operation(
        inputs={"left": RAW, "right": RAW}, outputs={"report": REPORT}
    )
    def compare(left, right):
        raise AssertionError("must not run")

    @flow
    def characterize(deck, *, corners):
        return {corner: simulate(deck, corner=corner) for corner in corners}

    @flow
    def study(deck, *, include_slow):
        corners = ["tt"]
        if include_slow:
            corners.append("ss")
        branches = characterize(deck, corners=corners)
        return compare(branches["tt"], branches["ss"])

    with plan() as draft:
        result = study(
            input_artifact("amplifier.spice", "spice-deck"), include_slow=True
        )
    normalized = draft.finish(outputs={"report": result})

    assert len(normalized.invocations) == 3
    assert len(normalized.edges) == 2
    assert len(normalized.boundaries) == 2
    study_boundary = next(item for item in normalized.boundaries if item.parent_id is None)
    nested = next(item for item in normalized.boundaries if item.parent_id is not None)
    assert nested.parent_id == study_boundary.id
    assert {item.name for item in nested.outputs} == {"ss", "tt"}
    assert normalized.validate() is normalized


def test_multiple_outputs_require_explicit_selection_but_are_inspectable():
    @operation(inputs={"deck": DECK}, outputs={"raw": RAW, "report": REPORT})
    def split(deck):
        raise AssertionError("must not run")

    @operation(inputs={"raw": RAW}, outputs={"report": REPORT})
    def measure(raw):
        raise AssertionError("must not run")

    with plan() as draft:
        deck = input_artifact("input.spice", "spice-deck")
        result = split(deck)
        assert result.declared_outputs == ("raw", "report")
        assert result.outputs["raw"] is result.raw
        with pytest.raises(BindingError, match="select one explicitly"):
            measure(result)
        report = measure(result.raw)
    normalized = draft.finish(outputs={"report": report})
    assert len(normalized.edges) == 1


def test_invalid_bindings_and_flow_outputs_fail_during_planning():
    @operation(
        inputs={"deck": DECK},
        config={"corner": parameter(str)},
        outputs={"raw": RAW},
    )
    def simulate(deck, *, corner):
        raise AssertionError("must not run")

    @operation(inputs={"raw": RAW}, outputs={"report": REPORT})
    def measure(raw):
        raise AssertionError("must not run")

    @flow
    def invalid_flow(deck):
        simulate(deck, corner="tt")
        return "not an artifact"

    with plan() as draft:
        deck = input_artifact("input.spice", "spice-deck")
        with pytest.raises(BindingError, match="missing config"):
            simulate(deck)
        with pytest.raises(BindingError, match="unexpected bindings"):
            simulate(deck, corner="tt", extra=True)
        with pytest.raises(BindingError, match="expects str"):
            simulate(deck, corner=3)
        with pytest.raises(BindingError, match="expects artifact kind"):
            measure(deck)
        with pytest.raises(AuthoringError, match="must be an operation output"):
            invalid_flow(deck)
        good = simulate(deck, corner="tt")
    normalized = draft.finish(outputs={"raw": good})
    assert len(normalized.invocations) == 1
    assert normalized.invocations[0].id == "invoke:0001"


def test_foreign_references_and_finished_or_reused_sessions_are_rejected():
    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def simulate(deck):
        raise AssertionError("must not run")

    first_draft = plan()
    with first_draft:
        foreign = simulate(input_artifact("one.spice", "spice-deck"))
    first_draft.finish(outputs={"raw": foreign})

    with plan() as second_draft:
        with pytest.raises(BindingError, match="different plan"):
            simulate(foreign)
    second_draft.finish(outputs={})

    with pytest.raises(AuthoringError, match="already been finished"):
        first_draft.finish(outputs={})
    with pytest.raises(PlanningScopeError, match="cannot be reused"):
        with first_draft:
            pass


def test_definition_declarations_and_submit_boundary_fail_early():
    with pytest.raises(AuthoringError, match="declarations absent from signature"):

        @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
        def invalid(other):
            pass

    with pytest.raises(AuthoringError, match="must use Parameter"):
        operation(config={"corner": str})

    with pytest.raises(NotImplementedError, match="outside this planning spike"):
        submit(object())
