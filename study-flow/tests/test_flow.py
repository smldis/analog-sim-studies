from __future__ import annotations

import os
from typing import Any

import pytest

import ass_study_flow
from ass_study_flow import (
    FlowSpec,
    OperationContext,
    OperationSpec,
    WorkItemSpec,
    demonstration_spec,
    prepare_flow,
    read_artifact_payload,
    run_local_demo,
    run_local_flow,
)
from ass_study_flow.artifacts import read_json


def uppercase_text(
    context: OperationContext,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "upper": {
            "item_id": context.item_id,
            "text": inputs["item"]["text"].upper(),
            "prefix": inputs["shared"]["prefix"],
        }
    }


def count_characters(
    context: OperationContext,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    upper = inputs["previous"]["upper"]
    return {
        "length": {
            "item_id": context.item_id,
            "value": len(upper["prefix"] + upper["text"]),
        }
    }


def total_length(
    context: OperationContext,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    del context
    return {
        "total": sum(output["length"]["value"] for output in inputs["mapped"])
    }


def text_flow_spec() -> FlowSpec:
    return FlowSpec(
        flow_id="text-lengths",
        shared_inputs={"prefix": ">"},
        items=(
            WorkItemSpec(item_id="one", inputs={"text": "ab"}),
            WorkItemSpec(item_id="two", inputs={"text": "cde"}),
        ),
        preparation=OperationSpec(
            operation_id="materialize-context",
            input_ports=("authored",),
            output_ports=("shared",),
        ),
        map_operations=(
            OperationSpec(
                operation_id="uppercase-text",
                input_ports=("shared", "item"),
                output_ports=("upper",),
            ),
            OperationSpec(
                operation_id="count-characters",
                input_ports=("previous",),
                output_ports=("length",),
            ),
        ),
        reduction=OperationSpec(
            operation_id="total-length",
            input_ports=("mapped",),
            output_ports=("total",),
        ),
    )


def test_preparation_materializes_neutral_dependency_plan_and_attempt(tmp_path) -> None:
    prepared = prepare_flow(
        demonstration_spec(), tmp_path, run_id="inspectable-run"
    )

    assert prepared.spec_ref.path.is_file()
    assert prepared.plan_ref.path.is_file()
    assert prepared.manifest_ref.path.is_file()
    assert prepared.shared_ref.path.is_file()
    assert prepared.preparation_attempt.record_path.is_file()
    assert prepared.preparation_attempt.executor_address == (
        f"local-process://{os.getpid()}"
    )

    plan = read_json(prepared.plan_ref.path)
    nodes = {node["invocation_id"]: node for node in plan["invocations"]}
    assert nodes["prepare"]["execution_role"] == "local-controller"
    assert nodes["prepare"]["operation_id"] == "materialize-shared-input"
    assert nodes["combine-inputs-alpha"]["depends_on"] == ["prepare"]
    assert nodes["describe-output-alpha"]["depends_on"] == [
        "combine-inputs-alpha"
    ]
    assert nodes["reduce"]["depends_on"] == [
        "describe-output-alpha",
        "describe-output-beta",
    ]
    assert len(nodes) == 6


def test_local_dask_maps_two_generic_chains_and_collects_them(tmp_path) -> None:
    completed = run_local_demo(tmp_path)

    result = read_artifact_payload(completed.result)
    assert result["collection"]["count"] == 2
    assert [item["item_id"] for item in result["collection"]["items"]] == [
        "alpha",
        "beta",
    ]
    assert len(completed.attempts) == 6
    assert [attempt.invocation_id for attempt in completed.attempts] == [
        "prepare",
        "combine-inputs-alpha",
        "describe-output-alpha",
        "combine-inputs-beta",
        "describe-output-beta",
        "reduce",
    ]
    for attempt in completed.attempts:
        assert attempt.status == "succeeded"
        assert attempt.record_path.is_file()
    mapped = completed.attempts[1:-1]
    assert all(attempt.executor_address.startswith("inproc://") for attempt in mapped)
    assert all(attempt.outputs[0].path.is_file() for attempt in mapped)


def test_public_executor_accepts_unrelated_bound_operations(tmp_path) -> None:
    completed = run_local_flow(
        tmp_path,
        text_flow_spec(),
        {
            "uppercase-text": uppercase_text,
            "count-characters": count_characters,
            "total-length": total_length,
        },
    )

    assert read_artifact_payload(completed.result) == {"total": 7}
    assert {attempt.item_id for attempt in completed.attempts[1:-1]} == {
        "one",
        "two",
    }


def test_later_map_operation_must_consume_previous() -> None:
    with pytest.raises(ValueError, match="must consume previous"):
        FlowSpec(
            flow_id="invalid-chain",
            shared_inputs={},
            items=(WorkItemSpec(item_id="only", inputs={}),),
            preparation=OperationSpec(
                "materialize", ("authored",), ("shared",)
            ),
            map_operations=(
                OperationSpec("first", ("item",), ("first-output",)),
                OperationSpec("second", ("item",), ("second-output",)),
            ),
            reduction=OperationSpec("collect", ("mapped",), ("result",)),
        )


def test_preparation_never_overwrites_an_existing_run(tmp_path) -> None:
    spec = demonstration_spec()
    prepare_flow(spec, tmp_path, run_id="same-run")

    with pytest.raises(FileExistsError, match="run already exists"):
        prepare_flow(spec, tmp_path, run_id="same-run")


def test_explicit_run_id_cannot_escape_the_output_root(tmp_path) -> None:
    with pytest.raises(ValueError, match="stable kebab-case"):
        prepare_flow(demonstration_spec(), tmp_path, run_id="../escape")


def test_package_root_does_not_promote_demonstration_domain_types() -> None:
    for obsolete in (
        "CaseSpec",
        "SimulationAttempt",
        "MeasurementResult",
        "StudySummary",
    ):
        assert not hasattr(ass_study_flow, obsolete)
