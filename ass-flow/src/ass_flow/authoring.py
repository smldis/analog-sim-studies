"""Public, executor-free authoring surface for static ASS Flow plans."""

from __future__ import annotations

from collections.abc import Sequence
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
import inspect
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

from .model import (
    ArtifactContract,
    ArtifactSource,
    ArtifactSourceReference,
    CollectionInputBinding,
    ConfigBinding,
    ConfigContract,
    ContractError,
    DependencyEdge,
    FlowBoundary,
    FlowDefinition,
    FlowIdentity,
    InputBinding,
    InputContract,
    Invocation,
    NamedOutput,
    OperationDefinition,
    OperationIdentity,
    OutputContract,
    OutputReference,
    Plan,
    Policy,
    ResourceContract,
    _keyed_plan_id,
    _stable_edge_id,
    normalize_authored_key,
    resolve_policy,
)


class AuthoringError(ValueError):
    """An authored declaration or static call cannot form a valid plan."""


class PlanningScopeError(AuthoringError):
    """Planning-only syntax was used without an active ``plan`` context."""


class BindingError(AuthoringError):
    """An operation call does not satisfy its declared contract."""


@dataclass(frozen=True, slots=True)
class Parameter:
    """An operation configuration declaration awaiting its authored name."""

    value_type: type

    def __post_init__(self) -> None:
        # Let the C1 contract remain authoritative for supported literal types.
        ConfigContract("value", self.value_type)


@dataclass(frozen=True, slots=True)
class ArtifactCollection:
    """A required ordered collection artifact input awaiting its authored name."""

    artifact: ArtifactContract

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, ArtifactContract):
            raise ContractError(
                "artifact collection must contain an ArtifactContract"
            )


@dataclass(frozen=True, slots=True)
class ArtifactValue:
    """A plan-owned artifact reference used to connect authored calls."""

    reference: ArtifactSourceReference | OutputReference
    artifact: ArtifactContract
    _draft: PlanDraft = field(repr=False, compare=False)
    _boundary_id: str | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class InvocationResult:
    """Immutable named outputs from one planned operation invocation."""

    _values: tuple[tuple[str, ArtifactValue], ...]

    @property
    def outputs(self) -> Mapping[str, ArtifactValue]:
        return MappingProxyType(dict(self._values))

    @property
    def declared_outputs(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self._values)

    def output(self, name: str) -> ArtifactValue:
        for output_name, value in self._values:
            if output_name == name:
                return value
        available = ", ".join(self.declared_outputs) or "none"
        raise AuthoringError(
            f"operation has no output {name!r}; declared outputs: {available}"
        )

    def __getitem__(self, name: str) -> ArtifactValue:
        return self.output(name)

    def __getattr__(self, name: str) -> ArtifactValue:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.output(name)
        except AuthoringError as error:
            raise AttributeError(str(error)) from error

    def _as_concise_input(self) -> ArtifactValue:
        if len(self._values) != 1:
            names = ", ".join(self.declared_outputs) or "none"
            raise BindingError(
                "an operation result can be used directly only when it has one "
                f"output; select one explicitly from: {names}"
            )
        return self._values[0][1]


@dataclass(frozen=True, slots=True)
class Operation:
    """A reusable immutable operation definition; its body is never executed."""

    definition: OperationDefinition
    _function: Callable[..., Any] = field(repr=False, compare=False)
    _signature: inspect.Signature = field(repr=False, compare=False)

    @property
    def identity(self) -> OperationIdentity:
        return self.definition.identity

    @property
    def __name__(self) -> str:
        return self._function.__name__

    def options(
        self, *, policy: Policy | None = None, key: str | None = None
    ) -> OperationCall:
        """Return an immutable call view with policy and/or authored identity."""

        if policy is not None:
            _require_policy(policy, "call policy")
        normalized_key = _optional_authored_key(key)
        return OperationCall(self, policy, normalized_key)

    def __call__(self, *args: Any, **kwargs: Any) -> InvocationResult:
        return self._plan_call(None, None, args, kwargs)

    def _plan_call(
        self,
        policy: Policy | None,
        key: str | None,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> InvocationResult:
        draft = _active_draft("operation")
        return draft._call_operation(self, policy, key, args, kwargs)


@dataclass(frozen=True, slots=True)
class OperationCall:
    """An immutable per-call view over an operation definition."""

    operation: Operation
    policy: Policy | None = None
    key: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.operation, Operation):
            raise AuthoringError("operation call must contain an Operation")
        if self.policy is not None:
            _require_policy(self.policy, "call policy")
        if self.key is not None:
            _require_authored_key(self.key)

    @property
    def definition(self) -> OperationDefinition:
        return self.operation.definition

    @property
    def identity(self) -> OperationIdentity:
        return self.operation.identity

    def options(
        self, *, policy: Policy | None = None, key: str | None = None
    ) -> OperationCall:
        """Compose an immutable override while retaining omitted options."""

        selected_policy = self.policy if policy is None else policy
        selected_key = self.key if key is None else _optional_authored_key(key)
        if selected_policy is not None:
            _require_policy(selected_policy, "call policy")
        return OperationCall(self.operation, selected_policy, selected_key)

    def __call__(self, *args: Any, **kwargs: Any) -> InvocationResult:
        return self.operation._plan_call(self.policy, self.key, args, kwargs)


@dataclass(frozen=True, slots=True)
class Flow:
    """A reusable Python strategy that executes only to construct a plan."""

    definition: FlowDefinition
    _function: Callable[..., Any] = field(repr=False, compare=False)
    _signature: inspect.Signature = field(repr=False, compare=False)

    @property
    def identity(self) -> FlowIdentity:
        return self.definition.identity

    @property
    def __name__(self) -> str:
        return self._function.__name__

    def options(self, *, key: str) -> FlowCall:
        """Return an immutable keyed call view; flows have no policy option."""

        return FlowCall(self, _require_authored_key(key))

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        draft = _active_draft("flow")
        return draft._call_flow(self, None, args, kwargs)


@dataclass(frozen=True, slots=True)
class FlowCall:
    """An immutable keyed call view over a flow definition."""

    flow: Flow
    key: str

    def __post_init__(self) -> None:
        if not isinstance(self.flow, Flow):
            raise AuthoringError("flow call must contain a Flow")
        _require_authored_key(self.key)

    @property
    def definition(self) -> FlowDefinition:
        return self.flow.definition

    @property
    def identity(self) -> FlowIdentity:
        return self.flow.identity

    def options(self, *, key: str) -> FlowCall:
        return FlowCall(self.flow, _require_authored_key(key))

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        draft = _active_draft("flow")
        return draft._call_flow(self.flow, self.key, args, kwargs)


def artifact(kind: str) -> ArtifactContract:
    """Declare an artifact kind for an operation input or output."""

    return ArtifactContract(kind)


def artifacts(kind: str) -> ArtifactCollection:
    """Declare a required, non-empty ordered collection artifact input."""

    return ArtifactCollection(ArtifactContract(kind))


def parameter(value_type: type) -> Parameter:
    """Declare the literal Python type of an operation configuration value."""

    return Parameter(value_type)


def operation(
    *,
    inputs: Mapping[str, ArtifactContract | ArtifactCollection] | None = None,
    config: Mapping[str, Parameter] | None = None,
    outputs: Mapping[str, ArtifactContract] | None = None,
    resources: Iterable[ResourceContract] = (),
    default_policy: Policy | None = None,
    policy: Policy | None = None,
    name: str | None = None,
    version: str = "1",
) -> Callable[[Callable[..., Any]], Operation]:
    """Decorate an operation body as immutable planning metadata.

    ``policy`` is accepted as a concise alias for ``default_policy``.  Supplying
    both is rejected so precedence remains explicit.
    """

    if policy is not None and default_policy is not None:
        raise AuthoringError("use only one of policy or default_policy")
    selected_policy = policy if policy is not None else default_policy
    if selected_policy is not None:
        _require_policy(selected_policy, "operation default policy")

    input_items = _input_declaration_mapping(inputs)
    config_items = _declaration_mapping(config, "config", Parameter)
    output_items = _declaration_mapping(outputs, "outputs", ArtifactContract)
    input_names = {item_name for item_name, _ in input_items}
    config_names = {item_name for item_name, _ in config_items}
    collisions = sorted(input_names & config_names)
    if collisions:
        raise AuthoringError(
            "names cannot be both inputs and config: " + ", ".join(collisions)
        )

    try:
        resource_items = tuple(resources)
    except TypeError as error:
        raise AuthoringError("resources must be an iterable") from error

    def decorate(function: Callable[..., Any]) -> Operation:
        if not callable(function):
            raise AuthoringError("@operation must decorate a callable")
        signature = inspect.signature(function)
        _validate_operation_signature(
            signature, input_names | config_names, function.__qualname__
        )
        identity = OperationIdentity(
            name or f"{function.__module__}.{function.__qualname__}", version
        )
        definition = OperationDefinition(
            identity=identity,
            inputs=tuple(
                InputContract(
                    item_name,
                    (
                        declaration.artifact
                        if isinstance(declaration, ArtifactCollection)
                        else declaration
                    ),
                    cardinality=(
                        "collection"
                        if isinstance(declaration, ArtifactCollection)
                        else "scalar"
                    ),
                )
                for item_name, declaration in input_items
            ),
            config=tuple(
                ConfigContract(item_name, declaration.value_type)
                for item_name, declaration in config_items
            ),
            outputs=tuple(
                OutputContract(item_name, contract)
                for item_name, contract in output_items
            ),
            resources=resource_items,
            default_policy=selected_policy,
        )
        return Operation(definition, function, signature)

    return decorate


def flow(
    function: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    version: str = "1",
) -> Flow | Callable[[Callable[..., Any]], Flow]:
    """Decorate a callable as a reusable, nested planning strategy."""

    def decorate(strategy: Callable[..., Any]) -> Flow:
        if not callable(strategy):
            raise AuthoringError("@flow must decorate a callable")
        identity = FlowIdentity(
            name or f"{strategy.__module__}.{strategy.__qualname__}", version
        )
        return Flow(FlowDefinition(identity), strategy, inspect.signature(strategy))

    if function is None:
        return decorate
    return decorate(function)


class PlanDraft:
    """Private-state builder activated only by an explicit context manager."""

    def __init__(self, default_policy: Policy | None = None):
        if default_policy is not None:
            _require_policy(default_policy, "plan default policy")
        self._default_policy = default_policy
        self._operations: dict[OperationIdentity, OperationDefinition] = {}
        self._flows: dict[FlowIdentity, FlowDefinition] = {}
        self._sources: list[ArtifactSource] = []
        self._source_keys: dict[tuple[str, ArtifactContract], ArtifactValue] = {}
        self._invocations: list[Invocation] = []
        self._edges: list[DependencyEdge] = []
        self._boundaries: list[FlowBoundary] = []
        self._boundary_parents: dict[str, str | None] = {}
        self._boundary_stack: list[str] = []
        self._scoped_keys: set[tuple[str | None, str]] = set()
        self._keyed_invocation_ids: set[str] = set()
        self._next_source = 1
        self._next_invocation = 1
        self._next_edge = 1
        self._next_boundary = 1
        self._entered = False
        self._exited = False
        self._failed = False
        self._finished = False
        self._token: Token[PlanDraft | None] | None = None

    def __enter__(self) -> PlanDraft:
        if self._entered:
            raise PlanningScopeError("a plan draft context cannot be reused")
        if _ACTIVE_DRAFT.get() is not None:
            raise PlanningScopeError(
                "nested plan contexts are not supported; use one active plan"
            )
        self._entered = True
        self._token = _ACTIVE_DRAFT.set(self)
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self._token is None:
            raise PlanningScopeError("plan draft context is not active")
        _ACTIVE_DRAFT.reset(self._token)
        self._token = None
        self._exited = True
        self._failed = exc_type is not None
        return False

    def finish(self, *, outputs: Mapping[str, Any]) -> Plan:
        """Freeze the authored graph as a validated immutable C1 ``Plan``."""

        if not self._entered:
            raise PlanningScopeError("enter the draft with 'with plan() as draft:'")
        if not self._exited:
            raise PlanningScopeError("finish the draft after leaving its plan context")
        if self._failed:
            raise AuthoringError("cannot finish a plan context that exited with an error")
        if self._finished:
            raise AuthoringError("this plan draft has already been finished")
        named_outputs = self._named_outputs(outputs, prefix=None, boundary_id=None)
        normalized = Plan(
            operations=tuple(self._operations.values()),
            flows=tuple(self._flows.values()),
            sources=tuple(self._sources),
            invocations=tuple(self._invocations),
            edges=tuple(self._edges),
            boundaries=tuple(self._boundaries),
            outputs=named_outputs,
        ).validate()
        self._finished = True
        return normalized

    def _input_artifact(self, uri: str, kind: str) -> ArtifactValue:
        if self._finished:
            raise AuthoringError("this plan draft has already been finished")
        contract = ArtifactContract(kind)
        if not isinstance(uri, str) or not uri or uri != uri.strip():
            raise AuthoringError("artifact URI must be a non-empty, trimmed string")
        key = (uri, contract)
        existing = self._source_keys.get(key)
        if existing is not None:
            return existing
        source_id = f"source:{self._next_source:04d}"
        self._next_source += 1
        source = ArtifactSource(source_id, uri, contract)
        value = ArtifactValue(ArtifactSourceReference(source_id), contract, self)
        self._sources.append(source)
        self._source_keys[key] = value
        return value

    def _call_operation(
        self,
        authored: Operation,
        call_policy: Policy | None,
        authored_key: str | None,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> InvocationResult:
        self._require_active()
        checkpoint = self._checkpoint()
        try:
            bound = _bind_operation(authored, args, kwargs)
            definition = authored.definition
            input_bindings: list[InputBinding | CollectionInputBinding] = []
            config_bindings: list[ConfigBinding] = []
            artifact_values: dict[str, tuple[ArtifactValue, ...]] = {}

            for contract in definition.inputs:
                authored_value = bound.arguments[contract.name]
                if contract.cardinality == "collection":
                    values = _artifact_collection(authored_value, contract.name)
                else:
                    values = (_concise_artifact(authored_value),)
                for member_index, value in enumerate(values):
                    member_label = (
                        f"input {contract.name!r} member {member_index}"
                        if contract.cardinality == "collection"
                        else f"input {contract.name!r}"
                    )
                    self._require_owned(value, member_label)
                    if value.artifact.kind != contract.artifact.kind:
                        raise BindingError(
                            f"{member_label} expects artifact kind "
                            f"{contract.artifact.kind!r}, got {value.artifact.kind!r}"
                        )
                artifact_values[contract.name] = values
                if contract.cardinality == "collection":
                    input_bindings.append(
                        CollectionInputBinding(
                            contract.name,
                            tuple(value.reference for value in values),
                        )
                    )
                else:
                    input_bindings.append(
                        InputBinding(contract.name, values[0].reference)
                    )

            for contract in definition.config:
                value = bound.arguments[contract.name]
                if type(value) is not contract.value_type:
                    raise BindingError(
                        f"config {contract.name!r} expects "
                        f"{contract.value_type.__name__}, got {type(value).__name__}"
                    )
                try:
                    config_bindings.append(ConfigBinding(contract.name, value))
                except ContractError as error:
                    raise BindingError(str(error)) from error

            boundary_id = self._boundary_stack[-1] if self._boundary_stack else None
            if authored_key is None:
                invocation_id = f"invoke:{self._next_invocation:04d}"
                self._next_invocation += 1
            else:
                self._reserve_key(boundary_id, authored_key)
                invocation_id = _keyed_plan_id(
                    "invoke", boundary_id, authored_key
                )
                self._keyed_invocation_ids.add(invocation_id)
            self._register_operation(definition)
            invocation = Invocation(
                id=invocation_id,
                operation=definition.identity,
                inputs=tuple(input_bindings),
                config=tuple(config_bindings),
                policy=resolve_policy(
                    call_policy, definition.default_policy, self._default_policy
                ),
                boundary_id=boundary_id,
                authored_key=authored_key,
            )
            self._invocations.append(invocation)

            for contract in definition.inputs:
                for member_index, value in enumerate(artifact_values[contract.name]):
                    if (
                        contract.cardinality == "scalar"
                        and not isinstance(value.reference, OutputReference)
                    ):
                        continue
                    target_member_index = (
                        member_index
                        if contract.cardinality == "collection"
                        else None
                    )
                    if (
                        authored_key is not None
                        and isinstance(value.reference, OutputReference)
                        and value.reference.invocation_id
                        in self._keyed_invocation_ids
                    ):
                        edge_id = _stable_edge_id(
                            value.reference,
                            invocation_id,
                            contract.name,
                            target_member_index,
                        )
                    else:
                        edge_id = f"edge:{self._next_edge:04d}"
                        self._next_edge += 1
                    self._edges.append(
                        DependencyEdge(
                            edge_id,
                            value.reference,
                            invocation_id,
                            contract.name,
                            contract.artifact.kind,
                            target_member_index,
                        )
                    )

            result_values = tuple(
                (
                    output.name,
                    ArtifactValue(
                        OutputReference(invocation_id, output.name),
                        output.artifact,
                        self,
                        boundary_id,
                    ),
                )
                for output in definition.outputs
            )
            return InvocationResult(result_values)
        except Exception:
            self._restore(checkpoint)
            raise

    def _call_flow(
        self,
        authored: Flow,
        authored_key: str | None,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        self._require_active()
        try:
            authored._signature.bind(*args, **kwargs)
        except TypeError as error:
            raise BindingError(
                f"flow {authored.identity.name!r} call is invalid: {error}"
            ) from error
        self._check_nested_handles((args, kwargs))
        checkpoint = self._checkpoint()
        parent_id = self._boundary_stack[-1] if self._boundary_stack else None
        boundary_id: str | None = None
        try:
            if authored_key is None:
                boundary_id = f"flow:{self._next_boundary:04d}"
                self._next_boundary += 1
            else:
                self._reserve_key(parent_id, authored_key)
                boundary_id = _keyed_plan_id("flow", parent_id, authored_key)
            self._register_flow(authored.definition)
            self._boundary_parents[boundary_id] = parent_id
            self._boundary_stack.append(boundary_id)
            result = authored._function(*args, **kwargs)
            named_outputs = self._named_outputs(
                result, prefix="output", boundary_id=boundary_id
            )
            self._boundaries.append(
                FlowBoundary(
                    boundary_id,
                    authored.identity,
                    parent_id=parent_id,
                    outputs=named_outputs,
                    authored_key=authored_key,
                )
            )
        except Exception:
            self._restore(checkpoint)
            raise
        finally:
            if (
                boundary_id is not None
                and self._boundary_stack
                and self._boundary_stack[-1] == boundary_id
            ):
                self._boundary_stack.pop()
        return result

    def _named_outputs(
        self,
        value: Any,
        *,
        prefix: str | None,
        boundary_id: str | None,
    ) -> tuple[NamedOutput, ...]:
        if prefix is None:
            if not isinstance(value, Mapping):
                raise AuthoringError("finish outputs must be a mapping of names to outputs")
            pairs = []
            for name, item in _sorted_named_items(value, "output"):
                pairs.extend(self._flatten_output(item, name, boundary_id))
        else:
            if value is None:
                pairs = []
            elif isinstance(value, Mapping):
                pairs = []
                for name, item in _sorted_named_items(value, "flow output"):
                    pairs.extend(self._flatten_output(item, name, boundary_id))
            else:
                pairs = self._flatten_output(value, prefix, boundary_id)
        names = [name for name, _ in pairs]
        if len(names) != len(set(names)):
            raise AuthoringError("nested outputs produce duplicate normalized names")
        return tuple(NamedOutput(name, reference) for name, reference in pairs)

    def _flatten_output(
        self, value: Any, prefix: str, boundary_id: str | None
    ) -> list[tuple[str, OutputReference]]:
        if isinstance(value, InvocationResult):
            value = value._as_concise_input()
        if isinstance(value, ArtifactValue):
            self._require_owned(value, f"output {prefix!r}")
            if not isinstance(value.reference, OutputReference):
                raise AuthoringError(
                    f"output {prefix!r} must be produced by an operation, not an input source"
                )
            if boundary_id is not None and not self._boundary_contains(
                boundary_id, value._boundary_id
            ):
                raise AuthoringError(
                    f"flow output {prefix!r} is not produced within that flow"
                )
            return [(prefix, value.reference)]
        if isinstance(value, Mapping):
            flattened = []
            for name, item in _sorted_named_items(value, "nested output"):
                flattened.extend(
                    self._flatten_output(item, f"{prefix}__{name}", boundary_id)
                )
            return flattened
        if isinstance(value, (list, tuple)):
            flattened = []
            for index, item in enumerate(value):
                flattened.extend(
                    self._flatten_output(item, f"{prefix}_{index}", boundary_id)
                )
            return flattened
        raise AuthoringError(
            f"output {prefix!r} must be an operation output or a list, tuple, or mapping of outputs"
        )

    def _require_active(self) -> None:
        if _ACTIVE_DRAFT.get() is not self or self._token is None:
            raise PlanningScopeError("use this operation or flow inside 'with plan():'")
        if self._finished:
            raise AuthoringError("this plan draft has already been finished")

    def _require_owned(self, value: ArtifactValue, label: str) -> None:
        if value._draft is not self:
            raise BindingError(f"{label} refers to a different plan draft")

    def _check_nested_handles(self, value: Any, seen: set[int] | None = None) -> None:
        if seen is None:
            seen = set()
        if isinstance(value, ArtifactValue):
            self._require_owned(value, "flow argument")
            return
        if isinstance(value, InvocationResult):
            for _, output in value._values:
                self._require_owned(output, "flow argument")
            return
        if isinstance(value, (Mapping, list, tuple)):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            items = (
                (*value.keys(), *value.values())
                if isinstance(value, Mapping)
                else value
            )
            for item in items:
                self._check_nested_handles(item, seen)

    def _boundary_contains(
        self, ancestor_id: str, candidate_id: str | None
    ) -> bool:
        cursor = candidate_id
        visited: set[str] = set()
        while cursor is not None and cursor not in visited:
            if cursor == ancestor_id:
                return True
            visited.add(cursor)
            cursor = self._boundary_parents.get(cursor)
        return False

    def _register_operation(self, definition: OperationDefinition) -> None:
        existing = self._operations.get(definition.identity)
        if existing is not None and existing != definition:
            raise AuthoringError(
                f"operation identity {definition.identity.name!r} has conflicting definitions"
            )
        self._operations.setdefault(definition.identity, definition)

    def _register_flow(self, definition: FlowDefinition) -> None:
        existing = self._flows.get(definition.identity)
        if existing is not None and existing != definition:
            raise AuthoringError(
                f"flow identity {definition.identity.name!r} has conflicting definitions"
            )
        self._flows.setdefault(definition.identity, definition)

    def _reserve_key(self, scope_id: str | None, authored_key: str) -> None:
        scoped_key = (scope_id, authored_key)
        if scoped_key in self._scoped_keys:
            scope_label = "root" if scope_id is None else scope_id
            raise AuthoringError(
                f"authored key {authored_key!r} is already used in scope "
                f"{scope_label!r}"
            )
        self._scoped_keys.add(scoped_key)

    def _checkpoint(self) -> tuple[Any, ...]:
        return (
            dict(self._operations),
            dict(self._flows),
            list(self._sources),
            dict(self._source_keys),
            list(self._invocations),
            list(self._edges),
            list(self._boundaries),
            dict(self._boundary_parents),
            set(self._scoped_keys),
            set(self._keyed_invocation_ids),
            self._next_source,
            self._next_invocation,
            self._next_edge,
            self._next_boundary,
        )

    def _restore(self, checkpoint: tuple[Any, ...]) -> None:
        (
            self._operations,
            self._flows,
            self._sources,
            self._source_keys,
            self._invocations,
            self._edges,
            self._boundaries,
            self._boundary_parents,
            self._scoped_keys,
            self._keyed_invocation_ids,
            self._next_source,
            self._next_invocation,
            self._next_edge,
            self._next_boundary,
        ) = checkpoint


_ACTIVE_DRAFT: ContextVar[PlanDraft | None] = ContextVar(
    "ass_flow_active_draft", default=None
)


def plan(*, default_policy: Policy | None = None) -> PlanDraft:
    """Create the sole explicit mutable planning scope."""

    return PlanDraft(default_policy)


def input_artifact(uri: str, kind: str) -> ArtifactValue:
    """Register an external artifact source in the active plan."""

    return _active_draft("input_artifact")._input_artifact(uri, kind)


def submit(*args: Any, **kwargs: Any) -> None:
    """Mark the deliberately unimplemented executor boundary."""

    raise NotImplementedError(
        "execution is outside this planning spike; construct a Plan with 'with plan()'"
    )


def _active_draft(action: str) -> PlanDraft:
    draft = _ACTIVE_DRAFT.get()
    if draft is None:
        raise PlanningScopeError(
            f"{action} calls require an active plan; use 'with plan() as draft:'"
        )
    return draft


def _require_policy(value: object, label: str) -> None:
    if not isinstance(value, Policy):
        raise AuthoringError(f"{label} must be a Policy")


def _require_authored_key(value: object) -> str:
    try:
        return normalize_authored_key(value)
    except ContractError as error:
        raise AuthoringError(str(error)) from error


def _optional_authored_key(value: object | None) -> str | None:
    return None if value is None else _require_authored_key(value)


def _input_declaration_mapping(
    value: Mapping[str, ArtifactContract | ArtifactCollection] | None,
) -> tuple[tuple[str, ArtifactContract | ArtifactCollection], ...]:
    if value is None:
        return ()
    if not isinstance(value, Mapping):
        raise AuthoringError("operation inputs must be a mapping")
    items = tuple(value.items())
    for name, declaration in items:
        if not isinstance(name, str) or not name.isidentifier():
            raise AuthoringError("operation inputs names must be Python identifiers")
        if not isinstance(declaration, ArtifactContract | ArtifactCollection):
            raise AuthoringError(
                f"operation inputs {name!r} must use artifact(...) or artifacts(...)"
            )
    return tuple(sorted(items, key=lambda item: item[0]))


def _declaration_mapping(
    value: Mapping[str, Any] | None, label: str, expected: type
) -> tuple[tuple[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, Mapping):
        raise AuthoringError(f"operation {label} must be a mapping")
    items = tuple(value.items())
    for name, declaration in items:
        if not isinstance(name, str) or not name.isidentifier():
            raise AuthoringError(f"operation {label} names must be Python identifiers")
        if not isinstance(declaration, expected):
            raise AuthoringError(
                f"operation {label} {name!r} must use {expected.__name__}"
            )
    return tuple(sorted(items, key=lambda item: item[0]))


def _sorted_named_items(
    value: Mapping[Any, Any], label: str
) -> tuple[tuple[str, Any], ...]:
    items = tuple(value.items())
    if any(not isinstance(name, str) or not name.isidentifier() for name, _ in items):
        raise AuthoringError(f"{label} names must be Python identifiers")
    return tuple(sorted(items, key=lambda item: item[0]))


def _validate_operation_signature(
    signature: inspect.Signature, declared_names: set[str], label: str
) -> None:
    parameters = tuple(signature.parameters.values())
    variadic = [
        item.name
        for item in parameters
        if item.kind
        in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]
    if variadic:
        raise AuthoringError(
            f"operation {label!r} may not use variadic parameters: {', '.join(variadic)}"
        )
    signature_names = {item.name for item in parameters}
    missing_declarations = sorted(signature_names - declared_names)
    absent_parameters = sorted(declared_names - signature_names)
    if missing_declarations or absent_parameters:
        details = []
        if missing_declarations:
            details.append("undeclared parameters " + ", ".join(missing_declarations))
        if absent_parameters:
            details.append("declarations absent from signature " + ", ".join(absent_parameters))
        raise AuthoringError(f"operation {label!r} has " + "; ".join(details))


def _bind_operation(
    authored: Operation, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> inspect.BoundArguments:
    definition = authored.definition
    declared_names = {
        contract.name for contract in (*definition.inputs, *definition.config)
    }
    unexpected = sorted(set(kwargs) - declared_names)
    if unexpected:
        raise BindingError("unexpected bindings: " + ", ".join(unexpected))
    try:
        bound = authored._signature.bind_partial(*args, **kwargs)
    except TypeError as error:
        raise BindingError(
            f"operation {definition.identity.name!r} call is invalid: {error}"
        ) from error
    missing_inputs = [
        contract.name
        for contract in definition.inputs
        if contract.required and contract.name not in bound.arguments
    ]
    missing_config = [
        contract.name
        for contract in definition.config
        if contract.required and contract.name not in bound.arguments
    ]
    if missing_inputs or missing_config:
        details = []
        if missing_inputs:
            details.append("missing inputs: " + ", ".join(missing_inputs))
        if missing_config:
            details.append("missing config: " + ", ".join(missing_config))
        raise BindingError("; ".join(details))
    return bound


def _concise_artifact(value: Any) -> ArtifactValue:
    if isinstance(value, InvocationResult):
        return value._as_concise_input()
    if isinstance(value, ArtifactValue):
        return value
    raise BindingError(
        "artifact inputs must be input_artifact(...) values or operation outputs"
    )


def _artifact_collection(value: Any, input_name: str) -> tuple[ArtifactValue, ...]:
    if isinstance(value, InvocationResult):
        # Preserve the actionable selection error for multi-output calls before
        # reporting that even a concise single output is not a collection.
        value._as_concise_input()
    if isinstance(value, (str, bytes, bytearray, memoryview)) or not isinstance(
        value, Sequence
    ):
        raise BindingError(
            f"collection input {input_name!r} must be a non-string sequence"
        )
    if not value:
        raise BindingError(f"collection input {input_name!r} must not be empty")
    members = []
    for member_index, member in enumerate(value):
        try:
            members.append(_concise_artifact(member))
        except BindingError as error:
            raise BindingError(
                f"collection input {input_name!r} member {member_index}: {error}"
            ) from error
    return tuple(members)


__all__ = [
    "ArtifactCollection",
    "ArtifactValue",
    "AuthoringError",
    "BindingError",
    "Flow",
    "FlowCall",
    "InvocationResult",
    "Operation",
    "OperationCall",
    "Parameter",
    "PlanDraft",
    "PlanningScopeError",
    "artifact",
    "artifacts",
    "flow",
    "input_artifact",
    "operation",
    "parameter",
    "plan",
    "submit",
]
