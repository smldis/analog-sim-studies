import json

import pytest

from ass_exec.journal import AttemptJournal, JournalError


def journal(tmp_path, identity="ass-test"):
    return AttemptJournal(tmp_path, identity)


def test_fresh_attempt_folds_to_unsubmitted(tmp_path):
    state = journal(tmp_path).fold()
    assert state.phase == "unsubmitted"
    assert state.events == ()


def test_events_are_append_only_and_sequenced(tmp_path):
    log = journal(tmp_path)
    log.append("created", operation="simulate")
    log.append("submit_intent", transport="fake")
    log.append("submit_receipt", handle={"job_id": "1"})
    assert [event.event for event in log.events()] == [
        "created",
        "submit_intent",
        "submit_receipt",
    ]
    assert [event.seq for event in log.events()] == [0, 1, 2]


def test_intent_without_receipt_folds_to_the_crash_window(tmp_path):
    log = journal(tmp_path)
    log.append("submit_intent", transport="fake")
    assert log.fold().phase == "intended"


def test_indeterminate_submission_stays_in_the_crash_window(tmp_path):
    log = journal(tmp_path)
    log.append("submit_intent", transport="fake")
    log.append("submit_indeterminate", error="TransportError: lost")
    assert log.fold().phase == "intended"


def test_established_refusal_returns_to_unsubmitted(tmp_path):
    log = journal(tmp_path)
    log.append("submit_intent", transport="fake")
    log.append("submit_refused", error="SubmissionRefused: bad queue")
    assert log.fold().phase == "unsubmitted"


def test_state_is_derived_only_from_the_durable_record(tmp_path):
    log = journal(tmp_path)
    log.append("submit_intent", transport="fake")
    log.append("submit_receipt", handle={"job_id": "42"})
    log.append("cancel_requested", reason="operator asked")

    reread = AttemptJournal(tmp_path, "ass-test").fold()
    assert reread.phase == "submitted"
    assert reread.handle == {"job_id": "42"}
    assert reread.cancel_requested is True
    assert reread.cancel_reason == "operator asked"


def test_manifest_becomes_visible_before_the_terminal_record(tmp_path):
    log = journal(tmp_path)
    log.append("submit_intent", transport="fake")
    log.append("submit_receipt", handle={"job_id": "7"})
    log.publish_terminal(outcome="succeeded", manifest={"value": 3})

    document = json.loads(log.manifest_path.read_text())
    assert document["outcome"] == "succeeded"
    assert document["result"] == {"value": 3}
    assert log.fold().phase == "terminal"
    assert log.events()[-1].event == "terminal"


def test_publication_leaves_no_partial_file(tmp_path):
    log = journal(tmp_path)
    log.publish_terminal(outcome="failed", manifest={"error": "boom"})
    assert not (log.directory / "manifest.json.partial").exists()


def test_unknown_events_and_outcomes_are_refused(tmp_path):
    log = journal(tmp_path)
    with pytest.raises(JournalError):
        log.append("invented_event")
    with pytest.raises(JournalError):
        log.publish_terminal(outcome="mostly_fine", manifest={})


def test_malformed_journal_lines_are_reported_not_ignored(tmp_path):
    log = journal(tmp_path)
    log.append("created")
    with open(log.log_path, "a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    with pytest.raises(JournalError):
        log.fold()
