"""Device-level MOS helpers shared by decomposition rules.

Polarity is taken only from the canonical device type; device names are never
used.  Canonical ``nmos`` and ``pmos`` are the primary polarity classes.  A
generic ``mosfet`` has unknown polarity: it can still be classified on
hierarchy level 1, but every rule that needs a same-doping comparison excludes
it because comparing two unknown polarities is not meaningful.

Connectivity in a canonical netlist is net identity: two pins are connected
(the paper's ``<->`` operator) exactly when they name the same net, and
explicitly not connected (the negated operator) otherwise.  A missing pin is
never connected to anything.
"""

from __future__ import annotations

from spice_canonical.canonical_netlist import Device


#: Canonical device types treated as MOS transistors.
MOS_TYPES = frozenset({"nmos", "pmos", "mosfet"})

_POLARITY = {"nmos": "n", "pmos": "p"}


def is_supported_mos(device: Device) -> bool:
    return device.type in MOS_TYPES


def mos_polarity(device: Device) -> str | None:
    """Return ``"n"`` or ``"p"``, or ``None`` when the polarity is unknown."""

    return _POLARITY.get(device.type)


def same_polarity(first: Device, second: Device) -> bool:
    """True only when both polarities are known and equal."""

    polarity = mos_polarity(first)
    return polarity is not None and polarity == mos_polarity(second)


def pin_net(device: Device, pin: str) -> str | None:
    """Return the net on ``pin`` (``d``/``g``/``s``/``b``), or ``None``."""

    for connection in device.connections:
        if connection.pin == pin:
            return connection.net
    return None


def decoupled(devices: tuple[Device, ...], *, sources: bool = False) -> bool:
    """True when no two devices share a gate-gate or gate-drain connection.

    This is the pairwise exclusion of the paper's analog inverter (Eq. 18)
    and inverting transconductance (Eq. 23).  With ``sources=True`` the
    Eq. 18 source-source exclusion is checked as well.  Missing pins are
    never connected.
    """

    for position, first in enumerate(devices):
        gate = pin_net(first, "g")
        source = pin_net(first, "s")
        for other, second in enumerate(devices):
            if position == other:
                continue
            if gate is not None and gate in (
                pin_net(second, "g"),
                pin_net(second, "d"),
            ):
                return False
            if sources and source is not None and source == pin_net(second, "s"):
                return False
    return True


def pins_connected(
    first: Device, first_pin: str, second: Device, second_pin: str
) -> bool:
    """True when both pins exist and share one net."""

    net = pin_net(first, first_pin)
    return net is not None and net == pin_net(second, second_pin)
