from dataclasses import FrozenInstanceError, replace
import json

import pytest

from ass_flow.model import (
    ArtifactContract,
    ArtifactSource,
    ArtifactSourceReference,
    ConfigBinding,
    ConfigContract,
    DependencyEdge,
    FlowBoundary,
    FlowDefinition,
    FlowIdentity,
    FrozenList,
    InputBinding,
    InputContract,
    Invocation,
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
    source = ArtifactSource("source:deck", "inputs/amplifier.spice", DECK)
    tt = Invocation(
        id="invoke:tt",
        operation=SIMULATE_ID,
        inputs=(InputBinding("deck", ArtifactSourceReference(source.id)),),
        config=(ConfigBinding("corner", "tt"),),
        policy=simulate.default_policy,
        boundary_id="flow:branches",
    )
    ss = Invocation(
        id="invoke:ss",
        operation=SIMULATE_ID,
        inputs=(InputBinding("deck", ArtifactSourceReference(source.id)),),
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
        sources=(source,),
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
