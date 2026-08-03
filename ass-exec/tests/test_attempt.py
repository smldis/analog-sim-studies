import json

import pytest

from ass_exec.attempt import (
    ReconciliationError,
    UnrecoverableAttempt,
    launch_or_attach,
    reconcile,
    request_cancel,
)
from ass_exec.journal import AttemptJournal
from ass_exec.transport import InProcessTransport, SubmissionRefused

from fakes import FakeBatchStore, FakeBatchTransport

BUNDLE = {
    "plan": "plan-1",
    "invocation": "inv-a",
    "operation": "double",
    "arguments": {"value": 21},
}


def journal(tmp_path, identity="ass-attempt"):
    return AttemptJournal(tmp_path, identity)


def in_process(counter=None):
    def double(value):
        if counter is not None:
            counter.append(value)
        return value * 2

    return InProcessTransport({"double": double})


def test_first_call_claims_and_submits_once(tmp_path):
    runs = []
    result = launch_or_attach(journal(tmp_path), in_process(runs), BUNDLE)
    assert result.disposition == "claimed"
    assert result.state.phase == "submitted"
    assert runs == [21]


def test_intent_is_durable_before_the_substrate_is_touched(tmp_path):
    log = journal(tmp_path)
    launch_or_attach(log, in_process(), BUNDLE)
    order = [event.event for event in log.events()]
    assert order.index("submit_intent") < order.index("submit_receipt")


def test_second_call_attaches_without_resubmitting(tmp_path):
    runs = []
    transport = in_process(runs)
    log = journal(tmp_path)
    launch_or_attach(log, transport, BUNDLE)

    again = launch_or_attach(AttemptJournal(tmp_path, log.identity), transport, BUNDLE)
    assert again.disposition == "attached"
    assert runs == [21]


def test_completed_attempt_returns_the_manifest_without_rerunning(tmp_path):
    runs = []
    transport = in_process(runs)
    log = journal(tmp_path)
    launch_or_attach(log, transport, BUNDLE)
    reconcile(log, transport)

    again = launch_or_attach(AttemptJournal(tmp_path, log.identity), transport, BUNDLE)
    assert again.disposition == "completed"
    assert again.manifest["outcome"] == "succeeded"
    assert runs == [21]


def test_successful_reconciliation_publishes_the_value(tmp_path):
    transport = in_process()
    log = journal(tmp_path)
    launch_or_attach(log, transport, BUNDLE)
    state = reconcile(log, transport)

    assert state.outcome == "succeeded"
    assert log.read_manifest()["result"]["value"] == 42


def test_failure_is_a_recorded_outcome_not_an_exception(tmp_path):
    def explode():
        raise ValueError("device did not converge")

    transport = InProcessTransport({"explode": explode})
    log = journal(tmp_path)
    launch_or_attach(log, transport, {**BUNDLE, "operation": "explode", "arguments": {}})
    state = reconcile(log, transport)

    assert state.outcome == "failed"
    assert "device did not converge" in json.dumps(log.read_manifest())


def test_established_refusal_permits_a_later_submission(tmp_path):
    log = journal(tmp_path)
    with pytest.raises(SubmissionRefused):
        launch_or_attach(log, InProcessTransport({}), BUNDLE)
    assert log.fold().phase == "unsubmitted"

    result = launch_or_attach(log, in_process(), BUNDLE)
    assert result.disposition == "claimed"


def test_indeterminate_submission_blocks_a_blind_resubmission(tmp_path):
    store = FakeBatchStore()
    lossy = FakeBatchTransport(
        store,
        drop_receipt=True,
        discovery_is_authoritative=False,
        can_discover=False,
    )
    log = journal(tmp_path)
    with pytest.raises(Exception):
        launch_or_attach(log, lossy, BUNDLE)

    assert log.fold().phase == "intended"
    with pytest.raises(UnrecoverableAttempt):
        launch_or_attach(log, lossy, BUNDLE)
    assert len(store.jobs) == 1


def test_cancellation_records_intent_before_asking_the_substrate(tmp_path):
    store = FakeBatchStore()
    transport = FakeBatchTransport(store)
    log = journal(tmp_path)
    launch_or_attach(log, transport, BUNDLE)

    state = request_cancel(log, transport, reason="operator stopped the sweep")
    assert state.cancel_requested is True
    assert store.jobs[log.identity]["state"] == "cancelled"

    order = [event.event for event in log.events()]
    assert order.index("cancel_requested") < len(order)


def test_cancellation_intent_is_recorded_even_before_submission(tmp_path):
    store = FakeBatchStore()
    log = journal(tmp_path)
    state = request_cancel(log, FakeBatchTransport(store), reason="changed mind")
    assert state.cancel_requested is True
    assert store.jobs == {}


def test_success_after_requested_cancellation_is_not_normalized(tmp_path):
    store = FakeBatchStore()
    transport = FakeBatchTransport(store)
    log = journal(tmp_path)
    launch_or_attach(log, transport, BUNDLE)
    request_cancel(log, transport, reason="operator stopped the sweep")
    store.jobs[log.identity]["state"] = "succeeded"

    state = reconcile(log, transport)
    assert state.outcome == "unreconciled"


def test_vanished_work_is_published_as_unreconciled(tmp_path):
    store = FakeBatchStore()
    transport = FakeBatchTransport(store)
    log = journal(tmp_path)
    launch_or_attach(log, transport, BUNDLE)
    store.jobs.clear()

    state = reconcile(log, transport)
    assert state.outcome == "unreconciled"


def test_terminal_claim_without_evidence_is_a_reconciliation_failure(tmp_path):
    log = journal(tmp_path)
    log.append("submit_intent", transport="fake")
    log.append("submit_receipt", handle={"job_id": "1"})
    log.append("terminal", outcome="succeeded", manifest=str(log.manifest_path))

    with pytest.raises(ReconciliationError):
        launch_or_attach(log, in_process(), BUNDLE)
