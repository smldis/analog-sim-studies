"""The two failure injections the architecture named as decisive.

These are the observations that discriminate who owns external attempt
identity. They run entirely locally against a fake substrate whose state
outlives its caller; no scheduler is required to obtain the evidence.
"""

import json

import pytest

from hedloom_exec.attempt import (
    UnrecoverableAttempt,
    launch_or_attach,
    reconcile,
)
from hedloom_exec.journal import AttemptJournal

from fakes import FakeBatchStore, FakeBatchTransport

BUNDLE = {
    "plan": "plan-1",
    "invocation": "inv-a",
    "operation": "simulate",
    "arguments": {},
}

IDENTITY = "hedloom-injection"


def test_acceptance_to_receipt_loss_attaches_and_never_duplicates(tmp_path):
    """Injection one: the substrate accepts, then the caller dies uninformed.

    A restarted controller must reach the accepted job by identity. The
    property under test is that exactly one job exists afterwards.
    """

    store = FakeBatchStore()
    first_controller = FakeBatchTransport(store, drop_receipt=True)
    log = AttemptJournal(tmp_path, IDENTITY)

    with pytest.raises(Exception):
        launch_or_attach(log, first_controller, BUNDLE)

    assert len(store.jobs) == 1
    accepted_job_id = store.jobs[IDENTITY]["job_id"]

    # A new process, sharing nothing but the durable record and the substrate.
    restarted = AttemptJournal(tmp_path, IDENTITY)
    second_controller = FakeBatchTransport(store)
    result = launch_or_attach(restarted, second_controller, BUNDLE)

    assert result.disposition == "attached"
    assert result.state.handle["job_id"] == accepted_job_id
    assert len(store.jobs) == 1
    assert store.jobs[IDENTITY]["runs"] == 1
    assert store.accepted == 1, "a second submission reached the substrate"


def test_acceptance_to_receipt_loss_fails_loudly_without_discovery(tmp_path):
    """The same injection at a site that cannot answer questions about itself.

    The required outcome is an explicit unsupported result. Silence, a guess,
    or a second submission would each be worse than the exception.
    """

    store = FakeBatchStore()
    log = AttemptJournal(tmp_path, IDENTITY)
    lossy = FakeBatchTransport(
        store,
        drop_receipt=True,
        discovery_is_authoritative=False,
        can_discover=False,
    )

    with pytest.raises(Exception):
        launch_or_attach(log, lossy, BUNDLE)

    restarted = AttemptJournal(tmp_path, IDENTITY)
    blind = FakeBatchTransport(
        store, discovery_is_authoritative=False, can_discover=False
    )
    with pytest.raises(UnrecoverableAttempt):
        launch_or_attach(restarted, blind, BUNDLE)

    assert len(store.jobs) == 1
    assert store.jobs[IDENTITY]["runs"] == 1
    assert store.accepted == 1, "a second submission reached the substrate"


def test_a_positive_discovery_is_usable_even_without_authority(tmp_path):
    """Only the negative answer needs authority.

    Because the identity was chosen before submission, a match names this exact
    work. A site that cannot be trusted to say "no" can still be believed when
    it says "yes", and attaching is then strictly better than failing.
    """

    store = FakeBatchStore()
    log = AttemptJournal(tmp_path, IDENTITY)
    lossy = FakeBatchTransport(
        store, drop_receipt=True, discovery_is_authoritative=False
    )

    with pytest.raises(Exception):
        launch_or_attach(log, lossy, BUNDLE)

    restarted = AttemptJournal(tmp_path, IDENTITY)
    result = launch_or_attach(
        restarted, FakeBatchTransport(store, discovery_is_authoritative=False), BUNDLE
    )

    assert result.disposition == "attached"
    assert len(store.jobs) == 1
    assert store.accepted == 1, "a second submission reached the substrate"


def test_terminal_to_manifest_loss_completes_by_attachment(tmp_path):
    """Injection two: the work finished, the caller died before recording it.

    A restarted controller must complete the attempt from published evidence
    without rerunning the payload.
    """

    store = FakeBatchStore()
    transport = FakeBatchTransport(store)
    log = AttemptJournal(tmp_path, IDENTITY)
    launch_or_attach(log, transport, BUNDLE)
    store.jobs[IDENTITY]["state"] = "succeeded"
    reconcile(log, transport)

    # Simulate the crash window inside publication: the manifest is visible,
    # the terminal record never reached the journal.
    surviving = [
        line
        for line in log.log_path.read_text().splitlines()
        if json.loads(line)["event"] != "terminal"
    ]
    log.log_path.write_text("\n".join(surviving) + "\n")
    assert log.fold().phase == "submitted"
    assert log.read_manifest() is not None

    restarted = AttemptJournal(tmp_path, IDENTITY)
    result = launch_or_attach(restarted, FakeBatchTransport(store), BUNDLE)

    assert result.disposition == "completed"
    assert result.manifest["outcome"] == "succeeded"
    assert result.state.phase == "terminal"
    assert store.jobs[IDENTITY]["runs"] == 1
    assert store.accepted == 1, "the payload was resubmitted"


def test_recovery_needs_no_knowledge_of_the_graph(tmp_path):
    """The boundary test: reconciliation reads no topology.

    If recovering an attempt ever required knowing which nodes were ready or
    which successors to release, the attempt layer would have absorbed graph
    scheduling authority. The bundle passed on recovery here carries no
    dependency information at all.
    """

    store = FakeBatchStore()
    log = AttemptJournal(tmp_path, IDENTITY)
    with pytest.raises(Exception):
        launch_or_attach(log, FakeBatchTransport(store, drop_receipt=True), BUNDLE)

    restarted = AttemptJournal(tmp_path, IDENTITY)
    result = launch_or_attach(restarted, FakeBatchTransport(store), {})

    assert result.disposition == "attached"


def test_the_fake_substrate_can_actually_observe_a_duplicate():
    """Guard the guard: these injections are only evidence if they can fail."""

    store = FakeBatchStore()
    transport = FakeBatchTransport(store)
    transport.submit(IDENTITY, BUNDLE)
    transport.submit(IDENTITY, BUNDLE)

    assert store.accepted == 2
    assert store.jobs[IDENTITY]["runs"] == 2
