"""What a run binds, independently of what decides when work runs.

A Plan declares meaning: operations, inputs, declared outputs, and the
placement each invocation resolved to. A *run* binds mechanism: which command
implements an operation, which substrate provides a placement, and which
address an upstream output actually landed at.

That binding is identical whether readiness is decided by a sequential loop or
by a Dask graph, so it lives here and both kernels use it. The invariant this
module exists to hold:

    Changing which kernel decides readiness changes how long a plan takes and
    nothing else — the same results, under the same identities.

Sharing the code is the strongest available guarantee of that. Two copies of
these rules would drift, and the drift would show up as a study that means
something different depending on how it was run.
"""

from __future__ import annotations

from typing import Any, Mapping

from ass_exec.planned import PlannedInvocation
from ass_exec.transport import Transport

__all__ = [
    "AnyPlacement",
    "UnsupportedPlacement",
    "available_transports",
    "build_bundle",
    "produced_by",
    "resolve",
    "select_transport",
]


class UnsupportedPlacement(RuntimeError):
    """An invocation asked for a placement this run cannot provide.

    Deliberately fatal rather than a fallback. Silently running work somewhere
    other than where it was asked to run is how a study quietly stops meaning
    what it says: a corner that needed a large-memory queue is not the same
    experiment when it lands on a laptop.
    """


class AnyPlacement(dict):
    """One transport standing in for every placement a plan may ask for."""

    def __init__(self, transport: Transport) -> None:
        super().__init__()
        self._transport = transport

    def get(self, _name: str, _default: Any = None) -> Transport:
        return self._transport

    def __iter__(self):
        return iter(())


def available_transports(
    transport: Transport | None, transports: Mapping[str, Transport] | None
) -> Mapping[str, Transport]:
    """Resolve the two ways a caller may offer substrates into one mapping."""

    if transports is not None:
        return transports
    if transport is None:
        raise ValueError("provide either transport or transports")
    return AnyPlacement(transport)


def resolve(reference: Any, produced: Mapping[str, Any]) -> Any:
    """Turn an input reference into the value or address it names.

    One lookup serves both kinds. An operation output is in ``produced``
    because the invocation that made it ran; a declared source is in there
    because the run seeded it before walking, which is what the identity model
    already claimed — a source is produced before it is used.

    A reference that is not there resolves to nothing, which is what a source
    did unconditionally before runs seeded them. Callers that do not supply
    source addresses therefore see exactly the behaviour they saw before.
    """

    if isinstance(reference, list):
        return [resolve(item, produced) for item in reference]
    if isinstance(reference, str):
        return produced.get(reference)
    return None


def produced_by(item: PlannedInvocation, result: Any) -> dict[str, Any]:
    """What this invocation contributes under the keys that reference it.

    A file output contributes its address, because that is what a downstream
    command opens. Anything else contributes its value.
    """

    contributed: dict[str, Any] = {}
    for name in item.output_names or ("",):
        key = f"output:{item.input_digest}:{name}"
        artifact = result.artifacts.get(name)
        if artifact is not None:
            contributed[key] = artifact.get("address", artifact.get("value"))
        else:
            contributed[key] = result.value
    return contributed


def select_transport(
    item: PlannedInvocation,
    transports: Mapping[str, Transport],
) -> tuple[str, Transport]:
    """Honour the placement the Plan already resolved for this invocation.

    ASS Flow resolves call override, operation default, plan default, then
    local at planning time, and stores the result on the invocation. This is
    where that decision finally has an effect.
    """

    name = (item.policy or {}).get("name") or "local"
    chosen = transports.get(name)
    if chosen is None:
        raise UnsupportedPlacement(
            f"{item.authored_key or item.invocation_id} asks for placement "
            f"{name!r}, which this run does not provide "
            f"(have: {', '.join(sorted(transports)) or 'none'})"
        )
    return name, chosen


def build_bundle(
    item: PlannedInvocation,
    *,
    produced: Mapping[str, Any],
    placement_name: str,
    transport: Transport,
    outputs: Mapping[str, Mapping[str, Mapping[str, Any]]] | None,
) -> dict[str, Any]:
    """Assemble the bundle one attempt is executed from.

    ``placement`` carries the invocation's own resource request to whichever
    transport runs it, and never reaches the input digest. ``resolved_inputs``
    carries upstream addresses for execution, and never reaches it either:
    which values they are is already implied by the declared input digests.
    """

    bundle = dict(item.bundle)
    bundle["placement"] = {
        "requested": dict(item.policy or {}),
        "resolved": {"placement": placement_name, "transport": transport.name},
    }
    bundle["resolved_inputs"] = {
        name: resolve(reference, produced)
        for name, reference in item.bundle["inputs"].items()
    }
    declared = (outputs or {}).get(item.operation)
    if declared:
        bundle["outputs"] = dict(declared)
    return bundle
