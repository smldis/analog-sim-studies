"""How much durability one invocation is worth.

Recording is a cost, and most invocations should not pay it. An ordinary
in-memory Python step that computes a number from two other numbers has nothing
worth reconstructing: if the caller dies, the step dies, and rerunning it is
cheaper than any record of it would have been.

Work that leaves the process is different. It can be expensive, it can be
observed by other people, and it can leave something behind that must be
cleaned up. That work earns a record.

The distinction is declared, never inferred from placement. An operation states
what it is; the runtime does not guess from where a call happened to land.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from ass_exec.attempt import LaunchResult, launch_or_attach, reconcile
from ass_exec.journal import AttemptJournal
from ass_exec.transport import Transport

__all__ = ["Durability", "ExecutionResult", "execute"]


class Durability(Enum):
    """What an invocation leaves behind."""

    EPHEMERAL = "ephemeral"
    """Nothing is written. Suitable for in-process work that dies with its
    caller and is cheaper to rerun than to record."""

    RECORDED = "recorded"
    """A full attempt directory: append-only events and a published manifest.
    Required for work that leaves the process."""


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """The outcome of one invocation, whatever its durability."""

    outcome: str
    value: Any = None
    detail: Mapping[str, Any] | None = None
    durability: Durability = Durability.EPHEMERAL
    disposition: str | None = None
    journal: AttemptJournal | None = None


def execute(
    transport: Transport,
    bundle: Mapping[str, Any],
    *,
    durability: Durability = Durability.EPHEMERAL,
    identity: str | None = None,
    root: str | None = None,
) -> ExecutionResult:
    """Run one invocation at the declared durability level.

    ``EPHEMERAL`` touches no filesystem at all: no directory is created, no
    identity is required, and nothing survives the call. ``RECORDED`` runs the
    full attempt protocol and can complete from an existing manifest without
    rerunning the payload.
    """

    if durability is Durability.EPHEMERAL:
        handle = transport.submit(identity or "ephemeral", bundle)
        observation = transport.poll(handle)
        detail = dict(observation.detail or {})
        return ExecutionResult(
            outcome=observation.state,
            value=detail.get("value"),
            detail=detail,
            durability=durability,
        )

    if identity is None or root is None:
        raise ValueError("recorded execution requires both identity and root")

    journal = AttemptJournal(root, identity)
    launched: LaunchResult = launch_or_attach(journal, transport, bundle)
    if launched.disposition == "completed":
        manifest = launched.manifest or {}
        result = dict(manifest.get("result", {}))
        return ExecutionResult(
            outcome=manifest.get("outcome", "unreconciled"),
            value=result.get("value"),
            detail=result,
            durability=durability,
            disposition="completed",
            journal=journal,
        )

    state = reconcile(journal, transport)
    published = journal.read_manifest() or {}
    result = dict(published.get("result", {}))
    return ExecutionResult(
        outcome=state.outcome or state.phase,
        value=result.get("value"),
        detail=result,
        durability=durability,
        disposition=launched.disposition,
        journal=journal,
    )
