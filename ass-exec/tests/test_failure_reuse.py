"""A failure is kept, not reused — unless a human says otherwise.

The record cannot tell a design that does not converge from a node that ran out
of memory. Caching either as final would be wrong in a different direction, so
rerunning is the default and acceptance is explicit.
"""

import pytest

from ass_exec.attempt import AttemptSpent, accept_for_reuse, launch_or_attach
from ass_exec.durability import Durability, execute
from ass_exec.journal import AttemptJournal
from ass_exec.reuse import attempts_for, scan_attempts
from ass_exec.transport import InProcessTransport

BUNDLE = {"operation": "simulate", "inputs": {"deck": "sha256:aaa"}}

COMMON = {"durability": Durability.RECORDED, "plan_id": "p", "invocation_id": "corner-tt"}


def flaky(outcomes):
    """An operation that fails the first `outcomes` times, then succeeds."""

    state = {"calls": 0}

    def simulate(**kwargs):
        state["calls"] += 1
        if state["calls"] <= outcomes:
            raise MemoryError("node ran out of memory")
        return {"gain_db": 60.0}

    return InProcessTransport({"simulate": simulate}), state


def test_a_success_is_reused(tmp_path):
    transport, state = flaky(0)
    execute(transport, BUNDLE, root=str(tmp_path), **COMMON)
    second = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)

    assert second.disposition == "completed"
    assert state["calls"] == 1


def test_a_failure_is_not_reused_and_the_work_runs_again(tmp_path):
    transport, state = flaky(1)
    first = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)
    second = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)

    assert first.outcome == "failed"
    assert second.outcome == "succeeded"
    assert state["calls"] == 2


def test_the_failed_attempt_is_retained_for_inspection(tmp_path):
    transport, _ = flaky(1)
    execute(transport, BUNDLE, root=str(tmp_path), **COMMON)
    execute(transport, BUNDLE, root=str(tmp_path), **COMMON)

    recorded = attempts_for(tmp_path, plan_id="p", invocation_id="corner-tt")
    outcomes = sorted(item.outcome for item in recorded)
    assert outcomes == ["failed", "succeeded"]
    assert len(scan_attempts(tmp_path)) == 2


def test_repeated_failures_each_get_their_own_attempt(tmp_path):
    transport, state = flaky(3)
    for _ in range(3):
        execute(transport, BUNDLE, root=str(tmp_path), **COMMON)

    assert state["calls"] == 3
    assert len(scan_attempts(tmp_path)) == 3
    assert all(item.outcome == "failed" for item in scan_attempts(tmp_path))


def test_an_accepted_failure_is_reused_afterwards(tmp_path):
    transport, state = flaky(1)
    first = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)
    assert first.outcome == "failed"

    accept_for_reuse(first.journal, reason="known-bad corner, under debug")
    second = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)

    assert second.disposition == "completed"
    assert second.outcome == "failed"
    assert state["calls"] == 1, "the work must not run again once accepted"


def test_acceptance_is_durable_and_attributable(tmp_path):
    transport, _ = flaky(1)
    result = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)
    accept_for_reuse(result.journal, reason="investigating the OOM separately")

    reread = AttemptJournal(tmp_path, result.journal.identity).fold()
    assert reread.reuse_accepted is True
    assert reread.reuse_reason == "investigating the OOM separately"


def test_accepting_a_result_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(Exception, match="no published result"):
        accept_for_reuse(AttemptJournal(tmp_path, "ass-nothing"), reason="x")


def test_the_low_level_path_reports_a_spent_attempt(tmp_path):
    transport, _ = flaky(1)
    result = execute(transport, BUNDLE, root=str(tmp_path), **COMMON)
    journal = AttemptJournal(tmp_path, result.journal.identity)

    with pytest.raises(AttemptSpent, match="not reused automatically"):
        launch_or_attach(journal, transport, BUNDLE)


def test_endless_failure_stops_with_an_actionable_error(tmp_path):
    transport, _ = flaky(99)
    for _ in range(3):
        execute(transport, BUNDLE, root=str(tmp_path), max_attempts=3, **COMMON)

    with pytest.raises(Exception, match="accept_for_reuse"):
        execute(transport, BUNDLE, root=str(tmp_path), max_attempts=3, **COMMON)


def test_a_changed_input_starts_a_fresh_sequence(tmp_path):
    """Failures at one set of inputs must not consume attempts at another."""

    transport, state = flaky(1)
    execute(transport, BUNDLE, root=str(tmp_path), **COMMON)

    changed = dict(BUNDLE, inputs={"deck": "sha256:bbb"})
    result = execute(transport, changed, root=str(tmp_path), **COMMON)

    assert result.outcome == "succeeded"
    assert state["calls"] == 2
