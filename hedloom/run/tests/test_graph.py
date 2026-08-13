"""The Dask kernel, held to the same meaning as the sequential one.

The load-bearing test here is not that a plan runs — it is
`test_the_graph_kernel_produces_the_same_identities_as_the_loop`. If the two
kernels can disagree about identity, a study means something different
depending on how it was run, and reuse across kernels becomes unsound.

The cluster is local and threaded, which is the shape this kernel documents:
no pickling of live transports, no nanny, and one thread per waiting
invocation.
"""

import pytest

from hedloom_exec.transport import InProcessTransport
from hedloom_run.driver import run_plan
from hedloom_run.graph import _task_key, run_plan_graph

distributed = pytest.importorskip("distributed")

from hedloom_run.cluster import local_cluster  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # Silent, because `dashboard_address=None` is not: a scheduler starts its
    # HTTP server regardless and this suite used to bind :8787 on every run,
    # colliding with whatever the developer was already watching.
    cluster = local_cluster(threads=4, dashboard="none")
    with distributed.Client(cluster) as connected:
        yield connected
    cluster.close()


def double(value=None, **kwargs):
    return (value or 1) * 2


def scale(factor=1, source=None, **kwargs):
    return (source or 1) * factor


def explode(**kwargs):
    raise RuntimeError("this corner does not converge")


def transports():
    return {
        "local": InProcessTransport(
            {"double": double, "scale": scale, "explode": explode}
        )
    }


def invocation(key, operation, *, config=None, source=None):
    item = {
        "id": f"invoke:{key}",
        "authored_key": key,
        "operation": {"name": operation, "version": "1"},
        "config": config or [],
        "inputs": [],
        "policy": {"name": "local", "options": {}},
    }
    if source is not None:
        item["inputs"] = [
            {
                "cardinality": "scalar",
                "name": "source",
                "reference": {
                    "type": "output",
                    "invocation_id": f"invoke:{source}",
                    "output_name": "out",
                },
            }
        ]
    return item


def document(invocations):
    return {
        "schema_version": 2,
        "sources": [],
        "operations": [
            {"identity": {"name": name, "version": "1"},
             "outputs": [{"name": "out"}]}
            for name in ("double", "scale", "explode")
        ],
        "invocations": invocations,
    }


def chain():
    """seed -> consumer, plus an unrelated sibling that shares nothing."""

    return document(
        [
            invocation("seed", "double", config=[{"name": "value", "value": 3}]),
            invocation(
                "consumer", "scale", config=[{"name": "factor", "value": 10}],
                source="seed",
            ),
            invocation("sibling", "double", config=[{"name": "value", "value": 5}]),
        ]
    )


def test_a_plan_runs_and_reports_in_plan_order(client, tmp_path):
    report = run_plan_graph(
        chain(),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
    )

    assert report.succeeded, report.summary()
    assert [item.authored_key for item in report.outcomes] == [
        "seed",
        "consumer",
        "sibling",
    ]


def test_an_upstream_value_reaches_its_consumer(client, tmp_path):
    report = run_plan_graph(
        chain(),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
    )

    by_key = {item.authored_key: item for item in report.outcomes}
    assert by_key["seed"].value == 6
    assert by_key["consumer"].value == 60, "the edge must carry the value"


def test_the_graph_kernel_produces_the_same_identities_as_the_loop(client, tmp_path):
    """Which kernel decides readiness must not change what a plan means."""

    sequential = run_plan(
        chain(),
        transports=transports(),
        plan_id="study",
        root=str(tmp_path / "loop"),
    )
    graphed = run_plan_graph(
        chain(),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path / "graph"),
    )

    assert [item.input_digest for item in sequential.outcomes] == [
        item.input_digest for item in graphed.outcomes
    ]
    assert [item.value for item in sequential.outcomes] == [
        item.value for item in graphed.outcomes
    ]


def test_a_result_recorded_by_one_kernel_is_reused_by_the_other(client, tmp_path):
    """The corollary: identity is shared, so the record is too."""

    run_plan(
        chain(),
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
    )
    graphed = run_plan_graph(
        chain(),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
    )

    assert all(item.reused for item in graphed.outcomes), graphed.summary()


def test_a_failure_blocks_its_dependent_and_spares_the_others(client, tmp_path):
    """One corner failing must not abandon the rest of a sweep."""

    report = run_plan_graph(
        document(
            [
                invocation("bad", "explode"),
                invocation("downstream", "scale", source="bad"),
                invocation("unrelated", "double",
                           config=[{"name": "value", "value": 7}]),
            ]
        ),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
    )

    by_key = {item.authored_key: item for item in report.outcomes}
    assert by_key["bad"].outcome == "failed"
    assert by_key["downstream"].outcome == "blocked"
    assert by_key["downstream"].disposition == "skipped"
    assert by_key["unrelated"].outcome == "succeeded", (
        "an independent branch must still run"
    )


def test_a_placement_nobody_provides_fails_rather_than_falling_back(
    client, tmp_path
):
    report = run_plan_graph(
        document(
            [
                {
                    **invocation("heavy", "double"),
                    "policy": {"name": "lsf-pool", "options": {}},
                }
            ]
        ),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
    )

    outcome = report.outcomes[0]
    assert outcome.disposition == "refused"
    assert "lsf-pool" in outcome.error


def test_events_report_while_the_sweep_is_still_running(client, tmp_path):
    seen = []
    report = run_plan_graph(
        chain(),
        client=client,
        transports=transports(),
        plan_id="study",
        root=str(tmp_path),
        on_event=seen.append,
    )

    assert len(seen) == len(report.outcomes)
    assert {item.authored_key for item in seen} == {"seed", "consumer", "sibling"}


def test_a_transport_that_cannot_reach_a_worker_is_refused_by_name(client, tmp_path):
    """Dask's own failure names a graph expression, not the placement."""

    import threading

    unshippable = InProcessTransport({"double": double})
    unshippable.lock = threading.Lock()

    with pytest.raises(TypeError) as raised:
        run_plan_graph(
            chain(),
            client=client,
            transports={"local": unshippable},
            plan_id="study",
            root=str(tmp_path),
        )

    assert "local" in str(raised.value)


def test_a_task_is_named_after_the_corner_it_runs():
    """The point of watching a sweep is knowing which corner is running."""

    from hedloom_exec.planned import plan_bundles

    items = plan_bundles(chain())
    keys = [_task_key(item) for item in items]

    assert keys[0].startswith("seed-")
    assert len(set(keys)) == len(keys)
