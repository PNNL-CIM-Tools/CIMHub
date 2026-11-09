"""The terminal and the shared power rules of a one-terminal DSS device (Load, Capacitor, PVSystem, Storage,
Generator).

The shared phase rule of the S4 spec: the bus's nodes give the phases (1/2/3 are A/B/C, and s1/s2 on a
split-phase island, DSS-5); an omitted node is the DSS default (conductor k on node k, the wye neutral on 0).
A wye device's neutral is ground, so it is grounded; a delta device is not.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md``, section S4, "Shared phase rule", and section S4b,
"Shared rules (S4b)".
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import NamedTuple

from cimtopology.core import BusSystem, System

from cimhub_opendss.importer.cimtbl.transformer import parse_bus

_PHASE_OF_NODE = {1: "A", 2: "B", 3: "C"}
_SPLIT_PHASE_OF_NODE = {1: "s1", 2: "s2"}
_SQRT3 = math.sqrt(3)


class DeviceTerminal(NamedTuple):
    """The bus, the CIM phases and the connection of a one-terminal device."""

    bus: str
    phases: str
    count: int
    delta: bool
    system: BusSystem

    @property
    def connection(self) -> str:
        return "D" if self.delta else "Y"

    @property
    def grounded(self) -> bool:
        return not self.delta


def is_delta(conn) -> bool:
    """DSS ``conn`` (enum or text; ``None`` is the wye default) is delta."""
    text = str(getattr(conn, "text", conn) or "wye").lower()
    if text in ("delta", "d", "ll"):
        return True
    if text in ("wye", "y", "ln", "star"):
        return False
    raise ValueError(f"conn={conn} is neither wye nor delta")


def device_terminal(label: str, spec, phases: int, delta: bool, buses: Mapping[str, BusSystem]) -> DeviceTerminal:
    """The terminal of ``label`` (``'Load 671'``) on bus ``spec`` with ``phases`` phases."""
    bus, given = parse_bus(spec)
    if bus not in buses:
        raise ValueError(f"{label}: bus {bus} has no voltage (the topology walk did not reach it)")
    system = buses[bus]
    if delta and phases == 2:
        raise ValueError(f"{label}: a 2-phase delta device is not mapped")
    conductors = 2 if delta and phases == 1 else phases
    defaults = (*range(1, conductors + 1), *(() if delta else (0,)))
    if len(given) > len(defaults):
        raise ValueError(f"{label}: bus {spec} gives more nodes than its {len(defaults)} conductors")
    nodes = given + defaults[len(given):]
    phase_nodes, neutral = nodes[:conductors], nodes[conductors:]
    if neutral and neutral != (0,):
        raise ValueError(f"{label}: bus {spec} puts the wye neutral on node {neutral[0]}, not ground (an "
                         "ungrounded or impedance-grounded neutral is not mapped)")
    split = system.system is System.SPLIT_PHASE
    if split and phases > 2:
        raise ValueError(f"{label}: a {phases}-phase device on split-phase bus {bus}")
    names = _SPLIT_PHASE_OF_NODE if split else _PHASE_OF_NODE
    unknown = [node for node in phase_nodes if node not in names]
    if unknown or len(set(phase_nodes)) != len(phase_nodes):
        raise ValueError(f"{label}: bus {spec} puts its {conductors} conductors on nodes {phase_nodes}, which "
                         f"are not distinct phases of a {system.system.name.lower().replace('_', '-')} bus")
    return DeviceTerminal(bus, "".join(names[node] for node in phase_nodes), phases, delta, system)


def rated_phase_kv(terminal: DeviceTerminal) -> float:
    """The kV a DSS device on ``terminal`` is rated at when it matches its bus: line to line for delta and for
    2 or 3 phases (a 2-phase split-phase device by the sqrt 3 rule: 0.208 for 120 V legs), line to neutral for
    1-phase wye. A single-phase island's voltage is its coil's, line to neutral."""
    kv, system = terminal.system.kv, terminal.system.system
    if system is System.SPLIT_PHASE:
        if terminal.delta:
            return kv
        return kv / 2 * (_SQRT3 if terminal.count == 2 else 1)
    if system is System.SINGLE_PHASE or terminal.delta or terminal.count > 1:
        return kv
    return kv / _SQRT3


def line_kv(kv: float, terminal: DeviceTerminal) -> float:
    """``ratedU`` (kV, line to line) of a DSS device rated ``kv``: x sqrt 3 for a 1-phase wye device, as the
    engine's CIM export writes it (S4b-4)."""
    return kv * _SQRT3 if terminal.count == 1 and not terminal.delta else kv


def reactive_power(kw: float, pf: float) -> float:
    """kvar at ``kw`` and ``pf``: kW x tan(acos abs(pf)), with the sign of pf."""
    return math.copysign(kw * math.tan(math.acos(abs(pf))), pf)


def generated_kvar(label: str, kw: float, *, pf: float, kvar, pf_given: bool) -> float:
    """The kvar a PVSystem or Generator is dispatched at: ``kvar`` when set, else from ``pf`` (its default filled).
    The engine keeps whichever of the two comes last and the record keeps no order, so both set raises unless
    they agree (S4b-2)."""
    from_pf = reactive_power(kw, pf)
    if kvar is None:
        return from_pf
    if pf_given and not math.isclose(from_pf, float(kvar), rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"{label}: pf={pf} gives {from_pf:.6g} kvar but kvar={kvar}; the engine keeps whichever "
                         "comes last, and the record keeps no order")
    return float(kvar)


def inverter_power(label: str, available_kw: float, kvar: float, kva: float) -> float:
    """The kW an inverter gives: ``available_kw`` cut to fit ``kva`` with ``kvar`` kept (the engine's default
    var priority)."""
    if abs(kvar) > kva:
        raise ValueError(f"{label}: {kvar:.6g} kvar is above its {kva:.6g} kVA")
    return min(available_kw, math.sqrt(kva ** 2 - kvar ** 2))
