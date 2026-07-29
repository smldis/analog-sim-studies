from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence, cast


SpiceFormat = Literal["eldo", "ngspice"]
SUPPORTED_SPICE_FORMATS: tuple[SpiceFormat, ...] = ("eldo", "ngspice")


class CanonicalParseError(ValueError):
    """Raised when a netlist is structurally inconsistent."""


@dataclass(frozen=True)
class Diagnostic:
    """A non-fatal omission or parsing assumption."""

    line: int
    message: str
    source: Path | None = None


@dataclass(frozen=True)
class Connection:
    """A named device or subcircuit pin connected to a net."""

    pin: str
    net: str


@dataclass(frozen=True)
class Parameter:
    """A device parameter rendered as a named value."""

    name: str
    value: str


@dataclass(frozen=True)
class Device:
    """One primitive device or subcircuit instance."""

    name: str
    type: str
    connections: tuple[Connection, ...]
    parameters: tuple[Parameter, ...] = ()


@dataclass(frozen=True)
class Circuit:
    """The top level or one named subcircuit."""

    name: str
    pins: tuple[str, ...]
    devices: tuple[Device, ...]


@dataclass(frozen=True)
class CanonicalNetlist:
    """Parsed circuits plus any non-fatal extraction diagnostics."""

    top: Circuit
    subcircuits: tuple[Circuit, ...]
    diagnostics: tuple[Diagnostic, ...] = ()

    def render(self) -> str:
        """Render the canonical tabular representation."""

        sections = []
        if self.top.devices:
            sections.append(
                f"TOP_LEVEL {_cell(self.top.name)}\n\n{_render_circuit_tables(self.top)}"
            )
        for circuit in self.subcircuits:
            sections.append(_render_subcircuit(circuit))
        return "\n\n".join(sections) + ("\n" if sections else "")


@dataclass(frozen=True)
class _LogicalStatement:
    line: int
    text: str
    source: Path | None = None


@dataclass(frozen=True)
class _RawDevice:
    line: int
    tokens: tuple[str, ...]
    source: Path | None = None


@dataclass
class _CircuitBuilder:
    name: str
    pins: tuple[str, ...]
    raw_devices: list[_RawDevice]


@dataclass(frozen=True)
class _FixedDeviceSpec:
    type: str
    pins: tuple[str, ...]
    tail: str


_FIXED_DEVICE_SPECS = {
    "R": _FixedDeviceSpec("resistor", ("p", "n"), "value"),
    "C": _FixedDeviceSpec("capacitor", ("p", "n"), "value"),
    "L": _FixedDeviceSpec("inductor", ("p", "n"), "value"),
    "V": _FixedDeviceSpec("vsource", ("p", "n"), "source"),
    "I": _FixedDeviceSpec("isource", ("p", "n"), "source"),
    "B": _FixedDeviceSpec("behavioral_source", ("p", "n"), "source"),
    "D": _FixedDeviceSpec("diode", ("a", "k"), "model"),
    "M": _FixedDeviceSpec("mosfet", ("d", "g", "s", "b"), "model"),
    "J": _FixedDeviceSpec("jfet", ("d", "g", "s"), "model"),
    "E": _FixedDeviceSpec("vcvs", ("p", "n", "cp", "cn"), "gain"),
    "G": _FixedDeviceSpec("vccs", ("p", "n", "cp", "cn"), "gain"),
    "F": _FixedDeviceSpec("cccs", ("p", "n"), "control"),
    "H": _FixedDeviceSpec("ccvs", ("p", "n"), "control"),
    "S": _FixedDeviceSpec("voltage_switch", ("p", "n", "cp", "cn"), "model"),
    "T": _FixedDeviceSpec("transmission_line", ("p1", "n1", "p2", "n2"), "model"),
    "O": _FixedDeviceSpec(
        "lossy_transmission_line", ("p1", "n1", "p2", "n2"), "model"
    ),
    "W": _FixedDeviceSpec("current_switch", ("p", "n"), "control_model"),
}

_NGSPICE_FIXED_DEVICE_SPECS = {
    "U": _FixedDeviceSpec("uniform_rc_line", ("p", "n", "common"), "model"),
    "Z": _FixedDeviceSpec("mesfet", ("d", "g", "s"), "model"),
}

_MODEL_DEVICE_PREFIXES = {"D", "J", "M", "Q", "S", "T", "O", "U", "W", "Z"}
_ASSIGNMENT_RE = re.compile(r"^([^=\s]+)=(.*)$")


def from_text(
    text: str,
    *,
    top_name: str = "TOP",
    spice_format: SpiceFormat = "eldo",
    device_type_map: Mapping[str, str] | None = None,
) -> CanonicalNetlist:
    """Extract the canonical representation from a supported SPICE string.

    Common SPICE primitives and named subcircuit calls are resolved structurally.
    Simulator directives are ignored. Unsupported device statements are retained
    as unresolved device rows and reported through ``diagnostics``.
    """

    spice_format = _validate_spice_format(spice_format)
    statements = tuple(
        _logical_statements(
            text,
            semicolon_comments=spice_format == "ngspice",
            skip_title=spice_format == "ngspice",
        )
    )
    netlist = _from_statements(
        statements, top_name=top_name, spice_format=spice_format
    )
    return normalize_device_types(netlist, device_type_map or {})


def from_file(
    path: str | Path,
    *,
    top_name: str = "TOP",
    spice_format: SpiceFormat = "eldo",
    stop_include: Sequence[str] = (),
    external_subcircuits: Mapping[str, Sequence[str]] | None = None,
    device_type_map: Mapping[str, str] | None = None,
) -> CanonicalNetlist:
    """Extract a canonical netlist and recursively expand available includes.

    Relative include paths are resolved from the directory of the file containing
    the directive. ``.LIB`` files are opaque model-library boundaries. Include
    paths matching a ``stop_include`` glob are likewise left opaque. External
    subcircuit pin signatures may be supplied for instances defined beyond a
    boundary. Missing includes and include cycles are reported as diagnostics.
    """

    spice_format = _validate_spice_format(spice_format)
    input_path = Path(path).expanduser().resolve()
    diagnostics: list[Diagnostic] = []
    statements = tuple(
        _statements_from_file(
            input_path,
            active=(),
            diagnostics=diagnostics,
            spice_format=spice_format,
            is_root=True,
            stop_include=stop_include,
        )
    )
    netlist = _from_statements(
        statements,
        top_name=top_name,
        spice_format=spice_format,
        initial_diagnostics=diagnostics,
        external_subcircuits=external_subcircuits or {},
    )
    return normalize_device_types(netlist, device_type_map or {})


def normalize_device_types(
    netlist: CanonicalNetlist, device_type_map: Mapping[str, str]
) -> CanonicalNetlist:
    """Return a netlist with explicitly mapped device types normalized.

    Matching is case-insensitive.  Each changed device retains its library-level
    type as a ``source_type`` parameter.  An empty map is an identity pass.
    """

    aliases = {source.casefold(): target for source, target in device_type_map.items()}
    if not aliases:
        return netlist

    def normalize_circuit(circuit: Circuit) -> Circuit:
        devices = []
        for device in circuit.devices:
            normalized = aliases.get(device.type.casefold())
            if normalized is None or normalized == device.type:
                devices.append(device)
                continue
            parameters = device.parameters
            if not any(
                parameter.name.casefold() == "source_type"
                for parameter in parameters
            ):
                parameters = (*parameters, Parameter("source_type", device.type))
            devices.append(
                Device(
                    name=device.name,
                    type=normalized,
                    connections=device.connections,
                    parameters=parameters,
                )
            )
        return Circuit(circuit.name, circuit.pins, tuple(devices))

    return CanonicalNetlist(
        top=normalize_circuit(netlist.top),
        subcircuits=tuple(normalize_circuit(item) for item in netlist.subcircuits),
        diagnostics=netlist.diagnostics,
    )


def _from_statements(
    statements: Sequence[_LogicalStatement],
    *,
    top_name: str,
    spice_format: SpiceFormat,
    initial_diagnostics: Sequence[Diagnostic] = (),
    external_subcircuits: Mapping[str, Sequence[str]] = {},
) -> CanonicalNetlist:
    top = _CircuitBuilder(name=top_name, pins=(), raw_devices=[])
    subcircuits: list[_CircuitBuilder] = []
    subcircuits_by_name: dict[str, _CircuitBuilder] = {}
    models: dict[str, tuple[str, str]] = {}
    current = top
    in_control = False

    for statement in statements:
        tokens = tuple(_split_tokens(statement.text))
        if not tokens:
            continue
        keyword = tokens[0].casefold()
        if spice_format == "ngspice":
            if keyword == ".control":
                if in_control:
                    raise CanonicalParseError(
                        f"line {statement.line}: nested .CONTROL blocks are unsupported"
                    )
                in_control = True
                continue
            if keyword == ".endc":
                if not in_control:
                    raise CanonicalParseError(
                        f"line {statement.line}: .ENDC appears outside .CONTROL"
                    )
                in_control = False
                continue
            if in_control:
                continue
        if keyword == ".subckt":
            if current is not top:
                raise CanonicalParseError(
                    f"line {statement.line}: nested .SUBCKT declarations are unsupported"
                )
            name, pins = _parse_subckt_header(tokens, statement.line)
            key = name.casefold()
            if key in subcircuits_by_name:
                raise CanonicalParseError(
                    f"line {statement.line}: duplicate subcircuit {name!r}"
                )
            current = _CircuitBuilder(name=name, pins=pins, raw_devices=[])
            subcircuits.append(current)
            subcircuits_by_name[key] = current
            continue
        if keyword == ".ends":
            if current is top:
                raise CanonicalParseError(
                    f"line {statement.line}: .ENDS appears outside a subcircuit"
                )
            if len(tokens) > 1 and tokens[1].casefold() != current.name.casefold():
                raise CanonicalParseError(
                    f"line {statement.line}: .ENDS {tokens[1]!r} does not match "
                    f".SUBCKT {current.name!r}"
                )
            current = top
            continue
        if keyword == ".model":
            _record_model(tokens, statement.line, models)
            continue
        if tokens[0].startswith("."):
            continue
        current.raw_devices.append(
            _RawDevice(statement.line, tokens, source=statement.source)
        )

    if in_control:
        raise CanonicalParseError("ngspice .CONTROL block is missing .ENDC")
    if current is not top:
        raise CanonicalParseError(f"subcircuit {current.name!r} is missing .ENDS")

    diagnostics = list(initial_diagnostics)
    instance_definitions: dict[str, _CircuitBuilder | tuple[str, ...]] = {
        **subcircuits_by_name,
        **{
            name.casefold(): tuple(pins)
            for name, pins in external_subcircuits.items()
            if name.casefold() not in subcircuits_by_name
        },
    }
    parsed_circuits = [
        _build_circuit(
            builder,
            instance_definitions,
            models,
            diagnostics,
            spice_format=spice_format,
        )
        for builder in [top, *subcircuits]
    ]
    return CanonicalNetlist(
        top=parsed_circuits[0],
        subcircuits=tuple(parsed_circuits[1:]),
        diagnostics=tuple(diagnostics),
    )


def _statements_from_file(
    path: Path,
    *,
    active: tuple[Path, ...],
    diagnostics: list[Diagnostic],
    spice_format: SpiceFormat,
    is_root: bool,
    stop_include: Sequence[str],
) -> Iterable[_LogicalStatement]:
    resolved = path.resolve()
    text = resolved.read_text(encoding="utf-8")
    current_active = (*active, resolved)

    for statement in _logical_statements(
        text,
        source=resolved,
        semicolon_comments=spice_format == "ngspice",
        skip_title=spice_format == "ngspice" and is_root,
    ):
        tokens = tuple(_split_tokens(statement.text))
        if not tokens or tokens[0].casefold() not in {".include", ".inc"}:
            yield statement
            continue
        if len(tokens) < 2:
            diagnostics.append(
                Diagnostic(
                    statement.line,
                    ".INCLUDE requires a file path",
                    source=resolved,
                )
            )
            continue

        include_path = _resolve_include_path(tokens[1], parent=resolved.parent)
        if _include_is_boundary(include_path, stop_include):
            continue
        if include_path in current_active:
            chain = " -> ".join(str(item) for item in (*current_active, include_path))
            diagnostics.append(
                Diagnostic(
                    statement.line,
                    f"include cycle skipped: {chain}",
                    source=resolved,
                )
            )
            continue
        if not include_path.is_file():
            diagnostics.append(
                Diagnostic(
                    statement.line,
                    f"included file was not found: {include_path}",
                    source=resolved,
                )
            )
            continue
        try:
            yield from _statements_from_file(
                include_path,
                active=current_active,
                diagnostics=diagnostics,
                spice_format=spice_format,
                is_root=False,
                stop_include=stop_include,
            )
        except (OSError, UnicodeError) as exc:
            diagnostics.append(
                Diagnostic(
                    statement.line,
                    f"included file could not be read: {include_path} ({exc})",
                    source=resolved,
                )
            )


def _include_is_boundary(path: Path, patterns: Sequence[str]) -> bool:
    path_text = str(path)
    return any(
        fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(path_text, pattern)
        for pattern in patterns
    )


def _resolve_include_path(token: str, *, parent: Path) -> Path:
    value = token
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    value = os.path.expandvars(value)
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = parent / path
    return path.resolve()


def _validate_spice_format(value: str) -> SpiceFormat:
    if value not in SUPPORTED_SPICE_FORMATS:
        supported = ", ".join(SUPPORTED_SPICE_FORMATS)
        raise CanonicalParseError(
            f"unsupported SPICE format {value!r}; choose one of: {supported}"
        )
    return cast(SpiceFormat, value)


def _parse_subckt_header(tokens: Sequence[str], line: int) -> tuple[str, tuple[str, ...]]:
    if len(tokens) < 2:
        raise CanonicalParseError(f"line {line}: .SUBCKT requires a name")
    name = tokens[1]
    pins: list[str] = []
    pin_tokens = tokens[2:]
    for index, token in enumerate(pin_tokens):
        if (
            token.casefold() in {"params:", "param:"}
            or "=" in token
            or (index + 1 < len(pin_tokens) and pin_tokens[index + 1] == "=")
        ):
            break
        pins.append(token)
    duplicate = _first_duplicate(pins)
    if duplicate is not None:
        raise CanonicalParseError(
            f"line {line}: subcircuit {name!r} repeats pin {duplicate!r}"
        )
    return name, tuple(pins)


def _record_model(
    tokens: Sequence[str], line: int, models: dict[str, tuple[str, str]]
) -> None:
    if len(tokens) < 3:
        raise CanonicalParseError(f"line {line}: .MODEL requires a name and type")
    name = tokens[1]
    model_type = tokens[2].partition("(")[0]
    models[name.casefold()] = (name, model_type)


def _build_circuit(
    builder: _CircuitBuilder,
    subcircuits: Mapping[str, _CircuitBuilder | tuple[str, ...]],
    models: dict[str, tuple[str, str]],
    diagnostics: list[Diagnostic],
    *,
    spice_format: SpiceFormat,
) -> Circuit:
    seen_devices: set[str] = set()
    for raw in builder.raw_devices:
        name = raw.tokens[0]
        key = name.casefold()
        if key in seen_devices:
            raise CanonicalParseError(
                f"line {raw.line}: circuit {builder.name!r} repeats device {name!r}"
            )
        seen_devices.add(key)
    devices = tuple(
        _parse_device(
            raw,
            subcircuits,
            models,
            diagnostics,
            spice_format=spice_format,
        )
        for raw in builder.raw_devices
    )
    return Circuit(name=builder.name, pins=builder.pins, devices=devices)


def _parse_device(
    raw: _RawDevice,
    subcircuits: Mapping[str, _CircuitBuilder | tuple[str, ...]],
    models: dict[str, tuple[str, str]],
    diagnostics: list[Diagnostic],
    *,
    spice_format: SpiceFormat,
) -> Device:
    name = raw.tokens[0]
    if not name:
        return _unresolved_device(raw, "empty device name", diagnostics)
    prefix = name[0].upper()
    if prefix == "X":
        return _parse_subcircuit_instance(raw, subcircuits, diagnostics)
    if prefix == "Q":
        return _parse_bjt(raw, models, diagnostics)
    if prefix == "K":
        return _parse_mutual_inductor(raw, diagnostics)
    spec = _FIXED_DEVICE_SPECS.get(prefix)
    if spec is None and spice_format == "ngspice":
        spec = _NGSPICE_FIXED_DEVICE_SPECS.get(prefix)
    if spec is None:
        return _unresolved_device(
            raw, f"unsupported device prefix {prefix!r}", diagnostics
        )
    required = 1 + len(spec.pins)
    if len(raw.tokens) < required:
        return _unresolved_device(
            raw,
            f"{spec.type} requires {len(spec.pins)} connection nodes",
            diagnostics,
        )

    connections = tuple(
        Connection(pin=pin, net=net)
        for pin, net in zip(spec.pins, raw.tokens[1:required], strict=True)
    )
    positional, named = _split_parameters(raw.tokens[required:])
    parameters = [*_parameters_for_tail(spec.tail, positional), *named]
    device_type = spec.type
    if prefix in _MODEL_DEVICE_PREFIXES:
        model = _parameter_value(parameters, "model")
        device_type = _type_from_model(model, spec.type, models)
    return Device(name, device_type, connections, tuple(parameters))


def _parse_subcircuit_instance(
    raw: _RawDevice,
    subcircuits: Mapping[str, _CircuitBuilder | tuple[str, ...]],
    diagnostics: list[Diagnostic],
) -> Device:
    positional, parameters = _split_parameters(raw.tokens[1:])
    if not positional:
        return _unresolved_device(raw, "subcircuit instance has no type", diagnostics)
    subckt_name = positional[-1]
    actual_nets = positional[:-1]
    definition = subcircuits.get(subckt_name.casefold())
    if definition is None:
        diagnostics.append(
            Diagnostic(
                raw.line,
                f"{raw.tokens[0]} references undefined subcircuit {subckt_name!r}; "
                "named pin connections could not be resolved",
                source=raw.source,
            )
        )
        unresolved = Parameter("unresolved_nets", " ".join(actual_nets))
        return Device(raw.tokens[0], subckt_name, (), (unresolved, *parameters))
    pins = definition.pins if isinstance(definition, _CircuitBuilder) else definition
    definition_name = definition.name if isinstance(definition, _CircuitBuilder) else subckt_name
    if len(actual_nets) != len(pins):
        raise CanonicalParseError(
            f"line {raw.line}: {raw.tokens[0]} connects {len(actual_nets)} nets to "
            f"{definition_name}, which declares {len(pins)} pins"
        )
    connections = tuple(
        Connection(pin=pin, net=net)
        for pin, net in zip(pins, actual_nets, strict=True)
    )
    return Device(raw.tokens[0], definition_name, connections, tuple(parameters))


def _parse_bjt(
    raw: _RawDevice,
    models: dict[str, tuple[str, str]],
    diagnostics: list[Diagnostic],
) -> Device:
    positional, named = _split_parameters(raw.tokens[1:])
    if len(positional) < 4:
        return _unresolved_device(
            raw, "bjt requires at least c, b, e, and model", diagnostics
        )

    model_index = next(
        (
            index
            for index in range(3, len(positional))
            if positional[index].casefold() in models
        ),
        None,
    )
    if model_index is None:
        model_index = 3
        if len(positional) > 4:
            diagnostics.append(
                Diagnostic(
                    raw.line,
                    f"{raw.tokens[0]} model is not declared in this file; assumed a "
                    "three-terminal BJT",
                    source=raw.source,
                )
            )
    if model_index not in {3, 4}:
        return _unresolved_device(
            raw, "could not distinguish BJT nodes from its model", diagnostics
        )

    pins = ("c", "b", "e", "s")[:model_index]
    connections = tuple(
        Connection(pin=pin, net=net)
        for pin, net in zip(pins, positional[:model_index], strict=True)
    )
    model = positional[model_index]
    parameters = [Parameter("model", model)]
    if positional[model_index + 1 :]:
        parameters.append(Parameter("arguments", " ".join(positional[model_index + 1 :])))
    parameters.extend(named)
    return Device(
        raw.tokens[0],
        _type_from_model(model, "bjt", models),
        connections,
        tuple(parameters),
    )


def _parse_mutual_inductor(
    raw: _RawDevice, diagnostics: list[Diagnostic]
) -> Device:
    positional, named = _split_parameters(raw.tokens[1:])
    if len(positional) < 3:
        return _unresolved_device(
            raw,
            "mutual inductor requires two inductors and a coupling value",
            diagnostics,
        )
    parameters = [
        Parameter("inductor1", positional[0]),
        Parameter("inductor2", positional[1]),
        Parameter("coupling", " ".join(positional[2:])),
        *named,
    ]
    return Device(raw.tokens[0], "mutual_inductor", (), tuple(parameters))


def _unresolved_device(
    raw: _RawDevice, reason: str, diagnostics: list[Diagnostic]
) -> Device:
    diagnostics.append(
        Diagnostic(raw.line, f"{raw.tokens[0]}: {reason}", source=raw.source)
    )
    return Device(
        name=raw.tokens[0],
        type="unresolved",
        connections=(),
        parameters=(Parameter("raw", " ".join(raw.tokens[1:])),),
    )


def _parameters_for_tail(tail: str, positional: Sequence[str]) -> list[Parameter]:
    if not positional:
        return []
    if tail == "source":
        source_kind = positional[0].casefold()
        if len(positional) == 2 and source_kind in {"dc", "ac"}:
            return [Parameter(source_kind, positional[1])]
        if len(positional) == 1 and re.match(
            r"^(pulse|pwl|sin|exp|sffm)\s*\(", positional[0], re.IGNORECASE
        ):
            return [Parameter("waveform", positional[0])]
        return [Parameter("source", " ".join(positional))]
    if tail in {"value", "gain"}:
        return [Parameter(tail, " ".join(positional))]
    if tail == "model":
        result = [Parameter("model", positional[0])]
        if len(positional) > 1:
            result.append(Parameter("arguments", " ".join(positional[1:])))
        return result
    if tail == "control":
        result = [Parameter("control", positional[0])]
        if len(positional) > 1:
            result.append(Parameter("gain", " ".join(positional[1:])))
        return result
    if tail == "control_model":
        result = [Parameter("control", positional[0])]
        if len(positional) > 1:
            result.append(Parameter("model", positional[1]))
        if len(positional) > 2:
            result.append(Parameter("arguments", " ".join(positional[2:])))
        return result
    raise AssertionError(f"unknown device tail parser: {tail}")


def _split_parameters(tokens: Sequence[str]) -> tuple[list[str], list[Parameter]]:
    positional: list[str] = []
    parameters: list[Parameter] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.casefold() in {"params:", "param:"}:
            index += 1
            continue
        match = _ASSIGNMENT_RE.match(token)
        if match:
            name, value = match.groups()
            if value == "" and index + 1 < len(tokens):
                index += 1
                value = tokens[index]
            parameters.append(Parameter(name, value))
            index += 1
            continue
        if index + 1 < len(tokens) and tokens[index + 1] == "=":
            value = tokens[index + 2] if index + 2 < len(tokens) else ""
            parameters.append(Parameter(token, value))
            index += 3
            continue
        if index + 1 < len(tokens) and tokens[index + 1].startswith("="):
            value = tokens[index + 1][1:]
            if value == "" and index + 2 < len(tokens):
                value = tokens[index + 2]
                index += 1
            parameters.append(Parameter(token, value))
            index += 2
            continue
        positional.append(token)
        index += 1
    return positional, parameters


def _type_from_model(
    model: str | None, fallback: str, models: dict[str, tuple[str, str]]
) -> str:
    if model is None:
        return fallback
    declaration = models.get(model.casefold())
    if declaration is not None:
        return declaration[1].lower()

    # ngspice model binning declares names such as nch.1 and instantiates nch.
    prefix = f"{model.casefold()}."
    binned_types = {
        candidate[1].lower()
        for name, candidate in models.items()
        if name.startswith(prefix)
    }
    if len(binned_types) == 1:
        return binned_types.pop()
    return fallback


def _parameter_value(parameters: Sequence[Parameter], name: str) -> str | None:
    return next(
        (parameter.value for parameter in parameters if parameter.name.casefold() == name),
        None,
    )


def _render_subcircuit(circuit: Circuit) -> str:
    pins = "\n".join([f"SUBCKT {_cell(circuit.name)}", "pin", *map(_cell, circuit.pins)])
    return f"{pins}\n\n{_render_circuit_tables(circuit)}"


def _render_circuit_tables(circuit: Circuit) -> str:
    incidents: dict[str, tuple[str, list[str]]] = {}
    for pin in circuit.pins:
        incidents.setdefault(pin.casefold(), (pin, []))
    for device in circuit.devices:
        for connection in device.connections:
            _, references = incidents.setdefault(
                connection.net.casefold(), (connection.net, [])
            )
            references.append(f"{device.name}.{connection.pin}")

    net_lines = [f"NET_INCIDENT_TABLE {_cell(circuit.name)}", "net | incident pins"]
    net_lines.extend(
        f"{_cell(net)} | {_cell(', '.join(references))}"
        for net, references in incidents.values()
    )

    device_lines = [
        f"DEVICE_TABLE {_cell(circuit.name)}",
        "name | type | connections | parameters",
    ]
    for device in circuit.devices:
        connections = ", ".join(
            f"{connection.pin}={connection.net}" for connection in device.connections
        )
        parameters = ", ".join(
            f"{parameter.name}={parameter.value}" for parameter in device.parameters
        )
        device_lines.append(
            " | ".join(
                map(_cell, (device.name, device.type, connections, parameters))
            )
        )
    return "\n".join([*net_lines, "", *device_lines])


def _cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "\\n")


def _logical_statements(
    text: str,
    *,
    source: Path | None = None,
    semicolon_comments: bool = False,
    skip_title: bool = False,
) -> Iterable[_LogicalStatement]:
    pending_line: int | None = None
    pending_text = ""
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if skip_title and line_number == 1:
            continue
        line = _strip_inline_comment(
            raw_line, semicolon_comments=semicolon_comments
        ).strip()
        if not line:
            continue
        if line.startswith("+"):
            if pending_line is None:
                raise CanonicalParseError(
                    f"line {line_number}: continuation appears without a preceding statement"
                )
            pending_text = f"{pending_text} {line[1:].strip()}"
            continue
        if pending_line is not None:
            yield _LogicalStatement(pending_line, pending_text, source=source)
        pending_line = line_number
        pending_text = line
    if pending_line is not None:
        yield _LogicalStatement(pending_line, pending_text, source=source)


def _strip_inline_comment(line: str, *, semicolon_comments: bool = False) -> str:
    stripped = line.lstrip()
    if stripped.startswith("*") or stripped.startswith("//"):
        return ""

    quote: str | None = None
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    escaped = False
    for index, character in enumerate(line):
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote is not None:
            escaped = True
            continue
        if quote is not None:
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            continue
        if character in depths:
            depths[character] += 1
            continue
        if character in closing and depths[closing[character]] > 0:
            depths[closing[character]] -= 1
            continue
        if any(depths.values()):
            continue
        if character == "$":
            return line[:index]
        if semicolon_comments and character == ";":
            return line[:index]
        if line.startswith("//", index) and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def _split_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    escaped = False

    for character in text:
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\" and quote is not None:
            current.append(character)
            escaped = True
            continue
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            current.append(character)
            quote = character
            continue
        if character in depths:
            current.append(character)
            depths[character] += 1
            continue
        if character in closing:
            current.append(character)
            opener = closing[character]
            if depths[opener] > 0:
                depths[opener] -= 1
            continue
        if character.isspace() and not any(depths.values()):
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(character)
    if current:
        tokens.append("".join(current))
    return tokens


def _first_duplicate(values: Sequence[str]) -> str | None:
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            return value
        seen.add(key)
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point for canonical netlist extraction."""

    parser = argparse.ArgumentParser(
        description="Extract the canonical graph representation from a supported SPICE netlist."
    )
    parser.add_argument("input", type=Path, help="input Eldo/SPICE netlist")
    parser.add_argument("-o", "--output", type=Path, help="output text file (default: stdout)")
    parser.add_argument("--top-name", default="TOP", help="name used for the top-level circuit")
    parser.add_argument(
        "--format",
        dest="spice_format",
        choices=SUPPORTED_SPICE_FORMATS,
        default="eldo",
        help="input SPICE dialect (default: eldo)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail when any device cannot be completely resolved",
    )
    parser.add_argument(
        "--stop-include",
        action="append",
        default=[],
        metavar="GLOB",
        help="do not expand .include paths matching this basename or path glob",
    )
    parser.add_argument(
        "--external-subcircuits",
        type=Path,
        metavar="JSON",
        help='JSON object mapping opaque subcircuit names to pin-name arrays',
    )
    parser.add_argument(
        "--device-type-map",
        type=Path,
        metavar="JSON",
        help=(
            "explicitly normalize device types using a JSON object mapping "
            "source types to canonical types"
        ),
    )
    args = parser.parse_args(argv)

    try:
        external_subcircuits = {}
        if args.external_subcircuits is not None:
            external_subcircuits = json.loads(
                args.external_subcircuits.read_text(encoding="utf-8")
            )
            if not isinstance(external_subcircuits, dict) or not all(
                isinstance(name, str)
                and isinstance(pins, list)
                and all(isinstance(pin, str) for pin in pins)
                for name, pins in external_subcircuits.items()
            ):
                raise CanonicalParseError(
                    "external subcircuits JSON must map names to pin-name arrays"
                )
        device_type_map = {}
        if args.device_type_map is not None:
            device_type_map = json.loads(
                args.device_type_map.read_text(encoding="utf-8")
            )
            if not isinstance(device_type_map, dict) or not all(
                isinstance(source, str)
                and isinstance(target, str)
                and source
                and target
                for source, target in device_type_map.items()
            ):
                raise CanonicalParseError(
                    "device type map JSON must map non-empty source type names "
                    "to non-empty canonical type names"
                )
        netlist = from_file(
            args.input,
            top_name=args.top_name,
            spice_format=args.spice_format,
            stop_include=args.stop_include,
            external_subcircuits=external_subcircuits,
            device_type_map=device_type_map,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, CanonicalParseError) as exc:
        parser.exit(2, f"error: {exc}\n")

    for diagnostic in netlist.diagnostics:
        source = diagnostic.source or args.input
        print(
            f"{source}:{diagnostic.line}: warning: {diagnostic.message}",
            file=sys.stderr,
        )
    if args.strict and netlist.diagnostics:
        return 2

    rendered = netlist.render()
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
