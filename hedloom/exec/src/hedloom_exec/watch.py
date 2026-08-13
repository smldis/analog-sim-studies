"""What the farm says about attempts that are still in flight.

With `bsub -I` a transport blocks from submission until the job is over, so the
durable record has a gap exactly where an operator is most curious: between
`submit_intent` and `terminal` it cannot say whether a corner is pending in the
queue or simulating. Nothing was watching, because the thread that could ask
was the thread that was waiting.

This module watches from outside. It reads the attempt directories, asks LSF
once about every live job, and records what it saw.

The invariant it holds:

    An observation is evidence *about* an attempt, never a transition *of* it.

An observer does not own the attempts it watches, so it writes to its own file
beside the record rather than into the log that decides outcomes. One writer
per file, no interleaving with the owner, and nothing an observer records can
change what an attempt concludes. A watcher may be killed, restarted, or run
twice with no effect on any result.

Two by-products fall out of watching. Queue latency per job becomes measurable,
which is the number the pooled-versus-direct question has always lacked. And
because this reads the record rather than the runner, it works unchanged
whether readiness belongs to `hedloom-run`'s loop or to a Dask graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import json

from hedloom_exec.journal import AttemptJournal
from hedloom_exec.lsf import CommandResult, CommandUnavailable, SubprocessRunner
from hedloom_exec.transport import TransportError

__all__ = [
    "AttemptStatus",
    "LSFStatusReader",
    "ObservationLog",
    "live_attempts",
    "observe",
    "render",
    "status_of",
]

_LSF_TRANSPORT = "lsf-interactive"

_STATE_WORDS = {
    "PEND": "pending",
    "PSUSP": "pending",
    "WAIT": "pending",
    "RUN": "running",
    "USUSP": "running",
    "SSUSP": "running",
    "DONE": "succeeded",
    "EXIT": "failed",
    "ZOMBI": "failed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _seconds_between(earlier: str | None, later: str | None) -> float | None:
    if not earlier or not later:
        return None
    try:
        return (
            datetime.fromisoformat(later) - datetime.fromisoformat(earlier)
        ).total_seconds()
    except ValueError:  # pragma: no cover - a record written by another tool
        return None


class ObservationLog:
    """An observer's own append-only file beside one attempt's record.

    Deliberately not `events.jsonl`. That log carries the ordering rules the
    recovery argument depends on and has exactly one writer; a second process
    appending to it would interleave with the owner for no benefit, since an
    observation never changes what an attempt concludes.
    """

    def __init__(self, root: str | Path, identity: str) -> None:
        self.identity = identity
        self.path = Path(root) / identity / "observations.jsonl"

    def entries(self) -> tuple[Mapping[str, Any], ...]:
        if not self.path.exists():
            return ()
        found = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    found.append(json.loads(line))
                except json.JSONDecodeError:
                    # An observation is not authoritative, so an unreadable one
                    # is skipped rather than raised: a corrupt watcher file must
                    # never stop a run or hide a result.
                    continue
        return tuple(found)

    def last_state(self) -> str | None:
        entries = self.entries()
        return entries[-1]["state"] if entries else None

    def record(self, state: str, **detail: Any) -> Mapping[str, Any] | None:
        """Append a state, but only when it is news.

        A sweep watched every ten seconds would otherwise write six identical
        lines a minute per job. What is worth keeping is the transition, which
        is also what makes queue latency computable afterwards.
        """

        if state == self.last_state():
            return None
        entry = {"at": _now(), "state": state, "detail": detail}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def first_at(self, state: str) -> str | None:
        for entry in self.entries():
            if entry.get("state") == state:
                return entry.get("at")
        return None


@dataclass(frozen=True, slots=True)
class AttemptStatus:
    """One row of a sweep: what the record says, and what the farm says."""

    identity: str
    invocation_id: str | None = None
    operation: str | None = None
    phase: str = "unsubmitted"
    outcome: str | None = None
    transport: str | None = None
    observed: str | None = None
    submitted_at: str | None = None
    running_at: str | None = None

    @property
    def queue_seconds(self) -> float | None:
        """How long this job waited before the farm started it.

        The per-job dispatch cost, measured rather than assumed. It is what
        decides whether a pooled placement would ever be worth its complexity.
        """

        return _seconds_between(self.submitted_at, self.running_at)

    @property
    def is_live(self) -> bool:
        return self.phase in ("intended", "submitted")


def _created(journal: AttemptJournal) -> Mapping[str, Any]:
    for event in journal.events():
        if event.event == "created":
            return event.data
    return {}


def _submitted_at(journal: AttemptJournal) -> str | None:
    for event in journal.events():
        if event.event == "submit_intent":
            return event.at
    return None


def status_of(root: str | Path, identity: str) -> AttemptStatus:
    """Read one attempt's status from the record and any observations."""

    journal = AttemptJournal(root, identity)
    state = journal.fold()
    created = _created(journal)
    log = ObservationLog(root, identity)
    return AttemptStatus(
        identity=identity,
        invocation_id=created.get("invocation"),
        operation=created.get("operation"),
        phase=state.phase,
        outcome=state.outcome,
        transport=state.transport,
        observed=log.last_state(),
        submitted_at=_submitted_at(journal),
        running_at=log.first_at("running"),
    )


def live_attempts(root: str | Path) -> tuple[AttemptStatus, ...]:
    """Every attempt under ``root`` that has been submitted and not concluded.

    A directory scan, like the rest of this unit's reading. Honest at prototype
    scale and obviously wrong at any other; an index belongs here only once a
    real sweep makes the scan hurt.
    """

    base = Path(root)
    if not base.is_dir():
        return ()
    found = []
    for directory in sorted(base.iterdir()):
        if not (directory / "events.jsonl").exists():
            continue
        status = status_of(base, directory.name)
        if status.is_live:
            found.append(status)
    return tuple(found)


class LSFStatusReader:
    """One `bjobs` call for every live job, not one per job.

    Asking per attempt would cost a process per corner per refresh, which for a
    sweep of any size is worse than the thing being watched. One call returns
    every job this user has, and the identities are matched here.

    The format is `-o "job_name stat"` deliberately. Default `bjobs` output
    truncates the job name, and its columns shift when a pending job has no
    execution host, so parsing it would mistake `PEND` for `RUN` on some rows —
    silently wrong in exactly the field being asked about. If the site's LSF is
    too old for `-o`, this refuses and says so rather than guessing;
    `lsf_preflight.py` checks it.
    """

    def __init__(self, runner: Callable[..., CommandResult] | None = None) -> None:
        self._run = runner or SubprocessRunner()

    def states(self) -> Mapping[str, str]:
        """Map job name to observed state for everything this user has queued."""

        try:
            result = self._run(
                ["bjobs", "-noheader", "-o", "job_name stat"]
            )
        except CommandUnavailable as error:
            raise TransportError(
                f"cannot ask LSF for job states: {error}"
            ) from error

        text = f"{result.stdout} {result.stderr}"
        if "Illegal option" in text or "Unknown option" in text:
            raise TransportError(
                "this site's bjobs does not support -o, so job status cannot be "
                "read without guessing at truncated columns. Run "
                "examples/lsf_preflight.py to confirm, and do not fall back to "
                "parsing the default format."
            )
        if result.returncode != 0 and not result.stdout.strip():
            # "No unfinished job found" is the ordinary empty answer.
            return {}

        states: dict[str, str] = {}
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) < 2:
                continue
            name, word = fields[0], fields[-1]
            states[name] = _STATE_WORDS.get(word, "running")
        return states


def observe(
    root: str | Path,
    reader: LSFStatusReader | None = None,
    *,
    attempts: Iterable[AttemptStatus] | None = None,
) -> tuple[AttemptStatus, ...]:
    """Ask the farm once about every live LSF attempt, and record any news.

    Attempts on other substrates are returned unchanged: an in-process
    invocation has no job to ask about, and inventing a state for it would be
    the silent wrongness this unit refuses elsewhere.
    """

    live = tuple(attempts) if attempts is not None else live_attempts(root)
    watched = [item for item in live if item.transport == _LSF_TRANSPORT]
    if not watched:
        return live

    states = (reader or LSFStatusReader()).states()
    updated: dict[str, AttemptStatus] = {}
    for item in watched:
        seen = states.get(item.identity)
        if seen is None:
            # Absent from LSF while the record says live: either it has
            # just finished and the owner has not published yet, or something
            # went wrong. Not our call to make — record nothing and leave it
            # to reconciliation, which owns the attempt.
            continue
        log = ObservationLog(root, item.identity)
        log.record(seen)
        updated[item.identity] = status_of(root, item.identity)

    return tuple(updated.get(item.identity, item) for item in live)


def render(rows: Iterable[AttemptStatus]) -> str:
    """One line per attempt, for a terminal.

    Deliberately plain text. The manifesto's headless rule applies to watching
    too: a view is a replaceable client of the record, so it must not become
    the only place a fact can be seen.
    """

    lines = [f"{'invocation':<34}{'phase':<11}{'farm':<10}{'queued':>8}"]
    for row in rows:
        queued = row.queue_seconds
        lines.append(
            f"{(row.invocation_id or row.identity)[:33]:<34}"
            f"{row.outcome or row.phase:<11}"
            f"{row.observed or '-':<10}"
            f"{('-' if queued is None else format(queued, '.0f') + 's'):>8}"
        )
    return "\n".join(lines)
