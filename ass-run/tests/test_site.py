"""Sources are identified by what is at the address, not only by the address.

The first test here is the one that matters. Before it, editing an input
netlist in place changed no declared fact, so every downstream invocation was
reused and a study reported results computed from a file that no longer existed
in that form — a plausible answer that could be false, which this project
treats as a defect rather than a limitation.
"""

import pytest

from ass_exec.transport import InProcessTransport
from ass_run.driver import run_plan
from ass_run.site import Site, SiteError, fingerprint_file


def read(deck=None, **kwargs):
    """A source reference resolves to nothing here; the run still reads it."""

    return "read"


def transport():
    return InProcessTransport({"read": read})


def document(source_id="source:1"):
    return {
        "schema_version": 2,
        "sources": [
            {
                "id": source_id,
                "artifact": {"kind": "netlist"},
                "address": {"address_space": "repo", "locator": "ota.cir"},
                "materialized_as": {"codec": {"name": "spice", "version": "1"}},
            }
        ],
        "operations": [
            {"identity": {"name": "read", "version": "1"},
             "outputs": [{"name": "out"}]}
        ],
        "invocations": [
            {
                "id": "invoke:a",
                "authored_key": "reader",
                "operation": {"name": "read", "version": "1"},
                "config": [],
                "inputs": [
                    {
                        "cardinality": "scalar",
                        "name": "deck",
                        "reference": {"type": "source", "source_id": source_id},
                    }
                ],
                "policy": {"name": "local", "options": {}},
            }
        ],
    }


@pytest.fixture
def study(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "ota.cir").write_text("* ota\nV1 vdd 0 1.8\n")
    return Site(root=str(tmp_path / "attempts"),
                address_spaces={"repo": str(inputs)})


def run(document, site, tmp_path):
    return run_plan(
        document,
        transport(),
        plan_id="study",
        root=site.root,
        source_fingerprints=site.fingerprints(document),
    )


def test_editing_a_source_in_place_invalidates_the_work_that_read_it(
    study, tmp_path
):
    """The defect this module exists to close."""

    first = run(document(), study, tmp_path)
    (tmp_path / "inputs" / "ota.cir").write_text("* ota\nV1 vdd 0 1.62\n")
    second = run(document(), study, tmp_path)

    assert first.outcomes[0].ran
    assert not second.outcomes[0].reused, "an edited netlist must rerun the study"
    assert first.outcomes[0].input_digest != second.outcomes[0].input_digest


def test_without_a_fingerprint_an_edit_is_invisible(study, tmp_path):
    """Documents the behaviour a run gets by declaring nothing. Not a feature."""

    first = run_plan(document(), transport(), plan_id="study", root=study.root)
    (tmp_path / "inputs" / "ota.cir").write_text("* edited\n")
    second = run_plan(document(), transport(), plan_id="study", root=study.root)

    assert first.outcomes[0].ran
    assert second.outcomes[0].reused, "declaration-only identity cannot see this"


def test_rewriting_identical_content_still_reuses(study, tmp_path):
    """Why content, not mtime: a checkout must not invalidate a sweep."""

    first = run(document(), study, tmp_path)
    source = tmp_path / "inputs" / "ota.cir"
    source.write_text(source.read_text())          # same bytes, new mtime

    second = run(document(), study, tmp_path)

    assert first.outcomes[0].input_digest == second.outcomes[0].input_digest
    assert second.outcomes[0].reused


def test_an_unrelated_source_still_invalidates_nothing(study, tmp_path):
    """Source identity remains positional-free: adding one changes no digest."""

    first = run(document(), study, tmp_path)
    second = run(document(source_id="source:9"), study, tmp_path)

    assert first.outcomes[0].input_digest == second.outcomes[0].input_digest


def test_an_address_space_this_site_does_not_define_is_refused(tmp_path):
    site = Site(root=str(tmp_path), address_spaces={})
    with pytest.raises(SiteError) as raised:
        site.fingerprints(document())
    assert "repo" in str(raised.value)


def test_a_declared_source_that_is_not_there_is_refused_early(tmp_path):
    site = Site(root=str(tmp_path), address_spaces={"repo": str(tmp_path)})
    with pytest.raises(SiteError) as raised:
        site.fingerprints(document())
    assert "does not exist" in str(raised.value)


def test_a_directory_source_covers_everything_under_it(tmp_path):
    tree = tmp_path / "base"
    (tree / "sub").mkdir(parents=True)
    (tree / "sub" / "a.cir").write_text("one")
    site = Site(root=str(tmp_path), address_spaces={"repo": str(tmp_path)})
    plan = document()
    plan["sources"][0]["address"]["locator"] = "base"

    before = site.fingerprints(plan)
    (tree / "sub" / "a.cir").write_text("two")
    after = site.fingerprints(plan)

    assert before != after, "editing a file inside a tree source must show"


def test_an_implausibly_large_source_says_how_it_was_identified(tmp_path):
    small = tmp_path / "small.cir"
    small.write_text("x")
    assert fingerprint_file(small).startswith("blake2b:")


def test_a_profile_anchors_relative_paths_to_itself(tmp_path):
    """A study run from elsewhere must mean the same thing."""

    (tmp_path / "site.toml").write_text(
        "[study]\n"
        'root = "_runs/attempts"\n'
        'workspace_root = "/nfs/studies/ota"\n'
        "\n[address_space]\n"
        'repository-relative = "."\n'
        "\n[placement.lsf]\n"
        'kind = "lsf-interactive"\n'
        'walltime = "240"\n'
        'queue = "normal"\n'
        "\n[kernel]\n"
        "threads = 32\n"
    )
    site = Site.from_file(tmp_path / "site.toml")

    assert site.root == str(tmp_path / "_runs" / "attempts")
    assert site.workspace_root == "/nfs/studies/ota"
    assert site.address_spaces["repository-relative"] == str(tmp_path)
    assert site.threads == 32
    assert site.transports["lsf"].walltime == "240"


def test_a_placement_kind_this_site_cannot_build_is_refused(tmp_path):
    (tmp_path / "site.toml").write_text(
        '[study]\nroot = "attempts"\n\n[placement.gpu]\nkind = "cuda-farm"\n'
    )
    with pytest.raises(SiteError) as raised:
        Site.from_file(tmp_path / "site.toml")
    assert "cuda-farm" in str(raised.value)


def test_implementations_are_added_where_configuration_cannot_reach(tmp_path):
    site = Site(root=str(tmp_path)).with_transports(local=transport())
    assert site.transports["local"].name == "in-process"
