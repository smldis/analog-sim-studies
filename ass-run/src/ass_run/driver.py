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
from ass_exec.planned import plan_bundles
from ass_exec.transport import Transport, TransportError

# Binding rules are shared with the Dask kernel rather than restated, so that
# changing which kernel decides readiness cannot change what a plan means.
from ass_run.binding import (
    UnsupportedPlacement,
    available_transports,
    build_bundle,
    produced_by,
    select_transport as _select_transport,
)

__all__ = ["InvocationOutcome", "RunReport", "UnsupportedPlacement", "run_plan"]


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

    available = available_transports(transport, transports)

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

        bundle = build_bundle(
            item,
            produced=produced,
            placement_name=placement_name,
            transport=chosen,
            outputs=outputs,
        )

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
            produced.update(produced_by(item, result))
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
