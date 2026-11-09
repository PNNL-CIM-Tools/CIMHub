"""A one-terminal device's DSS connection: ``bus1``, ``phases``, ``conn``, a load's ``kV`` from its bus and a DER's
from its ``ratedU``; shared by Load, Capacitor, PVSystem, Storage and Generator
(``EXPORT_MAPPING.md#s6d-loads-capacitors-capcontrol``, ``#s6e-der-and-reactors``).

The importer's shared phase rule inverted: the phase conductors go on the bus (1/2/3 for A/B/C, 1/2 for s1/s2), and a
wye device's neutral is the engine's node 0, so it must be grounded. A delta device across two conductors is DSS's
1-phase delta, written in branch order (A-B, B-C, C-A).
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import SPLIT_PHASE, get_base_voltage
from cimhub_core.getters.phase_power import SUM_REL_TOL, PhasePower
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_opendss.exporter.naming import Names

CONNECTION = {cim.PhaseShuntConnectionKind.Y: "wye", cim.PhaseShuntConnectionKind.Yn: "wye",
              cim.PhaseShuntConnectionKind.D: "delta"}
_A, _B, _C = cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C
#: a delta across two phases is the branch from one to the next (IEEE13's 692.3.1); a PhaseCode has no order
BRANCH = {frozenset(pair): pair for pair in ((_A, _B), (_B, _C), (_C, _A))}


class DeviceConnection(NamedTuple):
    bus1: str
    phases: int
    conn: str


def device_connection(device, conductors: tuple[cim.SinglePhaseKind, ...], connection, grounded,
                      names: Names) -> DeviceConnection:
    """The device's bus on its phase ``conductors`` (no neutral), DSS ``phases`` and ``conn``."""
    if connection not in CONNECTION:
        kind = connection.value if connection is not None else None
        raise ValueError(f"{describe(device)}: phaseConnection {kind} is not mapped (Y, Yn and D are)")
    conn = CONNECTION[connection]
    if conn == "wye" and grounded is not True:
        raise ValueError(f"{describe(device)}: a wye with grounded {grounded}; DSS puts its neutral on node 0")
    if conn == "delta" and len(conductors) not in (2, 3):
        raise ValueError(f"{describe(device)}: a delta on {len(conductors)} conductors (2 or 3 are mapped)")
    phases = 1 if conn == "delta" and len(conductors) == 2 else len(conductors)
    if phases == 1 and conn == "delta":
        conductors = BRANCH.get(frozenset(conductors), conductors)
    [node] = get_terminal_nodes(device)
    return DeviceConnection(bus_ref(node, conductors, names), phases, conn)


def device_kv(device, conductors: tuple[cim.SinglePhaseKind, ...], conn: str) -> float:
    """The kV a DSS device on its bus is rated at (E9, the importer's ``rated_phase_kv`` inverted): the
    BaseVoltage line to line for delta and for 2 or 3 phases, line to neutral for 1-phase wye. On a split-phase
    secondary (DSS-5) the BaseVoltage is the whole coil: a leg is half of it, and a 2-phase wye device is read by the
    engine's sqrt 3 rule (0.208 for 120 V legs)."""
    line_to_line = get_base_voltage(device, "kV", form="LL")
    if any(phase in SPLIT_PHASE for phase in conductors):
        if conn == "delta":
            return line_to_line
        leg = line_to_line / 2  # the centre tap halves the coil
        return leg * math.sqrt(3) if len(conductors) == 2 else leg
    if conn == "delta" or len(conductors) > 1:
        return line_to_line
    return get_base_voltage(device, "kV", form="LN")


def rated_kv(rated_u: float, conductors: tuple[cim.SinglePhaseKind, ...], conn: str) -> float:
    """A DER's DSS ``kv`` from its ``ratedU`` (line to line, in kV): / sqrt 3 for a 1-phase wye device, the importer's
    ``line_kv`` inverted (S4b-4). Not the bus's: a 240 V inverter on 120 V legs stays 240 V."""
    return rated_u / math.sqrt(3) if len(conductors) == 1 and conn == "wye" else rated_u


def equal_phases(per_phase: dict[cim.SinglePhaseKind, PhasePower]) -> bool:
    """Every phase's p and q alike (rel ``SUM_REL_TOL``): one DSS device carries them (E8)."""
    values = list(per_phase.values())
    return all(math.isclose(a, b, rel_tol=SUM_REL_TOL) for value in values for a, b in zip(value, values[0]))
