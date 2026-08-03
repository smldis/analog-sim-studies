"""Walk a Plan and run it.

This is the piece that was missing while a Plan could be authored and a single
invocation could be executed, but nothing joined the two: the loop lived in an
example. It is deliberately its own unit, because deciding *when* work runs is
a different responsibility from owning one attempt's durable record, and
because the obvious alternative — letting Dask decide readiness — should be a
replacement for this unit rather than a rewrite of another.

What it owns: dependency order, readiness, threading each invocation's outputs
to the inputs that reference them, and what to do when something fails.

What it does not own: attempt identity, journals, transports, reuse (all
`ass_exec`), and the Plan itself (`ass_flow`). It also does not branch on
results. Every plan it can run was fully determined before it started, which is
what makes a rerun predictable; result-dependent control remains an open
architectural question rather than something smuggled in here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ass_exec.attempt import AttemptError
from ass_exec.durability import Durability, execute
from ass_exec.planned import PlannedInvocation, plan_bundles
from ass_exec.transport import Transport, TransportError

__all__ = ["InvocationOutcome", "RunReport", "UnsupportedPlacement", "run_plan"]


class UnsupportedPlacement(RuntimeError):
    """An invocation asked for a placement this run cannot provide.

    Deliberately fatal rather than a fallback. Silently running work somewhere
    other than where it was asked to run is how a study quietly stops meaning
    what it says: a corner that needed a large-memory queue is not the same
    experiment when it lands on a laptop.
    """


@dataclass(frozen=True, slots=True)
class InvocationOutcome:
    """What happened to one invocation in one run."""

    invocation_id: str
    authored_key: str | None
    operation: str
    input_digest: str
    disposition: str
    outcome: str
    placement: str | None = None
    value: Any = None
    artifacts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    error: str | None = None

    @property
    def reused(self) -> bool:
        return self.disposition == "completed"

    @property
    def ran(self) -> bool:
        return self.disposition in ("claimed", "attached")


@dataclass(frozen=True, slots=True)
class RunReport:
    """The whole run, in the order the plan determined."""

    outcomes: tuple[InvocationOutcome, ...]

    @property
    def succeeded(self) -> bool:
        return all(item.outcome == "succeeded" for item in self.outcomes)

    @property
    def ran(self) -> tuple[InvocationOutcome, ...]:
        return tuple(item for item in self.outcomes if item.ran)

    @property
    def reused(self) -> tuple[InvocationOutcome, ...]:
        return tuple(item for item in self.outcomes if item.reused)

    @property
    def blocked(self) -> tuple[InvocationOutcome, ...]:
        return tuple(item for item in self.outcomes if item.outcome == "blocked")

    def summary(self) -> str:
        return "\n".join(
            f"{item.disposition:>9}  {item.authored_key or item.invocation_id:<20}"
            f"  {item.outcome}"
            for item in self.outcomes
        )


class _AnyPlacement(dict):
    """One transport standing in for every placement a plan may ask for."""

    def __init__(self, transport: Transport) -> None:
        super().__init__()
        self._transport = transport

    def get(self, _name: str, _default: Any = None) -> Transport:
        return self._transport

    def __iter__(self):
        return iter(())


def _resolve(reference: Any, produced: Mapping[str, Any]) -> Any:
    """Turn an input reference into the value or address it names."""

    if isinstance(reference, list):
        return [_resolve(item, produced) for item in reference]
    if isinstance(reference, str) and reference.startswith("output:"):
        return produced.get(reference)
    # A source reference resolves to nothing here: this unit does not read
    # addresses, and an operation that needs one declares it in its command.
    return None


def _record_outputs(
    item: PlannedInvocation, result: Any, produced: dict[str, Any]
) -> None:
    """Publish what this invocation produced under the keys that reference it.

    A file output contributes its address, because that is what a downstream
    command opens. Anything else contributes its value.
    """

    for name in item.output_names or ("",):
        key = f"output:{item.input_digest}:{name}"
        artifact = result.artifacts.get(name)
        if artifact is not None:
            produced[key] = artifact.get("address", artifact.get("value"))
        else:
            produced[key] = result.value


def _select_transport(
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


def run_plan(
    document: Mapping[str, Any],
    transport: Transport | None = None,
    *,
    transports: Mapping[str, Transport] | None = None,
    plan_id: str,
    root: str,
    workspace_root: str | None = None,
    commands: Mapping[str, Sequence[str]] | None = None,
    outputs: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    identity_env: Mapping[str, str] | None = None,
    stop_on_failure: bool = True,
    on_event: Callable[[InvocationOutcome], None] | None = None,
) -> RunReport:
    """Execute every invocation in a Plan, in dependency order.

    ``commands`` and ``outputs`` bind operations to how they actually run: a
    command line, and which files or streams count as its results. The Plan
    declares meaning; a run binds mechanism. Operations absent from both are
    executed in-process by the transport.

    ``transports`` maps a policy name to the substrate that provides it, so
    each invocation lands where its Plan says it should: one corner may take a
    dedicated LSF job while cheap reductions stay local. Passing a single
    ``transport`` instead provides every placement, which is convenient for a
    uniform run and wrong as soon as placements differ. A placement no
    transport provides is fatal, never a silent fallback.

    Work whose inputs are unchanged since a previous run is reused rather than
    repeated. On failure the default is to stop: successors are reported as
    ``blocked`` rather than run against inputs that do not exist.
    """

    if transports is None:
        if transport is None:
            raise ValueError("provide either transport or transports")
        available: Mapping[str, Transport] = _AnyPlacement(transport)
    else:
        available = transports

    produced: dict[str, Any] = {}
    outcomes: list[InvocationOutcome] = []
    failed = False

    for item in plan_bundles(
        document, commands=commands, identity_env=identity_env
    ):
        if failed and stop_on_failure:
            outcome = InvocationOutcome(
                invocation_id=item.invocation_id,
                authored_key=item.authored_key,
                operation=item.operation,
                input_digest=item.input_digest,
                disposition="skipped",
                outcome="blocked",
            )
            outcomes.append(outcome)
            if on_event:
                on_event(outcome)
            continue

        try:
            placement_name, chosen = _select_transport(item, available)
        except UnsupportedPlacement as error:
            failed = True
            outcome = InvocationOutcome(
                invocation_id=item.invocation_id,
                authored_key=item.authored_key,
                operation=item.operation,
                input_digest=item.input_digest,
                disposition="refused",
                outcome="failed",
                placement=(item.policy or {}).get("name"),
                error=str(error),
            )
            outcomes.append(outcome)
            if on_event:
                on_event(outcome)
            continue

        bundle = dict(item.bundle)
        bundle["placement"] = {
            "requested": dict(item.policy or {}),
            "resolved": {"placement": placement_name, "transport": chosen.name},
        }
        bundle["resolved_inputs"] = {
            name: _resolve(reference, produced)
            for name, reference in item.bundle["inputs"].items()
        }
        declared = (outputs or {}).get(item.operation)
        if declared:
            bundle["outputs"] = dict(declared)

        try:
            result = execute(
                chosen,
                bundle,
                durability=Durability.RECORDED,
                root=root,
                workspace_root=workspace_root,
                plan_id=plan_id,
                invocation_id=item.invocation_id,
            )
        except (AttemptError, TransportError) as error:
            failed = True
            outcome = InvocationOutcome(
                invocation_id=item.invocation_id,
                authored_key=item.authored_key,
                operation=item.operation,
                input_digest=item.input_digest,
                disposition="refused",
                outcome="failed",
                placement=placement_name,
                error=f"{type(error).__name__}: {error}",
            )
            outcomes.append(outcome)
            if on_event:
                on_event(outcome)
            continue

        if result.outcome == "succeeded":
            _record_outputs(item, result, produced)
        else:
            failed = True

        outcome = InvocationOutcome(
            invocation_id=item.invocation_id,
            authored_key=item.authored_key,
            operation=item.operation,
            input_digest=item.input_digest,
            disposition=result.disposition or "ran",
            outcome=result.outcome,
            placement=placement_name,
            value=result.value,
            artifacts=dict(result.artifacts),
            error=(result.detail or {}).get("error"),
        )
        outcomes.append(outcome)
        if on_event:
            on_event(outcome)

    return RunReport(tuple(outcomes))
