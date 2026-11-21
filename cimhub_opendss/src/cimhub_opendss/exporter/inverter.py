"""A PowerElectronicsConnection -> one DSS PVSystem or Storage per unit (``EXPORT_MAPPING.md#inverters``).

A DSS PVSystem or Storage is one inverter with one DC device. CIM lets several units share a connection (a PV array
and a battery behind one inverter), so the connection is chopped by ``get_inverter_units``: each unit's share is its
maxP over the units' total; it takes that share of ratedS, q and the q limits, and its own p (else its share of the
connection's p). One unit keeps the connection's name; several take their units' names. A connection with one unit
and unequal phases gives one 1-phase device per phase (E8), each a 1/n share of the connection and of the unit's
own ratings; with several units that raises. A device whose output is above its share of ratedS raises: the engine
would cut it (a DC-coupled PV feeding its battery is above its share of the AC rating).
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.der import get_der_output, get_inverter_rating, get_inverter_units
from cimhub_core.getters.in_service import get_in_service
from cimhub_opendss.exporter.injection import device_connection, equal_phases, rated_kv
from cimhub_opendss.exporter.naming import Names

#: the unit classes a DSS class carries
UNIT_CLASSES = (cim.PhotoVoltaicUnit, cim.BatteryUnit, cim.PowerElectronicsWindUnit)
#: float noise allowed when an output is checked against its kVA
KVA_REL_TOL = 1e-9


class InverterPiece(NamedTuple):
    """One DSS device of a connection: its name, unit, share and output (kW and kvar, the generation sign)."""

    name: str
    unit: cim.PowerElectronicsUnit
    share: float  # of the connection's ratedS and q limits
    unit_share: float  # of the unit's own ratings (maxP, energies): 1, or 1/n for one of n phases
    p: float
    q: float
    slots: dict  # the inverter slots: bus1, phases, conn, kv, kVA, kvarMax, kvarMaxAbs, Vminpu, enabled


def inverter_pieces(connection: cim.PowerElectronicsConnection, unit_class: type, namespace: str,
                    names: Names) -> list[InverterPiece]:
    """The DSS devices of ``connection``'s units of ``unit_class``, named in ``namespace``."""
    units = get_inverter_units(connection, "kW", "kVAr", sign="generation")
    other = [describe(share.unit) for share in units if not isinstance(share.unit, UNIT_CLASSES)]
    if other:
        raise ValueError(f"{describe(connection)}: units {other} have no DSS class (PhotoVoltaicUnit is a PVSystem, "
                         f"BatteryUnit a Storage, PowerElectronicsWindUnit a Generator)")
    output = get_der_output(connection, "kW", "kVAr", sign="generation")
    balanced = output.split or equal_phases(output.per_phase)
    pieces = []
    for share in units:
        if not isinstance(share.unit, unit_class):
            continue
        if balanced:
            name = names.name(connection if len(units) == 1 else share.unit, namespace)
            pieces.append(_piece(connection, name, share.unit, share.share, 1.0, share.p, share.q, output.phases,
                                 names))
            continue
        if len(units) > 1:
            raise ValueError(f"{describe(connection)}: unequal phases and {len(units)} units; one of them is mapped")
        if output.connection is cim.PhaseShuntConnectionKind.D:
            raise ValueError(f"{describe(connection)}: a delta inverter with unequal phases; a CIM phase on a delta "
                             f"device names no branch (E8)")
        for phase, power in output.per_phase.items():
            name = names.name(connection, namespace, suffix=f"_{phase.value.lower()}")
            fraction = 1 / len(output.per_phase)
            pieces.append(_piece(connection, name, share.unit, fraction, fraction, power.p, power.q, (phase,), names))
    return pieces


def _piece(connection, name: str, unit, share: float, unit_share: float, p: float, q: float, conductors,
           names: Names) -> InverterPiece:
    slots = _slots(connection, conductors, share, names)
    if math.hypot(p, q) > slots["kVA"] * (1 + KVA_REL_TOL):
        raise ValueError(f"{describe(connection)}: {describe(unit)} gives {p:g} kW and {q:g} kvar, above its "
                         f"{slots['kVA']:g} kVA share of the inverter (its maxP share {share:g})")
    return InverterPiece(name, unit, share, unit_share, p, q, slots)


def _slots(connection: cim.PowerElectronicsConnection, conductors, share: float, names: Names) -> dict:
    """The inverter's own slots for a device on ``conductors`` with ``share`` of its rating."""
    rating = get_inverter_rating(connection, "kVA", "kVAr", sign="generation", voltage_unit="kV")
    # cim18v17's PowerElectronicsConnection has no grounded: a wye inverter's neutral is ground, as on import
    placed = device_connection(connection, conductors, connection.phaseConnection, True, names)
    return dict(
        bus1=placed.bus1, phases=placed.phases, conn=placed.conn, kv=rated_kv(rating.rated_u, conductors, placed.conn),
        kVA=share * rating.rated_s,
        kvarMax=None if rating.max_q is None else share * rating.max_q,
        kvarMaxAbs=None if rating.min_q is None else -share * rating.min_q + 0.0,
        Vminpu=None if rating.max_fault_current is None else 1 / rating.max_fault_current,
        enabled=get_in_service(connection, which="normal"),
    )
