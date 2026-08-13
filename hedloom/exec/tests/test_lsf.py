"""Direct LSF submission, exercised against a fake `bsub`.

No cluster is contacted. What is testable without a farm is the submission
shape, the owner-bound discipline, and the mapping from exit status to
recorded outcome — which is most of what can go quietly wrong.
"""

import pytest

from hedloom_exec.attempt import launch_or_attach, reconcile
from hedloom_exec.durability import Durability, execute
from hedloom_exec.journal import AttemptJournal
from hedloom_exec.lsf import CommandResult, LSFInteractiveTransport, LSFPooledTransport
from hedloom_exec.transport import SubmissionRefused

BUNDLE = {"command": ["simulate", "--corner", "tt"]}


class FakeRunner:
    """Records argv and replays canned results, newest command first."""

    def __init__(self, result=None, bjobs=None):
        self.calls = []
        self.result = result or CommandResult(returncode=0, stdout="done")
        self.bjobs = bjobs or CommandResult(
            returncode=255, stderr="Job <hedloom-abc> is not found"
        )

    def __call__(self, argv, *, cwd=None, env=None, timeout=None):
        self.calls.append(list(argv))
        if argv[0] == "bjobs":
            return self.bjobs
        if argv[0] == "bkill":
            return CommandResult(returncode=0)
        return self.result


def transport(**kwargs):
    runner = kwargs.pop("runner", None) or FakeRunner()
    return LSFInteractiveTransport(walltime="30", runner=runner, **kwargs), runner


def test_submission_is_interactive_named_and_walltime_bounded():
    lsf, runner = transport()
    lsf.submit("hedloom-abc", BUNDLE)

    argv = runner.calls[0]
    assert argv[0] == "bsub"
    assert "-I" in argv
    assert argv[argv.index("-J") + 1] == "hedloom-abc"
    assert argv[argv.index("-W") + 1] == "30"
    assert argv[-3:] == ["simulate", "--corner", "tt"]


def test_walltime_is_mandatory():
    with pytest.raises(ValueError):
        LSFInteractiveTransport(walltime="")


def test_resource_request_is_passed_through():
    lsf, runner = transport(queue="normal", cores=4, resources="rusage[mem=8000]")
    lsf.submit("hedloom-abc", BUNDLE)

    argv = runner.calls[0]
    assert argv[argv.index("-q") + 1] == "normal"
    assert argv[argv.index("-n") + 1] == "4"
    assert argv[argv.index("-R") + 1] == "rusage[mem=8000]"


def test_a_bundle_without_a_command_is_refused_before_submission():
    lsf, runner = transport()
    with pytest.raises(SubmissionRefused):
        lsf.submit("hedloom-abc", {"arguments": {"value": 1}})
    assert runner.calls == []


def test_successful_exit_becomes_a_published_success(tmp_path):
    lsf, _ = transport()
    journal = AttemptJournal(tmp_path, "hedloom-abc")
    launch_or_attach(journal, lsf, BUNDLE)
    state = reconcile(journal, lsf)

    assert state.outcome == "succeeded"
    assert journal.read_manifest()["result"]["stdout"] == "done"


def test_nonzero_exit_becomes_a_published_failure(tmp_path):
    runner = FakeRunner(CommandResult(returncode=137, stderr="killed"))
    lsf, _ = transport(runner=runner)
    journal = AttemptJournal(tmp_path, "hedloom-abc")
    launch_or_attach(journal, lsf, BUNDLE)
    state = reconcile(journal, lsf)

    assert state.outcome == "failed"
    assert journal.read_manifest()["result"]["returncode"] == 137


def test_discovery_reports_nothing_when_no_job_survives():
    lsf, _ = transport()
    assert lsf.discover("hedloom-abc") is None


def test_discovery_finds_a_job_left_behind_by_an_earlier_run():
    runner = FakeRunner(bjobs=CommandResult(returncode=0, stdout="9001 RUN normal"))
    lsf, _ = transport(runner=runner)

    found = lsf.discover("hedloom-abc")
    assert found is not None
    assert "9001" in found["observed"]


def test_cancellation_targets_the_attempt_name():
    lsf, runner = transport()
    lsf.cancel({"identity": "hedloom-abc"})
    assert runner.calls[-1] == ["bkill", "-J", "hedloom-abc"]


def test_recorded_execution_over_lsf_reuses_a_published_result(tmp_path):
    runner = FakeRunner()
    lsf, _ = transport(runner=runner)
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path),
        "plan_id": "plan-1",
        "invocation_id": "inv-a",
    }

    first = execute(lsf, BUNDLE, **common)
    second = execute(lsf, BUNDLE, **common)

    assert first.outcome == "succeeded"
    assert second.disposition == "completed"
    assert sum(1 for call in runner.calls if call[0] == "bsub") == 1


def test_pooled_execution_refuses_rather_than_pretending():
    with pytest.raises(NotImplementedError):
        LSFPooledTransport().submit("hedloom-abc", BUNDLE)
