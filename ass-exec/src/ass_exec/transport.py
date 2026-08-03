"""The transport boundary: how one attempt reaches an execution substrate.

A transport moves one attempt to wherever it runs and reports what it observes
there. It is deliberately not allowed to decide which invocation is ready, to
release successors, or to own identity: those stay with the caller and with the
durable journal respectively.

``discovery_is_authoritative`` is the load-bearing declaration, and it is about
the *negative* answer only. Finding an accepted attempt is always usable
evidence: the identity was chosen before submission, so a match means the
substrate holds this exact work. Not finding one is the hard case — it may mean
the work was never accepted, or only that this substrate cannot be asked. A
transport that cannot distinguish those two must declare so, and the caller
must refuse to guess rather than risk a duplicate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

__all__ = [
    "Observation",
    "SubmissionRefused",
    "Transport",
    "TransportError",
    "InProcessTransport",
]

_OBSERVED_STATES = frozenset(
    {"absent", "pending", "running", "succeeded", "failed", "cancelled"}
)


class TransportError(RuntimeError):
    """The substrate could not be reached or answered incoherently.

    Raising this is an *indeterminate* result: the attempt may or may not have
    been accepted. Callers must not treat it as a refusal.
    """


class SubmissionRefused(TransportError):
    """The substrate definitely did not accept the attempt.

    A transport may raise this only when it can establish that no work was
    accepted — a rejected job script, an unknown queue, a failed validation
    before any call that could have created external work. This is the only
    submission failure that permits a later resubmission without discovery.
    """


@dataclass(frozen=True, slots=True)
class Observation:
    """One reading of external state. A reading, never a conclusion."""

    state: str
    detail: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.state not in _OBSERVED_STATES:
            raise TransportError(f"unknown observed state {self.state!r}")

    @property
    def is_terminal(self) -> bool:
        return self.state in ("succeeded", "failed", "cancelled")


@runtime_checkable
class Transport(Protocol):
    """Submit, discover, observe, and cancel one attempt on some substrate."""

    name: str
    discovery_is_authoritative: bool

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        """Accept the attempt and return a durable-recordable handle."""

    def discover(self, identity: str) -> Mapping[str, Any] | None:
        """Return the handle for an already-accepted attempt, else ``None``.

        Callers may only trust a ``None`` answer when
        ``discovery_is_authoritative`` is true.
        """

    def poll(self, handle: Mapping[str, Any]) -> Observation:
        """Read current external state for a previously returned handle."""

    def cancel(self, handle: Mapping[str, Any]) -> None:
        """Ask the substrate to stop the work. Delivery is not guaranteed."""


class InProcessTransport:
    """The degenerate local substrate: work runs inside the calling process.

    This is the honest local case rather than a simulation of a remote one.
    Because accepted work cannot outlive the process that accepted it, a
    restarted controller that finds no live record knows for certain that the
    attempt did not survive. Discovery is therefore authoritative, and the
    receipt-loss window that makes batch execution hard is genuinely absent
    here. Keeping the same contract for both cases is what lets the recovery
    argument be tested locally at all.
    """

    name = "in-process"
    discovery_is_authoritative = True

    def __init__(self, implementations: Mapping[str, Callable[..., Any]]) -> None:
        self._implementations = dict(implementations)
        self._results: dict[str, Observation] = {}

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        operation = bundle.get("operation")
        implementation = self._implementations.get(operation)
        if implementation is None:
            # Established before anything could run: a genuine refusal.
            raise SubmissionRefused(
                f"no implementation is bound for operation {operation!r}"
            )
        arguments = dict(bundle.get("arguments", {}))
        # Resolved upstream values are execution detail, never identity: which
        # values these are is already implied by the declared input digests, so
        # including them again would only make identity depend on itself.
        arguments.update(bundle.get("resolved_inputs", {}))
        try:
            value = implementation(**arguments)
        except Exception as error:  # deliberate: failure is a recordable outcome
            self._results[identity] = Observation(
                "failed", {"error": f"{type(error).__name__}: {error}"}
            )
        else:
            self._results[identity] = Observation("succeeded", {"value": value})
        return {"transport": self.name, "identity": identity}

    def discover(self, identity: str) -> Mapping[str, Any] | None:
        if identity in self._results:
            return {"transport": self.name, "identity": identity}
        return None

    def poll(self, handle: Mapping[str, Any]) -> Observation:
        identity = handle.get("identity")
        observation = self._results.get(identity)
        if observation is None:
            return Observation("absent")
        return observation

    def cancel(self, handle: Mapping[str, Any]) -> None:
        # Synchronous in-process work is already terminal by the time any
        # caller could cancel it. Recording the intent remains the caller's job.
        return None

    def forget(self, identity: str) -> None:
        """Drop a retained result once nobody can ask for it again.

        Results are held so `poll` can answer after `submit`. Work that leaves
        no record has no later reader, so retaining its value would only grow
        the process for the lifetime of a run.
        """

        self._results.pop(identity, None)
