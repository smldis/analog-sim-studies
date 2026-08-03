"""Reuse must mean "already done with these inputs", or it is a lie."""

import pytest

from ass_exec.durability import Durability, execute
from ass_exec.identity import attempt_identity
from ass_exec.reuse import (
    attempts_for,
    describe_staleness,
    input_digest,
    scan_attempts,
    stale_attempts,
)
from ass_exec.transport import InProcessTransport

BUNDLE = {
    "operation": "simulate",
    "command": ["ngspice", "-b", "tt.spice"],
    "inputs": {"deck": "sha256:aaa"},
}


def transport(runs=None):
    def simulate(**kwargs):
        if runs is not None:
            runs.append(kwargs)
        return "ok"

    return InProcessTransport({"simulate": simulate})


def test_digest_is_stable_across_key_order():
    first = input_digest({"operation": "a", "inputs": {"x": 1, "y": 2}})
    second = input_digest({"inputs": {"y": 2, "x": 1}, "operation": "a"})
    assert first == second


def test_changed_inputs_change_the_digest():
    changed = dict(BUNDLE, inputs={"deck": "sha256:bbb"})
    assert input_digest(BUNDLE) != input_digest(changed)


def test_placement_does_not_participate_in_identity():
    """Changing where work runs must not invalidate what it produced."""

    relocated = dict(BUNDLE, queue="bigmem", walltime="120", cores=16, env={"X": "1"})
    assert input_digest(relocated) == input_digest(BUNDLE)


def test_nominated_environment_does_participate():
    with_pdk = dict(BUNDLE, identity_env={"PDK_ROOT": "/pdk/sky130A"})
    other_pdk = dict(BUNDLE, identity_env={"PDK_ROOT": "/pdk/gf180"})
    assert input_digest(with_pdk) != input_digest(other_pdk)
    assert input_digest(with_pdk) != input_digest(BUNDLE)


def test_unserializable_inputs_are_refused_with_an_explanation():
    with pytest.raises(ValueError, match="JSON-serializable"):
        input_digest({"operation": "a", "inputs": {"handle": object()}})


def test_identity_is_content_addressed_when_a_digest_is_given():
    base = attempt_identity(plan_id="p", invocation_id="i")
    with_inputs = attempt_identity(plan_id="p", invocation_id="i", input_digest="abc")
    other_inputs = attempt_identity(plan_id="p", invocation_id="i", input_digest="def")

    assert base.rendered != with_inputs.rendered != other_inputs.rendered
    assert with_inputs.input_digest == "abc"


def test_unchanged_inputs_reuse_the_published_result(tmp_path):
    runs = []
    shared = transport(runs)
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path),
        "plan_id": "plan-1",
        "invocation_id": "inv-a",
    }

    first = execute(shared, BUNDLE, **common)
    second = execute(shared, BUNDLE, **common)

    assert first.disposition == "claimed"
    assert second.disposition == "completed"
    assert len(runs) == 1


def test_changed_inputs_do_not_reuse_the_old_result(tmp_path):
    """The defect this module exists to remove."""

    runs = []
    shared = transport(runs)
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path),
        "plan_id": "plan-1",
        "invocation_id": "inv-a",
    }

    execute(shared, BUNDLE, **common)
    changed = dict(BUNDLE, inputs={"deck": "sha256:bbb"})
    second = execute(shared, changed, **common)

    assert second.disposition == "claimed"
    assert len(runs) == 2
    assert len(scan_attempts(tmp_path)) == 2


def test_prior_results_are_named_as_superseded_not_discarded(tmp_path):
    common = {
        "durability": Durability.RECORDED,
        "root": str(tmp_path),
        "plan_id": "plan-1",
        "invocation_id": "inv-a",
    }
    execute(transport(), BUNDLE, **common)
    changed = dict(BUNDLE, inputs={"deck": "sha256:bbb"})
    execute(transport(), changed, **common)

    stale = stale_attempts(
        tmp_path,
        plan_id="plan-1",
        invocation_id="inv-a",
        current_digest=input_digest(changed),
    )

    assert len(stale) == 1
    assert stale[0].input_digest == input_digest(BUNDLE)
    assert stale[0].outcome == "succeeded"
    assert "succeeded" in describe_staleness(stale)


def test_attempts_are_attributable_to_their_invocation(tmp_path):
    common = {"durability": Durability.RECORDED, "root": str(tmp_path)}
    execute(transport(), BUNDLE, plan_id="plan-1", invocation_id="inv-a", **common)
    execute(transport(), BUNDLE, plan_id="plan-1", invocation_id="inv-b", **common)

    assert len(attempts_for(tmp_path, plan_id="plan-1", invocation_id="inv-a")) == 1
    assert len(scan_attempts(tmp_path)) == 2


def test_scanning_an_absent_root_is_empty_not_an_error(tmp_path):
    assert scan_attempts(tmp_path / "nothing-here") == ()


def test_recorded_execution_still_requires_enough_to_identify_itself(tmp_path):
    with pytest.raises(ValueError, match="plan_id and invocation_id"):
        execute(
            transport(), BUNDLE, durability=Durability.RECORDED, root=str(tmp_path)
        )
