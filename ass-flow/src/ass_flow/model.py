"""Immutable, executor-neutral values for the ASS Flow planning prototype.

This module deliberately contains no authoring context, callable body, or runtime
behavior.  A later builder is responsible for assigning stable IDs and resolving
policy precedence; :class:`Plan` only records and validates the resulting graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping, TypeAlias


class ModelError(ValueError):
    """Base class for invalid immutable model values."""


class ContractError(ModelError):
    """A contract or descriptive value is invalid in isolation."""


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One inspectable invariant violation in a normalized plan."""

    code: str
    path: str
    message: str


class PlanValidationError(ModelError):
    """Raised when a plan contains one or more invariant violations."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{issue.code} at {issue.path}: {issue.message}"
            for issue in self.issues
        )
        super().__init__(summary or "plan validation failed")


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]*$")
_AUTHORED_KEY_PATTERN = _ID_PATTERN


def _require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ContractError(f"{label} must be a non-empty, trimmed string")


def _require_id(value: object, label: str) -> None:
    _require_text(value, label)
    if not _ID_PATTERN.fullmatch(value):
        raise ContractError(
            f"{label} must contain only letters, digits, '.', '_', ':', '/', "
            "'@', '+', or '-'"
        )


def normalize_authored_key(value: object) -> str:
    """Validate and return one case-sensitive executor-neutral authored key.

    Keys use the same lexical subset as Plan IDs: they start with an ASCII
    letter or digit and then contain only ASCII letters, digits, ``.``, ``_``,
    ``:``, ``/``, ``@``, ``+``, or ``-``.  No whitespace normalization or case
    folding is performed, so the returned value is the authored identity.
    """

    if not isinstance(value, str) or not _AUTHORED_KEY_PATTERN.fullmatch(value):
        raise ContractError(
            "authored key must start with a letter or digit and contain only "
            "letters, digits, '.', '_', ':', '/', '@', '+', or '-'"
        )
    return value


def _keyed_plan_id(kind: str, scope_id: str | None, authored_key: str) -> str:
    """Derive a Plan ID from an exact scoped authored identity."""

    normalized_key = normalize_authored_key(authored_key)
    normalized_scope = "root" if scope_id is None else f"boundary\0{scope_id}"
    payload = f"{kind}\0{normalized_scope}\0{normalized_key}".encode("utf-8")
    return f"{kind}:key:{hashlib.sha256(payload).hexdigest()}"


def _stable_edge_id(
    source: ArtifactReference,
    target_invocation_id: str,
    target_input_name: str,
    target_member_index: int | None,
) -> str:
    """Derive an edge ID from stable endpoint/reference identity."""

    if isinstance(source, ArtifactSourceReference):
        source_identity = f"source\0{source.source_id}"
    else:
        source_identity = (
            f"output\0{source.invocation_id}\0{source.output_name}"
        )
    member_identity = (
        "scalar" if target_member_index is None else str(target_member_index)
    )
    payload = (
        f"{source_identity}\0{target_invocation_id}\0{target_input_name}"
        f"\0{member_identity}"
    ).encode("utf-8")
    return f"edge:key:{hashlib.sha256(payload).hexdigest()}"


def _require_name(value: object, label: str) -> None:
    _require_text(value, label)
    if not value.isidentifier():
        raise ContractError(f"{label} must be a Python identifier")


@dataclass(frozen=True, slots=True)
class FrozenList:
    """Deeply immutable representation of a JSON array."""

    items: tuple["FrozenValue", ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "items",
            tuple(freeze_data(item, label="array item") for item in self.items),
        )


@dataclass(frozen=True, slots=True)
class FrozenObject:
    """Deeply immutable, key-sorted representation of a JSON object."""

    items: tuple[tuple[str, "FrozenValue"], ...] = ()

    def __post_init__(self) -> None:
        entries = tuple(self.items)
        if any(not isinstance(entry, tuple) or len(entry) != 2 for entry in entries):
            raise ContractError("object items must be (string, value) pairs")
        if any(not isinstance(key, str) for key, _ in entries):
            raise ContractError("object keys must be strings")
        keys = [key for key, _ in entries]
        if len(keys) != len(set(keys)):
            raise ContractError("object keys must be unique")
        object.__setattr__(
            self,
            "items",
            tuple(
                (key, freeze_data(value, label=f"object.{key}"))
                for key, value in sorted(entries)
            ),
        )


FrozenValue: TypeAlias = (
    type(None) | bool | int | float | str | FrozenList | FrozenObject
)


def freeze_data(value: Any, *, label: str = "value") -> FrozenValue:
    """Copy JSON-compatible data into a recursively immutable value."""

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError(f"{label} must not contain NaN or infinity")
        return value
    if isinstance(value, FrozenList | FrozenObject):
        return value
    if isinstance(value, list):
        return FrozenList(
            tuple(freeze_data(item, label=f"{label}[]") for item in value)
        )
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ContractError(f"{label} object keys must be strings")
        return FrozenObject(
            tuple(
                (key, freeze_data(value[key], label=f"{label}.{key}"))
                for key in sorted(value)
            )
        )
    raise ContractError(
        f"{label} must be JSON-compatible plain data, got {type(value).__name__}"
    )


def plain_data(value: FrozenValue) -> Any:
    """Return a detached JSON-compatible representation of frozen data."""

    if isinstance(value, FrozenList):
        return [plain_data(item) for item in value.items]
    if isinstance(value, FrozenObject):
        return {key: plain_data(item) for key, item in value.items}
    return value


@dataclass(frozen=True, slots=True)
class ArtifactContract:
    kind: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "artifact kind")


@dataclass(frozen=True, slots=True)
class InputContract:
    name: str
    artifact: ArtifactContract
    required: bool = True
    cardinality: str = "scalar"

    def __post_init__(self) -> None:
        _require_name(self.name, "input name")
        if not isinstance(self.artifact, ArtifactContract):
            raise ContractError("input artifact must be an ArtifactContract")
        if not isinstance(self.required, bool):
            raise ContractError("input required must be a bool")
        if self.cardinality not in {"scalar", "collection"}:
            raise ContractError(
                "input cardinality must be either 'scalar' or 'collection'"
            )


_PLAIN_CONFIG_TYPES = (str, int, float, bool, list, dict, type(None))


@dataclass(frozen=True, slots=True)
class ConfigContract:
    name: str
    value_type: type
    required: bool = True

    def __post_init__(self) -> None:
        _require_name(self.name, "config name")
        if self.value_type not in _PLAIN_CONFIG_TYPES:
            raise ContractError(
                "config value_type must be one of str, int, float, bool, list, "
                "dict, or NoneType"
            )
        if not isinstance(self.required, bool):
            raise ContractError("config required must be a bool")


@dataclass(frozen=True, slots=True)
class OutputContract:
    name: str
    artifact: ArtifactContract

    def __post_init__(self) -> None:
        _require_name(self.name, "output name")
        if not isinstance(self.artifact, ArtifactContract):
            raise ContractError("output artifact must be an ArtifactContract")


@dataclass(frozen=True, slots=True)
class ResourceContract:
    """A descriptive resource request; it grants no scheduling authority."""

    name: str
    amount: int | float
    unit: str | None = None

    def __post_init__(self) -> None:
        _require_name(self.name, "resource name")
        if isinstance(self.amount, bool) or not isinstance(self.amount, int | float):
            raise ContractError("resource amount must be numeric")
        if isinstance(self.amount, float) and not math.isfinite(self.amount):
            raise ContractError("resource amount must be finite and positive")
        if self.amount <= 0:
            raise ContractError("resource amount must be finite and positive")
        if self.unit is not None:
            _require_text(self.unit, "resource unit")


@dataclass(frozen=True, slots=True)
class Policy:
    """Named, inspectable policy data with no executable semantics."""

    name: str
    options: FrozenObject | Mapping[str, Any] = field(default_factory=FrozenObject)

    def __post_init__(self) -> None:
        _require_id(self.name, "policy name")
        frozen = freeze_data(self.options, label=f"policy {self.name} options")
        if not isinstance(frozen, FrozenObject):
            raise ContractError("policy options must be a mapping")
        object.__setattr__(self, "options", frozen)


@dataclass(frozen=True, slots=True)
class NamedPolicyConstructor:
    """Callable syntax for constructing data-only policies of one name."""

    name: str

    def __post_init__(self) -> None:
        _require_id(self.name, "policy name")

    def __call__(self, **options: Any) -> Policy:
        return Policy(self.name, options)


def named_policy(name: str) -> NamedPolicyConstructor:
    return NamedPolicyConstructor(name)


def local(**options: Any) -> Policy:
    return Policy("local", options)


def resolve_policy(
    call_override: Policy | None,
    operation_default: Policy | None,
    plan_default: Policy | None,
) -> Policy:
    """Resolve the planning contract's precedence without executing a policy."""

    for candidate in (call_override, operation_default, plan_default):
        if candidate is not None:
            if not isinstance(candidate, Policy):
                raise ContractError("policy candidates must be Policy values or None")
            return candidate
    return local()


@dataclass(frozen=True, slots=True)
class OperationIdentity:
    name: str
    version: str

    def __post_init__(self) -> None:
        _require_text(self.name, "operation identity")
        _require_text(self.version, "operation version")


@dataclass(frozen=True, slots=True)
class FlowIdentity:
    name: str
    version: str

    def __post_init__(self) -> None:
        _require_text(self.name, "flow identity")
        _require_text(self.version, "flow version")


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    identity: OperationIdentity
    inputs: tuple[InputContract, ...] = ()
    config: tuple[ConfigContract, ...] = ()
    outputs: tuple[OutputContract, ...] = ()
    resources: tuple[ResourceContract, ...] = ()
    default_policy: Policy | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, OperationIdentity):
            raise ContractError("operation identity must be an OperationIdentity")
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "config", tuple(self.config))
        object.__setattr__(self, "outputs", tuple(self.outputs))
        object.__setattr__(self, "resources", tuple(self.resources))
        _require_instances(self.inputs, InputContract, "operation inputs")
        _require_instances(self.config, ConfigContract, "operation config")
        _require_instances(self.outputs, OutputContract, "operation outputs")
        _require_instances(self.resources, ResourceContract, "operation resources")
        if self.default_policy is not None and not isinstance(self.default_policy, Policy):
            raise ContractError("operation default_policy must be a Policy or None")


@dataclass(frozen=True, slots=True)
class FlowDefinition:
    identity: FlowIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, FlowIdentity):
            raise ContractError("flow identity must be a FlowIdentity")


@dataclass(frozen=True, slots=True)
class ArtifactSource:
    id: str
    uri: str
    artifact: ArtifactContract

    def __post_init__(self) -> None:
        _require_id(self.id, "artifact source id")
        _require_text(self.uri, "artifact source uri")
        if not isinstance(self.artifact, ArtifactContract):
            raise ContractError("source artifact must be an ArtifactContract")


@dataclass(frozen=True, slots=True)
class ArtifactSourceReference:
    source_id: str

    def __post_init__(self) -> None:
        _require_id(self.source_id, "artifact source reference")


@dataclass(frozen=True, slots=True)
class OutputReference:
    invocation_id: str
    output_name: str

    def __post_init__(self) -> None:
        _require_id(self.invocation_id, "output invocation id")
        _require_name(self.output_name, "output reference name")


ArtifactReference: TypeAlias = ArtifactSourceReference | OutputReference


@dataclass(frozen=True, slots=True)
class InputBinding:
    name: str
    reference: ArtifactReference
    cardinality: str = field(default="scalar", init=False)

    def __post_init__(self) -> None:
        _require_name(self.name, "input binding name")
        if not isinstance(self.reference, ArtifactSourceReference | OutputReference):
            raise ContractError("input binding must contain an artifact reference")


@dataclass(frozen=True, slots=True)
class CollectionInputBinding:
    """One ordered, non-empty collection of homogeneous artifact references."""

    name: str
    references: tuple[ArtifactReference, ...]
    cardinality: str = field(default="collection", init=False)

    def __post_init__(self) -> None:
        _require_name(self.name, "collection input binding name")
        object.__setattr__(self, "references", tuple(self.references))
        if not self.references:
            raise ContractError("collection input binding must not be empty")
        if not all(
            isinstance(reference, ArtifactSourceReference | OutputReference)
            for reference in self.references
        ):
            raise ContractError(
                "collection input binding must contain only artifact references"
            )


ArtifactInputBinding: TypeAlias = InputBinding | CollectionInputBinding


@dataclass(frozen=True, slots=True)
class ConfigBinding:
    name: str
    value: FrozenValue | Any

    def __post_init__(self) -> None:
        _require_name(self.name, "config binding name")
        object.__setattr__(
            self, "value", freeze_data(self.value, label=f"config {self.name}")
        )


@dataclass(frozen=True, slots=True)
class Invocation:
    id: str
    operation: OperationIdentity
    inputs: tuple[ArtifactInputBinding, ...] = ()
    config: tuple[ConfigBinding, ...] = ()
    policy: Policy = field(default_factory=local)
    boundary_id: str | None = None
    authored_key: str | None = None

    def __post_init__(self) -> None:
        _require_id(self.id, "invocation id")
        if not isinstance(self.operation, OperationIdentity):
            raise ContractError("invocation operation must be an OperationIdentity")
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "config", tuple(self.config))
        if not all(
            isinstance(value, InputBinding | CollectionInputBinding)
            for value in self.inputs
        ):
            raise ContractError(
                "invocation inputs must contain only InputBinding or "
                "CollectionInputBinding values"
            )
        _require_instances(self.config, ConfigBinding, "invocation config")
        if not isinstance(self.policy, Policy):
            raise ContractError("invocation policy must be a resolved Policy")
        if self.boundary_id is not None:
            _require_id(self.boundary_id, "invocation boundary id")
        if self.authored_key is not None:
            normalize_authored_key(self.authored_key)


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    id: str
    source: ArtifactReference
    target_invocation_id: str
    target_input_name: str
    artifact_kind: str
    target_member_index: int | None = None

    def __post_init__(self) -> None:
        _require_id(self.id, "dependency edge id")
        if not isinstance(self.source, ArtifactSourceReference | OutputReference):
            raise ContractError(
                "dependency edge source must be an artifact reference"
            )
        _require_id(self.target_invocation_id, "dependency target invocation id")
        _require_name(self.target_input_name, "dependency target input name")
        _require_text(self.artifact_kind, "dependency artifact kind")
        if self.target_member_index is not None and (
            isinstance(self.target_member_index, bool)
            or not isinstance(self.target_member_index, int)
            or self.target_member_index < 0
        ):
            raise ContractError(
                "dependency target_member_index must be a non-negative integer or None"
            )


@dataclass(frozen=True, slots=True)
class NamedOutput:
    name: str
    reference: OutputReference

    def __post_init__(self) -> None:
        _require_name(self.name, "named output")
        if not isinstance(self.reference, OutputReference):
            raise ContractError("named output must contain an OutputReference")


@dataclass(frozen=True, slots=True)
class FlowBoundary:
    id: str
    flow: FlowIdentity
    parent_id: str | None = None
    outputs: tuple[NamedOutput, ...] = ()
    authored_key: str | None = None

    def __post_init__(self) -> None:
        _require_id(self.id, "flow boundary id")
        if not isinstance(self.flow, FlowIdentity):
            raise ContractError("flow boundary flow must be a FlowIdentity")
        if self.parent_id is not None:
            _require_id(self.parent_id, "flow boundary parent id")
        object.__setattr__(self, "outputs", tuple(self.outputs))
        _require_instances(self.outputs, NamedOutput, "flow boundary outputs")
        if self.authored_key is not None:
            normalize_authored_key(self.authored_key)


def _require_instances(values: tuple[Any, ...], expected: type, label: str) -> None:
    if not all(isinstance(value, expected) for value in values):
        raise ContractError(f"{label} must contain only {expected.__name__} values")


@dataclass(frozen=True, slots=True)
class Plan:
    """A normalized static graph whose only behavior is inspection/validation."""

    operations: tuple[OperationDefinition, ...] = ()
    flows: tuple[FlowDefinition, ...] = ()
    sources: tuple[ArtifactSource, ...] = ()
    invocations: tuple[Invocation, ...] = ()
    edges: tuple[DependencyEdge, ...] = ()
    boundaries: tuple[FlowBoundary, ...] = ()
    outputs: tuple[NamedOutput, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        sequence_fields = (
            ("operations", OperationDefinition),
            ("flows", FlowDefinition),
            ("sources", ArtifactSource),
            ("invocations", Invocation),
            ("edges", DependencyEdge),
            ("boundaries", FlowBoundary),
            ("outputs", NamedOutput),
        )
        for name, expected in sequence_fields:
            values = tuple(getattr(self, name))
            object.__setattr__(self, name, values)
            _require_instances(values, expected, f"plan {name}")
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version < 1
        ):
            raise ContractError("plan schema_version must be a positive integer")

    def validate(self) -> "Plan":
        issues: list[ValidationIssue] = []

        def issue(code: str, path: str, message: str) -> None:
            issues.append(ValidationIssue(code, path, message))

        operations = _unique_index(
            self.operations,
            lambda value: value.identity,
            "operations",
            "duplicate_operation",
            issue,
        )
        flows = _unique_index(
            self.flows,
            lambda value: value.identity,
            "flows",
            "duplicate_flow",
            issue,
        )
        sources = _unique_index(
            self.sources,
            lambda value: value.id,
            "sources",
            "duplicate_source_id",
            issue,
        )
        invocations = _unique_index(
            self.invocations,
            lambda value: value.id,
            "invocations",
            "duplicate_invocation_id",
            issue,
        )
        _unique_index(
            self.edges,
            lambda value: value.id,
            "edges",
            "duplicate_edge_id",
            issue,
        )
        boundaries = _unique_index(
            self.boundaries,
            lambda value: value.id,
            "boundaries",
            "duplicate_boundary_id",
            issue,
        )
        _check_named_uniqueness(self.outputs, "outputs", "duplicate_plan_output", issue)

        scoped_authored_keys: dict[tuple[str | None, str], str] = {}

        def check_authored_key(
            authored_key: object,
            scope_id: str | None,
            path: str,
            owner_kind: str,
            owner_id: str,
        ) -> None:
            if authored_key is None:
                return
            if not isinstance(authored_key, str) or not _AUTHORED_KEY_PATTERN.fullmatch(
                authored_key
            ):
                issue(
                    "invalid_authored_key",
                    f"{path}.authored_key",
                    "key does not use the executor-neutral Plan ID syntax",
                )
                return
            scoped_key = (scope_id, authored_key)
            existing_path = scoped_authored_keys.get(scoped_key)
            if existing_path is not None:
                issue(
                    "duplicate_authored_key",
                    f"{path}.authored_key",
                    f"key {authored_key!r} is already used at {existing_path}",
                )
            else:
                scoped_authored_keys[scoped_key] = f"{path}.authored_key"
            expected_id = _keyed_plan_id(owner_kind, scope_id, authored_key)
            if owner_id != expected_id:
                issue(
                    f"keyed_{owner_kind}_id_mismatch",
                    f"{path}.id",
                    "ID is not derived from its containing scope and authored key",
                )

        for invocation_index, invocation in enumerate(self.invocations):
            check_authored_key(
                invocation.authored_key,
                invocation.boundary_id,
                f"invocations[{invocation_index}]",
                "invoke",
                invocation.id,
            )
        for boundary_index, boundary in enumerate(self.boundaries):
            check_authored_key(
                boundary.authored_key,
                boundary.parent_id,
                f"boundaries[{boundary_index}]",
                "flow",
                boundary.id,
            )

        for op_index, operation in enumerate(self.operations):
            path = f"operations[{op_index}]"
            _check_named_uniqueness(
                operation.inputs, f"{path}.inputs", "duplicate_input_contract", issue
            )
            _check_named_uniqueness(
                operation.config, f"{path}.config", "duplicate_config_contract", issue
            )
            _check_named_uniqueness(
                operation.outputs, f"{path}.outputs", "duplicate_output_contract", issue
            )
            _check_named_uniqueness(
                operation.resources,
                f"{path}.resources",
                "duplicate_resource_contract",
                issue,
            )
            input_names = {contract.name for contract in operation.inputs}
            config_names = {contract.name for contract in operation.config}
            for name in sorted(input_names & config_names):
                issue(
                    "binding_name_collision",
                    path,
                    f"{name!r} is declared as both input and config",
                )

        for boundary_index, boundary in enumerate(self.boundaries):
            path = f"boundaries[{boundary_index}]"
            if boundary.flow not in flows:
                issue("unknown_flow", f"{path}.flow", "flow definition is absent")
            if boundary.parent_id is not None and boundary.parent_id not in boundaries:
                issue(
                    "unknown_parent_boundary",
                    f"{path}.parent_id",
                    f"boundary {boundary.parent_id!r} is absent",
                )
            if boundary.parent_id == boundary.id:
                issue("boundary_cycle", f"{path}.parent_id", "boundary is its own parent")
            _check_named_uniqueness(
                boundary.outputs,
                f"{path}.outputs",
                "duplicate_boundary_output",
                issue,
            )
        _check_boundary_cycles(boundaries, issue)

        operation_for_invocation: dict[str, OperationDefinition] = {}
        expected_edges: dict[
            tuple[str, str, int | None], ArtifactReference
        ] = {}
        for invocation_index, invocation in enumerate(self.invocations):
            path = f"invocations[{invocation_index}]"
            operation = operations.get(invocation.operation)
            if operation is None:
                issue(
                    "unknown_operation",
                    f"{path}.operation",
                    "operation definition is absent",
                )
                continue
            operation_for_invocation.setdefault(invocation.id, operation)
            if invocation.boundary_id is not None and invocation.boundary_id not in boundaries:
                issue(
                    "unknown_invocation_boundary",
                    f"{path}.boundary_id",
                    f"boundary {invocation.boundary_id!r} is absent",
                )

            input_contracts = {contract.name: contract for contract in operation.inputs}
            config_contracts = {contract.name: contract for contract in operation.config}
            _check_named_uniqueness(
                invocation.inputs, f"{path}.inputs", "duplicate_input_binding", issue
            )
            _check_named_uniqueness(
                invocation.config, f"{path}.config", "duplicate_config_binding", issue
            )
            bound_inputs = {binding.name for binding in invocation.inputs}
            bound_config = {binding.name for binding in invocation.config}
            for contract in operation.inputs:
                if contract.required and contract.name not in bound_inputs:
                    issue(
                        "missing_input",
                        f"{path}.inputs",
                        f"required input {contract.name!r} is not bound",
                    )
            for contract in operation.config:
                if contract.required and contract.name not in bound_config:
                    issue(
                        "missing_config",
                        f"{path}.config",
                        f"required config {contract.name!r} is not bound",
                    )

            for binding_index, binding in enumerate(invocation.inputs):
                binding_path = f"{path}.inputs[{binding_index}]"
                contract = input_contracts.get(binding.name)
                if contract is None:
                    issue(
                        "unexpected_input",
                        binding_path,
                        f"input {binding.name!r} is not declared",
                    )
                    continue
                if binding.cardinality != contract.cardinality:
                    issue(
                        "input_cardinality_mismatch",
                        binding_path,
                        f"expected {contract.cardinality!r}, got "
                        f"{binding.cardinality!r}",
                    )
                if isinstance(binding, InputBinding):
                    indexed_references = ((None, binding.reference),)
                else:
                    indexed_references = tuple(enumerate(binding.references))
                for member_index, reference in indexed_references:
                    reference_path = (
                        binding_path
                        if member_index is None
                        else f"{binding_path}.references[{member_index}]"
                    )
                    reference_kind = _reference_kind(
                        reference,
                        sources,
                        invocations,
                        operation_for_invocation,
                        operations,
                        reference_path,
                        issue,
                    )
                    if (
                        reference_kind is not None
                        and reference_kind != contract.artifact.kind
                    ):
                        issue(
                            "input_kind_mismatch",
                            reference_path,
                            f"expected {contract.artifact.kind!r}, got "
                            f"{reference_kind!r}",
                        )
                    if (
                        contract.cardinality == "collection"
                        or isinstance(reference, OutputReference)
                    ):
                        expected_edges[
                            (invocation.id, binding.name, member_index)
                        ] = reference

            for binding_index, binding in enumerate(invocation.config):
                binding_path = f"{path}.config[{binding_index}]"
                contract = config_contracts.get(binding.name)
                if contract is None:
                    issue(
                        "unexpected_config",
                        binding_path,
                        f"config {binding.name!r} is not declared",
                    )
                elif not _matches_config_type(binding.value, contract.value_type):
                    issue(
                        "config_type_mismatch",
                        binding_path,
                        f"expected {contract.value_type.__name__}",
                    )

        seen_edge_targets: set[tuple[str, str, int | None]] = set()
        dependency_pairs: list[tuple[str, str]] = []
        for edge_index, edge in enumerate(self.edges):
            path = f"edges[{edge_index}]"
            target_key = (
                edge.target_invocation_id,
                edge.target_input_name,
                edge.target_member_index,
            )
            if target_key in seen_edge_targets:
                issue(
                    "duplicate_target_edge",
                    path,
                    "more than one edge targets the same invocation input member",
                )
            seen_edge_targets.add(target_key)
            expected_source = expected_edges.get(target_key)
            if expected_source is None:
                issue(
                    "edge_without_output_binding",
                    path,
                    "target input is absent, source-bound, or otherwise invalid",
                )
            elif edge.source != expected_source:
                issue(
                    "edge_binding_mismatch",
                    path,
                    "edge source differs from the target input binding",
                )

            source_kind = _reference_kind(
                edge.source,
                sources,
                invocations,
                operation_for_invocation,
                operations,
                f"{path}.source",
                issue,
            )
            target_operation = operation_for_invocation.get(edge.target_invocation_id)
            target_contract = None
            target_binding = None
            if target_operation is None:
                issue(
                    "unknown_edge_target",
                    f"{path}.target_invocation_id",
                    f"invocation {edge.target_invocation_id!r} is absent or invalid",
                )
            else:
                target_contract = next(
                    (
                        contract
                        for contract in target_operation.inputs
                        if contract.name == edge.target_input_name
                    ),
                    None,
                )
                if target_contract is None:
                    issue(
                        "unknown_edge_input",
                        f"{path}.target_input_name",
                        f"input {edge.target_input_name!r} is not declared",
                    )
                target_invocation = invocations.get(edge.target_invocation_id)
                if target_invocation is not None:
                    target_binding = next(
                        (
                            binding
                            for binding in target_invocation.inputs
                            if binding.name == edge.target_input_name
                        ),
                        None,
                    )
            if target_contract is not None:
                if (
                    target_contract.cardinality == "scalar"
                    and edge.target_member_index is not None
                ):
                    issue(
                        "unexpected_edge_member_position",
                        f"{path}.target_member_index",
                        "scalar inputs must not have a member position",
                    )
                elif target_contract.cardinality == "collection":
                    if edge.target_member_index is None:
                        issue(
                            "missing_edge_member_position",
                            f"{path}.target_member_index",
                            "collection input edges require a member position",
                        )
                    elif (
                        isinstance(target_binding, CollectionInputBinding)
                        and edge.target_member_index >= len(target_binding.references)
                    ):
                        issue(
                            "invalid_edge_member_position",
                            f"{path}.target_member_index",
                            "member position is outside the collection binding",
                        )
            if source_kind is not None and edge.artifact_kind != source_kind:
                issue(
                    "edge_source_kind_mismatch",
                    f"{path}.artifact_kind",
                    f"edge says {edge.artifact_kind!r}, source produces {source_kind!r}",
                )
            if (
                target_contract is not None
                and edge.artifact_kind != target_contract.artifact.kind
            ):
                issue(
                    "edge_target_kind_mismatch",
                    f"{path}.artifact_kind",
                    f"edge says {edge.artifact_kind!r}, target accepts "
                    f"{target_contract.artifact.kind!r}",
                )
            if (
                isinstance(edge.source, OutputReference)
                and edge.source.invocation_id in invocations
                and edge.target_invocation_id in invocations
            ):
                dependency_pairs.append(
                    (edge.source.invocation_id, edge.target_invocation_id)
                )
                source_invocation = invocations[edge.source.invocation_id]
                target_invocation = invocations[edge.target_invocation_id]
                if (
                    source_invocation.authored_key is not None
                    and target_invocation.authored_key is not None
                ):
                    expected_edge_id = _stable_edge_id(
                        edge.source,
                        edge.target_invocation_id,
                        edge.target_input_name,
                        edge.target_member_index,
                    )
                    if edge.id != expected_edge_id:
                        issue(
                            "stable_edge_id_mismatch",
                            f"{path}.id",
                            "edge ID is not derived from its stable endpoints, "
                            "target input, and member position",
                        )

        for target_key, source in expected_edges.items():
            if target_key not in seen_edge_targets:
                member_suffix = (
                    "" if target_key[2] is None else f"[{target_key[2]}]"
                )
                issue(
                    "missing_dependency_edge",
                    f"invocations[{target_key[0]}].inputs[{target_key[1]}]"
                    f"{member_suffix}",
                    f"artifact binding from {_reference_label(source)} has no edge",
                )
        if _has_dependency_cycle(invocations, dependency_pairs):
            issue("dependency_cycle", "edges", "dependency graph must be acyclic")

        for boundary_index, boundary in enumerate(self.boundaries):
            for output_index, output in enumerate(boundary.outputs):
                path = f"boundaries[{boundary_index}].outputs[{output_index}]"
                _reference_kind(
                    output.reference,
                    sources,
                    invocations,
                    operation_for_invocation,
                    operations,
                    path,
                    issue,
                )
                owner = invocations.get(output.reference.invocation_id)
                if owner is not None and not _is_boundary_descendant(
                    owner.boundary_id, boundary.id, boundaries
                ):
                    issue(
                        "boundary_output_not_owned",
                        path,
                        "output invocation is not contained by this boundary",
                    )

        for output_index, output in enumerate(self.outputs):
            _reference_kind(
                output.reference,
                sources,
                invocations,
                operation_for_invocation,
                operations,
                f"outputs[{output_index}]",
                issue,
            )

        if issues:
            raise PlanValidationError(issues)
        return self

    def to_data(self) -> dict[str, Any]:
        """Return deterministic plain data, independent of tuple insertion order."""

        return {
            "schema_version": self.schema_version,
            "operations": [
                _operation_data(value)
                for value in sorted(self.operations, key=_operation_sort_key)
            ],
            "flows": [
                {"identity": _flow_identity_data(value.identity)}
                for value in sorted(self.flows, key=_flow_sort_key)
            ],
            "sources": [
                {
                    "id": value.id,
                    "uri": value.uri,
                    "artifact": _artifact_data(value.artifact),
                }
                for value in sorted(self.sources, key=lambda item: item.id)
            ],
            "invocations": [
                _invocation_data(value)
                for value in sorted(self.invocations, key=lambda item: item.id)
            ],
            "edges": [
                {
                    "id": value.id,
                    "source": _reference_data(value.source),
                    "target_invocation_id": value.target_invocation_id,
                    "target_input_name": value.target_input_name,
                    "target_member_index": value.target_member_index,
                    "artifact_kind": value.artifact_kind,
                }
                for value in sorted(self.edges, key=lambda item: item.id)
            ],
            "boundaries": [
                {
                    "id": value.id,
                    "flow": _flow_identity_data(value.flow),
                    "parent_id": value.parent_id,
                    "authored_key": value.authored_key,
                    "outputs": _named_outputs_data(value.outputs),
                }
                for value in sorted(self.boundaries, key=lambda item: item.id)
            ],
            "outputs": _named_outputs_data(self.outputs),
        }

    def to_json(self) -> str:
        """Return canonical compact JSON suitable for inspection and comparison."""

        return json.dumps(
            self.to_data(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )


def _unique_index(values, key, path, code, issue):
    result = {}
    seen = set()
    for index, value in enumerate(values):
        item_key = key(value)
        if item_key in seen:
            issue(code, f"{path}[{index}]", f"duplicate value {item_key!r}")
        else:
            seen.add(item_key)
            result[item_key] = value
    return result


def _check_named_uniqueness(values, path, code, issue):
    seen: set[str] = set()
    for index, value in enumerate(values):
        if value.name in seen:
            issue(code, f"{path}[{index}]", f"duplicate name {value.name!r}")
        seen.add(value.name)


def _reference_kind(
    reference,
    sources,
    invocations,
    operation_for_invocation,
    operations,
    path,
    issue,
):
    if isinstance(reference, ArtifactSourceReference):
        source = sources.get(reference.source_id)
        if source is None:
            issue(
                "unknown_artifact_source",
                path,
                f"source {reference.source_id!r} is absent",
            )
            return None
        return source.artifact.kind
    invocation = invocations.get(reference.invocation_id)
    if invocation is None:
        issue(
            "unknown_output_invocation",
            path,
            f"invocation {reference.invocation_id!r} is absent",
        )
        return None
    operation = operation_for_invocation.get(invocation.id) or operations.get(
        invocation.operation
    )
    if operation is None:
        issue(
            "unknown_output_operation",
            path,
            "owning invocation has no operation definition",
        )
        return None
    output = next(
        (value for value in operation.outputs if value.name == reference.output_name),
        None,
    )
    if output is None:
        issue(
            "unknown_owned_output",
            path,
            f"operation does not declare output {reference.output_name!r}",
        )
        return None
    return output.artifact.kind


def _matches_config_type(value: FrozenValue, expected: type) -> bool:
    if expected is list:
        return isinstance(value, FrozenList)
    if expected is dict:
        return isinstance(value, FrozenObject)
    if expected is type(None):
        return value is None
    return type(value) is expected


def _check_boundary_cycles(boundaries, issue) -> None:
    for boundary_id in boundaries:
        visited: set[str] = set()
        cursor: str | None = boundary_id
        while cursor is not None and cursor in boundaries:
            if cursor in visited:
                issue(
                    "boundary_cycle",
                    f"boundaries[{boundary_id}]",
                    "parent links must be acyclic",
                )
                break
            visited.add(cursor)
            cursor = boundaries[cursor].parent_id


def _is_boundary_descendant(candidate, ancestor, boundaries) -> bool:
    cursor = candidate
    visited: set[str] = set()
    while cursor is not None and cursor not in visited:
        if cursor == ancestor:
            return True
        visited.add(cursor)
        boundary = boundaries.get(cursor)
        cursor = boundary.parent_id if boundary is not None else None
    return False


def _has_dependency_cycle(invocations, pairs) -> bool:
    adjacency: dict[str, set[str]] = {identifier: set() for identifier in invocations}
    for source, target in pairs:
        adjacency[source].add(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> bool:
        if identifier in visiting:
            return True
        if identifier in visited:
            return False
        visiting.add(identifier)
        if any(visit(target) for target in adjacency[identifier]):
            return True
        visiting.remove(identifier)
        visited.add(identifier)
        return False

    return any(visit(identifier) for identifier in adjacency if identifier not in visited)


def _operation_sort_key(value: OperationDefinition):
    return value.identity.name, value.identity.version


def _flow_sort_key(value: FlowDefinition):
    return value.identity.name, value.identity.version


def _operation_identity_data(value: OperationIdentity) -> dict[str, str]:
    return {"name": value.name, "version": value.version}


def _flow_identity_data(value: FlowIdentity) -> dict[str, str]:
    return {"name": value.name, "version": value.version}


def _artifact_data(value: ArtifactContract) -> dict[str, str]:
    return {"kind": value.kind}


def _policy_data(value: Policy) -> dict[str, Any]:
    return {"name": value.name, "options": plain_data(value.options)}


def _operation_data(value: OperationDefinition) -> dict[str, Any]:
    return {
        "identity": _operation_identity_data(value.identity),
        "inputs": [
            {
                "name": item.name,
                "artifact": _artifact_data(item.artifact),
                "required": item.required,
                "cardinality": item.cardinality,
            }
            for item in sorted(value.inputs, key=lambda item: item.name)
        ],
        "config": [
            {
                "name": item.name,
                "value_type": f"{item.value_type.__module__}.{item.value_type.__qualname__}",
                "required": item.required,
            }
            for item in sorted(value.config, key=lambda item: item.name)
        ],
        "outputs": [
            {"name": item.name, "artifact": _artifact_data(item.artifact)}
            for item in sorted(value.outputs, key=lambda item: item.name)
        ],
        "resources": [
            {"name": item.name, "amount": item.amount, "unit": item.unit}
            for item in sorted(value.resources, key=lambda item: item.name)
        ],
        "default_policy": (
            _policy_data(value.default_policy)
            if value.default_policy is not None
            else None
        ),
    }


def _reference_data(value: ArtifactReference) -> dict[str, str]:
    if isinstance(value, ArtifactSourceReference):
        return {"type": "source", "source_id": value.source_id}
    return {
        "type": "output",
        "invocation_id": value.invocation_id,
        "output_name": value.output_name,
    }


def _reference_label(value: ArtifactReference) -> str:
    if isinstance(value, ArtifactSourceReference):
        return value.source_id
    return f"{value.invocation_id}.{value.output_name}"


def _invocation_data(value: Invocation) -> dict[str, Any]:
    return {
        "id": value.id,
        "operation": _operation_identity_data(value.operation),
        "inputs": [
            _input_binding_data(item)
            for item in sorted(value.inputs, key=lambda item: item.name)
        ],
        "config": [
            {"name": item.name, "value": plain_data(item.value)}
            for item in sorted(value.config, key=lambda item: item.name)
        ],
        "policy": _policy_data(value.policy),
        "boundary_id": value.boundary_id,
        "authored_key": value.authored_key,
    }


def _input_binding_data(value: ArtifactInputBinding) -> dict[str, Any]:
    if isinstance(value, InputBinding):
        return {
            "name": value.name,
            "cardinality": value.cardinality,
            "reference": _reference_data(value.reference),
        }
    return {
        "name": value.name,
        "cardinality": value.cardinality,
        "references": [
            _reference_data(reference) for reference in value.references
        ],
    }


def _named_outputs_data(values: tuple[NamedOutput, ...]) -> list[dict[str, Any]]:
    return [
        {"name": value.name, "reference": _reference_data(value.reference)}
        for value in sorted(values, key=lambda item: item.name)
    ]


__all__ = [
    "ArtifactContract",
    "ArtifactInputBinding",
    "ArtifactReference",
    "ArtifactSource",
    "ArtifactSourceReference",
    "ConfigBinding",
    "ConfigContract",
    "CollectionInputBinding",
    "ContractError",
    "DependencyEdge",
    "FlowBoundary",
    "FlowDefinition",
    "FlowIdentity",
    "FrozenList",
    "FrozenObject",
    "InputBinding",
    "InputContract",
    "Invocation",
    "ModelError",
    "NamedOutput",
    "NamedPolicyConstructor",
    "OperationDefinition",
    "OperationIdentity",
    "OutputContract",
    "OutputReference",
    "Plan",
    "PlanValidationError",
    "Policy",
    "ResourceContract",
    "ValidationIssue",
    "freeze_data",
    "local",
    "named_policy",
    "plain_data",
    "resolve_policy",
]
