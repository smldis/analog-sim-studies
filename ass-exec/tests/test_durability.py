"""Durability is declared, and the cheap level really is cheap."""

from ass_exec.durability import Durability, ExecutionResult, execute
from ass_exec.identity import attempt_identity
from ass_exec.transport import InProcessTransport

BUNDLE = {"operation": "double", "arguments": {"value": 21}}


def transport(runs=None):
    def double(value):
        if runs is not None:
            runs.append(value)
        return value * 2

    return InProcessTransport({"double": double})


def test_ephemeral_execution_writes_nothing(tmp_path):
    result = execute(transport(), BUNDLE, durability=Durability.EPHEMERAL)

    assert result.outcome == "succeeded"
    assert result.value == 42
    assert result.journal is None
    assert list(tmp_path.iterdir()) == []


def test_ephemeral_execution_needs_no_identity_or_root():
    result = execute(transport(), BUNDLE)
    assert isinstance(result, ExecutionResult)
    assert result.durability is Durability.EPHEMERAL


def test_recorded_execution_leaves_a_readable_attempt(tmp_path):
    identity = attempt_identity(plan_id="plan-1", invocation_id="inv-a").rendered
    result = execute(
        transport(),
        BUNDLE,
        durability=Durability.RECORDED,
        identity=identity,
        root=str(tmp_path),
    )

    assert result.outcome == "succeeded"
    assert result.value == 42
    assert (tmp_path / identity / "events.jsonl").exists()
    assert (tmp_path / identity / "manifest.json").exists()


def test_recorded_execution_reuses_a_published_result(tmp_path):
    runs = []
    shared = transport(runs)
    identity = attempt_identity(plan_id="plan-1", invocation_id="inv-a").rendered
    common = {
        "durability": Durability.RECORDED,
        "identity": identity,
        "root": str(tmp_path),
    }

    first = execute(shared, BUNDLE, **common)
    second = execute(shared, BUNDLE, **common)

    assert first.disposition == "claimed"
    assert second.disposition == "completed"
    assert second.value == 42
    assert runs == [21]


def test_ephemeral_execution_does_not_reuse_anything(tmp_path):
    runs = []
    shared = transport(runs)
    execute(shared, BUNDLE, durability=Durability.EPHEMERAL)
    execute(shared, BUNDLE, durability=Durability.EPHEMERAL)

    # Nothing was recorded, so nothing can be skipped. That is the trade the
    # cheap level makes, and it is the right one for work that dies with its
    # caller.
    assert runs == [21, 21]
