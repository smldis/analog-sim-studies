from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import subprocess
import sys

import dask
from dask import delayed
from dask.callbacks import Callback
import pytest

from examples import characterization
from hedloom_flow import (
    OperationDefinition,
    OperationIdentity,
    ResourceContract,
    address,
    artifact,
    artifacts,
    codec,
    input_artifact,
    local,
    materialization,
    named_policy,
    operation,
    parameter,
    plan,
)
from hedloom_flow.experimental.local_dask import (
    DelayedLowering,
    InvocationExecutionError,
    LocalDaskPreflightError,
    lower_delayed,
)


VALUE = artifact("test-value")
RESULT = artifact("test-result")
TEST_MATERIALIZATION = materialization(
    codec=codec("test-value"),
    address_space="injected",
    access_scope="test-process",
)


def _source(locator, contract=VALUE):
    return input_artifact(
        address("injected", locator),
        artifact=contract,
        materialized_as=TEST_MATERIALIZATION,
    )


class StrangeValue:
    pass


def _adversarial_plan():
    @operation(
        name="poison.nonexistent.authoring.split",
        inputs={"source": VALUE},
        config={"settings": parameter(dict)},
        outputs={"left": VALUE, "right": VALUE},
    )
    def authored_split(source, *, settings):
        raise AssertionError("decorated operation bodies must not run")

    @operation(
        name="poison.nonexistent.authoring.scale",
        inputs={"value": VALUE},
        outputs={"scaled": VALUE},
    )
    def authored_scale(value):
        raise AssertionError("decorated operation bodies must not run")

    @operation(
        name="poison.nonexistent.authoring.combine",
        inputs={
            "base": VALUE,
            "scaled": VALUE,
            "ordered": artifacts("test-value"),
        },
        outputs={"summary": RESULT, "strange": RESULT},
    )
    def authored_combine(base, scaled, ordered):
        raise AssertionError("decorated operation bodies must not run")

    @operation(name="poison.nonexistent.authoring.zero", outputs={})
    def authored_zero():
        raise AssertionError("decorated operation bodies must not run")

    @operation(
        name="poison.nonexistent.authoring.orphan",
        outputs={"unused": VALUE},
    )
    def authored_orphan():
        raise AssertionError("decorated operation bodies must not run")

    with plan() as draft:
        primary = _source("primary")
        existing = _source("existing")
        split = authored_split(
            primary,
            settings={"biases": [1, {"delta": 2}]},
        )
        scaled = authored_scale(split.left)
        combined = authored_combine(
            base=existing,
            scaled=scaled,
            ordered=(existing, split.right, scaled),
        )
        authored_zero()
        authored_orphan()
    normalized = draft.finish(
        outputs={
            "summary": combined.summary,
            "summary_alias": combined.summary,
            "strange": combined.strange,
        }
    )
    shuffled = replace(
        normalized,
        operations=tuple(reversed(normalized.operations)),
        sources=tuple(reversed(normalized.sources)),
        invocations=tuple(reversed(normalized.invocations)),
        edges=tuple(reversed(normalized.edges)),
        boundaries=tuple(reversed(normalized.boundaries)),
        outputs=tuple(reversed(normalized.outputs)),
    )
    return shuffled, {
        "split": authored_split.identity,
        "scale": authored_scale.identity,
        "combine": authored_combine.identity,
        "zero": authored_zero.identity,
        "orphan": authored_orphan.identity,
    }


def _implementations(identities, counters=None, configs=None, strange=None):
    if counters is None:
        counters = {}
    if configs is None:
        configs = []
    if strange is None:
        strange = StrangeValue()

    def count(name):
        counters[name] = counters.get(name, 0) + 1

    def split(source, *, settings):
        count("split")
        configs.append(settings)
        assert settings == {"biases": [1, {"delta": 2}]}
        total = sum(source) + settings["biases"][0] + settings["biases"][1]["delta"]
        settings["biases"].append("mutated")
        settings["biases"][1]["delta"] = 999
        return {"left": total, "right": sum(source) * 2}

    def scale(value):
        count("scale")
        return {"scaled": value * 10}

    def combine(*, base, scaled, ordered):
        count("combine")
        assert isinstance(ordered, tuple)
        return {
            "summary": (base, scaled, ordered),
            "strange": strange,
        }

    def zero():
        count("zero")
        return {}

    def orphan():
        count("orphan")
        return {"unused": "retained"}

    return {
        identities["split"]: split,
        identities["scale"]: scale,
        identities["combine"]: combine,
        identities["zero"]: zero,
        identities["orphan"]: orphan,
    }


def _source_values(normalized, *, primary=(2, 3), existing=5):
    by_locator = {source.address.locator: source.id for source in normalized.sources}
    return {
        by_locator["primary"]: primary,
        by_locator["existing"]: existing,
    }


def _single_invocation_plan(*, outputs=("value",)):
    declarations = {name: RESULT for name in outputs}

    @operation(
        name="runtime.single",
        outputs=declarations,
    )
    def refusing_body():
        raise AssertionError("decorated operation body must not run")

    with plan() as draft:
        result = refusing_body()
    named = {} if not outputs else {outputs[0]: result[outputs[0]]}
    return draft.finish(outputs=named), refusing_body.identity


def _compute(*values, optimize_graph=False):
    return dask.compute(
        *values,
        scheduler="synchronous",
        optimize_graph=optimize_graph,
    )


def test_shuffled_graph_lowers_recursively_with_ordered_values_aliases_and_orphans():
    normalized, identities = _adversarial_plan()
    counters = {}
    strange = StrangeValue()
    lowered = lower_delayed(
        normalized,
        operations=_implementations(identities, counters=counters, strange=strange),
        sources=_source_values(normalized, primary=[2, 3]),
    )

    assert isinstance(lowered, DelayedLowering)
    assert set(lowered.invocations) == {item.id for item in normalized.invocations}
    assert set(lowered.outputs) == {"summary", "summary_alias", "strange"}
    assert lowered.outputs["summary"] is lowered.outputs["summary_alias"]
    assert len(set(lowered.invocation_keys.values())) == len(normalized.invocations)
    assert all(
        lowered.invocation_keys[identifier] == task.key
        for identifier, task in lowered.invocations.items()
    )
    assert not any(
        hasattr(lowered, name)
        for name in ("compute", "run", "submit", "cancel", "persist", "publish")
    )
    with pytest.raises(TypeError):
        lowered.outputs["new"] = object()
    with pytest.raises(FrozenInstanceError):
        lowered.outputs = {}

    summary, alias, observed_strange = _compute(
        lowered.outputs["summary"],
        lowered.outputs["summary_alias"],
        lowered.outputs["strange"],
    )
    assert summary == (5, 80, (5, 10, 80))
    assert alias == summary
    assert observed_strange is strange
    assert counters == {"split": 1, "scale": 1, "combine": 1}

    zero_id = next(
        item.id for item in normalized.invocations if item.operation == identities["zero"]
    )
    orphan_id = next(
        item.id
        for item in normalized.invocations
        if item.operation == identities["orphan"]
    )
    assert _compute(
        lowered.invocations[zero_id], lowered.invocations[orphan_id]
    ) == ({}, {"unused": "retained"})
    assert counters["zero"] == 1
    assert counters["orphan"] == 1


def test_empty_named_output_roots_retain_all_invocation_tasks():
    normalized, identities = _adversarial_plan()
    empty_roots = replace(normalized, outputs=())
    counters = {}
    lowered = lower_delayed(
        empty_roots,
        operations=_implementations(identities, counters=counters),
        sources=_source_values(empty_roots),
    )

    assert dict(lowered.outputs) == {}
    _compute(*lowered.invocations.values())
    assert counters == {
        "split": 1,
        "scale": 1,
        "combine": 1,
        "zero": 1,
        "orphan": 1,
    }


def test_one_merged_unoptimized_compute_runs_each_wrapper_once_and_config_is_fresh():
    normalized, identities = _adversarial_plan()
    counters = {}
    configs = []
    lowered = lower_delayed(
        normalized,
        operations=_implementations(identities, counters=counters, configs=configs),
        sources=_source_values(normalized),
    )

    _compute(*lowered.invocations.values(), *lowered.outputs.values())
    assert counters == {
        "split": 1,
        "scale": 1,
        "combine": 1,
        "zero": 1,
        "orphan": 1,
    }
    _compute(lowered.outputs["summary"])
    assert counters["split"] == counters["scale"] == counters["combine"] == 2
    assert len(configs) == 2
    assert configs[0] is not configs[1]
    assert configs[0]["biases"] is not configs[1]["biases"]


def test_two_lowerings_merge_without_keys_or_bound_values_colliding():
    normalized, identities = _adversarial_plan()
    first = lower_delayed(
        normalized,
        operations=_implementations(identities),
        sources=_source_values(normalized, primary=[2, 3], existing=5),
    )

    second_operations = _implementations(identities)
    original_scale = second_operations[identities["scale"]]

    def alternate_scale(value):
        result = original_scale(value)
        return {"scaled": result["scaled"] + 1}

    second_operations[identities["scale"]] = alternate_scale
    second = lower_delayed(
        normalized,
        operations=second_operations,
        sources=_source_values(normalized, primary=[10], existing=7),
    )

    assert set(first.invocation_keys.values()).isdisjoint(
        second.invocation_keys.values()
    )
    first_result, second_result = _compute(
        first.outputs["summary"], second.outputs["summary"]
    )
    assert first_result == (5, 80, (5, 10, 80))
    assert second_result == (7, 131, (7, 20, 131))


def test_lowering_record_equality_is_identity_based():
    normalized, identities = _adversarial_plan()
    first = lower_delayed(
        normalized,
        operations=_implementations(identities),
        sources=_source_values(normalized),
    )
    second = lower_delayed(
        normalized,
        operations=_implementations(identities),
        sources=_source_values(normalized),
    )

    assert first == first
    assert first != second


class _KeyRecorder(Callback):
    def __init__(self):
        self.keys = []
        super().__init__()

    def _pretask(self, key, dask_graph, state):
        self.keys.append(key)


def test_raw_keys_are_one_to_one_and_list_source_survives_forced_fusion():
    assert dask.__version__ == "2026.7.1"
    normalized, identities = _adversarial_plan()
    lowered = lower_delayed(
        normalized,
        operations=_implementations(identities),
        sources=_source_values(normalized, primary=[2, 3]),
    )
    raw_keys = {
        key
        for task in (*lowered.invocations.values(), *lowered.outputs.values())
        for key in task.dask
    }
    invocation_keys = set(lowered.invocation_keys.values())
    assert invocation_keys <= raw_keys
    assert {
        key for key in raw_keys if ":invocation:" in str(key)
    } == invocation_keys

    default_recorder = _KeyRecorder()
    with default_recorder:
        default_result = _compute(lowered.outputs["summary"], optimize_graph=True)[0]
    fused_recorder = _KeyRecorder()
    with dask.config.set({"optimization.fuse.delayed": True}), fused_recorder:
        fused_result = _compute(lowered.outputs["summary"], optimize_graph=True)[0]

    assert default_result == fused_result == (5, 80, (5, 10, 80))
    assert default_recorder.keys
    assert fused_recorder.keys
    # Optimization may replace visible dependency keys; correctness cannot rely
    # on the pre-optimization invocation mapping surviving execution unchanged.
    assert set(default_recorder.keys) != raw_keys
    assert set(fused_recorder.keys) != raw_keys


def test_concrete_source_container_is_opaque_to_hidden_dask_collections():
    @operation(
        name="runtime.opaque_source",
        inputs={"source": VALUE},
        outputs={"value": RESULT},
    )
    def refusing_body(source):
        raise AssertionError("decorated operation body must not run")

    with plan() as draft:
        source = _source("opaque")
        result = refusing_body(source)
    normalized = draft.finish(outputs={"value": result})
    hidden_calls = []
    hidden = delayed(lambda: hidden_calls.append("ran"))()
    lowered = lower_delayed(
        normalized,
        operations={refusing_body.identity: lambda source: {"value": source[0]}},
        sources={normalized.sources[0].id: [hidden]},
    )

    assert _compute(lowered.outputs["value"])[0] is hidden
    assert hidden_calls == []


class _CountingMapping(Mapping):
    def __init__(self, values):
        self.values = dict(values)
        self.iterations = 0

    def __getitem__(self, key):
        return self.values[key]

    def __iter__(self):
        self.iterations += 1
        return iter(self.values)

    def __len__(self):
        return len(self.values)


def test_explicit_mappings_are_copied_once_and_then_detached():
    normalized, identities = _adversarial_plan()
    operations = _CountingMapping(_implementations(identities))
    sources = _CountingMapping(_source_values(normalized))
    lowered = lower_delayed(
        normalized,
        operations=operations,
        sources=sources,
    )
    operations.values.clear()
    sources.values.clear()

    assert operations.iterations == 1
    assert sources.iterations == 1
    assert _compute(lowered.outputs["summary"])[0] == (5, 80, (5, 10, 80))


@pytest.mark.parametrize(
    ("implementation", "cause_type"),
    [
        (lambda required: {"value": required}, TypeError),
        (lambda: (_ for _ in ()).throw(LookupError("implementation")), LookupError),
        (lambda: 7, TypeError),
        (lambda: {}, ValueError),
        (lambda: {"value": 1, "extra": 2}, ValueError),
    ],
)
def test_runtime_signature_implementation_shape_and_name_failures_are_attributable(
    implementation, cause_type
):
    normalized, identity = _single_invocation_plan()
    lowered = lower_delayed(
        normalized,
        operations={identity: implementation},
        sources={},
    )

    with pytest.raises(InvocationExecutionError) as caught:
        _compute(lowered.outputs["value"])

    invocation = normalized.invocations[0]
    assert caught.value.invocation_id == invocation.id
    assert caught.value.operation == identity
    assert identity.name in str(caught.value)
    assert isinstance(caught.value.__cause__, cause_type)


class _UnreadableMapping(Mapping):
    def __getitem__(self, key):
        raise LookupError("unreadable")

    def __iter__(self):
        raise LookupError("unreadable")

    def __len__(self):
        return 1


def test_runtime_mapping_read_and_policy_recheck_failures_are_attributable():
    normalized, identity = _single_invocation_plan()
    unreadable = lower_delayed(
        normalized,
        operations={identity: lambda: _UnreadableMapping()},
        sources={},
    )
    with pytest.raises(InvocationExecutionError) as mapping_error:
        _compute(unreadable.outputs["value"])
    assert isinstance(mapping_error.value.__cause__, LookupError)

    policy_checked = lower_delayed(
        normalized,
        operations={identity: lambda: {"value": 1}},
        sources={},
    )
    object.__setattr__(normalized.invocations[0].policy, "name", "changed")
    with pytest.raises(InvocationExecutionError) as policy_error:
        _compute(policy_checked.outputs["value"])
    assert isinstance(policy_error.value.__cause__, ValueError)


def test_runtime_does_not_catch_baseexception():
    class DeliberateStop(BaseException):
        pass

    normalized, identity = _single_invocation_plan()

    def stop():
        raise DeliberateStop()

    lowered = lower_delayed(normalized, operations={identity: stop}, sources={})
    with pytest.raises(DeliberateStop):
        _compute(lowered.outputs["value"])


@pytest.mark.parametrize(
    "invalid_operations",
    [[], {"not-an-identity": lambda: None}, {OperationIdentity("extra", "1"): 7}],
)
def test_preflight_rejects_non_mapping_or_malformed_operation_registries(
    invalid_operations,
):
    normalized, _ = _single_invocation_plan()
    with pytest.raises(LocalDaskPreflightError):
        lower_delayed(normalized, operations=invalid_operations, sources={})


def test_preflight_requires_exact_operation_identity_but_allows_well_formed_unused():
    normalized, identity = _single_invocation_plan()
    wrong_version = OperationIdentity(identity.name, "other")
    with pytest.raises(LocalDaskPreflightError, match="missing exact"):
        lower_delayed(
            normalized,
            operations={wrong_version: lambda: {"value": 1}},
            sources={},
        )

    extra = OperationIdentity("unused.registry.entry", "1")
    lowered = lower_delayed(
        normalized,
        operations={identity: lambda: {"value": 1}, extra: lambda: None},
        sources={},
    )
    assert _compute(lowered.outputs["value"]) == (1,)


def test_preflight_requires_exact_sources_and_rejects_top_level_dask_collections():
    normalized, identities = _adversarial_plan()
    operations = _implementations(identities)
    source_values = _source_values(normalized)
    one_source_id = next(iter(source_values))

    with pytest.raises(LocalDaskPreflightError, match="sources must be a mapping"):
        lower_delayed(normalized, operations=operations, sources=[])
    with pytest.raises(LocalDaskPreflightError, match="match the Plan exactly"):
        lower_delayed(
            normalized,
            operations=operations,
            sources={key: value for key, value in source_values.items() if key != one_source_id},
        )
    with pytest.raises(LocalDaskPreflightError, match="match the Plan exactly"):
        lower_delayed(
            normalized,
            operations=operations,
            sources={**source_values, "source:extra": 3},
        )
    with pytest.raises(LocalDaskPreflightError, match="top-level Dask collection"):
        lower_delayed(
            normalized,
            operations=operations,
            sources={**source_values, one_source_id: delayed(lambda: 1)()},
        )


def test_preflight_rejects_invalid_plan_policy_options_and_used_resources():
    normalized, identity = _single_invocation_plan()
    implementation = {identity: lambda: {"value": 1}}
    with pytest.raises(LocalDaskPreflightError, match="plan must"):
        lower_delayed(object(), operations=implementation, sources={})

    invalid_plan = replace(normalized, invocations=())
    with pytest.raises(LocalDaskPreflightError, match="validation"):
        lower_delayed(invalid_plan, operations=implementation, sources={})

    for unsupported_policy in (
        local(queue="anything"),
        named_policy("lsf")(),
    ):
        changed_invocation = replace(
            normalized.invocations[0], policy=unsupported_policy
        )
        changed = replace(normalized, invocations=(changed_invocation,))
        with pytest.raises(LocalDaskPreflightError, match="option-free local"):
            lower_delayed(changed, operations=implementation, sources={})

    used_definition = replace(
        normalized.operations[0],
        resources=(ResourceContract("cores", 1),),
    )
    used_resources = replace(normalized, operations=(used_definition,))
    with pytest.raises(LocalDaskPreflightError, match="unsupported resources"):
        lower_delayed(used_resources, operations=implementation, sources={})

    unused_identity = OperationIdentity("runtime.unused", "1")
    unused_definition = OperationDefinition(
        unused_identity,
        resources=(ResourceContract("cores", 1),),
    )
    unused_resources = replace(
        normalized, operations=(*normalized.operations, unused_definition)
    )
    accepted = lower_delayed(
        unused_resources,
        operations={**implementation, unused_identity: lambda: None},
        sources={},
    )
    assert _compute(accepted.outputs["value"]) == (1,)


def test_zero_output_requires_an_empty_mapping():
    normalized, identity = _single_invocation_plan(outputs=())
    accepted = lower_delayed(
        normalized,
        operations={identity: lambda: {}},
        sources={},
    )
    assert _compute(*accepted.invocations.values()) == ({},)

    refused = lower_delayed(
        normalized,
        operations={identity: lambda: {"unexpected": 1}},
        sources={},
    )
    with pytest.raises(InvocationExecutionError) as caught:
        _compute(*refused.invocations.values())
    assert isinstance(caught.value.__cause__, ValueError)


def test_plain_import_isolated_and_optional_dependency_error_is_short(tmp_path):
    source_root = Path(__file__).resolve().parents[1] / "src"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source_root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    script = """
import sys
import hedloom_flow
assert 'dask' not in sys.modules
assert 'hedloom_flow.experimental' not in sys.modules
import hedloom_flow.experimental
assert 'dask' not in sys.modules
assert 'hedloom_flow.experimental.local_dask' not in sys.modules
try:
    import hedloom_flow.experimental.local_dask
except ImportError as error:
    print(str(error))
else:
    raise AssertionError('Dask unexpectedly importable under python -S')
"""
    completed = subprocess.run(
        [sys.executable, "-S", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == (
        "hedloom_flow.experimental.local_dask requires the optional dependency "
        "'dask==2026.7.1'"
    )

    broken_dask = tmp_path / "dask"
    broken_dask.mkdir()
    (broken_dask / "__init__.py").write_text(
        "raise ModuleNotFoundError("
        "\"No module named 'dask_missing_dependency'\", "
        "name='dask_missing_dependency')\n",
        encoding="utf-8",
    )
    broken_environment = environment.copy()
    broken_environment["PYTHONPATH"] = os.pathsep.join(
        (str(tmp_path), str(source_root))
    )
    broken_script = """
try:
    import hedloom_flow.experimental.local_dask
except ModuleNotFoundError as error:
    print(error.name)
else:
    raise AssertionError('broken Dask import unexpectedly succeeded')
"""
    broken = subprocess.run(
        [sys.executable, "-S", "-c", broken_script],
        check=False,
        capture_output=True,
        text=True,
        env=broken_environment,
    )

    assert broken.returncode == 0, broken.stderr
    assert broken.stdout.strip() == "dask_missing_dependency"
    assert "optional dependency" not in broken.stderr


def test_characterization_command_is_semantic_repeatable_and_uses_injected_source(
    tmp_path,
):
    component_root = Path(__file__).resolve().parents[1]
    source_root = component_root / "src"
    example = component_root / "examples" / "local_dask_characterization.py"
    poison_source = tmp_path / "inputs" / "two-stage-opamp.json"
    poison_source.mkdir(parents=True)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(source_root), str(component_root))
    )
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    def run_example():
        return subprocess.run(
            [sys.executable, str(example)],
            cwd=tmp_path,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    first = run_example()
    second = run_example()
    assert first.returncode == second.returncode == 0, first.stderr or second.stderr
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout

    normalized = characterization.build_characterization_plan()
    observed = json.loads(first.stdout)
    assert observed == {
        "plan": {
            "counts": {
                "boundaries": 4,
                "edges": 3,
                "flows": 2,
                "invocations": 4,
                "operations": 2,
                "outputs": 4,
                "sources": 1,
            },
            "ids": {
                "boundaries": [item.id for item in normalized.boundaries],
                "edges": [item.id for item in normalized.edges],
                "invocations": [item.id for item in normalized.invocations],
                "sources": [item.id for item in normalized.sources],
            },
            "schema_version": 3,
        },
        "results": {
            "corners__ff": {
                "corner": "ff",
                "design": "two-stage-opamp",
                "temperature_c": -40,
            },
            "corners__ss": {
                "corner": "ss",
                "design": "two-stage-opamp",
                "temperature_c": 125,
            },
            "corners__tt": {
                "corner": "tt",
                "design": "two-stage-opamp",
                "temperature_c": 27,
            },
            "summary": {
                "corner_count": 3,
                "corner_order": ["tt", "ss", "ff"],
                "temperatures_c": [27, 125, -40],
            },
        },
    }
    assert normalized.sources[0].address.locator == "inputs/two-stage-opamp.json"
    assert poison_source.is_dir()
