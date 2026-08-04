"""Bundle derivation from a Plan document, and transitive staleness.

The invariant under test: an invocation's digest changes exactly when its own
declaration or any ancestor's declaration changes.
"""


import pytest

from ass_exec.planned import PlanDerivationError, plan_bundles, source_references

SOURCE = {
    "id": "source:0001",
    "artifact": {"kind": "design"},
    "address": {"address_space": "repository-relative", "locator": "opamp.json"},
    "materialized_as": {"codec": {"name": "json", "version": "1"}},
}


def corner(key, temperature, name="sim"):
    return {
        "id": f"invoke:{key}",
        "authored_key": key,
        "operation": {"name": name, "version": "1"},
        "config": [{"name": "corner", "value": key}, {"name": "t", "value": temperature}],
        "inputs": [
            {
                "cardinality": "scalar",
                "name": "design",
                "reference": {"type": "source", "source_id": "source:0001"},
            }
        ],
    }


def summary(members):
    return {
        "id": "invoke:summary",
        "authored_key": "summary",
        "operation": {"name": "summarize", "version": "1"},
        "config": [],
        "inputs": [
            {
                "cardinality": "collection",
                "name": "measurements",
                "references": [
                    {
                        "type": "output",
                        "invocation_id": f"invoke:{member}",
                        "output_name": "metrics",
                    }
                    for member in members
                ],
            }
        ],
    }


def document():
    return {
        "schema_version": 2,
        "sources": [SOURCE],
        "invocations": [corner("tt", 27), corner("ss", 125), summary(["tt", "ss"])],
    }


def digests(doc, **kwargs):
    return {item.authored_key: item.input_digest for item in plan_bundles(doc, **kwargs)}


def test_derivation_is_deterministic():
    assert digests(document()) == digests(document())


def test_producers_are_ordered_before_consumers():
    doc = document()
    doc["invocations"] = list(reversed(doc["invocations"]))
    order = [item.authored_key for item in plan_bundles(doc)]
    assert order.index("summary") == 2


def test_a_source_is_named_the_way_an_input_binding_names_it():
    """The agreement that makes a declared source deliverable.

    A run hands a body its external file by putting the located path in the
    map under the string an input binding carries. If this named it any other
    way the map would be looked up and miss, and the body would be called with
    nothing — which is exactly what happened before runs seeded sources.
    """

    fingerprints = {"source:0001": "blake2b:abc"}
    bound = {
        item.bundle["inputs"]["design"]
        for item in plan_bundles(document(), source_fingerprints=fingerprints)
        if "design" in item.bundle["inputs"]
    }

    assert bound, "the fixture must bind a source somewhere"
    assert bound == set(source_references(document(), fingerprints))


def test_a_source_named_with_a_different_fingerprint_is_a_different_source():
    """Why the fingerprint is required rather than optional.

    It is part of the digest, so naming a source with one mapping while the
    run derived bundles with another produces strings nothing looks up — a
    miss that would look exactly like having no sources at all.
    """

    named = set(source_references(document(), {"source:0001": "blake2b:abc"}))

    assert named != set(source_references(document(), {"source:0001": "blake2b:def"}))
    assert named != set(source_references(document()))


def test_a_changed_config_invalidates_only_its_own_branch_and_downstream():
    before = digests(document())
    doc = document()
    doc["invocations"][1]["config"][1]["value"] = 150  # ss temperature
    after = digests(doc)

    assert after["ss"] != before["ss"], "the edited invocation must change"
    assert after["tt"] == before["tt"], "an unrelated sibling must not change"
    assert after["summary"] != before["summary"], "downstream must change"


def test_a_changed_source_invalidates_everything_downstream():
    before = digests(document())
    doc = document()
    doc["sources"][0]["address"]["locator"] = "opamp-v2.json"
    after = digests(doc)

    assert after["tt"] != before["tt"]
    assert after["ss"] != before["ss"]
    assert after["summary"] != before["summary"]


def test_an_operation_version_bump_invalidates_results():
    before = digests(document())
    doc = document()
    doc["invocations"][0]["operation"]["version"] = "2"
    after = digests(doc)

    assert after["tt"] != before["tt"]
    assert after["ss"] == before["ss"]


def test_collection_member_order_is_part_of_identity():
    before = digests(document())
    doc = document()
    doc["invocations"][2] = summary(["ss", "tt"])
    assert digests(doc)["summary"] != before["summary"]


def test_an_unrelated_added_source_does_not_invalidate_anything():
    """Source IDs are authored-order; identity must come from the declaration."""

    before = digests(document())
    doc = document()
    doc["sources"].insert(
        0,
        {
            "id": "source:0000",
            "artifact": {"kind": "other"},
            "address": {"address_space": "repository-relative", "locator": "x.json"},
            "materialized_as": {},
        },
    )
    assert digests(doc) == before


def test_nominated_environment_participates():
    plain = digests(document())
    with_pdk = digests(document(), identity_env={"PDK_ROOT": "/pdk/sky130A"})
    assert with_pdk["tt"] != plain["tt"]


def test_commands_are_attached_for_external_operations():
    planned = plan_bundles(document(), commands={"sim": ["ngspice", "-b"]})
    by_key = {item.authored_key: item for item in planned}

    assert by_key["tt"].bundle["command"] == ["ngspice", "-b"]
    assert "command" not in by_key["summary"].bundle


def test_dependencies_are_reported():
    planned = {item.authored_key: item for item in plan_bundles(document())}
    assert set(planned["summary"].depends_on) == {"invoke:tt", "invoke:ss"}
    assert planned["tt"].depends_on == ()


def test_an_unsupported_schema_is_refused():
    doc = document()
    doc["schema_version"] = 99
    with pytest.raises(PlanDerivationError, match="unsupported Plan schema"):
        plan_bundles(doc)


def test_a_dangling_dependency_is_refused():
    doc = document()
    doc["invocations"][2] = summary(["tt", "missing"])
    with pytest.raises(PlanDerivationError, match="cycle or dangling"):
        plan_bundles(doc)


def test_an_unknown_source_is_refused():
    doc = document()
    doc["invocations"][0]["inputs"][0]["reference"]["source_id"] = "source:9999"
    with pytest.raises(PlanDerivationError, match="unknown source"):
        plan_bundles(doc)


def test_the_real_ass_flow_example_plan_derives(tmp_path):
    """Against a Plan produced by ASS Flow itself, not a hand-written fixture."""

    import json
    import os
    import subprocess
    import sys

    flow = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "ass-flow",
    )
    if not os.path.isdir(flow):
        pytest.skip("ass-flow is not a sibling of this unit")

    environment = dict(os.environ, PYTHONPATH=os.path.join(flow, "src"))
    completed = subprocess.run(
        [sys.executable, os.path.join(flow, "examples", "characterization.py")],
        capture_output=True,
        text=True,
        env=environment,
        cwd=flow,
    )
    assert completed.returncode == 0, completed.stderr

    planned = plan_bundles(json.loads(completed.stdout))
    assert len(planned) == 4
    assert len({item.input_digest for item in planned}) == 4

    # The reduction must depend on all three corners it fans in.
    reduction = [item for item in planned if len(item.depends_on) == 3]
    assert len(reduction) == 1


def test_the_end_to_end_example_reuses_and_supersedes():
    """The example is the slice; keep it runnable."""

    import os
    import subprocess
    import sys

    unit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    flow = os.path.join(os.path.dirname(unit), "ass-flow", "src")
    if not os.path.isdir(flow):
        pytest.skip("ass-flow is not a sibling of this unit")

    completed = subprocess.run(
        [sys.executable, os.path.join(unit, "examples", "planned_characterization.py")],
        capture_output=True,
        text=True,
        cwd=unit,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join([os.path.join(unit, "src"), flow])),
    )
    assert completed.returncode == 0, completed.stderr
    output = completed.stdout

    first, second, third = output.split("run —")[1:4]
    assert first.count("ran    ") == 4 and "reused" not in first
    assert second.count("reused") == 4 and "ran    " not in second
    # The edited corner and the reduction downstream of it, and nothing else.
    assert third.count("ran    ") == 2 and third.count("reused") == 2
    assert "superseded but retained" in output
