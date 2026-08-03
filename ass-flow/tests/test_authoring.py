from dataclasses import FrozenInstanceError, replace
import json

import pytest

from ass_flow import (
    AuthoringError,
    BindingError,
    CollectionInputBinding,
    FlowCall,
    InputBinding,
    PlanningScopeError,
    PlanValidationError,
    address,
    artifact,
    artifacts,
    codec,
    flow,
    input_artifact,
    local,
    materializable,
    materialization,
    named_policy,
    operation,
    parameter,
    plan,
    submit,
)


DECK = artifact("spice-deck")
RAW = artifact("simulation-raw")
REPORT = artifact("measurement-report")
MEASUREMENT = artifact("measurement")
TEST_CODEC = codec("test-data", encoding="utf-8")
TEST_MATERIALIZATION = materialization(
    codec=TEST_CODEC,
    address_space="test-address-space",
    access_scope="test-scope",
)


def _source(locator, artifact_contract):
    return input_artifact(
        address("test-address-space", locator),
        artifact=artifact_contract,
        materialized_as=TEST_MATERIALIZATION,
    )


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
        result = study(_source("input.spice", DECK))
    normalized = draft.finish(outputs={"raw": result})

    assert calls == []
    assert len(normalized.invocations) == 1
    assert len(normalized.boundaries) == 1


def test_external_sources_require_the_strict_structured_authoring_surface():
    with plan() as draft:
        with pytest.raises(TypeError, match="positional"):
            input_artifact("legacy-uri", "spice-deck")
        with pytest.raises(AuthoringError, match=r"address\(\.\.\.\)"):
            input_artifact(
                "legacy-uri",
                artifact=DECK,
                materialized_as=TEST_MATERIALIZATION,
            )
        deck = _source("input.spice", DECK)
    normalized = draft.finish(outputs={})

    assert deck.reference.value_class == "artifact"
    assert normalized.sources[0].address.locator == "input.spice"


def test_source_deduplication_uses_the_complete_immutable_declaration():
    alternate_materialization = materialization(
        codec=codec("test-data", variant="alternate"),
        address_space="test-address-space",
        access_scope="test-scope",
    )
    shared_address = address("test-address-space", "shared.data")

    with plan() as draft:
        first = input_artifact(
            shared_address,
            artifact=DECK,
            materialized_as=TEST_MATERIALIZATION,
        )
        repeated = input_artifact(
            shared_address,
            artifact=DECK,
            materialized_as=TEST_MATERIALIZATION,
        )
        different_kind = input_artifact(
            shared_address,
            artifact=RAW,
            materialized_as=TEST_MATERIALIZATION,
        )
        different_materialization = input_artifact(
            shared_address,
            artifact=DECK,
            materialized_as=alternate_materialization,
        )
    normalized = draft.finish(outputs={})

    assert first is repeated
    assert len(normalized.sources) == 3
    assert different_kind.reference != first.reference
    assert different_materialization.reference != first.reference


def test_address_space_mismatch_fails_without_mutating_the_plan():
    mismatched = materialization(
        codec=TEST_CODEC,
        address_space="other-address-space",
        access_scope="test-scope",
    )

    with plan() as draft:
        with pytest.raises(AuthoringError, match="address space must match"):
            input_artifact(
                address("test-address-space", "opaque/../locator"),
                artifact=DECK,
                materialized_as=mismatched,
            )
        accepted = _source("opaque/../locator", DECK)
    normalized = draft.finish(outputs={})

    assert accepted.reference.source_id == "source:0001"
    assert normalized.sources[0].address.locator == "opaque/../locator"


def test_output_materialization_capability_is_ephemeral_metadata_only():
    def build(*, advertise_capability):
        output = (
            materializable(RAW, as_=TEST_MATERIALIZATION)
            if advertise_capability
            else RAW
        )

        @operation(
            name="authoring.capability.produce",
            inputs={"deck": DECK},
            outputs={"raw": output},
        )
        def produce(deck):
            raise AssertionError("must not run")

        @operation(
            name="authoring.capability.consume",
            inputs={"raw": RAW},
            outputs={"report": REPORT},
        )
        def consume(raw):
            raise AssertionError("must not run")

        with plan() as draft:
            deck = _source("input.spice", DECK)
            raw = produce(deck)
            report = consume(raw)
        return draft.finish(outputs={"report": report})

    plain = build(advertise_capability=False)
    capable = build(advertise_capability=True)
    produced = capable.invocations[0]
    consumed = capable.invocations[1]
    capability = capable.operations[0].outputs[0].can_materialize_as

    assert capability == TEST_MATERIALIZATION
    assert consumed.inputs[0].reference.value_class == "ephemeral"
    assert capable.outputs[0].reference.value_class == "ephemeral"
    assert [item.id for item in capable.sources] == [item.id for item in plain.sources]
    assert [item.id for item in capable.invocations] == [
        item.id for item in plain.invocations
    ]
    assert [item.id for item in capable.edges] == [item.id for item in plain.edges]
    assert capable.sources == plain.sources
    assert capable.invocations == plain.invocations
    assert capable.edges == plain.edges
    assert capable.outputs == plain.outputs
    assert produced.id == "invoke:0001"
    assert len(capable.sources) == 1
    assert not hasattr(capability, "locator")

    capable_data = capable.to_data()
    plain_data = plain.to_data()
    assert capable_data["operations"][1]["outputs"][0][
        "can_materialize_as"
    ] == capable_data["sources"][0]["materialized_as"]
    assert plain_data["operations"][1]["outputs"][0][
        "can_materialize_as"
    ] is None


def test_materializable_declarations_are_rejected_for_operation_inputs():
    with pytest.raises(AuthoringError, match=r"artifact\(\.\.\.\) or artifacts"):
        operation(inputs={"deck": materializable(DECK, as_=TEST_MATERIALIZATION)})


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
        deck = _source("input.spice", DECK)
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
        deck = _source("input.spice", DECK)
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
            result = study(_source("input.spice", DECK))
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
    assert isinstance(first.invocations[1].inputs[0], InputBinding)
    assert first.invocations[1].inputs[0].cardinality == "scalar"
    assert first.edges[0].target_member_index is None
    assert all(
        item["authored_key"] is None for item in first.to_data()["invocations"]
    )
    assert first.to_data()["boundaries"][0]["authored_key"] is None


def test_collection_input_preserves_member_order_in_bindings_edges_and_json():
    @operation(
        name="authoring.collections.measure",
        inputs={"deck": DECK},
        config={"label": parameter(str)},
        outputs={"measurement": MEASUREMENT},
    )
    def measure(deck, *, label):
        raise AssertionError("must not run")

    @operation(
        name="authoring.collections.summarize",
        inputs={"measurements": artifacts("measurement")},
        outputs={"report": REPORT},
    )
    def summarize(measurements):
        raise AssertionError("must not run")

    def build():
        with plan() as draft:
            deck = _source("input.spice", DECK)
            measurements = [
                measure(deck, label=label) for label in ("ss", "tt", "ff")
            ]
            report = summarize(measurements)
        return draft.finish(outputs={"report": report})

    first = build()
    second = build()
    summary = first.invocations[-1]
    binding = summary.inputs[0]

    assert first.to_data() == second.to_data()
    assert first.to_json() == second.to_json()
    assert first.operations[-1].inputs[0].required is True
    assert first.operations[-1].inputs[0].cardinality == "collection"
    assert isinstance(binding, CollectionInputBinding)
    assert binding.cardinality == "collection"
    assert [reference.invocation_id for reference in binding.references] == [
        "invoke:0001",
        "invoke:0002",
        "invoke:0003",
    ]
    assert [edge.source.invocation_id for edge in first.edges] == [
        "invoke:0001",
        "invoke:0002",
        "invoke:0003",
    ]
    assert [edge.target_member_index for edge in first.edges] == [0, 1, 2]

    data = json.loads(first.to_json())
    serialized_binding = data["invocations"][-1]["inputs"][0]
    assert serialized_binding["cardinality"] == "collection"
    assert [
        reference["invocation_id"]
        for reference in serialized_binding["references"]
    ] == ["invoke:0001", "invoke:0002", "invoke:0003"]
    assert [edge["target_member_index"] for edge in data["edges"]] == [0, 1, 2]
    assert "value" not in serialized_binding


def test_external_source_collection_member_gets_an_edge_without_scalar_regression():
    @operation(
        name="authoring.source_collections.measure",
        inputs={"deck": DECK},
        outputs={"measurement": MEASUREMENT},
    )
    def measure(deck):
        raise AssertionError("must not run")

    @operation(
        name="authoring.source_collections.summarize",
        inputs={"measurements": artifacts("measurement")},
        outputs={"report": REPORT},
    )
    def summarize(measurements):
        raise AssertionError("must not run")

    def build():
        with plan() as draft:
            deck = _source("input.spice", DECK)
            external = _source("existing-measurement.json", MEASUREMENT)
            produced = measure(deck)
            report = summarize([external, produced])
        return draft.finish(outputs={"report": report})

    first = build()
    second = build()
    data = json.loads(first.to_json())
    binding = data["invocations"][-1]["inputs"][0]

    assert first.to_data() == second.to_data()
    assert first.to_json() == second.to_json()
    assert len(first.edges) == 2
    assert [reference["type"] for reference in binding["references"]] == [
        "source",
        "output",
    ]
    assert [reference["value_class"] for reference in binding["references"]] == [
        "artifact",
        "ephemeral",
    ]
    assert [edge["source"]["type"] for edge in data["edges"]] == [
        "source",
        "output",
    ]
    assert [edge["source"]["value_class"] for edge in data["edges"]] == [
        "artifact",
        "ephemeral",
    ]
    assert [edge["target_member_index"] for edge in data["edges"]] == [0, 1]


def test_collection_inputs_reject_invalid_authored_values_early():
    @operation(inputs={"deck": DECK}, outputs={"measurement": MEASUREMENT})
    def measure(deck):
        raise AssertionError("must not run")

    @operation(
        inputs={"deck": DECK},
        outputs={"left": MEASUREMENT, "right": MEASUREMENT},
    )
    def split(deck):
        raise AssertionError("must not run")

    @operation(
        inputs={"measurements": artifacts("measurement")},
        outputs={"report": REPORT},
    )
    def summarize(measurements):
        raise AssertionError("must not run")

    with plan() as foreign_draft:
        foreign = measure(_source("foreign.spice", DECK))
    foreign_draft.finish(outputs={"measurement": foreign})

    with plan() as draft:
        deck = _source("input.spice", DECK)
        existing_measurement = _source(
            "existing-measurement.json", MEASUREMENT
        )
        measurement = measure(deck)
        multiple = split(deck)
        for invalid in (deck, "measurement.json", b"measurement", {"one": measurement}):
            with pytest.raises(BindingError, match="non-string sequence"):
                summarize(invalid)
        with pytest.raises(BindingError, match="non-string sequence"):
            summarize(member for member in [measurement])
        with pytest.raises(BindingError, match="must not be empty"):
            summarize([])
        with pytest.raises(BindingError, match="expects artifact kind"):
            summarize([measurement, deck])
        with pytest.raises(BindingError, match="different plan"):
            summarize([foreign])
        with pytest.raises(BindingError, match="select one explicitly"):
            summarize([multiple])
        report = summarize((measurement, existing_measurement))
    normalized = draft.finish(outputs={"report": report})

    assert len(normalized.invocations) == 3
    assert [edge.target_member_index for edge in normalized.edges] == [0, 1]
    assert normalized.to_data()["edges"][1]["source"]["type"] == "source"


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
            deck = _source("input.spice", DECK)
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
            _source("amplifier.spice", DECK), include_slow=True
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
        deck = _source("input.spice", DECK)
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
        deck = _source("input.spice", DECK)
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
        foreign = simulate(_source("one.spice", DECK))
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


def test_policy_and_key_options_compose_immutably_in_either_order():
    override = named_policy("lsf")(queue="short")

    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def simulate(deck):
        raise AssertionError("must not run")

    policy_view = simulate.options(policy=override)
    policy_then_key = policy_view.options(key="policy-first")
    key_view = simulate.options(key="key-first")
    key_then_policy = key_view.options(policy=override)

    assert policy_view.policy is override
    assert policy_view.key is None
    assert key_view.policy is None
    assert key_view.key == "key-first"
    assert policy_then_key.policy is override
    assert policy_then_key.key == "policy-first"
    assert key_then_policy.policy is override
    assert key_then_policy.key == "key-first"
    with pytest.raises(FrozenInstanceError):
        policy_then_key.key = "changed"

    with plan() as draft:
        deck = _source("input.spice", DECK)
        policy_then_key(deck)
        key_then_policy(deck)
    normalized = draft.finish(outputs={})

    assert [item.authored_key for item in normalized.invocations] == [
        "policy-first",
        "key-first",
    ]
    assert [item.policy for item in normalized.invocations] == [override, override]
    assert all("authored_key" in item for item in normalized.to_data()["invocations"])


def test_keyed_nested_flows_repeat_and_survive_an_unkeyed_sibling_insertion():
    @operation(
        name="authoring.identities.produce",
        inputs={"deck": DECK},
        outputs={"raw": RAW},
    )
    def produce(deck):
        raise AssertionError("must not run")

    @operation(
        name="authoring.identities.consume",
        inputs={"raw": artifacts("simulation-raw")},
        outputs={"report": REPORT},
    )
    def consume(raw):
        raise AssertionError("must not run")

    @operation(
        name="authoring.identities.noise",
        inputs={"deck": DECK},
        outputs={"raw": RAW},
    )
    def noise(deck):
        raise AssertionError("must not run")

    @flow(name="authoring.identities.inner")
    def inner(raw):
        return consume.options(key="consumer")(raw)

    @flow(name="authoring.identities.outer")
    def outer(deck):
        raw = [
            produce.options(key="producer-left")(deck),
            produce.options(key="producer-right")(deck),
        ]
        return inner.options(key="inner")(raw)

    @flow(name="authoring.identities.noise_flow")
    def noise_flow(deck):
        return noise(deck)

    def build(*, insert_sibling):
        with plan() as draft:
            deck = _source("input.spice", DECK)
            if insert_sibling:
                noise_flow(deck)
            report = outer.options(key="outer")(deck)
        return draft.finish(outputs={"report": report})

    baseline = build(insert_sibling=False)
    repeated = build(insert_sibling=False)
    inserted = build(insert_sibling=True)

    outer_view = outer.options(key="original")
    changed_outer_view = outer_view.options(key="changed")
    assert isinstance(outer_view, FlowCall)
    assert outer_view.key == "original"
    assert changed_outer_view.key == "changed"
    with pytest.raises(FrozenInstanceError):
        outer_view.key = "mutated"
    with pytest.raises(TypeError, match="policy"):
        outer.options(policy=local())

    assert baseline.to_data() == repeated.to_data()
    assert baseline.to_json() == repeated.to_json()
    assert {
        item.authored_key: item.id
        for item in baseline.invocations
        if item.authored_key is not None
    } == {
        item.authored_key: item.id
        for item in inserted.invocations
        if item.authored_key is not None
    }
    assert {
        item.authored_key: item.id
        for item in baseline.boundaries
        if item.authored_key is not None
    } == {
        item.authored_key: item.id
        for item in inserted.boundaries
        if item.authored_key is not None
    }
    assert [item.id for item in baseline.edges] == [item.id for item in inserted.edges]
    assert all(item.id.startswith("edge:key:") for item in baseline.edges)
    assert [item.target_member_index for item in baseline.edges] == [0, 1]
    assert inserted.invocations[0].id == "invoke:0001"
    assert inserted.boundaries[0].id == "flow:0001"
    assert {
        item["authored_key"] for item in baseline.to_data()["boundaries"]
    } == {"outer", "inner"}

    malformed = replace(
        baseline,
        edges=(replace(baseline.edges[0], id="edge:wrong"), baseline.edges[1]),
    )
    with pytest.raises(PlanValidationError) as caught:
        malformed.validate()
    assert "stable_edge_id_mismatch" in {
        issue.code for issue in caught.value.issues
    }


def test_duplicate_keys_share_one_operation_and_flow_namespace_per_scope():
    calls = []

    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def produce(deck):
        raise AssertionError("must not run")

    @flow
    def leaf(deck):
        calls.append("flow body ran")
        return produce(deck)

    @flow
    def keyed_scope(deck):
        return produce.options(key="reused")(deck)

    with plan() as draft:
        deck = _source("input.spice", DECK)
        produce.options(key="op-duplicate")(deck)
        with pytest.raises(AuthoringError, match="already used"):
            produce.options(key="op-duplicate")(deck)

        leaf.options(key="flow-duplicate")(deck)
        with pytest.raises(AuthoringError, match="already used"):
            leaf.options(key="flow-duplicate")(deck)

        produce.options(key="cross-kind")(deck)
        with pytest.raises(AuthoringError, match="already used"):
            leaf.options(key="cross-kind")(deck)

        keyed_scope.options(key="scope-a")(deck)
        keyed_scope.options(key="scope-b")(deck)
        leaf(deck)
    normalized = draft.finish(outputs={})

    assert calls == ["flow body ran", "flow body ran"]
    reused = [
        invocation
        for invocation in normalized.invocations
        if invocation.authored_key == "reused"
    ]
    assert len(reused) == 2
    assert reused[0].boundary_id != reused[1].boundary_id
    assert reused[0].id != reused[1].id
    assert [
        boundary.id
        for boundary in normalized.boundaries
        if boundary.authored_key is None
    ] == ["flow:0001"]
    assert normalized.validate() is normalized


def test_keyed_calls_and_edges_do_not_consume_unkeyed_counters():
    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def produce(deck):
        raise AssertionError("must not run")

    @operation(inputs={"raw": RAW}, outputs={"report": REPORT})
    def consume(raw):
        raise AssertionError("must not run")

    with plan() as draft:
        deck = _source("input.spice", DECK)
        keyed_raw = produce.options(key="keyed-producer")(deck)
        consume.options(key="keyed-consumer")(keyed_raw)
        unkeyed_raw = produce(deck)
        unkeyed_report = consume(unkeyed_raw)
    normalized = draft.finish(outputs={"report": unkeyed_report})

    unkeyed_invocation_ids = [
        item.id for item in normalized.invocations if item.authored_key is None
    ]
    assert unkeyed_invocation_ids == [
        "invoke:0001",
        "invoke:0002",
    ]
    stable_edges = [
        item for item in normalized.edges if item.id.startswith("edge:key:")
    ]
    counter_edges = [
        item.id for item in normalized.edges if item.id.startswith("edge:0")
    ]
    assert len(stable_edges) == 1
    assert counter_edges == ["edge:0001"]


def test_duplicate_operation_rollback_does_not_leak_or_consume_counters():
    @operation(
        name="authoring.rollback.accepted",
        inputs={"deck": DECK},
        outputs={"raw": RAW},
    )
    def accepted(deck):
        raise AssertionError("must not run")

    @operation(
        name="authoring.rollback.rejected",
        inputs={"deck": DECK},
        outputs={"raw": RAW},
    )
    def rejected(deck):
        raise AssertionError("must not run")

    with plan() as draft:
        deck = _source("input.spice", DECK)
        accepted(deck)
        accepted.options(key="reserved")(deck)
        with pytest.raises(AuthoringError, match="already used"):
            rejected.options(key="reserved")(deck)
        accepted(deck)
    normalized = draft.finish(outputs={})

    unkeyed_invocation_ids = [
        item.id for item in normalized.invocations if item.authored_key is None
    ]
    assert unkeyed_invocation_ids == [
        "invoke:0001",
        "invoke:0002",
    ]
    assert {item.identity.name for item in normalized.operations} == {
        "authoring.rollback.accepted"
    }
    assert len(normalized.invocations) == 3


def test_failing_keyed_flow_restores_keys_graph_and_every_unkeyed_counter():
    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def produce(deck):
        raise AssertionError("must not run")

    @operation(inputs={"raw": RAW}, outputs={"report": REPORT})
    def consume(raw):
        raise AssertionError("must not run")

    @flow(name="authoring.rollback.failing")
    def failing(deck):
        raw = produce.options(key="step")(deck)
        consume(raw)
        raise RuntimeError("planned failure")

    @flow(name="authoring.rollback.success")
    def success(deck):
        return produce.options(key="step")(deck)

    @flow(name="authoring.rollback.unkeyed")
    def unkeyed(deck):
        return produce(deck)

    with plan() as draft:
        deck = _source("input.spice", DECK)
        with pytest.raises(RuntimeError, match="planned failure"):
            failing.options(key="boundary")(deck)
        keyed = success.options(key="boundary")(deck)
        raw = produce(deck)
        report = consume(raw)
        later = unkeyed(deck)
    normalized = draft.finish(
        outputs={"keyed": keyed, "report": report, "later": later}
    )

    unkeyed_invocation_ids = [
        item.id for item in normalized.invocations if item.authored_key is None
    ]
    assert unkeyed_invocation_ids == [
        "invoke:0001",
        "invoke:0002",
        "invoke:0003",
    ]
    assert [item.id for item in normalized.edges] == ["edge:0001"]
    assert [item.id for item in normalized.boundaries if item.authored_key is None] == [
        "flow:0001"
    ]
    assert {item.identity.name for item in normalized.flows} == {
        "authoring.rollback.success",
        "authoring.rollback.unkeyed",
    }
    assert {item.authored_key for item in normalized.invocations} == {None, "step"}


@pytest.mark.parametrize(
    "invalid_key",
    ["", " leading", "trailing ", "_leading", "bad key", "é"],
)
def test_invalid_authored_key_syntax_fails_before_graph_mutation(invalid_key):
    @operation(inputs={"deck": DECK}, outputs={"raw": RAW})
    def produce(deck):
        raise AssertionError("must not run")

    @flow
    def wrapper(deck):
        return produce(deck)

    with plan() as draft:
        deck = _source("input.spice", DECK)
        with pytest.raises(AuthoringError, match="authored key"):
            produce.options(key=invalid_key)(deck)
        with pytest.raises(AuthoringError, match="authored key"):
            wrapper.options(key=invalid_key)(deck)
        result = produce(deck)
    normalized = draft.finish(outputs={"raw": result})

    assert [item.id for item in normalized.invocations] == ["invoke:0001"]
    assert normalized.boundaries == ()
