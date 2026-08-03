"""Attempt identities chosen before submission.

An attempt identity must exist *before* a transport is asked to accept work, so
that a submission whose receipt is lost can still be discovered afterwards. It
is therefore derived only from authored planning facts and an attempt sequence,
never from a transport handle, a process, or a wall-clock reading.

The rendered form is deliberately restricted to characters that survive use as
a batch job name, a filesystem directory, and an environment value.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import re

__all__ = ["AttemptIdentity", "IdentityError", "attempt_identity"]

_SAFE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_DIGEST_BYTES = 10


class IdentityError(ValueError):
    """An attempt identity cannot be derived from the given planning facts."""


@dataclass(frozen=True, slots=True)
class AttemptIdentity:
    """One externally reconcilable attempt at one planned invocation."""

    plan_id: str
    invocation_id: str
    sequence: int
    rendered: str

    def __str__(self) -> str:
        return self.rendered


def _require_component(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise IdentityError(f"{label} must be a non-empty string")
    if not _SAFE.match(value):
        raise IdentityError(
            f"{label} must match [A-Za-z0-9][A-Za-z0-9._-]* to remain usable as "
            f"a job name and directory component; got {value!r}"
        )
    return value


def attempt_identity(
    *, plan_id: str, invocation_id: str, sequence: int = 0
) -> AttemptIdentity:
    """Derive the stable identity of one attempt at one planned invocation.

    The identity is a pure function of its arguments: the same planning facts
    always render the same value, in this process or a later one. That is what
    lets a restarted controller ask a transport whether *this* attempt was
    already accepted.
    """

    _require_component(plan_id, "plan_id")
    _require_component(invocation_id, "invocation_id")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise IdentityError("sequence must be a non-negative integer")

    material = f"{plan_id}\x1f{invocation_id}\x1f{sequence}".encode()
    digest = blake2b(material, digest_size=_DIGEST_BYTES).hexdigest()
    return AttemptIdentity(
        plan_id=plan_id,
        invocation_id=invocation_id,
        sequence=sequence,
        rendered=f"ass-{digest}",
    )
