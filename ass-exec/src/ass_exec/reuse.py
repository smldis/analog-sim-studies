"""Input identity, sound reuse, and explaining what went stale.

Reuse is only honest if "already done" means "already done *with these
inputs*". This module derives a digest over the parts of a bundle that
determine its result, so that a changed input produces a different attempt
rather than a silently reused old one.

What participates is a real design decision, not an implementation detail:

* The operation, its command or arguments, its working directory, its declared
  input digests, and any environment explicitly nominated as identity-bearing.
* **Not** where or how the work ran. Queue, walltime, cores, and host do not
  change what a deterministic operation produces, so changing them must not
  invalidate a result. Placement is a scheduling concern; identity is a
  semantic one, and conflating them would make every resource tweak look like
  a new experiment.

An operation whose result depends on something outside this list — wall-clock
time, a mutable network resource, an undeclared file — is not honestly
reusable, and no digest can fix that. Declaring inputs is how an author makes
that promise explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

from ass_exec.journal import AttemptJournal

__all__ = [
    "AttemptRecord",
    "describe_staleness",
    "IDENTITY_KEYS",
    "attempts_for",
    "input_digest",
    "scan_attempts",
    "stale_attempts",
]

IDENTITY_KEYS = (
    "operation",
    "operation_version",
    "command",
    "arguments",
    "cwd",
    "inputs",
    "outputs",
    "identity_env",
)
"""Bundle keys that determine the result. Everything else is execution detail.

``operation_version`` is here because a reimplemented operation may produce a
different answer from the same inputs; omitting it would reuse results across a
change in meaning.
"""


def input_digest(bundle: Mapping[str, Any]) -> str:
    """Digest the identity-bearing content of a bundle.

    Deterministic across processes: the same declared inputs always produce the
    same digest, so two runs can agree on whether work is already done.
    """

    material = {
        key: bundle[key]
        for key in IDENTITY_KEYS
        if key in bundle and bundle[key] is not None
    }
    try:
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    except TypeError as error:
        raise ValueError(
            "bundle inputs must be JSON-serializable to have a stable identity; "
            "pass a digest or a declared reference rather than a live object"
        ) from error
    return blake2b(canonical.encode(), digest_size=16).hexdigest()


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """What one attempt directory says about itself, without opening the payload."""

    identity: str
    plan_id: str | None
    invocation_id: str | None
    input_digest: str | None
    outcome: str | None
    directory: Path

    @property
    def is_terminal(self) -> bool:
        return self.outcome is not None


def scan_attempts(root: str | Path) -> tuple[AttemptRecord, ...]:
    """Read every attempt under ``root``.

    A directory scan is honest for a prototype and obviously wrong at scale;
    an index belongs here only once a real workload makes the scan hurt.
    """

    base = Path(root)
    if not base.is_dir():
        return ()

    records: list[AttemptRecord] = []
    for directory in sorted(base.iterdir()):
        if not (directory / "events.jsonl").exists():
            continue
        journal = AttemptJournal(base, directory.name)
        state = journal.fold()
        created = next(
            (event for event in state.events if event.event == "created"), None
        )
        data = created.data if created else {}
        records.append(
            AttemptRecord(
                identity=directory.name,
                plan_id=data.get("plan"),
                invocation_id=data.get("invocation"),
                input_digest=data.get("input_digest"),
                outcome=state.outcome,
                directory=directory,
            )
        )
    return tuple(records)


def attempts_for(
    root: str | Path,
    *,
    plan_id: str,
    invocation_id: str,
    records: Iterable[AttemptRecord] | None = None,
) -> tuple[AttemptRecord, ...]:
    """Every recorded attempt at one planned invocation, across input changes.

    Pass ``records`` from a single `scan_attempts` when asking about many
    invocations. Otherwise each question rescans and reparses every attempt
    directory, which turns a sweep of n invocations into n full rescans.
    """

    source = scan_attempts(root) if records is None else records
    return tuple(
        record
        for record in source
        if record.plan_id == plan_id and record.invocation_id == invocation_id
    )


def stale_attempts(
    root: str | Path,
    *,
    plan_id: str,
    invocation_id: str,
    current_digest: str,
    records: Iterable[AttemptRecord] | None = None,
) -> tuple[AttemptRecord, ...]:
    """Prior results for this invocation that no longer describe current inputs.

    These are not garbage. They are what the work used to conclude, and being
    able to name them is how a changed input gets explained rather than
    silently overwritten.
    """

    return tuple(
        record
        for record in attempts_for(
            root,
            plan_id=plan_id,
            invocation_id=invocation_id,
            records=records,
        )
        if record.input_digest is not None and record.input_digest != current_digest
    )


def describe_staleness(records: Iterable[AttemptRecord]) -> str:
    """One human-readable line per superseded attempt."""

    return "\n".join(
        f"{record.identity}: {record.outcome or 'unfinished'} "
        f"(inputs {record.input_digest})"
        for record in records
    )
