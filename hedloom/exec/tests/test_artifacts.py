"""File outputs on a shared store: record the address, never move the bytes.

The invariant: an operation's declared outputs exist after a successful run,
and a downstream invocation resolves them to the same paths.
"""

import sys

import pytest

from hedloom_exec.artifacts import MissingOutput, OutputDeclarationError, capture_outputs
from hedloom_exec.durability import Durability, execute
from hedloom_exec.lsf import LSFInteractiveTransport, SubprocessRunner
from hedloom_exec.transport import InProcessTransport

WRITES_A_FILE = [
    sys.executable,
    "-c",
    "open('sim.raw','w').write('waveform'); print('progress: done')",
]


def farm(tmp_path, monkeypatch):
    import os

    fake = os.path.join(os.path.dirname(__file__), "fakefarm")
    monkeypatch.setenv("PATH", fake + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_LSF_STATE", str(tmp_path / "lsf"))
    return LSFInteractiveTransport(walltime="5", runner=SubprocessRunner())


def test_a_file_the_command_wrote_itself_is_recorded(tmp_path, monkeypatch):
    transport = farm(tmp_path, monkeypatch)
    result = execute(
        transport,
        {"command": WRITES_A_FILE, "outputs": {"raw": {"path": "sim.raw"}}},
        durability=Durability.RECORDED,
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        plan_id="p",
        invocation_id="corner-tt",
    )

    assert result.outcome == "succeeded"
    address = result.address("raw")
    assert address is not None
    assert open(address).read() == "waveform"
    assert result.artifacts["raw"]["size"] == len("waveform")


def test_stdout_is_diagnostics_not_the_result(tmp_path, monkeypatch):
    """A command that prints progress while writing its real answer to disk."""

    transport = farm(tmp_path, monkeypatch)
    result = execute(
        transport,
        {"command": WRITES_A_FILE, "outputs": {"raw": {"path": "sim.raw"}}},
        durability=Durability.RECORDED,
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        plan_id="p",
        invocation_id="corner-tt",
    )

    assert set(result.artifacts) == {"raw"}
    workdir = tmp_path / "work" / result.journal.identity
    assert "progress: done" in (workdir / "stdout.log").read_text()


def test_a_command_may_declare_stdout_as_its_output(tmp_path, monkeypatch):
    transport = farm(tmp_path, monkeypatch)
    result = execute(
        transport,
        {
            "command": [sys.executable, "-c", "print('42')"],
            "outputs": {"answer": {"stream": "stdout"}},
        },
        durability=Durability.RECORDED,
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        plan_id="p",
        invocation_id="i",
    )

    assert result.artifacts["answer"]["value"].strip() == "42"


def test_a_promised_output_that_never_appears_fails_the_invocation(
    tmp_path, monkeypatch
):
    transport = farm(tmp_path, monkeypatch)
    result = execute(
        transport,
        {
            "command": [sys.executable, "-c", "print('done')"],
            "outputs": {"raw": {"path": "sim.raw"}},
        },
        durability=Durability.RECORDED,
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        plan_id="p",
        invocation_id="i",
    )

    assert result.outcome == "failed"
    assert "was not produced" in result.detail["error"]


def test_each_attempt_gets_its_own_workspace(tmp_path, monkeypatch):
    """A rerun must not write over the evidence of the previous attempt."""

    transport = farm(tmp_path, monkeypatch)
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path / "attempts"),
        "workspace_root": str(tmp_path / "work"),
        "plan_id": "p",
        "invocation_id": "i",
    }
    missing = {
        "command": [sys.executable, "-c", "pass"],
        "outputs": {"raw": {"path": "sim.raw"}},
    }
    first = execute(transport, missing, **common)
    second = execute(transport, missing, **common)

    assert first.outcome == "failed" and second.outcome == "failed"
    assert first.journal.identity != second.journal.identity
    assert len(list((tmp_path / "work").iterdir())) == 2


def test_an_unrelated_file_in_the_workspace_is_not_promoted(tmp_path, monkeypatch):
    """Only what was declared is recorded; the rest stays as unnamed evidence."""

    transport = farm(tmp_path, monkeypatch)
    result = execute(
        transport,
        {
            "command": [
                sys.executable,
                "-c",
                "open('sim.raw','w').write('x'); open('scratch.tmp','w').write('y')",
            ],
            "outputs": {"raw": {"path": "sim.raw"}},
        },
        durability=Durability.RECORDED,
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        plan_id="p",
        invocation_id="i",
    )

    assert set(result.artifacts) == {"raw"}
    workdir = tmp_path / "work" / result.journal.identity
    assert (workdir / "scratch.tmp").exists()


def test_downstream_resolves_the_recorded_address(tmp_path, monkeypatch):
    """The point of a shared store: the next step opens the same path."""

    transport = farm(tmp_path, monkeypatch)
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path / "attempts"),
        "workspace_root": str(tmp_path / "work"),
        "plan_id": "p",
    }
    produced = execute(
        transport,
        {"command": WRITES_A_FILE, "outputs": {"raw": {"path": "sim.raw"}}},
        invocation_id="simulate",
        **common,
    )

    consumer = InProcessTransport({"measure": lambda deck: open(deck).read().upper()})
    measured = execute(
        consumer,
        {
            "operation": "measure",
            "inputs": {"deck": produced.artifacts["raw"]["address"]},
            "resolved_inputs": {"deck": produced.address("raw")},
        },
        invocation_id="measure",
        **common,
    )

    assert measured.value == "WAVEFORM"


def test_capturing_a_different_file_is_a_different_result():
    from hedloom_exec.reuse import input_digest

    base = {"command": ["sim"], "outputs": {"raw": {"path": "a.raw"}}}
    other = {"command": ["sim"], "outputs": {"raw": {"path": "b.raw"}}}
    assert input_digest(base) != input_digest(other)


def test_an_output_escaping_its_workspace_is_refused(tmp_path):
    with pytest.raises(OutputDeclarationError, match="outside its working directory"):
        capture_outputs(
            {"raw": {"path": "../elsewhere.raw"}}, workdir=tmp_path
        )


def test_an_unknown_declaration_kind_is_refused(tmp_path):
    with pytest.raises(OutputDeclarationError, match="declares none of"):
        capture_outputs({"raw": {"somehow": True}}, workdir=tmp_path)


def test_a_missing_file_is_reported_as_missing(tmp_path):
    with pytest.raises(MissingOutput):
        capture_outputs({"raw": {"path": "nope.raw"}}, workdir=tmp_path)
