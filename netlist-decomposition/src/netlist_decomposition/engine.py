"""Small rule engine for structural functional-block tags.

This is deliberately a graph matcher, not an electrical verifier.  Its output is
a set of overlapping candidate tags: for example, one MOS may be tagged as a
diode transistor, as a one-device transistor stack, and as the reference device
of a current mirror at the same time.  Tags are not a partition of the devices.

Transistor classification and transistor stacks follow Abel et al. (2021),
"A Functional Block Decomposition Method for Automatic Op-Amp Design":

- hierarchy level 1 (Eq. 7 and 8): ``normal_transistor`` / ``diode_transistor``;
- transistor stacks (Eq. 9): ordered same-doping chains of 1-3 HL1 transistors.

Stack members are ordered bottom-to-top, i.e. from the stack source to the
stack drain, matching the paper's ``x_{k,1} .. x_{k,n}`` numbering where the
source not connected to any member drain is the stack source.

Drain and source are assumed to have already been assigned their intended roles
in the canonical netlist.  No drain/source swapping or bulk inference is done.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol, Sequence

from spice_canonical.canonical_netlist import Circuit, Device

from netlist_decomposition import mos
from netlist_decomposition.mos import MOS_TYPES


@dataclass(frozen=True)
class IncidentPin:
    device: str
    pin: str


class CircuitGraph:
    """Indexed view of one canonical circuit.

    ``vdd_nets`` and ``vss_nets`` are declared power rails (positive rails
    for PMOS sources, ground rails for NMOS sources).  They are never
    inferred from net names; blocks that need supply context (the load
    search of Algorithm 3, the paper's analog inverter) read them from
    here.  ``supply_nets`` is their union.
    """

    def __init__(
        self,
        circuit: Circuit,
        *,
        vdd_nets: Iterable[str] = (),
        vss_nets: Iterable[str] = (),
    ) -> None:
        self.circuit = circuit
        self.vdd_nets = frozenset(vdd_nets)
        self.vss_nets = frozenset(vss_nets)
        self.supply_nets = self.vdd_nets | self.vss_nets
        self.devices = {device.name: device for device in circuit.devices}
        incidents: dict[str, list[IncidentPin]] = {}
        for device in circuit.devices:
            for connection in device.connections:
                incidents.setdefault(connection.net, []).append(
                    IncidentPin(device.name, connection.pin)
                )
        self._incidents = {
            net: tuple(net_incidents) for net, net_incidents in incidents.items()
        }

    def pin_net(self, device: Device, pin: str) -> str | None:
        for connection in device.connections:
            if connection.pin == pin:
                return connection.net
        return None

    def incidents(self, net: str) -> tuple[IncidentPin, ...]:
        return self._incidents.get(net, ())

    def mos_devices(self) -> tuple[Device, ...]:
        return tuple(
            device for device in self.circuit.devices if device.type in MOS_TYPES
        )

    def channel_incidents(self, net: str) -> tuple[IncidentPin, ...]:
        """Return MOS drain/source terminals on ``net``."""

        return tuple(
            incident
            for incident in self.incidents(net)
            if incident.pin in {"d", "s"}
            and self.devices[incident.device].type in MOS_TYPES
        )


Role = tuple[str, tuple[str, ...]]
NamedNet = tuple[str, str]
Property = tuple[str, str]


@dataclass(frozen=True)
class BlockCandidate:
    """A match returned by a rule before the engine assigns its tag id."""

    kind: str
    members: frozenset[str]
    roles: tuple[Role, ...] = ()
    nets: tuple[NamedNet, ...] = ()
    properties: tuple[Property, ...] = ()


@dataclass(frozen=True)
class BlockTag:
    """One structural interpretation of a group of devices.

    ``level`` is the tag's tagging set -- the hierarchy level of its kind
    per ``KIND_LEVELS``, stamped when the tag enters the index.  Kinds not
    registered there get ``None`` and are never filtered by ``max_level``.
    """

    id: str
    kind: str
    members: frozenset[str]
    roles: tuple[Role, ...]
    nets: tuple[NamedNet, ...]
    properties: tuple[Property, ...]
    rule: str
    level: int | None = None

    def devices_for(self, role: str) -> tuple[str, ...]:
        return next((devices for name, devices in self.roles if name == role), ())

    def net_for(self, name: str) -> str | None:
        return next((net for net_name, net in self.nets if net_name == name), None)


#: Tagging sets: every block kind belongs to a hierarchy level of the
#: paper's Fig. 15 (extensions get levels by analogy).  This is taxonomy
#: metadata only -- it says nothing about *when* a kind is recognized;
#: that is declared by ``COMPOSITION_PASSES``.
KIND_LEVELS: dict[str, int] = {
    # level 1 (Eq. 7/8)
    "normal_transistor": 1,
    "diode_transistor": 1,
    # level 2 (Eq. 9-19 + extensions + legacy candidates)
    "transistor_stack": 2,
    "voltage_bias": 2,
    "current_bias": 2,
    "current_mirror": 2,
    "differential_pair": 2,
    "gate_connected_couple": 2,
    "cascode_differential_pair": 2,
    "analog_inverter": 2,
    "source_follower": 2,
    "differential_pair_candidate": 2,
    "cmos_inverter": 2,
    # level 3 (Eq. 20-29 + follower extension)
    "transconductance": 3,
    "load": 3,
    "stage_bias": 3,
    "source_follower_stage": 3,
    # level 4 (Eq. 30-39)
    "amplification_stage": 4,
    "circuit_bias": 4,
    "compensation_capacitor": 4,
    "load_capacitor": 4,
}


class BlockIndex:
    """Deduplicated collection exposed to later/higher-level rules."""

    def __init__(self) -> None:
        self._tags: list[BlockTag] = []
        self._keys: set[tuple[object, ...]] = set()
        self._kind_counts: dict[str, int] = {}

    def __iter__(self):  # type annotation kept compatible with Python 3.10
        return iter(self._tags)

    def of_kind(self, kind: str) -> tuple[BlockTag, ...]:
        return tuple(tag for tag in self._tags if tag.kind == kind)

    @staticmethod
    def _key(tag: BlockCandidate | BlockTag) -> tuple[object, ...]:
        return (
            tag.kind,
            tuple(sorted(tag.members)),
            tag.roles,
            tag.nets,
            tag.properties,
        )

    def add(self, candidate: BlockCandidate, *, rule: str) -> bool:
        key = self._key(candidate)
        if key in self._keys:
            return False

        count = self._kind_counts.get(candidate.kind, 0) + 1
        self._kind_counts[candidate.kind] = count
        self._tags.append(
            BlockTag(
                id=f"{candidate.kind}:{count}",
                kind=candidate.kind,
                members=candidate.members,
                roles=candidate.roles,
                nets=candidate.nets,
                properties=candidate.properties,
                rule=rule,
                level=KIND_LEVELS.get(candidate.kind),
            )
        )
        self._keys.add(key)
        return True

    def discard(self, tags: Iterable[BlockTag]) -> None:
        """Remove tags from the index (the Eq. 19 deletions).

        The removed tags' dedup keys are freed with them, so an identical
        candidate could be re-added afterwards; deletions therefore run
        only once every producer of the affected kinds has finished.
        Kind counters are not rewound -- tag ids stay unique for the life
        of the index.
        """

        doomed = {tag.id for tag in tags}
        if not doomed:
            return
        for tag in self._tags:
            if tag.id in doomed:
                self._keys.discard(self._key(tag))
        self._tags = [tag for tag in self._tags if tag.id not in doomed]

    def as_tuple(self) -> tuple[BlockTag, ...]:
        return tuple(self._tags)


class Rule(Protocol):
    name: str

    def find(
        self, graph: CircuitGraph, blocks: BlockIndex
    ) -> Iterable[BlockCandidate]: ...


Matcher = Callable[[CircuitGraph, BlockIndex], Iterable[BlockCandidate]]


@dataclass(frozen=True)
class FunctionRule:
    """Adapter that makes a normal Python matcher function into a rule.

    ``level`` is the hierarchy level of the kinds the rule emits (default
    2).  A rule runs in the composition pass whose ``completes`` tuple
    contains its level (see ``COMPOSITION_PASSES``), to a fixed point,
    before that pass's resolution steps.
    """

    name: str
    matcher: Matcher
    level: int = 2

    def find(
        self, graph: CircuitGraph, blocks: BlockIndex
    ) -> Iterable[BlockCandidate]:
        return self.matcher(graph, blocks)


class DecompositionEngine:
    """Apply ordered rules to a fixed point."""

    def __init__(self, rules: Sequence[Rule], *, max_passes: int = 16) -> None:
        if max_passes < 1:
            raise ValueError("max_passes must be at least one")
        self.rules = tuple(rules)
        self.max_passes = max_passes

    def run(self, circuit: Circuit) -> tuple[BlockTag, ...]:
        return self.run_index(CircuitGraph(circuit)).as_tuple()

    def run_index(self, graph: CircuitGraph) -> BlockIndex:
        """Run the rules to a fixed point and return the mutable index."""

        blocks = BlockIndex()
        self.extend_index(graph, blocks)
        return blocks

    def extend_index(self, graph: CircuitGraph, blocks: BlockIndex) -> None:
        """Run the rules to a fixed point on an existing index."""

        for _ in range(self.max_passes):
            changed = False
            for rule in self.rules:
                for candidate in rule.find(graph, blocks):
                    unknown = candidate.members.difference(graph.devices)
                    if unknown:
                        raise ValueError(
                            f"rule {rule.name!r} returned unknown devices: "
                            f"{sorted(unknown)}"
                        )
                    changed |= blocks.add(candidate, rule=rule.name)
            if not changed:
                return

        raise RuntimeError(
            f"functional decomposition did not converge in {self.max_passes} passes"
        )


def _device_role(name: str, *devices: Device) -> Role:
    return name, tuple(device.name for device in devices)


HL1_NORMAL = "normal_transistor"
HL1_DIODE = "diode_transistor"


def _hl1_transistors(
    graph: CircuitGraph, _blocks: BlockIndex
) -> Iterable[BlockCandidate]:
    """Classify supported MOS devices per Abel et al. (2021) Eq. 7 and Eq. 8.

    A diode transistor (Eq. 8) has its drain connected to its gate and not to
    its source.  A normal transistor (Eq. 7) has no self connection at all:
    drain, gate, and source are on three distinct nets.  A device whose gate
    and source share a net, or whose drain and source share a net, is neither.
    """

    for device in graph.mos_devices():
        drain = mos.pin_net(device, "d")
        gate = mos.pin_net(device, "g")
        source = mos.pin_net(device, "s")
        if drain is None or gate is None or source is None:
            continue
        if drain == gate and drain != source:
            yield BlockCandidate(
                kind=HL1_DIODE,
                members=frozenset({device.name}),
                roles=(_device_role("device", device),),
                nets=(("gate_drain", gate), ("source", source)),
                properties=(("mos_type", device.type),),
            )
        elif drain != source and drain != gate and gate != source:
            yield BlockCandidate(
                kind=HL1_NORMAL,
                members=frozenset({device.name}),
                roles=(_device_role("device", device),),
                nets=(("drain", drain), ("gate", gate), ("source", source)),
                properties=(("mos_type", device.type),),
            )


def _stack_variant(member_classes: Sequence[str]) -> str:
    """Composition-only variant label for a bottom-to-top ``nt``/``dt`` sequence.

    ``diode_pair`` is the paper's dip.  An all-normal multi-device stack is the
    composition underlying the paper's cascode pair, and the mixed pairs
    underlie mp1/mp2; those paper names additionally require the enclosing
    voltage- or current-bias context, so only neutral labels are used here.
    """

    if all(item == "nt" for item in member_classes):
        return "single_normal" if len(member_classes) == 1 else "all_normal"
    if all(item == "dt" for item in member_classes):
        if len(member_classes) == 1:
            return "single_diode"
        return "diode_pair" if len(member_classes) == 2 else "all_diode"
    if len(member_classes) == 2:
        if member_classes[0] == "dt":
            return "mixed_pair_diode_bottom"
        return "mixed_pair_diode_top"
    return "mixed"


def transistor_stack_rule(*, exclusive_internal_nets: bool = False) -> FunctionRule:
    """Create the Eq. 9 transistor-stack rule.

    Stacks of one to three transistors are built from the HL1
    ``normal_transistor``/``diode_transistor`` tags.  Members are reported
    bottom-to-top: ``ordered_devices[0]`` provides the stack source and
    ``ordered_devices[-1]`` the stack drain.  For every pair of a lower and a
    higher member, the higher gate must not touch the lower drain and the
    higher drain must not touch the lower source.  Eq. 9 states these
    exclusions for adjacent members; the paper's prose states them for all
    lower/higher pairs, and this stricter reading is used because it also
    rejects degenerate three-device rings.

    ``exclusive_internal_nets`` is an optional conservative policy, not a paper
    rule: it additionally requires every net inside a stack to carry exactly
    two MOS drain/source terminals, which drops stacks that branch (for
    example through a differential-pair common source).
    """

    def matcher(
        graph: CircuitGraph, blocks: BlockIndex
    ) -> Iterable[BlockCandidate]:
        classes: dict[str, str] = {}
        for tag in blocks.of_kind(HL1_NORMAL):
            classes[tag.devices_for("device")[0]] = "nt"
        for tag in blocks.of_kind(HL1_DIODE):
            classes[tag.devices_for("device")[0]] = "dt"
        members = tuple(
            device for device in graph.mos_devices() if device.name in classes
        )

        def valid_extension(current: tuple[Device, ...], upper: Device) -> bool:
            lower = current[-1]
            internal = mos.pin_net(lower, "d")
            if internal != mos.pin_net(upper, "s"):
                return False
            if not mos.same_polarity(lower, upper):
                return False
            if (
                exclusive_internal_nets
                and len(graph.channel_incidents(internal)) != 2
            ):
                return False
            # HL1 classification guarantees non-None d/g/s nets for members.
            gate = mos.pin_net(upper, "g")
            drain = mos.pin_net(upper, "d")
            return not any(
                gate == mos.pin_net(item, "d") or drain == mos.pin_net(item, "s")
                for item in current
            )

        def extend(current: tuple[Device, ...]) -> Iterable[tuple[Device, ...]]:
            yield current
            if len(current) == 3:
                return
            for upper in members:
                if upper not in current and valid_extension(current, upper):
                    yield from extend(current + (upper,))

        for bottom in members:
            for stack in extend((bottom,)):
                names = tuple(device.name for device in stack)
                member_classes = tuple(classes[name] for name in names)
                yield BlockCandidate(
                    kind="transistor_stack",
                    members=frozenset(names),
                    roles=(("ordered_devices", names),),
                    nets=(
                        ("source", mos.pin_net(stack[0], "s") or ""),
                        ("drain", mos.pin_net(stack[-1], "d") or ""),
                    ),
                    properties=(
                        ("length", str(len(stack))),
                        ("mos_type", stack[0].type),
                        ("member_classes", ",".join(member_classes)),
                        ("structural_variant", _stack_variant(member_classes)),
                        (
                            "internal_nets",
                            ",".join(
                                mos.pin_net(device, "d") or ""
                                for device in stack[:-1]
                            ),
                        ),
                    ),
                )

    return FunctionRule("transistor stacks", matcher)


def _differential_pairs(
    graph: CircuitGraph, _blocks: BlockIndex
) -> Iterable[BlockCandidate]:
    candidates = graph.mos_devices()
    for position, left in enumerate(candidates):
        for right in candidates[position + 1 :]:
            common_source = graph.pin_net(left, "s")
            if (
                not mos.same_polarity(left, right)
                or common_source is None
                or graph.pin_net(right, "s") != common_source
                or graph.pin_net(right, "b") != graph.pin_net(left, "b")
                or graph.pin_net(right, "g") == graph.pin_net(left, "g")
                or graph.pin_net(right, "d") == graph.pin_net(left, "d")
            ):
                continue
            yield BlockCandidate(
                kind="differential_pair_candidate",
                members=frozenset({left.name, right.name}),
                roles=(
                    _device_role("input_1", left),
                    _device_role("input_2", right),
                ),
                nets=(
                    ("input_1", graph.pin_net(left, "g") or ""),
                    ("input_2", graph.pin_net(right, "g") or ""),
                    ("common_source", common_source),
                ),
                properties=(("mos_type", left.type),),
            )


def _cmos_inverters(
    graph: CircuitGraph, _blocks: BlockIndex
) -> Iterable[BlockCandidate]:
    pmos = tuple(device for device in graph.mos_devices() if device.type == "pmos")
    nmos = tuple(device for device in graph.mos_devices() if device.type == "nmos")
    for pull_up in pmos:
        for pull_down in nmos:
            common_gate = graph.pin_net(pull_up, "g")
            common_drain = graph.pin_net(pull_up, "d")
            if (
                common_gate is not None
                and common_drain is not None
                and graph.pin_net(pull_down, "g") == common_gate
                and graph.pin_net(pull_down, "d") == common_drain
            ):
                yield BlockCandidate(
                    kind="cmos_inverter",
                    members=frozenset({pull_up.name, pull_down.name}),
                    roles=(
                        _device_role("pull_up", pull_up),
                        _device_role("pull_down", pull_down),
                    ),
                    nets=(("input", common_gate), ("output", common_drain)),
                )


DEFAULT_RULES: tuple[Rule, ...] = (
    FunctionRule("HL1 transistors", _hl1_transistors, level=1),
    transistor_stack_rule(),
    FunctionRule("differential-pair candidates", _differential_pairs),
    FunctionRule("CMOS inverters", _cmos_inverters),
)


PassRunner = Callable[[CircuitGraph, BlockIndex, Sequence[Rule]], None]


@dataclass(frozen=True)
class CompositionPass:
    """One composition pass of the recognition pipeline.

    ``completes`` names the tagging sets (hierarchy levels, ``KIND_LEVELS``)
    whose membership is final once this pass ends: later passes may only
    enrich existing tags of those levels with properties, never add or
    remove them.  The one in-pass deletion is Eq. 19, which runs inside
    pass 2 *before* level 2 completes.
    """

    number: int
    name: str
    completes: tuple[int, ...]
    run: PassRunner


def _pass_rules(rules: Sequence[Rule], completes: tuple[int, ...]) -> tuple[Rule, ...]:
    return tuple(rule for rule in rules if getattr(rule, "level", 2) in completes)


def _run_classify(
    graph: CircuitGraph, blocks: BlockIndex, rules: Sequence[Rule]
) -> None:
    DecompositionEngine(_pass_rules(rules, (1,))).extend_index(graph, blocks)


def _run_structure(
    graph: CircuitGraph, blocks: BlockIndex, rules: Sequence[Rule]
) -> None:
    from netlist_decomposition import bias, hl2

    DecompositionEngine(_pass_rules(rules, (2,))).extend_index(graph, blocks)
    bias.resolve_bias_blocks(graph, blocks)
    hl2.resolve_hl2_blocks(graph, blocks)
    # Eq. 19 closes the pass, as in Algorithm 1: level 2 membership is
    # final only after this deletion.
    bias.prune_irrelevant(blocks)


def _run_stages(
    graph: CircuitGraph, blocks: BlockIndex, rules: Sequence[Rule]
) -> None:
    from netlist_decomposition import stages

    DecompositionEngine(_pass_rules(rules, (3, 4))).extend_index(graph, blocks)
    stages.resolve_stage_blocks(graph, blocks)


#: The recognition pipeline: three composition passes mirroring Abel et
#: al. (2021) Section 7, decoupled from the four-level kind taxonomy
#: (``KIND_LEVELS``).  Pass 1 classifies transistors (7.1, Eq. 7/8).
#: Pass 2 runs the monotone structural rules (stacks, candidates),
#: Algorithm 1 (biases, mirrors), the pair/follower/inverter resolution,
#: and closes level 2 with the Eq. 19 deletion (7.2).  Pass 3 runs
#: Algorithm 2 (7.3) and completes levels 3 AND 4 together, because the
#: inverting transconductance (level 3, Eq. 23) and its stage bias
#: (Eq. 27/28) are mutually dependent with the amplification stages and
#: resolvable only through the stage loop -- emitting level-3 kinds there
#: is the declared contract, not a level violation.  The op-amp
#: classification above level 4 is not implemented.  Passes can be run
#: individually on a caller-owned ``CircuitGraph``/``BlockIndex`` as long
#: as the earlier passes ran before -- later passes only read tags, never
#: raw devices.
COMPOSITION_PASSES: tuple[CompositionPass, ...] = (
    CompositionPass(1, "classify", (1,), _run_classify),
    CompositionPass(2, "structure", (2,), _run_structure),
    CompositionPass(3, "stages", (3, 4), _run_stages),
)


def decompose(
    circuit: Circuit,
    rules: Sequence[Rule] = DEFAULT_RULES,
    *,
    vdd_nets: Iterable[str] = (),
    vss_nets: Iterable[str] = (),
    max_level: int = 4,
) -> tuple[BlockTag, ...]:
    """Return all functional-block tags found in one canonical circuit.

    ``max_level`` selects tagging sets, with completion-plus-view
    semantics: every composition pass that completes a level ``<=
    max_level`` runs, then the returned tuple is filtered to tags whose
    ``level`` is unknown (``None``) or ``<= max_level``.  Because pass 3
    completes levels 3 and 4 together, ``max_level=3`` runs Algorithm 2 in
    full and view-filters the level-4 tags -- the index behind the view
    always holds the complete pass output; the filter is a read view, not
    a deletion (unlike Eq. 19, which is a real deletion inside pass 2).

    Each pass runs its monotone rules (selected by the rules' ``level``
    attribute against the pass's ``completes``) to a fixed point, then its
    resolution steps -- Algorithm 1, the pair/follower/inverter
    recognition, and the closing Eq. 19 deletion in pass 2 (see
    ``netlist_decomposition.bias`` and ``.hl2``); Algorithm 2's
    transconductance/load/stage-bias recognition, amplification-stage
    loop, circuit bias, and capacitors in pass 3 (see
    ``netlist_decomposition.stages``) -- which need complete block sets
    and negative conditions a monotone rule cannot express.

    ``vdd_nets``/``vss_nets`` declare the power rails.  Without them the
    Algorithm 3 load search can only find load stacks whose sources sit on
    transconductance outputs (folded arrangements), and no source follower
    is recognized.
    """

    graph = CircuitGraph(circuit, vdd_nets=vdd_nets, vss_nets=vss_nets)
    blocks = BlockIndex()
    for composition_pass in COMPOSITION_PASSES:
        if all(level > max_level for level in composition_pass.completes):
            continue
        composition_pass.run(graph, blocks, rules)
    return tuple(
        tag
        for tag in blocks.as_tuple()
        if tag.level is None or tag.level <= max_level
    )


def suppress_false_stacks(tags: Sequence[BlockTag]) -> tuple[BlockTag, ...]:
    """Drop transistor stacks that climb through a differential pair.

    This is the one false multiple assignment from Section 4.6 of Abel et al.
    (2021) that the currently implemented blocks can express: a stack whose
    internal net is the common source of a differential-pair candidate and
    that contains one of the pair's devices (for example a tail device stacked
    with one input device).  The paper suppresses these to avoid false analog
    inverters.

    Candidate generation stays separate from suppression: ``decompose`` still
    returns these stacks, and callers opt in by filtering through this
    function.  Full Section 4.6 handling (irrelevant same-type containment per
    Eq. 19, and suppression informed by HL2 voltage/current biases) needs
    functional blocks that are not implemented yet; extend this function when
    they exist.
    """

    pairs = tuple(
        tag for tag in tags if tag.kind == "differential_pair_candidate"
    )

    def is_false(tag: BlockTag) -> bool:
        if tag.kind != "transistor_stack":
            return False
        internal = dict(tag.properties).get("internal_nets", "")
        internal_nets = set(filter(None, internal.split(",")))
        return any(
            pair.net_for("common_source") in internal_nets
            and tag.members & pair.members
            for pair in pairs
        )

    return tuple(tag for tag in tags if not is_false(tag))
