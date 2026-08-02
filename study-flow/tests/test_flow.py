from __future__ import annotations

import os

import pytest

from ass_study_flow import demonstration_spec, prepare_study, run_local_demo
from ass_study_flow.artifacts import read_json


def test_local_preparation_materializes_inspectable_dependency_and_plan(
    tmp_path,
) -> None:
    prepared = prepare_study(
        demonstration_spec(), tmp_path, run_id="inspectable-run"
    )

    assert prepared.prepared_by_pid == os.getpid()
    assert prepared.spec_path.is_file()
    assert prepared.artifact_path.is_file()
    assert prepared.plan_path.is_file()

    plan = read_json(prepared.plan_path)
    assert plan["source_spec"] == str(prepared.spec_path)
    nodes = {node["id"]: node for node in plan["nodes"]}
    assert nodes["prepare"]["execution_role"] == "local-controller"
    assert nodes["simulate-low"]["execution_role"] == "mapped-worker"
    assert nodes["simulate-low"]["depends_on"] == ["prepare"]
    assert nodes["measure-low"]["depends_on"] == ["simulate-low"]
    assert nodes["reduce"]["depends_on"] == ["measure-low", "measure-high"]
    assert len(nodes) == 6


def test_local_dask_maps_two_basic_flows_and_reduces_them(tmp_path) -> None:
    completed = run_local_demo(tmp_path)

    assert completed.summary.count == 2
    assert completed.summary.minimum == pytest.approx(9.0)
    assert completed.summary.maximum == pytest.approx(11.0)
    assert completed.summary.mean == pytest.approx(10.0)
    assert completed.summary.artifact_path.is_file()

    case_ids = {item.case_id for item in completed.summary.measurements}
    assert case_ids == {"low", "high"}
    for measurement in completed.summary.measurements:
        assert measurement.artifact_path.is_file()
        assert measurement.simulation_artifact.is_file()
        simulation = read_json(measurement.simulation_artifact)
        assert simulation["attempt"]["worker_address"].startswith("inproc://")

    published = read_json(completed.summary.artifact_path)
    assert published["kind"] == "study-summary"
    assert published["summary"]["count"] == 2
    assert published["source_plan"] == str(completed.prepared.plan_path)


def test_preparation_never_overwrites_an_existing_run(tmp_path) -> None:
    spec = demonstration_spec()
    prepare_study(spec, tmp_path, run_id="same-run")

    with pytest.raises(FileExistsError, match="run already exists"):
        prepare_study(spec, tmp_path, run_id="same-run")


def test_explicit_run_id_cannot_escape_the_output_root(tmp_path) -> None:
    with pytest.raises(ValueError, match="stable kebab-case"):
        prepare_study(demonstration_spec(), tmp_path, run_id="../escape")
