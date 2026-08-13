"""The cluster a site is willing to run, including what it will not expose.

`run_plan_graph` takes a client and refuses to build one, because how much a
site tolerates running at once is an operational decision. That stays true.
What was missing is the other half of the same decision: a Dask cluster opens
listening sockets, and on a shared submit host those are not private.

Two facts make this an option rather than a footnote. Both were measured
against `distributed==2026.7.1`, the version `hedloom-run[dask]` pins:

* A `Scheduler` **always** starts an HTTP server. `Scheduler.__init__` calls
  `start_http_server(...)` unconditionally; `dashboard=False` only skips
  installing the bokeh routes, leaving a listener on `:8787` still serving
  `/health`, `/metrics` and `/api`. Every `Worker` starts one of its own.
* Both bind every interface. A study on a login host therefore publishes its
  corner names, workspace paths and profiler to anything that can reach the
  host — and loopback does not help, because loopback is per host, not per
  user.

So the exposure is declared, in the profile, beside the concurrency:

    [kernel]
    threads = 32
    dashboard = "network"     # "network" | "loopback" | "none"

`"network"` is the default and is exactly what Dask does unaided: that branch
passes no address at all, so an installation that adopts this module without
declaring anything is indistinguishable from one that never used it.

The invariant:

    Exposure changes how a run can be watched and nothing about what it
    computes.

No identity, no reuse, no Plan content is touched — the same promise the choice
of kernel already makes.

**Why "none" needs a private seam.** There is no supported way to ask
`distributed` for a scheduler that does not listen, so this suppresses
`ServerNode.start_http_server` while the cluster is built. Both the scheduler
and the workers create their servers there, so one override silences all of
them, and `ServerNode` being their shared base is what makes it a single seam
rather than a sweep.

Depending on a private method is defensible only if the *behaviour* is what is
tested. `tests/test_cluster.py` asserts that a silent cluster holds no HTTP
server and that work still runs, so an upgrade that moves the seam fails on the
symptom rather than on an import.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from hedloom_run.site import EXPOSURES, Site, SiteError

__all__ = ["EXPOSURES", "cluster_for", "local_cluster"]


def _no_http_server(
    self: Any,
    routes: Any,
    dashboard_address: Any,
    default_port: int = 0,
    ssl_options: Any = None,
) -> None:
    """Stand in for `ServerNode.start_http_server`, which always binds."""

    return None


@contextmanager
def _without_http_servers() -> Iterator[None]:
    """Hold the seam open only while a cluster is being built.

    Scoped in time rather than in space: the patch is global, but a scheduler
    and its workers create their servers during construction, so covering the
    construction covers their whole lives. Anything built afterwards — by this
    process, or by a library sharing it — listens normally.
    """

    from distributed.node import ServerNode

    original = ServerNode.start_http_server
    ServerNode.start_http_server = _no_http_server
    try:
        yield
    finally:
        ServerNode.start_http_server = original


def local_cluster(
    *,
    threads: int | None = None,
    dashboard: str = "network",
    processes: bool = False,
) -> Any:
    """Build the local, threaded cluster this kernel documents.

    One worker with many threads, for the reasons `hedloom_run.graph` sets out: an
    invocation waiting on `bsub -I` costs a thread rather than anything scarce,
    nothing secedes, and no nanny may restart a worker holding live farm
    clients.

    ``threads`` left as None gives Dask's own sizing, which is this host's CPU
    count — right for a local study and wrong for a farm sweep, where the
    number is the site's MAX JOB policy and belongs in the profile.
    """

    from distributed import LocalCluster

    if dashboard not in EXPOSURES:
        raise SiteError(
            f"unknown dashboard exposure {dashboard!r}; a site may declare "
            f"{', '.join(repr(item) for item in EXPOSURES)}"
        )
    if dashboard == "none" and processes:
        # Refused rather than quietly downgraded. Workers in their own
        # processes reach the scheduler over TCP, so a silent multi-process
        # cluster cannot exist; binding anyway under a name that promises
        # silence would be the kind of plausible falsehood this project treats
        # as a defect.
        raise SiteError(
            "a multi-process cluster cannot be silent: its workers connect to "
            "the scheduler over TCP, which needs a listening socket. Run "
            "processes=False, which is the shape this kernel documents, or "
            "declare dashboard = 'loopback'"
        )

    options: dict[str, Any] = {"processes": processes, "n_workers": 1}
    if threads is not None:
        options["threads_per_worker"] = threads

    if dashboard == "network":
        # Deliberately passes no address: naming Dask's default here would
        # copy a value that is theirs to change, and this branch promises to
        # be indistinguishable from not using this module at all.
        return LocalCluster(**options)

    if dashboard == "loopback":
        # Both servers. The worker's is a second listener and defaults to every
        # interface exactly as the scheduler's does, so binding only the
        # scheduler would leave the study half exposed and look closed.
        return LocalCluster(
            **options,
            dashboard_address="127.0.0.1:0",
            worker_dashboard_address="127.0.0.1:0",
        )

    with _without_http_servers():
        # `dashboard_address=None` as well as the suppression: it is what makes
        # the scheduler skip connecting bokeh routes to an application the
        # patch never built.
        return LocalCluster(**options, dashboard_address=None)


def cluster_for(site: Site, **overrides: Any) -> Any:
    """Build the cluster this site's profile describes.

    The first reader `Site.threads` has ever had. Until now the number was
    written once in the profile and again in the operator's `LocalCluster(...)`
    call with nothing comparing them — a gap the register records under *Two
    concurrency limits, not one*, whose fuller resolution (a dedicated farm
    worker bounded by a Dask resource) this does not foreclose.
    """

    settings: dict[str, Any] = {"threads": site.threads, "dashboard": site.dashboard}
    settings.update(overrides)
    return local_cluster(**settings)
