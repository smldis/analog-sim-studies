"""Running a whole plan: order, reuse, value threading, and stopping."""

import sys

import pytest

from ass_exec.transport import InProcessTransport
from ass_run.driver import run_plan


def corner(key, temperature):
    return {
        "id": f"invoke:{key}",
        "authored_key": key,
        "operation": {"name": "estimate", "version": "1"},
        "config": [{"name": "t", "value": temperature}],
        "inputs": [],
    }


def summary(members):
    return {
        "id": "invoke:summary",
        "authored_key": "summary",
        "operation": {"name": "summarize", "version": "1"},
        "config": [],
        "inputs": [
            {
                "cardinality": "collection",
                "name": "measurements",
                "references": [
                    {
                        "type": "output",
                        "invocation_id": f"invoke:{member}",
                        "output_name": "metrics",
                    }
                    for member in members
                ],
            }
        ],
    }


def document(temperatures=(27, 125)):
    keys = ["tt", "ss"]
    return {
        "schema_version": 2,
        "sources": [],
        "operations": [
            {
                "identity": {"name": "estimate", "version": "1"},
                "outputs": [{"name": "metrics"}],
            },
            {
                "identity": {"name": "summarize", "version": "1"},
                "outputs": [{"name": "summary"}],
            },
        ],
        "invocations": [
            corner(key, value) for key, value in zip(keys, temperatures)
        ] + [summary(keys)],
    }


def transport(runs=None, failing=None):
    def estimate(*, t, **kwargs):
        if runs is not None:
            runs.append(t)
        if failing is not None and t == failing:
            raise ValueError("did not converge")
        return 60.0 - 0.05 * t

    def summarize(*, measurements=None, **kwargs):
        return {"worst": min(measurements), "count": len(measurements)}

    return InProcessTransport({"estimate": estimate, "summarize": summarize})


def test_a_plan_runs_in_dependency_order(tmp_path):
    report = run_plan(
        document(), transport(), plan_id="p", root=str(tmp_path)
    )

    assert report.succeeded
    assert [item.authored_key for item in report.outcomes] == ["tt", "ss", "summary"]


def test_outputs_are_threaded_into_the_inputs_that_reference_them(tmp_path):
    report = run_plan(document(), transport(), plan_id="p", root=str(tmp_path))
    final = report.outcomes[-1]

    assert final.value["count"] == 2
    assert final.value["worst"] == pytest.approx(60.0 - 0.05 * 125)


def test_a_second_run_reuses_everything(tmp_path):
    runs = []
    shared = transport(runs)
    run_plan(document(), shared, plan_id="p", root=str(tmp_path))
    second = run_plan(document(), shared, plan_id="p", root=str(tmp_path))

    assert len(second.reused) == 3
    assert second.ran == ()
    assert runs == [27, 125]


def test_editing_one_input_reruns_it_and_its_dependents_only(tmp_path):
    runs = []
    shared = transport(runs)
    run_plan(document(), shared, plan_id="p", root=str(tmp_path))
    report = run_plan(
        document((27, 150)), shared, plan_id="p", root=str(tmp_path)
    )

    reran = {item.authored_key for item in report.ran}
    reused = {item.authored_key for item in report.reused}
    assert reran == {"ss", "summary"}
    assert reused == {"tt"}
    assert runs == [27, 125, 150]


def test_a_failure_blocks_its_successors_rather_than_running_them(tmp_path):
    report = run_plan(
        document(), transport(failing=125), plan_id="p", root=str(tmp_path)
    )

    assert not report.succeeded
    by_key = {item.authored_key: item for item in report.outcomes}
    assert by_key["tt"].outcome == "succeeded"
    assert by_key["ss"].outcome == "failed"
    assert by_key["summary"].outcome == "blocked"
    assert report.blocked


def test_continuing_past_a_failure_is_possible_but_not_the_default(tmp_path):
    report = run_plan(
        document(),
        transport(failing=125),
        plan_id="p",
        root=str(tmp_path),
        stop_on_failure=False,
    )

    by_key = {item.authored_key: item for item in report.outcomes}
    assert by_key["summary"].outcome != "blocked"


def test_progress_is_reportable_while_the_run_proceeds(tmp_path):
    seen = []
    run_plan(
        document(),
        transport(),
        plan_id="p",
        root=str(tmp_path),
        on_event=seen.append,
    )
    assert [item.authored_key for item in seen] == ["tt", "ss", "summary"]


def test_the_report_summarises_what_happened(tmp_path):
    report = run_plan(document(), transport(), plan_id="p", root=str(tmp_path))
    text = report.summary()
    assert "tt" in text and "succeeded" in text


def test_a_failed_corner_is_retried_on_the_next_run(tmp_path):
    """Failures are not cached, so a fixed environment reruns them."""

    first = run_plan(
        document(), transport(failing=125), plan_id="p", root=str(tmp_path)
    )
    assert not first.succeeded

    second = run_plan(document(), transport(), plan_id="p", root=str(tmp_path))
    assert second.succeeded
    by_key = {item.authored_key: item for item in second.outcomes}
    assert by_key["tt"].reused, "the corner that worked must not rerun"
    assert by_key["ss"].ran
