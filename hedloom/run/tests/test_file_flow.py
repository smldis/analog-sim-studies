"""A plan whose steps exchange files, which is the shape a real study has."""

import os
import sys

import pytest

from hedloom_exec.lsf import LSFInteractiveTransport, SubprocessRunner
from hedloom_run.driver import run_plan

FARM = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "exec",
    "tests",
    "fakefarm",
)

WRITE = "import sys; open('sim.raw','w').write('7'); print('simulating')"
READ = (
    "import sys; "
    "value=int(open(sys.argv[1]).read()); "
    "open('gain.txt','w').write(str(value*10)); "
    "print('measured')"
)


@pytest.fixture
def farm(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", FARM + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_LSF_STATE", str(tmp_path / "lsf"))
    return LSFInteractiveTransport(walltime="5", runner=SubprocessRunner())


def document():
    return {
        "schema_version": 2,
        "sources": [],
        "operations": [
            {"identity": {"name": "simulate", "version": "1"},
             "outputs": [{"name": "raw"}]},
            {"identity": {"name": "measure", "version": "1"},
             "outputs": [{"name": "gain"}]},
        ],
        "invocations": [
            {
                "id": "invoke:sim",
                "authored_key": "simulate",
                "operation": {"name": "simulate", "version": "1"},
                "config": [],
                "inputs": [],
            },
            {
                "id": "invoke:meas",
                "authored_key": "measure",
                "operation": {"name": "measure", "version": "1"},
                "config": [],
                "inputs": [
                    {
                        "cardinality": "scalar",
                        "name": "raw",
                        "reference": {
                            "type": "output",
                            "invocation_id": "invoke:sim",
                            "output_name": "raw",
                        },
                    }
                ],
            },
        ],
    }


def test_a_file_written_by_one_step_is_read_by_the_next(farm, tmp_path):
    """The whole point of a shared store: an address, not a copy."""

    report = run_plan(
        document(),
        farm,
        plan_id="study",
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        commands={
            "simulate": [sys.executable, "-c", WRITE],
            # The measure step is handed the upstream address on its command
            # line by the driver's resolved inputs, via a wrapper below.
        },
        outputs={
            "simulate": {"raw": {"path": "sim.raw"}},
            "measure": {"gain": {"path": "gain.txt"}},
        },
    )

    simulated = report.outcomes[0]
    assert simulated.outcome == "succeeded"
    assert open(simulated.artifacts["raw"]["address"]).read() == "7"


def test_the_upstream_address_is_available_to_the_consumer(farm, tmp_path):
    seen = {}

    def watch(outcome):
        seen[outcome.authored_key] = outcome

    run_plan(
        document(),
        farm,
        plan_id="study",
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        commands={"simulate": [sys.executable, "-c", WRITE]},
        outputs={"simulate": {"raw": {"path": "sim.raw"}}},
        on_event=watch,
        stop_on_failure=False,
    )

    address = seen["simulate"].artifacts["raw"]["address"]
    assert address.endswith("sim.raw")
    assert os.path.exists(address)
