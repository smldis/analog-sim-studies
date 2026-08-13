"""Append-only attempt journal and atomic terminal publication.

The journal is the durable record that outlives any process, worker, executor,
or scheduler handle. Everything a restarted controller needs to reason about an
attempt is derived by folding this file; nothing is inferred from the continued
existence of an in-memory object.

Two ordering rules carry the whole recovery argument:

* ``submit_intent`` is written and flushed **before** a transport is asked to
  accept work, so an accepted submission whose receipt is lost still has a
  durable trace naming the identity to look for.
* ``terminal`` is written **after** the result manifest is atomically visible,
  so a journal that claims a terminal outcome always has readable evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Iterator, Mapping
import errno
import fcntl
import json
import os

__all__ = [
    "AttemptJournal",
    "AttemptState",
    "ConcurrentClaim",
    "JournalError",
    "JournalEvent",
    "TERMINAL_OUTCOMES",
]

TERMINAL_OUTCOMES = frozenset({"succeeded", "failed", "cancelled", "unreconciled"})

_EVENTS = frozenset(
    {
        "created",
        "submit_intent",
        "submit_receipt",
        "submit_refused",
        "submit_indeterminate",
        "submit_lost",
        "cancel_requested",
        "observed",
        "terminal",
        "reuse_accepted",
        "placement",
    }
)


class JournalError(RuntimeError):
    """The durable record is missing, malformed, or internally contradictory."""


class ConcurrentClaim(JournalError):
    """Another caller holds this attempt right now.

    Reported rather than waited on: a second submission of the same attempt is
    the defect, so the honest response is to say who is already doing it.
    """


@dataclass(frozen=True, slots=True)
class JournalEvent:
    seq: int
    at: str
    event: str
    data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AttemptState:
    """The folded view of one attempt's durable history.

    ``phase`` is one of ``unsubmitted``, ``intended``, ``submitted``, or
    ``terminal``. ``intended`` is the crash window: durable intent exists but no
    receipt does, so whether the external system accepted the work is unknown
    from the record alone and must be settled by discovery.
    """

    identity: str
    phase: str
    handle: Mapping[str, Any] | None = None
    transport: str | None = None
    outcome: str | None = None
    manifest_path: str | None = None
    cancel_requested: bool = False
    cancel_reason: str | None = None
    reuse_accepted: bool = False
    reuse_reason: str | None = None
    placement: Mapping[str, Any] = field(default_factory=dict)
    observations: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    events: tuple[JournalEvent, ...] = field(default_factory=tuple)

    @property
    def is_terminal(self) -> bool:
        return self.phase == "terminal"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _fsync_directory(path: Path) -> None:
    """Persist a directory entry, not just a file's contents.

    Without this, `os.replace` and the creation of `events.jsonl` are not
    crash-durable: the data survives but the name pointing at it can be lost.
    Both ordering rules above depend on the entry, not only the bytes.
    """

    try:
        descriptor = os.open(path, os.O_RDONLY)
    except (NotADirectoryError, FileNotFoundError):  # pragma: no cover
        return
    try:
        os.fsync(descriptor)
    except OSError:  # pragma: no cover - not every filesystem permits this
        pass
    finally:
        os.close(descriptor)


class AttemptJournal:
    """One attempt's durable directory: an event log plus a published manifest.

    The directory layout is deliberately plain so that an operator, a script, a
    CI job, or an agent can read the same facts without this package.
    """

    def __init__(self, root: str | os.PathLike[str], identity: str) -> None:
        self.identity = identity
        self.directory = Path(root) / identity
        self.log_path = self.directory / "events.jsonl"
        self.manifest_path = self.directory / "manifest.json"
        self.lock_path = self.directory / "claim.lock"
        self._next_seq: int | None = None

    def exists(self) -> bool:
        return self.log_path.exists()

    @contextmanager
    def claim(self) -> Iterator[None]:
        """Hold this attempt exclusively while deciding what to do with it.

        Reading the record, recording intent, and submitting must be one
        indivisible step. Without it two controllers -- or two threads of one
        plan runner -- can both fold an unsubmitted state and both submit,
        producing two real jobs for one attempt. An advisory lock on a file in
        the attempt directory is enough: every writer goes through here.
        """

        self.directory.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                raise ConcurrentClaim(
                    f"attempt {self.identity} is already being launched by "
                    f"another caller"
                ) from error
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def append(self, event: str, /, **data: Any) -> JournalEvent:
        """Durably append one event, flushing before returning.

        The flush is the point of the method: a caller may crash immediately
        after it returns, and the record must already be on disk.
        """

        if event not in _EVENTS:
            raise JournalError(f"unknown journal event {event!r}")
        self.directory.mkdir(parents=True, exist_ok=True)
        if self._next_seq is None:
            # Counted once per journal instance rather than on every append,
            # which made writing n events cost O(n^2) reads of the whole log.
            self._next_seq = sum(1 for _ in self._raw_lines())
        fresh_log = not self.log_path.exists()
        record = {
            "seq": self._next_seq,
            "at": _now(),
            "event": event,
            "data": data,
        }
        line = json.dumps(record, sort_keys=True, separators=(",", ":"))
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if fresh_log:
            _fsync_directory(self.directory)
        self._next_seq += 1
        return JournalEvent(record["seq"], record["at"], event, data)

    def _raw_lines(self) -> Iterator[str]:
        if not self.log_path.exists():
            return iter(())
        return (
            line
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def events(self) -> tuple[JournalEvent, ...]:
        parsed: list[JournalEvent] = []
        for index, line in enumerate(self._raw_lines()):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise JournalError(
                    f"attempt {self.identity} has a malformed journal line {index}"
                ) from error
            if not isinstance(record, dict) or not {"seq", "at", "event"} <= set(
                record
            ):
                raise JournalError(
                    f"attempt {self.identity} has a structurally invalid journal "
                    f"line {index}: {line[:80]!r}"
                )
            parsed.append(
                JournalEvent(
                    seq=record["seq"],
                    at=record["at"],
                    event=record["event"],
                    data=record.get("data") or {},
                )
            )
        return tuple(parsed)

    def fold(self) -> AttemptState:
        """Derive current state from the durable record alone."""

        phase = "unsubmitted"
        handle: Mapping[str, Any] | None = None
        transport: str | None = None
        outcome: str | None = None
        manifest_path: str | None = None
        cancel_requested = False
        cancel_reason: str | None = None
        reuse_accepted = False
        reuse_reason: str | None = None
        placement: dict[str, Any] = {}
        observations: list[Mapping[str, Any]] = []
        events = self.events()

        for item in events:
            if item.event == "submit_intent":
                phase = "intended"
                transport = item.data.get("transport")
            elif item.event == "submit_receipt":
                phase = "submitted"
                handle = item.data.get("handle")
            elif item.event in ("submit_refused", "submit_lost"):
                phase = "unsubmitted"
                handle = None
            elif item.event == "submit_indeterminate":
                # The substrate may hold accepted work. Staying in the crash
                # window is the safe reading; only discovery may leave it.
                phase = "intended"
            elif item.event == "cancel_requested":
                cancel_requested = True
                cancel_reason = item.data.get("reason")
            elif item.event == "placement":
                placement = dict(item.data)
            elif item.event == "reuse_accepted":
                reuse_accepted = True
                reuse_reason = item.data.get("reason")
            elif item.event == "observed":
                observations.append(item.data)
            elif item.event == "terminal":
                phase = "terminal"
                outcome = item.data.get("outcome")
                manifest_path = item.data.get("manifest")

        if outcome is not None and outcome not in TERMINAL_OUTCOMES:
            raise JournalError(
                f"attempt {self.identity} records unknown outcome {outcome!r}"
            )

        return AttemptState(
            identity=self.identity,
            phase=phase,
            handle=handle,
            transport=transport,
            outcome=outcome,
            manifest_path=manifest_path,
            cancel_requested=cancel_requested,
            cancel_reason=cancel_reason,
            reuse_accepted=reuse_accepted,
            reuse_reason=reuse_reason,
            placement=placement,
            observations=tuple(observations),
            events=events,
        )

    def publish_terminal(
        self, *, outcome: str, manifest: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Make the manifest atomically visible, then record the outcome.

        The write-replace order matters: a crash between the two leaves a
        readable manifest and a non-terminal journal, which reconciliation can
        resolve. The reverse order would leave a terminal claim with no
        evidence behind it.
        """

        if outcome not in TERMINAL_OUTCOMES:
            raise JournalError(f"unknown terminal outcome {outcome!r}")
        self.directory.mkdir(parents=True, exist_ok=True)
        document = {
            "attempt": self.identity,
            "outcome": outcome,
            "published_at": _now(),
            "result": dict(manifest),
        }
        temporary = self.directory / "manifest.json.partial"
        payload = json.dumps(document, sort_keys=True, indent=2) + "\n"
        with open(temporary, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.manifest_path)
        # The rename is only durable once the directory entry is persisted;
        # otherwise a crash can leave a terminal record with no manifest.
        _fsync_directory(self.directory)
        self.append("terminal", outcome=outcome, manifest=str(self.manifest_path))
        return document

    def read_manifest(self) -> Mapping[str, Any] | None:
        """Return the published manifest, or ``None`` if none is visible."""

        if not self.manifest_path.exists():
            return None
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise JournalError(
                f"attempt {self.identity} has an unreadable published manifest"
            ) from error
