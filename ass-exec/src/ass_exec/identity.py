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
_SEPARATOR = "\x1f"
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
    input_digest: str | None = None

    def __str__(self) -> str:
        return self.rendered


def _require_component(value: object, label: str) -> str:
    """Components must be unambiguous, not printable-safe.

    Only the *rendered* identity is used as a job name and directory, and that
    is a generated hash. Components merely have to hash unambiguously, so
    ordinary planner IDs like ``invoke:key:9f2c...`` are welcome. The one real
    requirement is that no component can contain the field separator, which
    would let two different pairs collide.
    """

    if not isinstance(value, str) or not value:
        raise IdentityError(f"{label} must be a non-empty string")
    if _SEPARATOR in value:
        raise IdentityError(f"{label} must not contain the field separator")
    if any(character.isspace() and character != " " for character in value):
        raise IdentityError(f"{label} must not contain control whitespace")
    return value


def attempt_identity(
    *,
    plan_id: str,
    invocation_id: str,
    sequence: int = 0,
    input_digest: str | None = None,
) -> AttemptIdentity:
    """Derive the stable identity of one attempt at one planned invocation.

    The identity is a pure function of its arguments: the same planning facts
    always render the same value, in this process or a later one. That is what
    lets a restarted controller ask a transport whether *this* attempt was
    already accepted.

    Including ``input_digest`` makes the identity content-addressed, so changed
    inputs produce a different attempt rather than colliding with an existing
    result. Reuse then cannot be stale by construction: finding a manifest at
    this identity means the work was done with exactly these inputs.
    """

    _require_component(plan_id, "plan_id")
    _require_component(invocation_id, "invocation_id")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        raise IdentityError("sequence must be a non-negative integer")
    if input_digest is not None:
        _require_component(input_digest, "input_digest")

    material = _SEPARATOR.join(
        (plan_id, invocation_id, str(sequence), input_digest or "")
    ).encode()
    digest = blake2b(material, digest_size=_DIGEST_BYTES).hexdigest()
    rendered = f"ass-{digest}"
    assert _SAFE.match(rendered)  # the generated form is what must be safe
    return AttemptIdentity(
        plan_id=plan_id,
        invocation_id=invocation_id,
        sequence=sequence,
        rendered=rendered,
        input_digest=input_digest,
    )
