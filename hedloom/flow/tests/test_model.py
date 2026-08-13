from dataclasses import FrozenInstanceError, replace
import json

import pytest

from hedloom_flow.model import (
    ArtifactAddress,
    ArtifactContract,
    ArtifactSource,
    ArtifactSourceReference,
    CodecContract,
    ConfigBinding,
    ConfigContract,
    CollectionInputBinding,
    ContractError,
    DependencyEdge,
    FlowBoundary,
    FlowDefinition,
    FlowIdentity,
    FrozenList,
    FrozenObject,
    InputBinding,
    InputContract,
    Invocation,
    MaterializationSpec,
    NamedOutput,
    OperationDefinition,
    OperationIdentity,
    OutputContract,
    OutputReference,
    Plan,
    PlanValidationError,
    local,
    named_policy,
    resolve_policy,
)


DECK = ArtifactContract("spice-deck")
RAW = ArtifactContract("simulation-raw")
REPORT = ArtifactContract("measurement-report")

SIMULATE_ID = OperationIdentity("example.simulate", "1")
MERGE_ID = OperationIdentity("example.merge", "1")
ROOT_FLOW_ID = FlowIdentity("example.study", "1")
BRANCH_FLOW_ID = FlowIdentity("example.characterize", "1")

JSON_CODEC = CodecContract(
    "json", "1", {"encoding": "utf-8", "dialect": {"indent": None}}
)
REPOSITORY_JSON = MaterializationSpec(
    JSON_CODEC, "repository-relative", "repository-checkout"
)


def source(identifier: str, locator: str, artifact: ArtifactContract) -> ArtifactSource:
    return ArtifactSource(
        identifier,
        ArtifactAddress("repository-relative", locator),
        artifact,
        REPOSITORY_JSON,
    )


def branching_plan() -> Plan:
    simulate = OperationDefinition(
        identity=SIMULATE_ID,
        inputs=(InputContract("deck", DECK),),
        config=(ConfigContract("corner", str),),
        outputs=(OutputContract("raw", RAW),),
        default_policy=named_policy("lsf")(queue="short"),
    )
    merge = OperationDefinition(
        identity=MERGE_ID,
        inputs=(InputContract("left", RAW), InputContract("right", RAW)),
        outputs=(OutputContract("report", REPORT),),
    )
    deck_source = source("source:deck", "inputs/amplifier.spice", DECK)
    tt = Invocation(
        id="invoke:tt",
        operation=SIMULATE_ID,
        inputs=(InputBinding("deck", ArtifactSourceReference(deck_source.id)),),
        config=(ConfigBinding("corner", "tt"),),
        policy=simulate.default_policy,
        boundary_id="flow:branches",
    )
    ss = Invocation(
        id="invoke:ss",
        operation=SIMULATE_ID,
        inputs=(InputBinding("deck", ArtifactSourceReference(deck_source.id)),),
        config=(ConfigBinding("corner", "ss"),),
        policy=simulate.default_policy,
        boundary_id="flow:branches",
    )
    merged = Invocation(
        id="invoke:merge",
        operation=MERGE_ID,
        inputs=(
            InputBinding("left", OutputReference(tt.id, "raw")),
            InputBinding("right", OutputReference(ss.id, "raw")),
        ),
        policy=local(),
        boundary_id="flow:root",
    )
    return Plan(
        operations=(simulate, merge),
        flows=(FlowDefinition(ROOT_FLOW_ID), FlowDefinition(BRANCH_FLOW_ID)),
        sources=(deck_source,),
        invocations=(tt, ss, merged),
        edges=(
            DependencyEdge(
                "edge:tt:merge",
                OutputReference(tt.id, "raw"),
                merged.id,
                "left",
                RAW.kind,
            ),
            DependencyEdge(
                "edge:ss:merge",
                OutputReference(ss.id, "raw"),
                merged.id,
                "right",
                RAW.kind,
            ),
        ),
        boundaries=(
            FlowBoundary(
                "flow:root",
                ROOT_FLOW_ID,
                outputs=(NamedOutput("report", OutputReference(merged.id, "report")),),
            ),
            FlowBoundary(
                "flow:branches",
                BRANCH_FLOW_ID,
                parent_id="flow:root",
                outputs=(
                    NamedOutput("tt", OutputReference(tt.id, "raw")),
                    NamedOutput("ss", OutputReference(ss.id, "raw")),
                ),
            ),
        ),
        outputs=(NamedOutput("report", OutputReference(merged.id, "report")),),
    )


def collection_plan() -> Plan:
    plan = branching_plan()
    merge = replace(
        plan.operations[1],
        inputs=(InputContract("measurements", RAW, cardinality="collection"),),
    )
    merged = replace(
        plan.invocations[2],
        inputs=(
            CollectionInputBinding(
                "measurements",
                (
                    OutputReference("invoke:tt", "raw"),
                    OutputReference("invoke:ss", "raw"),
                ),
            ),
        ),
    )
    edges = (
        replace(
            plan.edges[0],
            target_input_name="measurements",
            target_member_index=0,
        ),
        replace(
            plan.edges[1],
            target_input_name="measurements",
            target_member_index=1,
        ),
    )
    return replace(
        plan,
        operations=(plan.operations[0], merge),
        invocations=(*plan.invocations[:2], merged),
        edges=edges,
    )


def source_collection_plan() -> Plan:
    plan = collection_plan()
    external = source(
        "source:measurements", "inputs/existing-measurements.json", RAW
    )
    merged = replace(
        plan.invocations[2],
        inputs=(
            CollectionInputBinding(
                "measurements",
                (
                    ArtifactSourceReference(external.id),
                    OutputReference("invoke:ss", "raw"),
                ),
            ),
        ),
    )
    edges = (
        replace(
            plan.edges[0],
            id="edge:0001",
            source=ArtifactSourceReference(external.id),
        ),
        replace(plan.edges[1], id="edge:0002"),
    )
    return replace(
        plan,
        sources=(*plan.sources, external),
        invocations=(*plan.invocations[:2], merged),
        edges=edges,
    )


def test_values_are_deeply_immutable_and_policies_are_only_data():
    options = {"queue": "short", "constraints": ["linux", "x86_64"]}
    lsf = named_policy("lsf")
    policy = lsf(**options)
    options["constraints"].append("mutated-after-construction")

    assert policy.name == "lsf"
    assert isinstance(dict(policy.options.items)["constraints"], FrozenList)
    assert policy != local()
    assert resolve_policy(None, policy, local()) is policy
    assert resolve_policy(None, None, None) == local()
    with pytest.raises(FrozenInstanceError):
        policy.name = "changed"
    with pytest.raises(FrozenInstanceError):
        branching_plan().invocations[0].id = "changed"


def test_materialization_values_are_deeply_immutable_canonical_data_only():
    options = {"encoding": "utf-8", "features": ["z", {"enabled": True}]}
    declared_codec = CodecContract("json", "2", options)
    declared_address = ArtifactAddress(
        "repository-relative", "inputs/../opaque.json"
    )
    declared_materialization = MaterializationSpec(
        declared_codec, "repository-relative", "repository-checkout"
    )
    options["features"].append("mutated")

    assert dict(declared_codec.options.items)["features"] == FrozenList(
        ("z", FrozenObject((("enabled", True),)))
    )
    assert declared_address.locator == "inputs/../opaque.json"
    assert declared_materialization.codec is declared_codec
    with pytest.raises(FrozenInstanceError):
        declared_address.locator = "normalized.json"
    with pytest.raises(ContractError, match="artifact locator"):
        ArtifactAddress("repository-relative", " bad ")
    with pytest.raises(ContractError, match="artifact address space"):
        ArtifactAddress("bad space", "opaque")

    data = branching_plan().to_data()
    assert data["schema_version"] == 3
    assert data["sources"][0]["materialized_as"]["codec"] == {
        "name": "json",
        "version": "1",
        "options": {"dialect": {"indent": None}, "encoding": "utf-8"},
    }
    assert data["sources"][0]["address"] == {
        "address_space": "repository-relative",
        "locator": "inputs/amplifier.spice",
    }
    assert data["operations"][0]["outputs"][0]["can_materialize_as"] is None
    with pytest.raises(ContractError, match="schema_version must be 3"):
        Plan(schema_version=1)

    malformed_codec = replace(JSON_CODEC)
    malformed_options = FrozenObject()
    object.__setattr__(malformed_options, "items", (("bad", object()),))
    object.__setattr__(malformed_codec, "options", malformed_options)
    malformed_materialization = replace(REPOSITORY_JSON, codec=malformed_codec)
    valid = branching_plan()
    malformed_source = replace(
        valid.sources[0], materialized_as=malformed_materialization
    )
    with pytest.raises(PlanValidationError) as caught:
        replace(valid, sources=(malformed_source,)).validate()
    assert "invalid_source_materialization" in {
        issue.code for issue in caught.value.issues
    }


@pytest.mark.parametrize(
    ("field", "replacement", "expected_code"),
    [
        ("address", None, "invalid_source_address"),
        ("artifact", None, "invalid_source_artifact"),
        ("materialized_as", None, "invalid_source_materialization"),
        (
            "address",
            ArtifactAddress("other-space", "inputs/amplifier.spice"),
            "source_address_space_mismatch",
        ),
    ],
)
def test_plan_independently_rejects_malformed_source_declarations(
    field, replacement, expected_code
):
    valid = branching_plan()
    malformed_source = replace(valid.sources[0])
    object.__setattr__(malformed_source, field, replacement)
    malformed = replace(valid, sources=(malformed_source,))

    with pytest.raises(PlanValidationError) as caught:
        malformed.validate()

    assert expected_code in {issue.code for issue in caught.value.issues}


def test_reference_value_classes_are_fixed_and_canonical():
    source_reference = ArtifactSourceReference("source:deck")
    output_reference = OutputReference("invoke:merge", "report")

    assert source_reference.value_class == "artifact"
    assert output_reference.value_class == "ephemeral"
    with pytest.raises(FrozenInstanceError):
        source_reference.value_class = "ephemeral"
    data = branching_plan().to_data()
    source_binding = next(
        binding
        for invocation in data["invocations"]
        for binding in invocation["inputs"]
        if binding["reference"]["type"] == "source"
    )
    assert source_binding["reference"]["value_class"] == "artifact"
    assert data["outputs"][0]["reference"]["value_class"] == "ephemeral"


def test_valid_nested_branching_and_fan_in_plan():
    plan = branching_plan()

    assert plan.validate() is plan
    assert [boundary.id for boundary in plan.boundaries] == [
        "flow:root",
        "flow:branches",
    ]
    assert len(plan.edges) == 2
    assert plan.outputs[0].reference == OutputReference("invoke:merge", "report")


def test_plain_data_and_json_are_deterministic():
    plan = branching_plan()
    reordered = replace(
        plan,
        operations=tuple(reversed(plan.operations)),
        flows=tuple(reversed(plan.flows)),
        invocations=tuple(reversed(plan.invocations)),
        edges=tuple(reversed(plan.edges)),
        boundaries=tuple(reversed(plan.boundaries)),
    )

    assert reordered.validate() is reordered
    assert reordered.to_data() == plan.to_data()
    assert reordered.to_json() == plan.to_json()
    assert json.loads(plan.to_json()) == plan.to_data()
    assert " " not in plan.to_json()


def test_collection_plan_accepts_one_positioned_edge_per_ordered_member():
    plan = collection_plan()

    assert plan.validate() is plan
    binding = plan.invocations[-1].inputs[0]
    assert isinstance(binding, CollectionInputBinding)
    assert [reference.invocation_id for reference in binding.references] == [
        "invoke:tt",
        "invoke:ss",
    ]
    assert [edge.target_member_index for edge in plan.edges] == [0, 1]
    serialized_invocation = next(
        invocation
        for invocation in plan.to_data()["invocations"]
        if invocation["id"] == "invoke:merge"
    )
    assert [
        reference["invocation_id"]
        for reference in serialized_invocation["inputs"][0]["references"]
    ] == ["invoke:tt", "invoke:ss"]


def test_source_collection_members_have_positioned_edges_and_validate_by_index():
    plan = source_collection_plan()
    reordered = replace(
        plan,
        sources=tuple(reversed(plan.sources)),
        invocations=tuple(reversed(plan.invocations)),
        edges=tuple(reversed(plan.edges)),
    )

    assert plan.validate() is plan
    assert reordered.validate() is reordered
    assert [type(edge.source) for edge in plan.edges] == [
        ArtifactSourceReference,
        OutputReference,
    ]
    assert [edge.target_member_index for edge in plan.edges] == [0, 1]
    assert reordered.to_json() == plan.to_json()
    assert json.loads(plan.to_json()) == plan.to_data()

    malformed = replace(
        plan,
        edges=(
            replace(plan.edges[0], source=OutputReference("invoke:tt", "raw")),
            plan.edges[1],
        ),
    )
    with pytest.raises(PlanValidationError) as caught:
        malformed.validate()
    assert "edge_binding_mismatch" in {
        issue.code for issue in caught.value.issues
    }


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda plan: replace(plan, edges=plan.edges[:1]),
            "missing_dependency_edge",
        ),
        (
            lambda plan: replace(
                plan,
                edges=(
                    plan.edges[0],
                    replace(plan.edges[1], target_member_index=0),
                ),
            ),
            "duplicate_target_edge",
        ),
        (
            lambda plan: replace(
                plan,
                edges=(
                    replace(plan.edges[0], target_member_index=1),
                    replace(plan.edges[1], target_member_index=0),
                ),
            ),
            "edge_binding_mismatch",
        ),
        (
            lambda plan: replace(
                plan,
                edges=(replace(plan.edges[0], target_member_index=None), plan.edges[1]),
            ),
            "missing_edge_member_position",
        ),
        (
            lambda plan: replace(
                plan,
                edges=(replace(plan.edges[0], target_member_index=7), plan.edges[1]),
            ),
            "invalid_edge_member_position",
        ),
        (
            lambda plan: replace(
                plan,
                invocations=(
                    *plan.invocations[:2],
                    replace(plan.invocations[2], inputs=()),
                ),
                edges=(),
            ),
            "missing_input",
        ),
    ],
)
def test_collection_member_position_defects_are_rejected(mutate, expected_code):
    malformed = mutate(collection_plan())

    with pytest.raises(PlanValidationError) as caught:
        malformed.validate()

    assert expected_code in {issue.code for issue in caught.value.issues}


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda plan: replace(
                plan, invocations=plan.invocations + (plan.invocations[0],)
            ),
            "duplicate_invocation_id",
        ),
        (
            lambda plan: replace(
                plan,
                invocations=(
                    replace(
                        plan.invocations[0],
                        inputs=(
                            InputBinding("deck", ArtifactSourceReference("source:absent")),
                        ),
                    ),
                    *plan.invocations[1:],
                ),
            ),
            "unknown_artifact_source",
        ),
        (
            lambda plan: replace(
                plan,
                edges=(replace(plan.edges[0], artifact_kind="wrong-kind"), plan.edges[1]),
            ),
            "edge_source_kind_mismatch",
        ),
        (
            lambda plan: replace(plan, edges=plan.edges[1:]),
            "missing_dependency_edge",
        ),
        (
            lambda plan: replace(
                plan,
                outputs=(
                    NamedOutput("report", OutputReference("invoke:merge", "absent")),
                ),
            ),
            "unknown_owned_output",
        ),
        (
            lambda plan: replace(
                plan,
                boundaries=(
                    plan.boundaries[0],
                    replace(
                        plan.boundaries[1],
                        outputs=(
                            NamedOutput(
                                "foreign", OutputReference("invoke:merge", "report")
                            ),
                        ),
                    ),
                ),
            ),
            "boundary_output_not_owned",
        ),
    ],
)
def test_malformed_plans_are_rejected_with_structured_issues(mutate, expected_code):
    malformed = mutate(branching_plan())

    with pytest.raises(PlanValidationError) as caught:
        malformed.validate()

    assert expected_code in {issue.code for issue in caught.value.issues}


def test_authored_key_values_and_scoped_namespace_are_validated_in_the_model():
    plan = branching_plan()

    with pytest.raises(ContractError, match="authored key"):
        replace(plan.invocations[0], authored_key="bad key")

    corrupted_invocation = replace(plan.invocations[0])
    object.__setattr__(corrupted_invocation, "authored_key", "bad key")
    corrupted_plan = replace(
        plan,
        invocations=(corrupted_invocation, *plan.invocations[1:]),
    )
    with pytest.raises(PlanValidationError) as corrupted_caught:
        corrupted_plan.validate()
    assert "invalid_authored_key" in {
        issue.code for issue in corrupted_caught.value.issues
    }

    malformed = replace(
        plan,
        invocations=(
            *plan.invocations[:2],
            replace(
                plan.invocations[2],
                boundary_id=None,
                authored_key="shared",
            ),
        ),
        boundaries=(
            replace(plan.boundaries[0], authored_key="shared"),
            plan.boundaries[1],
        ),
    )

    with pytest.raises(PlanValidationError) as caught:
        malformed.validate()

    codes = {issue.code for issue in caught.value.issues}
    assert "duplicate_authored_key" in codes
    assert "keyed_invoke_id_mismatch" in codes
    assert "keyed_flow_id_mismatch" in codes
