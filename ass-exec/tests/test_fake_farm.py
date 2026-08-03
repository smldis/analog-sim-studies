"""End-to-end submission through the real subprocess layer.

These tests use a fake `bsub`/`bjobs`/`bkill` on PATH rather than the injected
runner, so everything below the transport is genuine: argument construction,
child binding, exit-status propagation, and output capture. What remains
unreproducible is LSF's own scheduling and its interactive lifetime guarantee.
"""

import os
import sys

import pytest

from ass_exec.attempt import launch_or_attach, reconcile
from ass_exec.durability import Durability, execute
from ass_exec.journal import AttemptJournal
from ass_exec.lsf import LSFInteractiveTransport

FARM = os.path.join(os.path.dirname(__file__), "fakefarm")

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="the fake farm uses executable scripts"
)


@pytest.fixture
def farm(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", FARM + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_LSF_STATE", str(tmp_path / "farm"))
    return LSFInteractiveTransport(walltime="5", queue="normal")


def test_a_real_submission_runs_the_command_and_records_success(farm, tmp_path):
    journal = AttemptJournal(tmp_path, "ass-farm-ok")
    bundle = {"command": [sys.executable, "-c", "print('simulated')"]}

    launch_or_attach(journal, farm, bundle)
    state = reconcile(journal, farm)

    assert state.outcome == "succeeded"
    assert "simulated" in journal.read_manifest()["result"]["stdout"]


def test_a_failing_command_propagates_its_exit_status(farm, tmp_path):
    journal = AttemptJournal(tmp_path, "ass-farm-fail")
    bundle = {"command": [sys.executable, "-c", "raise SystemExit(3)"]}

    launch_or_attach(journal, farm, bundle)
    state = reconcile(journal, farm)

    assert state.outcome == "failed"
    assert journal.read_manifest()["result"]["returncode"] == 3


def test_the_submission_reaches_bsub_with_its_declared_shape(farm, tmp_path):
    import json

    journal = AttemptJournal(tmp_path, "ass-farm-shape")
    execute(
        farm,
        {"command": [sys.executable, "-c", "pass"]},
        durability=Durability.RECORDED,
        identity="ass-farm-shape",
        root=str(tmp_path),
    )

    recorded = json.loads(
        (tmp_path / "farm" / "ass-farm-shape.json").read_text()
    )
    assert recorded["options"]["-J"] == "ass-farm-shape"
    assert recorded["options"]["-W"] == "5"
    assert recorded["options"]["-q"] == "normal"


def test_discovery_and_cancellation_reach_the_real_commands(farm, tmp_path):
    execute(
        farm,
        {"command": [sys.executable, "-c", "pass"]},
        durability=Durability.RECORDED,
        identity="ass-farm-live",
        root=str(tmp_path),
    )

    assert farm.discover("ass-farm-live") is not None
    farm.cancel({"identity": "ass-farm-live"})
    assert farm.discover("ass-farm-live") is None


def test_an_unknown_job_name_is_not_discovered(farm):
    assert farm.discover("ass-never-submitted") is None
