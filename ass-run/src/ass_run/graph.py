"""Readiness owned by Dask; placement still owned by the Plan.

One task per invocation, edges where one invocation's output feeds another's
input. Dask decides what is ready and how much runs at once; it does not decide
where anything runs, what an attempt's identity is, or whether work may be
reused — those stay with the Plan and with `ass_exec`, exactly as they were
under the sequential driver.

The invariant this kernel must not break:

    Changing which kernel decides readiness changes how long a plan takes and
    nothing else — the same results, under the same identities.

The binding rules it obeys are therefore imported from `ass_run.binding` rather
than restated here.

**Cluster shape matters, and the recommended one is unusual.** Use a local,
threaded cluster on the submit host:

    from distributed import Client, LocalCluster
    cluster = LocalCluster(processes=False, threads_per_worker=32)

Three measured reasons, recorded in `docs/vision/open-concepts.md`:

* An invocation waiting on `bsub -I` costs about 16 KiB of thread and one
  client process. Concurrency here is a safety rail, not a scarce resource, and
  `threads_per_worker` *is* the rail — there is deliberately no limit parameter
  in this module. Size it from the site's MAX JOB policy and per-user process
  limits, which are facts to ask for rather than guess.
* Nothing secedes. A worker holding live `bsub -I` clients should read as
  running, and `secede()` would report it idle by excluding the task from the
  parallelism count.
* Threads avoid supervision and duplication, not serialization. A nanny that
  restarts a worker under memory pressure would take that worker's blocked
  clients with it — and, under owner-bound lifetime, that many running farm
  jobs. Measured, though, and worth knowing: Dask serializes every task even on
  an in-process cluster, so a **transport always travels as a copy**, never as
  a shared live object. Ours are effectively stateless per submission, so a
  copy is correct. A transport that must be a singleton — a pooled one holding
  a client to a second cluster — cannot be passed this way and will need a
  factory constructed on the worker.

A failed invocation blocks its dependents by returning a blocked outcome, not
by raising. Independent branches continue: one corner failing does not abandon
the other forty-nine, which is what a sweep wants and what the sequential
driver could not offer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ass_exec.attempt import AttemptError
from ass_exec.durability import Durability, execute
from ass_exec.planned import PlannedInvocation, plan_bundles
from ass_exec.transport import Transport, TransportError

from ass_run.binding import (
    UnsupportedPlacement,
    available_transports,
    build_bundle,
    produced_by,
    select_transport,
)
from ass_run.driver import InvocationOutcome, RunReport

__all__ = ["run_plan_graph"]


@dataclass(frozen=True, slots=True)
class _RunConfig:
    """Where the durable record and the workspaces live, for one run."""

    plan_id: str
    root: str
    workspace_root: str | None = None
    outputs: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None


@dataclass(frozen=True, slots=True)
class _Step:
    """One task's return: what happened, and what downstream tasks may read.

    The produced map travels along the graph edge rather than through shared
    state, so a task depends on exactly the outputs it declared inputs from.
    """

    outcome: InvocationOutcome
    produced: Mapping[str, Any] = field(default_factory=dict)


def _outcome(
    item: PlannedInvocation,
    *,
    disposition: str,
    outcome: str,
    placement: str | None = None,
    error: str | None = None,
) -> InvocationOutcome:
    return InvocationOutcome(
        invocation_id=item.invocation_id,
        authored_key=item.authored_key,
        operation=item.operation,
        input_digest=item.input_digest,
        disposition=disposition,
        outcome=outcome,
        placement=placement,
        error=error,
    )


def _run_one(
    item: PlannedInvocation,
    transports: Mapping[str, Transport],
    config: _RunConfig,
    *upstream: _Step,
) -> _Step:
    """Execute one invocation once every input it named has landed.

    Runs on a worker. Everything it needs arrives as an argument: there is no
    shared state between tasks, which is what lets the same function serve a
    thread, a process, or eventually a pooled worker.
    """

    unmet = [step for step in upstream if step.outcome.outcome != "succeeded"]
    if unmet:
        # Deliberately not an exception. A dependent of failed work has not
        # failed; it never ran, and the report should say so. Independent
        # branches of the plan are unaffected.
        return _Step(_outcome(item, disposition="skipped", outcome="blocked"))

    produced: dict[str, Any] = {}
    for step in upstream:
        produced.update(step.produced)

    try:
        placement_name, chosen = select_transport(item, transports)
    except UnsupportedPlacement as error:
        return _Step(
            _outcome(
                item,
                disposition="refused",
                outcome="failed",
                placement=(item.policy or {}).get("name"),
                error=str(error),
            )
        )

    bundle = build_bundle(
        item,
        produced=produced,
        placement_name=placement_name,
        transport=chosen,
        outputs=config.outputs,
    )

    try:
        result = execute(
            chosen,
            bundle,
            durability=Durability.RECORDED,
            root=config.root,
            workspace_root=config.workspace_root,
            plan_id=config.plan_id,
            invocation_id=item.invocation_id,
        )
    except (AttemptError, TransportError) as error:
        return _Step(
            _outcome(
                item,
                disposition="refused",
                outcome="failed",
                placement=placement_name,
                error=f"{type(error).__name__}: {error}",
            )
        )

    contributed = produced_by(item, result) if result.outcome == "succeeded" else {}
    return _Step(
        InvocationOutcome(
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
        ),
        contributed,
    )


def _require_shippable(transports: Mapping[str, Transport]) -> None:
    """Refuse a transport that cannot reach a worker, before anything runs.

    Dask serializes every task, so each transport is copied to the worker that
    runs the invocation. Left to Dask, a transport holding a lock, a socket, or
    a live client fails deep inside the protocol with a message about graph
    expressions, naming neither the placement nor the cause.
    """

    import cloudpickle

    for name, transport in transports.items():
        try:
            cloudpickle.dumps(transport)
        except Exception as error:  # deliberate: any failure to ship qualifies
            raise TypeError(
                f"the transport for placement {name!r} cannot be sent to a "
                f"worker ({type(error).__name__}: {error}). Dask copies a "
                "transport to the worker that runs the invocation, so it must "
                "be serializable; a transport that must stay a singleton needs "
                "to be built on the worker instead of passed to it."
            ) from error


def _task_key(item: PlannedInvocation) -> str:
    """A key an operator can recognise in a dashboard.

    Named after the authored key rather than a digest, because the point of
    watching a sweep is knowing which *corner* is running. The digest suffix
    keeps it unique when the same key is planned twice.
    """

    name = item.authored_key or item.invocation_id
    return f"{name}-{item.input_digest[:8]}"


def run_plan_graph(
    document: Mapping[str, Any],
    transport: Transport | None = None,
    *,
    client: Any,
    transports: Mapping[str, Transport] | None = None,
    plan_id: str,
    root: str,
    workspace_root: str | None = None,
    commands: Mapping[str, Sequence[str]] | None = None,
    outputs: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    identity_env: Mapping[str, str] | None = None,
    on_event: Callable[[InvocationOutcome], None] | None = None,
) -> RunReport:
    """Execute a Plan as a Dask graph and report in the Plan's own order.

    ``client`` is a `distributed.Client`. It is required rather than created
    here: the cluster's shape is an operational decision — how many concurrent
    jobs the site tolerates, whether a dashboard is served — and a library that
    silently started one would be choosing it for the operator.

    ``on_event`` fires as tasks complete, in completion order, so a long sweep
    is observable while it runs. The returned report stays in plan order, so a
    run remains comparable with any other run of the same plan.
    """

    from distributed import as_completed

    available = available_transports(transport, transports)
    _require_shippable(
        dict(transports) if transports is not None else {"*": transport}
    )
    config = _RunConfig(
        plan_id=plan_id,
        root=root,
        workspace_root=workspace_root,
        outputs=outputs,
    )

    items = plan_bundles(document, commands=commands, identity_env=identity_env)
    futures: dict[str, Any] = {}
    taken: set[str] = set()
    for item in items:
        # Two tasks sharing a key would be one task to Dask, and one of the two
        # invocations would never run. Readable first, unique always.
        key = _task_key(item)
        while key in taken:
            key = f"{key}.{len(taken)}"
        taken.add(key)
        futures[item.invocation_id] = client.submit(
            _run_one,
            item,
            available,
            config,
            *(futures[dependency] for dependency in item.depends_on),
            key=key,
            # Side-effecting work with a durable record of its own. Dask must
            # not decide two invocations are the same call and run one; reuse
            # is `ass_exec`'s decision, made against declared inputs.
            pure=False,
        )

    completed: dict[str, _Step] = {}
    for future in as_completed(list(futures.values())):
        step = future.result()
        completed[step.outcome.invocation_id] = step
        if on_event:
            on_event(step.outcome)

    return RunReport(
        tuple(completed[item.invocation_id].outcome for item in items)
    )
