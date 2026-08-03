"""The attempt protocol: claim, attach, reconcile, or refuse to guess.

This module encodes the ownership hypothesis under test. The durable journal
owns attempt identity; the transport owns delivery; the substrate owns external
state after acceptance. No live object is treated as the authority for any of
them.

``launch_or_attach`` must resolve to exactly one of three dispositions, or fail
loudly. The failure is not a defect: an unrecoverable attempt is a real
property of a substrate that cannot answer questions about its own accepted
work, and reporting it beats acting blindly.

Under the current owner-bound lifetime decision, work is not meant to survive
its caller, so the ``attached`` disposition and ``UnrecoverableAttempt`` are
reachable only for a transport whose substrate keeps work after the submitter
dies. Nothing here does today. They are retained because the distinction they
encode — accepted, refused, or indeterminate — is exactly what an orphan-reaping
path needs in order to know whether there is anything to kill.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ass_exec.artifacts import (
    MissingOutput,
    capture_outputs,
    write_diagnostics,
)
from ass_exec.journal import AttemptJournal, AttemptState
from ass_exec.reuse import input_digest
from ass_exec.transport import Observation, SubmissionRefused, Transport

__all__ = [
    "AttemptCancelled",
    "AttemptError",
    "AttemptSpent",
    "StaleIdentity",
    "LaunchResult",
    "REUSABLE_OUTCOMES",
    "ReconciliationError",
    "UnrecoverableAttempt",
    "accept_for_reuse",
    "is_reusable",
    "launch_or_attach",
    "reconcile",
    "request_cancel",
]

REUSABLE_OUTCOMES = frozenset({"succeeded"})
"""Outcomes a later run may return instead of doing the work again.

Only success. A failure may have been the work's own verdict — a design that
does not converge — or something incidental to it: an out-of-memory kill, a
preempted node, a full filesystem. The record cannot tell those apart, and
guessing in either direction is worse than not guessing. Caching an infrastructure
failure would poison an invocation permanently; discarding a real negative
result would waste the run that produced it.

So a failed attempt is kept, not reused: rerunning is the default, the earlier
attempt stays on disk for inspection, and an operator who has looked at it can
mark it reusable with `accept_for_reuse`.
"""


class AttemptError(RuntimeError):
    """The attempt cannot proceed under its recorded state."""


class UnrecoverableAttempt(AttemptError):
    """Durable intent exists and the substrate cannot say whether it accepted.

    Raised only when discovery is non-authoritative. Resubmitting here could
    duplicate externally scheduled work; abandoning could lose it. Neither is
    the caller's choice to make silently.
    """


class ReconciliationError(AttemptError):
    """The durable record and the observed substrate state disagree."""


class AttemptCancelled(AttemptError):
    """Cancellation was recorded for this attempt; it must not be launched.

    Recorded intent outlives the process that recorded it. Submitting anyway
    would start work an operator has already stopped.
    """


class StaleIdentity(AttemptError):
    """The stored result under this identity came from different inputs.

    Only reachable when a caller supplies an identity by hand. A derived
    identity cannot produce this, because different inputs land elsewhere.
    """


class AttemptSpent(AttemptError):
    """This attempt reached a terminal outcome that may not be reused.

    Not a failure of the protocol: the work is finished and its record stands.
    The caller should run a fresh attempt at a later sequence, leaving this one
    intact for inspection.
    """


def is_reusable(state: AttemptState, manifest: Mapping[str, Any] | None) -> bool:
    """Whether a published result may stand in for running the work again."""

    if manifest is None:
        return False
    if state.reuse_accepted:
        return True
    return manifest.get("outcome") in REUSABLE_OUTCOMES


def accept_for_reuse(journal: AttemptJournal, *, reason: str) -> AttemptState:
    """Record that a human inspected this result and chose to keep it.

    The escape hatch for a failure worth preserving — a known-bad corner being
    debugged, or a negative result that should not be recomputed on every run.
    It is durable and attributable rather than a flag on a command line.
    """

    published = journal.read_manifest()
    if published is None:
        raise AttemptError(
            f"attempt {journal.identity} has no published result to accept"
        )
    journal.append("reuse_accepted", reason=reason, outcome=published.get("outcome"))
    return journal.fold()


@dataclass(frozen=True, slots=True)
class LaunchResult:
    """What ``launch_or_attach`` resolved to, and the state it left behind."""

    disposition: str
    state: AttemptState
    manifest: Mapping[str, Any] | None = None


def launch_or_attach(
    journal: AttemptJournal,
    transport: Transport,
    bundle: Mapping[str, Any],
) -> LaunchResult:
    """Resolve one attempt to exactly one of three durable dispositions.

    ``completed`` — a manifest is already visible; the payload does not rerun.
    ``attached`` — the substrate already holds this attempt; no new submission.
    ``claimed``  — nothing was accepted before; this call submits it once.
    """

    with journal.claim():
        return _launch_or_attach_locked(journal, transport, bundle)


def _launch_or_attach_locked(
    journal: AttemptJournal,
    transport: Transport,
    bundle: Mapping[str, Any],
) -> LaunchResult:
    published = journal.read_manifest()
    state = journal.fold()
    _require_matching_inputs(journal, state, bundle)

    if state.cancel_requested and not state.is_terminal and published is None:
        raise AttemptCancelled(
            f"attempt {journal.identity} has a recorded cancellation "
            f"({state.cancel_reason!r}) and will not be launched"
        )

    if published is not None:
        if not state.is_terminal:
            # Crash between atomic publication and the terminal record. The
            # manifest is the evidence; the journal is repaired to match it.
            journal.append(
                "terminal",
                outcome=published.get("outcome"),
                manifest=str(journal.manifest_path),
                repaired=True,
            )
            state = journal.fold()
        if not is_reusable(state, published):
            raise AttemptSpent(
                f"attempt {journal.identity} ended as "
                f"{published.get('outcome')!r}, which is not reused "
                f"automatically. Run a later sequence, or call "
                f"accept_for_reuse(...) after inspecting it."
            )
        return LaunchResult("completed", state, published)

    if state.is_terminal:
        raise ReconciliationError(
            f"attempt {journal.identity} claims a terminal outcome but no "
            f"manifest is visible at {journal.manifest_path}"
        )

    if state.phase == "submitted":
        return LaunchResult("attached", state)

    if state.phase == "intended":
        handle = transport.discover(journal.identity)
        if handle is not None:
            journal.append("submit_receipt", handle=dict(handle), recovered=True)
            return LaunchResult("attached", journal.fold())
        if not transport.discovery_is_authoritative:
            raise UnrecoverableAttempt(
                f"attempt {journal.identity} recorded submission intent to "
                f"transport {transport.name!r}, which cannot authoritatively "
                f"confirm or deny acceptance; recoverable execution is "
                f"unsupported here"
            )
        journal.append("submit_lost", transport=transport.name)

    if not state.events:
        journal.append(
            "created",
            plan=bundle.get("plan"),
            invocation=bundle.get("invocation"),
            operation=bundle.get("operation"),
            # Recorded so a later run can name what this result was computed
            # from, and explain it as superseded rather than silently replace it.
            input_digest=input_digest(bundle),
        )

    # Intent is durable before the substrate is touched. Everything downstream
    # depends on this ordering.
    journal.append("submit_intent", transport=transport.name)
    try:
        handle = transport.submit(journal.identity, bundle)
    except SubmissionRefused as error:
        # The transport established that nothing was accepted, so the attempt
        # returns to the unsubmitted phase and may be retried directly.
        journal.append("submit_refused", error=f"{type(error).__name__}: {error}")
        raise
    except Exception as error:
        # Any other failure is indeterminate: the substrate may already hold
        # this work. The attempt stays in the crash window, where only
        # discovery may release it.
        journal.append(
            "submit_indeterminate", error=f"{type(error).__name__}: {error}"
        )
        raise
    journal.append("submit_receipt", handle=dict(handle))
    return LaunchResult("claimed", journal.fold())


def _require_matching_inputs(
    journal: AttemptJournal,
    state: AttemptState,
    bundle: Mapping[str, Any],
) -> None:
    """Refuse to reuse a record that was created from different inputs.

    The guard lives here, where identity meets the journal, rather than only in
    `execute`. Both entry points pass through this function, so a hand-supplied
    identity cannot route around it.
    """

    created = next(
        (event for event in state.events if event.event == "created"), None
    )
    if created is None:
        return
    recorded = created.data.get("input_digest")
    if recorded is None or not bundle:
        return
    current = input_digest(bundle)
    if recorded != current:
        raise StaleIdentity(
            f"attempt {journal.identity} was created from inputs {recorded} "
            f"but this bundle digests to {current}. Derive the identity from "
            f"plan_id/invocation_id so changed inputs get their own attempt."
        )


def request_cancel(
    journal: AttemptJournal, transport: Transport, *, reason: str
) -> AttemptState:
    """Record cancellation intent durably, then ask the substrate to stop.

    Intent is recorded first and unconditionally. A lost acknowledgement cannot
    establish whether the substrate acted, so cancellation is an intent to be
    reconciled later, never a fact established by this call returning.
    """

    journal.append("cancel_requested", reason=reason)
    state = journal.fold()
    if state.phase == "submitted" and state.handle is not None:
        transport.cancel(state.handle)
    return journal.fold()


def reconcile(
    journal: AttemptJournal,
    transport: Transport,
    *,
    bundle_outputs: Mapping[str, Mapping[str, Any]] | None = None,
) -> AttemptState:
    """Observe the substrate and publish a terminal manifest when one is due.

    Success requires both an acceptable external state and an atomically
    published manifest. A disagreement between the record and the substrate is
    published as ``unreconciled`` rather than normalized into either outcome.
    """

    published = journal.read_manifest()
    state = journal.fold()
    if published is not None or state.is_terminal:
        return state

    if state.phase != "submitted" or state.handle is None:
        raise ReconciliationError(
            f"attempt {journal.identity} cannot be reconciled from phase "
            f"{state.phase!r}"
        )

    observation: Observation = transport.poll(state.handle)
    journal.append(
        "observed", state=observation.state, detail=dict(observation.detail or {})
    )

    if not observation.is_terminal:
        if observation.state == "absent":
            journal.publish_terminal(
                outcome="unreconciled",
                manifest={
                    "reason": "substrate reports no such accepted work",
                    "handle": dict(state.handle),
                },
            )
            return journal.fold()
        return journal.fold()

    outcome = observation.state
    if state.cancel_requested and outcome == "succeeded":
        # Cancellation was requested and the work finished anyway. That is a
        # real, reportable disagreement rather than a plain success.
        journal.publish_terminal(
            outcome="unreconciled",
            manifest={
                "reason": "cancellation was requested but the work succeeded",
                "cancel_reason": state.cancel_reason,
                "observed": dict(observation.detail or {}),
            },
        )
        return journal.fold()

    detail = dict(observation.detail or {})
    location = state.handle.get("workdir")
    workdir = Path(location) if location else None
    write_diagnostics(workdir, detail.get("stdout", ""), detail.get("stderr", ""))

    if outcome == "succeeded":
        try:
            produced = capture_outputs(
                bundle_outputs,
                workdir=workdir,
                stdout=detail.get("stdout", ""),
                stderr=detail.get("stderr", ""),
                value=detail.get("value"),
            )
        except MissingOutput as error:
            # The work reported success but did not produce what it promised.
            # That is a failed invocation, not a successful one with a gap.
            journal.publish_terminal(
                outcome="failed",
                manifest={**detail, "error": str(error)},
            )
            return journal.fold()
        if produced:
            detail["artifacts"] = [item.as_data() for item in produced]

    journal.publish_terminal(outcome=outcome, manifest=detail)
    return journal.fold()
