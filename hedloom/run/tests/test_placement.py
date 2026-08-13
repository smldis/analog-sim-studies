"""Each invocation lands where its Plan said it should.

Hedloom Flow resolves placement at planning time and stores it on the invocation.
These tests are where that decision finally has an effect.
"""

import json
import os

import pytest

from hedloom_exec.journal import AttemptJournal
from hedloom_exec.lsf import LSFInteractiveTransport, SubprocessRunner
from hedloom_exec.transport import InProcessTransport
from hedloom_run.driver import UnsupportedPlacement, run_plan

FARM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "exec",
    "tests",
    "fakefarm",
)


class Recorder(InProcessTransport):
    def __init__(self, name):
        super().__init__({"work": lambda **kwargs: name})
        self.name = name
        self.seen = []

    def submit(self, identity, bundle):
        self.seen.append(identity)
        return super().submit(identity, bundle)


def invocation(key, policy):
    return {
        "id": f"invoke:{key}",
        "authored_key": key,
        "operation": {"name": "work", "version": "1"},
        "config": [{"name": "k", "value": key}],
        "inputs": [],
        "policy": policy,
    }


def document(*policies):
    return {
        "schema_version": 2,
        "sources": [],
        "operations": [
            {"identity": {"name": "work", "version": "1"},
             "outputs": [{"name": "out"}]}
        ],
        "invocations": [
            invocation(key, policy) for key, policy in policies
        ],
    }


def test_invocations_land_on_the_placement_they_asked_for(tmp_path):
    local = Recorder("local")
    direct = Recorder("lsf-direct")

    report = run_plan(
        document(
            ("cheap", {"name": "local", "options": {}}),
            ("heavy", {"name": "lsf-direct", "options": {"queue": "bigmem"}}),
        ),
        transports={"local": local, "lsf-direct": direct},
        plan_id="p",
        root=str(tmp_path),
    )

    assert report.succeeded
    by_key = {item.authored_key: item for item in report.outcomes}
    assert by_key["cheap"].placement == "local"
    assert by_key["heavy"].placement == "lsf-direct"
    assert len(local.seen) == 1 and len(direct.seen) == 1


def test_a_placement_nobody_provides_fails_rather_than_falling_back(tmp_path):
    """Running elsewhere silently would change what the study means."""

    report = run_plan(
        document(("heavy", {"name": "lsf-pool", "options": {}})),
        transports={"local": Recorder("local")},
        plan_id="p",
        root=str(tmp_path),
    )

    assert not report.succeeded
    outcome = report.outcomes[0]
    assert outcome.disposition == "refused"
    assert "lsf-pool" in outcome.error


def test_a_single_transport_still_serves_a_uniform_run(tmp_path):
    report = run_plan(
        document(("a", {"name": "local", "options": {}})),
        Recorder("local"),
        plan_id="p",
        root=str(tmp_path),
    )
    assert report.succeeded


def test_requested_resolved_and_observed_are_recorded_separately(tmp_path):
    """A run that came out misplaced is only explainable if these stay apart."""

    direct = Recorder("lsf-direct")
    run_plan(
        document(
            ("heavy", {"name": "lsf-direct", "options": {"queue": "bigmem"}})
        ),
        transports={"lsf-direct": direct},
        plan_id="p",
        root=str(tmp_path),
    )

    identity = direct.seen[0]
    manifest = json.loads(
        (tmp_path / identity / "manifest.json").read_text()
    )
    placement = manifest["result"]["placement"]

    assert placement["requested"]["name"] == "lsf-direct"
    assert placement["requested"]["options"]["queue"] == "bigmem"
    assert placement["resolved"]["transport"] == "lsf-direct"
    assert placement["observed"]["transport"] == "lsf-direct"


def test_placement_is_recorded_before_the_substrate_is_touched(tmp_path):
    direct = Recorder("lsf-direct")
    run_plan(
        document(("heavy", {"name": "lsf-direct", "options": {}})),
        transports={"lsf-direct": direct},
        plan_id="p",
        root=str(tmp_path),
    )

    events = [
        item.event
        for item in AttemptJournal(tmp_path, direct.seen[0]).events()
    ]
    assert events.index("placement") < events.index("submit_intent")


def test_an_authored_resource_need_survives_all_the_way_to_the_submission(
    tmp_path, monkeypatch
):
    """Plan → driver → transport → the command a scheduler would actually read.

    The three units each carry part of this: Hedloom Flow resolves the policy, the
    driver puts it on the bundle, the transport turns it into `bsub` arguments.
    A per-unit test can show any one of those and still miss the seam, so this
    one goes through the real subprocess layer and inspects what the submission
    command was given. The farm is a fake, so this is evidence about our half
    of the exchange only: whether LSF admits the request is preflight's job.
    """

    monkeypatch.setenv("PATH", FARM + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_LSF_STATE", str(tmp_path / "lsf"))

    report = run_plan(
        document(
            (
                "corner",
                {
                    "name": "lsf-direct",
                    "options": {
                        "queue": "bigmem",
                        "cores": 8,
                        "memory_mb": 16000,
                        "licences": {"spectre": 1},
                    },
                },
            )
        ),
        transports={
            "lsf-direct": LSFInteractiveTransport(
                walltime="5", runner=SubprocessRunner()
            )
        },
        plan_id="study",
        root=str(tmp_path / "attempts"),
        commands={"work": ["/bin/echo", "ran"]},
    )

    assert report.succeeded, report.summary()
    submitted = list((tmp_path / "lsf").glob("*.json"))
    assert len(submitted) == 1
    options = json.loads(submitted[0].read_text())["options"]

    assert options["-q"] == "bigmem"
    assert options["-n"] == "8"
    assert options["-R"] == "rusage[mem=16000,spectre=1]"
    assert options["-W"] == "5", "the site default bounds a job that asks for none"


def test_placement_does_not_change_result_identity(tmp_path):
    """Where work runs must never invalidate what it produced."""

    first = run_plan(
        document(("a", {"name": "local", "options": {}})),
        transports={"local": Recorder("local")},
        plan_id="p",
        root=str(tmp_path),
    )
    moved = run_plan(
        document(("a", {"name": "lsf-direct", "options": {"queue": "big"}})),
        transports={"lsf-direct": Recorder("lsf-direct")},
        plan_id="p",
        root=str(tmp_path),
    )

    assert first.outcomes[0].input_digest == moved.outcomes[0].input_digest
    assert moved.outcomes[0].reused, "moving work must not rerun it"
