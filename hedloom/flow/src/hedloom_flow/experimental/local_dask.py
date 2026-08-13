"""Experimental, local-only lowering of a validated Plan to Dask Delayed.

The adapter constructs an inspectable graph only.  It deliberately provides no
compute, submission, persistence, cancellation, publication, or source-I/O
surface; callers choose and invoke Dask's scheduler themselves.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Hashable
import uuid

try:
    import dask
    from dask import delayed
except ModuleNotFoundError as error:  # pragma: no cover - isolated import evidence
    if error.name != "dask":
        raise
    raise ImportError(
        "hedloom_flow.experimental.local_dask requires the optional dependency "
        "'dask==2026.7.1'"
    ) from error

from hedloom_flow.model import (
    ArtifactSourceReference,
    CollectionInputBinding,
    FrozenList,
    FrozenObject,
    InputBinding,
    OperationIdentity,
    OutputReference,
    Plan,
    Policy,
)


class LocalDaskPreflightError(ValueError):
    """The Plan or an explicit runtime binding cannot be lowered locally."""


class InvocationExecutionError(RuntimeError):
    """One implementation failed its attributable invocation contract."""

    def __init__(self, invocation_id: str, operation: OperationIdentity):
        self.invocation_id = invocation_id
        self.operation_identity = operation
        self.operation = operation
        super().__init__(
            f"invocation {invocation_id!r} for operation "
            f"{operation.name!r} version {operation.version!r} failed"
        )


@dataclass(frozen=True, slots=True, eq=False)
class DelayedLowering:
    """Immutable inspection handles for one freshly namespaced Dask graph."""

    invocations: Mapping[str, Any]
    outputs: Mapping[str, Any]
    invocation_keys: Mapping[str, Hashable]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "invocations", MappingProxyType(dict(self.invocations))
        )
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        object.__setattr__(
            self,
            "invocation_keys",
            MappingProxyType(dict(self.invocation_keys)),
        )


_OPTION_FREE_LOCAL = Policy("local")


def lower_delayed(
    plan: Plan,
    *,
    operations: Mapping[OperationIdentity, Callable[..., Any]],
    sources: Mapping[str, Any],
) -> DelayedLowering:
    """Lower one Plan using explicit implementations and decoded source values.

    Each call creates a new opaque key namespace.  The returned Delayed values
    are not computed or persisted by this function.
    """

    if not isinstance(plan, Plan):
        raise LocalDaskPreflightError("plan must be an hedloom_flow.model.Plan")
    try:
        plan.validate()
    except Exception as error:
        raise LocalDaskPreflightError("plan validation failed") from error

    operation_registry = _copy_mapping(operations, "operations")
    source_registry = _copy_mapping(sources, "sources")

    for identity, implementation in operation_registry.items():
        if not isinstance(identity, OperationIdentity):
            raise LocalDaskPreflightError(
                "operation registry keys must be OperationIdentity values"
            )
        if not callable(implementation):
            raise LocalDaskPreflightError(
                "operation registry values must be callable"
            )

    invocation_by_id = {invocation.id: invocation for invocation in plan.invocations}
    operation_by_identity = {
        operation.identity: operation for operation in plan.operations
    }
    used_identities = {invocation.operation for invocation in plan.invocations}
    missing_operations = sorted(
        used_identities - operation_registry.keys(),
        key=lambda identity: (identity.name, identity.version),
    )
    if missing_operations:
        missing = ", ".join(
            f"{identity.name!r} version {identity.version!r}"
            for identity in missing_operations
        )
        raise LocalDaskPreflightError(
            f"operation registry is missing exact bindings for: {missing}"
        )

    expected_source_ids = {source.id for source in plan.sources}
    actual_source_ids = set(source_registry)
    if actual_source_ids != expected_source_ids:
        missing = sorted(expected_source_ids - actual_source_ids)
        extra = sorted(actual_source_ids - expected_source_ids, key=repr)
        details = []
        if missing:
            details.append("missing " + ", ".join(repr(value) for value in missing))
        if extra:
            details.append("extra " + ", ".join(repr(value) for value in extra))
        raise LocalDaskPreflightError(
            "source IDs must match the Plan exactly: " + "; ".join(details)
        )

    for source_id, value in source_registry.items():
        if dask.is_dask_collection(value):
            raise LocalDaskPreflightError(
                f"source {source_id!r} must not be a top-level Dask collection"
            )

    for invocation in plan.invocations:
        if invocation.policy != _OPTION_FREE_LOCAL:
            raise LocalDaskPreflightError(
                f"invocation {invocation.id!r} requires option-free local policy"
            )
        definition = operation_by_identity[invocation.operation]
        if definition.resources:
            raise LocalDaskPreflightError(
                f"invocation {invocation.id!r} uses operation "
                f"{invocation.operation.name!r} with unsupported resources"
            )

    namespace = uuid.uuid4().hex
    source_tasks = {
        source_id: delayed(
            _source_thunk(value),
            pure=False,
        )(dask_key_name=_dask_key(namespace, "source", source_id))
        for source_id, value in source_registry.items()
    }
    invocation_tasks: dict[str, Any] = {}
    projection_tasks: dict[OutputReference, Any] = {}

    def project(reference: OutputReference) -> Any:
        existing = projection_tasks.get(reference)
        if existing is not None:
            return existing
        owner = build_invocation(reference.invocation_id)
        task = delayed(_project_output, pure=False)(
            owner,
            reference.output_name,
            dask_key_name=_dask_key(
                namespace,
                "projection",
                reference.invocation_id,
                reference.output_name,
            ),
        )
        projection_tasks[reference] = task
        return task

    def resolve(reference: ArtifactSourceReference | OutputReference) -> Any:
        if isinstance(reference, ArtifactSourceReference):
            return source_tasks[reference.source_id]
        return project(reference)

    def build_invocation(invocation_id: str) -> Any:
        existing = invocation_tasks.get(invocation_id)
        if existing is not None:
            return existing
        invocation = invocation_by_id[invocation_id]
        implementation = operation_registry[invocation.operation]
        definition = operation_by_identity[invocation.operation]
        keyword_arguments: dict[str, Any] = {}
        for binding in invocation.inputs:
            if isinstance(binding, InputBinding):
                keyword_arguments[binding.name] = resolve(binding.reference)
            elif isinstance(binding, CollectionInputBinding):
                keyword_arguments[binding.name] = tuple(
                    resolve(reference) for reference in binding.references
                )
        for binding in invocation.config:
            keyword_arguments[binding.name] = binding.value

        wrapper = _invocation_wrapper(
            invocation.id,
            invocation.operation,
            invocation.policy,
            implementation,
            tuple(binding.name for binding in invocation.config),
            tuple(output.name for output in definition.outputs),
        )
        task = delayed(wrapper, pure=False)(
            dask_key_name=_dask_key(namespace, "invocation", invocation.id),
            **keyword_arguments,
        )
        invocation_tasks[invocation_id] = task
        return task

    # Retain every invocation task, including work not reachable from Plan roots.
    for invocation_id in sorted(invocation_by_id):
        build_invocation(invocation_id)

    named_outputs = {
        output.name: project(output.reference)
        for output in sorted(plan.outputs, key=lambda value: value.name)
    }
    ordered_invocations = {
        invocation_id: invocation_tasks[invocation_id]
        for invocation_id in sorted(invocation_tasks)
    }
    invocation_keys = {
        invocation_id: task.key
        for invocation_id, task in ordered_invocations.items()
    }
    return DelayedLowering(
        invocations=ordered_invocations,
        outputs=named_outputs,
        invocation_keys=invocation_keys,
    )


def _copy_mapping(value: object, label: str) -> dict[Any, Any]:
    if not isinstance(value, Mapping):
        raise LocalDaskPreflightError(f"{label} must be a mapping")
    try:
        return dict(value)
    except Exception as error:
        raise LocalDaskPreflightError(f"could not copy {label} mapping") from error


def _dask_key(namespace: str, role: str, *logical_identity: str) -> str:
    return ":".join(("hedloom-flow-local-dask", namespace, role, *logical_identity))


def _source_thunk(value: Any) -> Callable[[], Any]:
    def provide_source() -> Any:
        return value

    return provide_source


def _project_output(snapshot: dict[str, Any], output_name: str) -> Any:
    return snapshot[output_name]


def _invocation_wrapper(
    invocation_id: str,
    operation: OperationIdentity,
    policy: Policy,
    implementation: Callable[..., Any],
    config_names: tuple[str, ...],
    output_names: tuple[str, ...],
) -> Callable[..., dict[str, Any]]:
    expected_outputs = frozenset(output_names)
    config_name_set = frozenset(config_names)

    def invoke(**keyword_arguments: Any) -> dict[str, Any]:
        try:
            call_arguments = {
                name: _thaw(value) if name in config_name_set else value
                for name, value in keyword_arguments.items()
            }
            if policy != _OPTION_FREE_LOCAL:
                raise ValueError("captured policy is not option-free local")
            result = implementation(**call_arguments)
            if not isinstance(result, Mapping):
                raise TypeError("implementation result must be a Mapping")
            snapshot = dict(result)
            if snapshot.keys() != expected_outputs:
                expected = ", ".join(sorted(expected_outputs)) or "none"
                actual = ", ".join(sorted(map(repr, snapshot))) or "none"
                raise ValueError(
                    "implementation result names must exactly match declared "
                    f"outputs (expected: {expected}; actual: {actual})"
                )
            return snapshot
        except Exception as error:
            raise InvocationExecutionError(invocation_id, operation) from error

    return invoke


def _thaw(value: Any) -> Any:
    if isinstance(value, FrozenList):
        return [_thaw(item) for item in value.items]
    if isinstance(value, FrozenObject):
        return {key: _thaw(item) for key, item in value.items}
    return value


__all__ = [
    "DelayedLowering",
    "InvocationExecutionError",
    "LocalDaskPreflightError",
    "lower_delayed",
]
