"""What a site exposes, and the promise that the default exposes what it did.

Two tests carry this module. `test_a_silent_cluster_holds_no_http_server` is
the one the feature exists for, and it asserts a behaviour rather than an
internal: if a future `distributed` moves the seam this module suppresses, the
failure names a cluster that opened a server, not a missing attribute.

`test_the_network_exposure_asks_dask_for_nothing` is the one that protects
every existing installation. `"network"` must pass no address at all, because
the moment it names one it has taken over a default that belongs to Dask.
"""

import pytest

from ass_run.cluster import cluster_for, local_cluster
from ass_run.site import Site, SiteError

distributed = pytest.importorskip("distributed")


class Recorder:
    """Stands in for `LocalCluster` to capture what it was asked for."""

    def __init__(self):
        self.kwargs = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return "cluster"


@pytest.fixture
def recorded(monkeypatch):
    """Intercept cluster construction: these tests are about the request."""

    recorder = Recorder()
    monkeypatch.setattr(distributed, "LocalCluster", recorder)
    return recorder


def test_the_network_exposure_asks_dask_for_nothing(recorded):
    local_cluster(threads=4, dashboard="network")

    assert "dashboard_address" not in recorded.kwargs
    assert "worker_dashboard_address" not in recorded.kwargs
    assert recorded.kwargs == {
        "processes": False,
        "n_workers": 1,
        "threads_per_worker": 4,
    }


def test_network_is_what_a_site_gets_without_declaring_anything(tmp_path, recorded):
    site = Site(root=str(tmp_path))

    assert site.dashboard == "network"

    cluster_for(site)
    assert "dashboard_address" not in recorded.kwargs


def test_unset_threads_leave_the_sizing_to_dask(recorded):
    local_cluster()

    assert "threads_per_worker" not in recorded.kwargs


def test_loopback_binds_the_worker_too(recorded):
    local_cluster(threads=2, dashboard="loopback")

    # Two servers, so binding only the scheduler would look closed and leave
    # the study half exposed.
    assert recorded.kwargs["dashboard_address"] == "127.0.0.1:0"
    assert recorded.kwargs["worker_dashboard_address"] == "127.0.0.1:0"


def test_a_site_carries_its_exposure_to_the_cluster(tmp_path, recorded):
    site = Site(root=str(tmp_path), threads=7, dashboard="loopback")

    cluster_for(site)

    assert recorded.kwargs["threads_per_worker"] == 7
    assert recorded.kwargs["dashboard_address"] == "127.0.0.1:0"


def test_an_override_beats_the_profile(tmp_path, recorded):
    site = Site(root=str(tmp_path), threads=7, dashboard="loopback")

    cluster_for(site, threads=2)

    assert recorded.kwargs["threads_per_worker"] == 2


def test_a_multi_process_cluster_cannot_be_silent():
    # Workers in their own processes dial the scheduler over TCP, so the
    # request is impossible rather than merely awkward, and is refused.
    with pytest.raises(SiteError, match="cannot be silent"):
        local_cluster(dashboard="none", processes=True)


def test_an_unknown_exposure_is_refused():
    with pytest.raises(SiteError, match="unknown dashboard exposure"):
        local_cluster(dashboard="private")


def test_a_profile_naming_an_unknown_exposure_is_refused_at_construction(tmp_path):
    with pytest.raises(SiteError, match="not one of"):
        Site(root=str(tmp_path), dashboard="off")


def test_a_silent_cluster_holds_no_http_server():
    """The feature: no listener, and the work still runs.

    Asserted through the objects rather than through `ss`, so the test says
    what it means on any host — a scheduler and every worker without an HTTP
    server is exactly the condition that leaves nothing bound.
    """

    cluster = local_cluster(threads=2, dashboard="none")
    try:
        assert getattr(cluster.scheduler, "http_server", None) is None
        for worker in cluster.workers.values():
            assert getattr(worker, "http_server", None) is None

        with distributed.Client(cluster) as client:
            assert client.submit(lambda: 6 * 7).result() == 42
    finally:
        cluster.close()


def test_the_seam_is_restored_for_whatever_is_built_next():
    """Scoped in time: silencing one cluster must not silence the process."""

    silent = local_cluster(threads=1, dashboard="none")
    silent.close()

    after = local_cluster(threads=1, dashboard="loopback")
    try:
        assert after.scheduler.http_server is not None
    finally:
        after.close()
