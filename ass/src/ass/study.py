"""A study: one object that can show you its Plan and then run it.

The two halves of this system were always joined by hand. An author wrote a
Plan; someone else wrote a binding supplying implementations, commands, output
paths, transports and roots; a third caller walked the result. Each seam was a
place where the study could mean something different from what was authored.

`submit()` joins them. It is deliberately not a new capability: it materializes
the same Plan, binds the same operations, and calls the same kernel. What it
removes is the opportunity to bind them inconsistently.

The invariant:

    Nothing is spent until `submit`, and what runs is what the Plan showed.

`study.plan` is complete and inspectable before submission — the manifesto's
requirement to materialize jobs before spending simulation resources — and the
operations that run are the ones the Plan names, because both come from the
same declaration rather than from two files that must agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ass_exec.transport import Transport
from ass_run.driver import InvocationOutcome, RunReport, run_plan
from ass_run.site import Site

from ass.binding import BoundTransport

__all__ = ["Study", "StudyRun", "submit"]


@dataclass(frozen=True, slots=True)
class StudyRun:
    """What a run produced, addressable the way it was authored."""

    report: RunReport
    document: Mapping[str, Any]

    def __getitem__(self, authored_key: str) -> InvocationOutcome:
        for outcome in self.report.outcomes:
            if outcome.authored_key == authored_key:
                return outcome
        raise KeyError(f"no invocation was authored with key {authored_key!r}")

    @property
    def value(self) -> Any:
        """The last invocation's value: a plan's conclusion is its final step."""

        return self.report.outcomes[-1].value if self.report.outcomes else None

    @property
    def succeeded(self) -> bool:
        return self.report.succeeded

    def summary(self) -> str:
        return self.report.summary()


class Study:
    """An authored Plan together with the operations that implement it."""

    def __init__(self, plan: Any, implementations: Mapping[str, Callable[..., Any]]):
        self.plan = plan
        self.implementations = dict(implementations)

    @property
    def document(self) -> Mapping[str, Any]:
        return self.plan.to_data()

    def summary(self) -> str:
        """What will run, before anything is spent."""

        document = self.document
        invocations = sorted(
            document.get("invocations", []),
            key=lambda item: item.get("authored_key") or item["id"],
        )
        lines = [
            f"plan schema {document.get('schema_version')}: "
            f"{len(invocations)} invocations, "
            f"{len(document.get('sources', []))} sources"
        ]
        # Widths follow the study rather than a guess: an authored key that
        # overran a fixed column used to run into the operation name, which is
        # unreadable exactly when a study is large enough to need reading.
        keys = [item.get("authored_key") or item["id"] for item in invocations]
        key_width = max((len(item) for item in keys), default=0) + 2
        name_width = (
            max(
                (len(item["operation"]["name"]) for item in invocations),
                default=0,
            )
            + 2
        )
        for invocation, key in zip(invocations, keys):
            placement = (invocation.get("policy") or {}).get("name", "local")
            lines.append(
                f"  {key:<{key_width}}"
                f"{invocation['operation']['name']:<{name_width}}{placement}"
            )
        return "\n".join(lines)

    def submit(
        self,
        *,
        site: Site,
        client: Any = None,
        watch: bool = False,
        on_event: Callable[[InvocationOutcome], None] | None = None,
    ) -> StudyRun:
        """Run this study, honouring every placement the Plan resolved.

        ``client`` gives readiness to Dask; without one the study is walked in
        one thread, which is right for a plan small enough not to need a
        cluster and wrong for a sweep. The cluster is the caller's because its
        shape — how many concurrent jobs this site tolerates — is an
        operational decision a library must not make silently.
        """

        document = self.document
        transports = {
            name: BoundTransport(self.implementations, delegate)
            for name, delegate in site.transports.items()
        }
        if not transports:
            transports = {"local": BoundTransport(self.implementations)}

        report_to = _reporter(on_event, watch)
        # One reading of every declared source serves both: its content decides
        # whether work is stale, and its location is what the body receives.
        # They are computed together because the second is keyed by the first.
        fingerprints = site.fingerprints(document)
        common = dict(
            transports=transports,
            plan_id=_plan_id(document),
            root=site.root,
            workspace_root=site.workspace_root,
            source_fingerprints=fingerprints,
            source_addresses=site.source_addresses(document, fingerprints),
            on_event=report_to,
        )

        if client is None:
            report = run_plan(document, **common)
        else:
            from ass_run.graph import run_plan_graph

            report = run_plan_graph(document, client=client, **common)
        return StudyRun(report=report, document=document)


def _plan_id(document: Mapping[str, Any]) -> str:
    """A stable name for this plan's records.

    Taken from the plan's own declared outputs rather than invented per run:
    two runs of the same study must land on the same attempts, or nothing is
    ever reused.
    """

    # Declared outputs are a list of {"name", "reference"} records, not a
    # mapping. Reading them as one stringified the whole record — reference and
    # producing invocation id included — so a study whose output came from a
    # differently keyed invocation landed on a different attempt root and
    # reused nothing, however unchanged the work itself was.
    names = sorted(
        str(item["name"])
        for item in document.get("outputs") or ()
        if isinstance(item, Mapping) and "name" in item
    )
    return "-".join(names) if names else "study"


def _reporter(
    on_event: Callable[[InvocationOutcome], None] | None, watch: bool
) -> Callable[[InvocationOutcome], None] | None:
    if on_event is not None:
        return on_event
    if not watch:
        return None

    def report(outcome: InvocationOutcome) -> None:
        name = outcome.authored_key or outcome.invocation_id
        detail = f"  {outcome.error}" if outcome.error else ""
        print(f"[{outcome.disposition:>9}] {name:<32}{outcome.outcome}{detail}")

    return report


def submit(
    study: Study,
    *,
    site: Site,
    client: Any = None,
    watch: bool = False,
) -> StudyRun:
    """Run a study. The verb ASS Flow reserved and refused until now."""

    return study.submit(site=site, client=client, watch=watch)
