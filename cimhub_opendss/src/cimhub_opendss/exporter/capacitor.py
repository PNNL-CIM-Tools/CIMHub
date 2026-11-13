"""LinearShuntCompensator -> OpenDSS ``Capacitor`` (``EXPORT_MAPPING.md#capacitor``).

One section, as on import: ``kvar`` = bPerSection x nomU^2 (``get_shunt_reactive_power`` at the nominal voltage),
``kv`` = nomU, and ``states`` the sections in service (``sections``; DSS has no normal state for a capacitor).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.shunt import get_shunt_reactive_power
from cimhub_opendss.exporter.injection import device_connection
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.LinearShuntCompensator,)
NATIVE_CLASS = schema.Capacitor
NAMESPACE = "Capacitor"

_NOT_IN_CIM = "untranscribed or raising on import; not in CIM"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the Capacitor namespace"),
    "bus1": Slot("written", "bus_ref of the phase conductors; a wye's neutral is node 0, so it must be grounded"),
    "bus2": Slot("not mapped", "a shunt has one terminal"),
    "phases": Slot("written", "the phase conductors; a delta across two is 1"),
    "kvar": Slot("written", "get_shunt_reactive_power(sections='maximum', voltage='nominal') (kVAr); "
                            "maximumSections other than 1 raises"),
    "kv": Slot("written", "nomU (kV), the voltage bPerSection was derived on"),
    "conn": Slot("written", "phaseConnection Y/Yn -> wye, D -> delta; others raise"),
    "Numsteps": Slot("not mapped", "one section; more raise, as on import"),
    "states": Slot("written", "[sections], the sections in service (0 or 1); normalSections is not written"),
    "cmatrix": Slot("not mapped", "kvar carries the susceptance"),
    "cuf": Slot("not mapped", "kvar carries the susceptance"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", _NOT_IN_CIM))}


def capacitor_name(shunt: cim.LinearShuntCompensator, names: Names) -> str:
    """The shunt's DSS name, as its record and its CapControl write it."""
    return names.name(shunt, NAMESPACE)


def export(context) -> list[schema.Capacitor]:
    """One Capacitor per LinearShuntCompensator."""
    return [_capacitor(shunt, context.names) for shunt in context.objects(*CIM_CLASSES)]


def _capacitor(shunt: cim.LinearShuntCompensator, names: Names) -> schema.Capacitor:
    rated = get_shunt_reactive_power(shunt, "kVAr", sections="maximum", voltage="nominal", voltage_unit="kV")
    if rated.sections != 1:
        raise ValueError(f"{describe(shunt)}: maximumSections {rated.sections}; one section is mapped, as on import")
    in_service = get_shunt_reactive_power(shunt, sections="actual", voltage="nominal").sections
    if in_service not in (0, 1):
        raise ValueError(f"{describe(shunt)}: sections {in_service}; a one-section bank has 0 or 1")
    connection = device_connection(shunt, rated.phases, rated.connection, rated.grounded, names)
    return NATIVE_CLASS(name=capacitor_name(shunt, names), bus1=connection.bus1, phases=connection.phases,
                        conn=connection.conn, kvar=rated.total, kv=rated.voltage, states=[int(in_service)],
                        enabled=get_in_service(shunt, which="normal"))
