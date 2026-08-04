"""One file authors a study and runs it.

What these hold is the seam that used to be hand-written: that the bodies which
run are the ones the Plan names, that a declared output lands where the
operation said it would, and that nothing is spent before `submit`.
"""

from pathlib import Path

import pytest

from ass import (
    Site,
    address,
    artifact,
    codec,
    file,
    flow,
    input_artifact,
    local,
    materialization,
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


FIXTURE_MATERIALIZATION = materialization(
    codec=codec("utf-8-text"),
    address_space="fixtures",
    access_scope="test-scope",
)


@operation(inputs={"given": TEXT}, outputs={"size": returned(kind="count")})
def measure_source(given) -> int:
    """A body whose input is a file this study did not create."""

    return len(Path(given).read_text())


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
    # Named from this module, whatever pytest imported it as.
    definitions = {
        item["identity"]["name"]: item for item in document["operations"]
    }
    name = f"{write_note.identity.name}"
    implementation = definitions[name]["implementation"]

    assert name.endswith(".write_note"), name
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


def _reads_a_source():
    with plan(default_policy=local()) as draft:
        given = input_artifact(
            address("fixtures", "given.txt"),
            artifact=TEXT,
            materialized_as=FIXTURE_MATERIALIZATION,
        )
        outputs = {"size": measure_source.options(key="read")(given).size}
    return draft.finish(outputs=outputs)


@pytest.fixture
def fixtures(tmp_path):
    directory = tmp_path / "fixtures"
    directory.mkdir()
    (directory / "given.txt").write_text("abcde")
    return directory


@pytest.fixture
def reading_site(tmp_path, fixtures):
    return Site(
        root=str(tmp_path / "attempts"),
        workspace_root=str(tmp_path / "work"),
        address_spaces={"fixtures": str(fixtures)},
    )


def test_a_declared_source_reaches_the_body_that_asked_for_it(reading_site):
    """A study may start from a file it did not write.

    Every real study does: a netlist, a model card, a corner file someone else
    owns. Until sources were seeded this body was handed None, and the only way
    to read an external file was to write its path into a second file by hand.
    """

    run = study(_reads_a_source()).submit(site=reading_site)

    assert run.succeeded, run.summary()
    assert run["read"].value == 5


def test_editing_a_source_reruns_the_work_that_read_it(reading_site, fixtures):
    """Delivery and staleness read the same file, so they cannot disagree."""

    first = study(_reads_a_source()).submit(site=reading_site)
    assert first["read"].value == 5

    (fixtures / "given.txt").write_text("abcdefgh")
    again = study(_reads_a_source()).submit(site=reading_site)

    assert not again.report.outcomes[0].reused, again.summary()
    assert again["read"].value == 8


def test_an_unedited_source_reuses_what_read_it(reading_site):
    study(_reads_a_source()).submit(site=reading_site)
    again = study(_reads_a_source()).submit(site=reading_site)

    assert all(item.reused for item in again.report.outcomes), again.summary()


def test_a_command_renders_as_something_an_operator_can_read():
    assert str(shell("ngspice", "-b", Path("/tmp/x.cir"))) == "ngspice -b /tmp/x.cir"
    assert isinstance(shell("true"), Shell)
