import pytest

from ass_exec.identity import IdentityError, attempt_identity


def test_identity_is_a_pure_function_of_planning_facts():
    first = attempt_identity(plan_id="plan-1", invocation_id="inv-a", sequence=0)
    second = attempt_identity(plan_id="plan-1", invocation_id="inv-a", sequence=0)
    assert first == second
    assert first.rendered == second.rendered


def test_distinct_invocations_and_sequences_render_distinct_identities():
    base = attempt_identity(plan_id="plan-1", invocation_id="inv-a")
    other_invocation = attempt_identity(plan_id="plan-1", invocation_id="inv-b")
    retry = attempt_identity(plan_id="plan-1", invocation_id="inv-a", sequence=1)
    other_plan = attempt_identity(plan_id="plan-2", invocation_id="inv-a")
    rendered = {
        base.rendered,
        other_invocation.rendered,
        retry.rendered,
        other_plan.rendered,
    }
    assert len(rendered) == 4


def test_rendered_form_survives_use_as_job_name_and_directory():
    identity = attempt_identity(plan_id="plan-1", invocation_id="inv-a")
    assert identity.rendered.startswith("ass-")
    assert identity.rendered.replace("-", "").isalnum()
    assert len(identity.rendered) <= 60


@pytest.mark.parametrize(
    "kwargs",
    [
        {"plan_id": "", "invocation_id": "inv"},
        {"plan_id": "plan 1", "invocation_id": "inv"},
        {"plan_id": "plan", "invocation_id": "inv/a"},
        {"plan_id": "plan", "invocation_id": "inv", "sequence": -1},
        {"plan_id": "plan", "invocation_id": "inv", "sequence": True},
    ],
)
def test_unusable_components_are_refused(kwargs):
    with pytest.raises(IdentityError):
        attempt_identity(**kwargs)
