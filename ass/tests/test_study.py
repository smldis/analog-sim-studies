"""One file authors a study and runs it.

What these hold is the seam that used to be hand-written: that the bodies which
run are the ones the Plan names, that a declared output lands where the
operation said it would, and that nothing is spent before `submit`.
"""

from pathlib import Path

import pytest

from ass import (
    Site,
    artifact,
    file,
    flow,
    local,
    operation,
    parameter,
    plan,
    returned,
    shell,
    study,
    sweep,
)
from ass.binding import BoundTransport, Shell, Workspace
from ass_exec.transport import SubmissionRefused

TEXT = artifact("text-file")
COUNT = artifact("count")


@operation(config={"word": parameter(str)}, outputs={"note": file("note.txt",
                                                                 kind="text-file")})
def write_note(out, *, word: str) -> None:
    out.note.write_text(word * 3)


@operation(inputs={"note": TEXT}, outputs={"size": returned(kind="count")})
def measure(note) -> int:
    return len(Path(note).read_text())


@operation(config={"word": parameter(str)},
           outputs={"copy": file("copy.txt", kind="text-file")})
def copy_via_shell(out, *, word: str):
    return shell("sh", "-c", f"printf %s {word} > {out.copy}")


@flow
def notes(words):
    sizes = []
    for word in sweep(words, key=lambda item: item):
        sizes.append(measure(write_note(word=word)))
    return {"sizes": sizes[-1]}


def build(words=("ab", "cde")):
    with plan(default_policy=local()) as draft:
        outputs = notes.options(key="notes")(words)
    return draft.finish(outputs=outputs)


@pytest.fixture
def site(tmp_path):
    return Site(root=str(tmp_path / "attempts"),
                workspace_root=str(tmp_path / "work"))


def test_the_plan_is_complete_before_anything_is_spent(tmp_path):
    subject = study(build())
    document = subject.document

    assert document["schema_version"] == 3
    assert len(document["invocations"]) == 4
    assert not (tmp_path / "attempts").exists(), "summary must spend nothing"
    assert "write_note" in subject.summary()


def test_the_body_that_runs_is_the_one_the_plan_names(site):
    run = study(build()).submit(site=site)

    assert run.succeeded, run.summary()
    assert run["ab:measure"].value == 6
    assert run["cde:measure"].value == 9


def test_a_declared_file_lands_where_the_operation_said(site):
    run = study(build()).submit(site=site)

    address = run["ab:write_note"].artifacts["note"]["address"]
    assert Path(address).name == "note.txt"
    assert Path(address).read_text() == "ababab"


def test_the_plan_carries_what_implements_each_operation(tmp_path):
    document = study(build()).document
    definitions = {
        item["identity"]["name"]: item for item in document["operations"]
    }
    implementation = definitions["tests.test_study.write_note"]["implementation"]

    assert implementation["entry_point"].endswith(":write_note")
    assert implementation["fingerprint"]


def test_a_second_run_reuses_everything(site):
    study(build()).submit(site=site)
    again = study(build()).submit(site=site)

    assert all(item.reused for item in again.report.outcomes), again.summary()


def test_one_edited_point_reruns_only_its_own_branch(site):
    study(build()).submit(site=site)
    edited = study(build(words=("ab", "xyz"))).submit(site=site)

    outcomes = {item.authored_key: item for item in edited.report.outcomes}
    assert outcomes["ab:write_note"].reused
    assert outcomes["ab:measure"].reused
    assert not outcomes["xyz:write_note"].reused
    assert not outcomes["xyz:measure"].reused


def test_a_sweep_keys_every_call_inside_it(tmp_path):
    keys = {
        item["authored_key"] for item in study(build()).document["invocations"]
    }
    assert {"ab:write_note", "ab:measure", "cde:write_note", "cde:measure"} == keys


def test_a_body_may_ask_for_a_command_to_be_run(site):
    with plan(default_policy=local()) as draft:
        outputs = {"copy": copy_via_shell.options(key="copy")(word="hello").copy}
    run = study(draft.finish(outputs=outputs)).submit(site=site)

    assert run.succeeded, run.summary()
    address = run["copy"].artifacts["copy"]["address"]
    assert Path(address).read_text() == "hello"


def test_an_operation_with_no_bound_body_refuses(tmp_path):
    transport = BoundTransport({})
    with pytest.raises(SubmissionRefused):
        transport.submit("ass-abc", {"operation": "nobody.implements.this"})


def test_a_workspace_offers_only_declared_file_outputs(tmp_path):
    workspace = Workspace(tmp_path, {"raw": {"path": "corner.raw"},
                                     "value": {"value": True}})

    assert workspace.raw == tmp_path / "corner.raw"
    with pytest.raises(AttributeError):
        workspace.value
    with pytest.raises(AttributeError):
        workspace.undeclared


def test_a_command_renders_as_something_an_operator_can_read():
    assert str(shell("ngspice", "-b", Path("/tmp/x.cir"))) == "ngspice -b /tmp/x.cir"
    assert isinstance(shell("true"), Shell)
