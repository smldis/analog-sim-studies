"""Regression cover for the defects an adversarial review found.

Each test names the failure it prevents, because several of these were hidden
by fakes that agreed with the code's own misunderstandings.
"""

import json
import threading

import pytest

from ass_exec.attempt import (
    AttemptCancelled,
    StaleIdentity,
    launch_or_attach,
    reconcile,
    request_cancel,
)
from ass_exec.durability import Durability, execute
from ass_exec.journal import AttemptJournal, ConcurrentClaim, JournalError
from ass_exec.lsf import (
    CommandResult,
    CommandUnavailable,
    LSFInteractiveTransport,
)
from ass_exec.transport import InProcessTransport, SubmissionRefused, TransportError

BUNDLE = {"command": ["simulate"], "operation": "simulate"}


class Runner:
    def __init__(self, **replies):
        self.calls = []
        self.replies = replies

    def __call__(self, argv, *, cwd=None, env=None, timeout=None):
        self.calls.append(list(argv))
        reply = self.replies.get(argv[0], CommandResult(returncode=0, stdout="done"))
        if isinstance(reply, Exception):
            raise reply
        return reply


def lsf(**replies):
    runner = Runner(**replies)
    return LSFInteractiveTransport(walltime="10", runner=runner), runner


# --- the handle contract ----------------------------------------------------


def test_polling_a_discovered_running_job_does_not_report_it_absent():
    """A job bjobs says is RUNNING must not be published as unreconciled."""

    transport, _ = lsf(
        bjobs=CommandResult(returncode=0, stdout="9001 user RUN normal ass-x")
    )
    handle = transport.discover("ass-x")

    assert handle["kind"] == "live"
    assert transport.poll(handle).state == "running"


def test_a_discovered_pending_job_reads_as_pending():
    transport, _ = lsf(
        bjobs=CommandResult(returncode=0, stdout="9001 user PEND normal ass-x")
    )
    assert transport.poll(transport.discover("ass-x")).state == "pending"


def test_a_finished_submission_handle_still_reads_from_its_exit_status():
    transport, _ = lsf(bsub=CommandResult(returncode=0, stdout="ok"))
    handle = transport.submit("ass-x", BUNDLE)

    assert handle["kind"] == "completed"
    assert transport.poll(handle).state == "succeeded"


# --- submission rejection versus payload failure ----------------------------


def test_a_rejected_submission_is_refused_not_recorded_as_a_failed_result():
    """Nothing ran, so nothing may be published as the work's outcome."""

    transport, _ = lsf(
        bsub=CommandResult(returncode=255, stderr="Job not submitted: Bad queue name")
    )
    with pytest.raises(SubmissionRefused):
        transport.submit("ass-x", BUNDLE)


def test_a_rejected_submission_leaves_nothing_cached(tmp_path):
    transport, _ = lsf(
        bsub=CommandResult(returncode=255, stderr="Job not submitted: Bad queue name")
    )
    with pytest.raises(SubmissionRefused):
        execute(
            transport,
            BUNDLE,
            durability=Durability.RECORDED,
            root=str(tmp_path),
            plan_id="p",
            invocation_id="i",
        )

    journals = [item for item in tmp_path.iterdir() if item.is_dir()]
    assert all(not (item / "manifest.json").exists() for item in journals)


def test_a_payload_exiting_255_is_still_treated_as_work_that_ran():
    """The ambiguity resolves toward the work, so no real result is discarded."""

    transport, _ = lsf(bsub=CommandResult(returncode=255, stderr="segfault"))
    handle = transport.submit("ass-x", BUNDLE)
    assert transport.poll(handle).state == "failed"


# --- a missing command is not a refusal -------------------------------------


def test_a_missing_bsub_is_a_refusal_because_nothing_was_accepted():
    transport, _ = lsf(bsub=CommandUnavailable("'bsub' is not available"))
    with pytest.raises(SubmissionRefused):
        transport.submit("ass-x", BUNDLE)


def test_a_missing_bjobs_is_indeterminate_not_a_refusal():
    """Reporting a refusal here would licence a duplicate submission."""

    transport, _ = lsf(bjobs=CommandUnavailable("'bjobs' is not available"))
    with pytest.raises(CommandUnavailable):
        transport.discover("ass-x")
    with pytest.raises(TransportError):
        transport.discover("ass-x")


def test_a_bjobs_outage_is_not_read_as_never_accepted():
    """The distinction discovery_is_authoritative rests on."""

    transport, _ = lsf(
        bjobs=CommandResult(returncode=255, stderr="Cannot connect to LSF batch daemon")
    )
    with pytest.raises(TransportError, match="could not answer"):
        transport.discover("ass-x")


def test_a_genuine_not_found_still_answers_none():
    transport, _ = lsf(
        bjobs=CommandResult(returncode=255, stderr="Job <ass-x> is not found")
    )
    assert transport.discover("ass-x") is None


# --- cancellation is honoured -----------------------------------------------


def test_a_cancelled_attempt_is_not_launched_by_a_later_run(tmp_path):
    transport = InProcessTransport({"simulate": lambda **kw: "ran"})
    journal = AttemptJournal(tmp_path, "ass-cancelled")
    request_cancel(journal, transport, reason="operator stopped the sweep")

    with pytest.raises(AttemptCancelled, match="recorded cancellation"):
        launch_or_attach(journal, transport, {"operation": "simulate"})


# --- identity and inputs must agree at the low level ------------------------


def test_the_low_level_path_refuses_a_record_from_different_inputs(tmp_path):
    transport = InProcessTransport({"simulate": lambda **kw: "ran"})
    journal = AttemptJournal(tmp_path, "ass-fixed")
    launch_or_attach(journal, transport, {"operation": "simulate", "inputs": {"a": 1}})

    reopened = AttemptJournal(tmp_path, "ass-fixed")
    with pytest.raises(StaleIdentity, match="digests to"):
        launch_or_attach(
            reopened, transport, {"operation": "simulate", "inputs": {"a": 2}}
        )


# --- concurrency ------------------------------------------------------------


def test_two_concurrent_callers_cannot_both_claim_one_attempt(tmp_path):
    journal = AttemptJournal(tmp_path, "ass-race")
    with journal.claim():
        with pytest.raises(ConcurrentClaim):
            with AttemptJournal(tmp_path, "ass-race").claim():
                pass


def test_only_one_of_many_threads_submits(tmp_path):
    calls = []
    lock = threading.Lock()

    def simulate(**kwargs):
        with lock:
            calls.append(1)
        return "ran"

    transport = InProcessTransport({"simulate": simulate})
    errors = []

    def attempt():
        try:
            launch_or_attach(
                AttemptJournal(tmp_path, "ass-threads"),
                transport,
                {"operation": "simulate"},
            )
        except Exception as error:  # ConcurrentClaim is the expected loser
            errors.append(error)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(calls) == 1, "the payload ran more than once for one attempt"


# --- journal durability and validation --------------------------------------


def test_sequence_numbers_stay_correct_without_rereading_the_log(tmp_path):
    journal = AttemptJournal(tmp_path, "ass-seq")
    for _ in range(5):
        journal.append("observed", state="running")

    reread = AttemptJournal(tmp_path, "ass-seq").events()
    assert [item.seq for item in reread] == [0, 1, 2, 3, 4]


def test_a_structurally_invalid_line_raises_a_journal_error(tmp_path):
    journal = AttemptJournal(tmp_path, "ass-torn")
    journal.append("created")
    with open(journal.log_path, "a", encoding="utf-8") as handle:
        handle.write('{"seq": 1}\n')  # valid JSON, missing required fields

    with pytest.raises(JournalError, match="structurally invalid"):
        AttemptJournal(tmp_path, "ass-torn").fold()


def test_a_json_scalar_line_raises_a_journal_error(tmp_path):
    journal = AttemptJournal(tmp_path, "ass-scalar")
    journal.append("created")
    with open(journal.log_path, "a", encoding="utf-8") as handle:
        handle.write("5\n")

    with pytest.raises(JournalError):
        AttemptJournal(tmp_path, "ass-scalar").fold()


# --- ephemeral isolation ----------------------------------------------------


def test_concurrent_ephemeral_calls_do_not_read_each_other(tmp_path):
    transport = InProcessTransport({"echo": lambda value: value})
    first = execute(transport, {"operation": "echo", "arguments": {"value": "a"}})
    second = execute(transport, {"operation": "echo", "arguments": {"value": "b"}})

    assert first.value == "a"
    assert second.value == "b"


def test_ephemeral_results_are_not_retained():
    transport = InProcessTransport({"echo": lambda value: value})
    for index in range(20):
        execute(transport, {"operation": "echo", "arguments": {"value": index}})

    assert transport._results == {}, "ephemeral work leaked retained results"


# --- scan reuse -------------------------------------------------------------


def test_staleness_can_be_asked_from_one_scan(tmp_path):
    from ass_exec.reuse import scan_attempts, stale_attempts

    transport = InProcessTransport({"simulate": lambda **kw: "ran"})
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path),
        "plan_id": "p",
        "invocation_id": "i",
    }
    execute(transport, {"operation": "simulate", "inputs": {"a": 1}}, **common)
    execute(transport, {"operation": "simulate", "inputs": {"a": 2}}, **common)

    known = scan_attempts(tmp_path)
    stale = stale_attempts(
        tmp_path,
        plan_id="p",
        invocation_id="i",
        current_digest=json.loads("null") or "unmatched",
        records=known,
    )
    assert len(stale) == 2
