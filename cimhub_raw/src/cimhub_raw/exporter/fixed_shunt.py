"""LinearShuntCompensator with no control -> Fixed shunt (``EXPORT_MAPPING.md#fixed-shunt``).

A shunt with a RegulatingControl is a switched-shunt block, and a branch's line shunt its GI/BI/GJ/BJ
(``EXPORT_MAPPING.md#which-shunt-is-which``).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters.in_service import get_in_service
from cimhub_raw.exporter import branch
from cimhub_raw.exporter.identity import keyed_ids, terminal_buses
from cimhub_raw.exporter.shunt_admittance import bus_base_admittance
from cimhub_raw.importer.cimtbl.derived import mva_from_per_unit
from cimhub_raw.importer.cimtbl.fixed_shunt import PREFIX

NATIVE_CLASS = schema.FixedShuntRecord
CIM_CLASSES = (cim.LinearShuntCompensator,)  # with switched_shunt; line shunts with branch
ID_WIDTH = 2

_ADMITTANCE = "get_shunt_admittance {} of the sections in service (pu on the bus base) x SBASE"
SLOTS = {NATIVE_CLASS: {
    "bus_number": Slot("written", "I: the terminal's busNumber"),
    "shunt_id": Slot("written", "ID: the cap_<I>_<ID> key, else the next free (X2)"),
    "status": Slot("rule", "STATUS: 0 when inService is false, else 1"),
    "gl": Slot("written", "GL (MW at 1 pu): " + _ADMITTANCE.format("g")),
    "bl": Slot("written", "BL (Mvar at 1 pu): " + _ADMITTANCE.format("b")),
}}


def export(context) -> list[schema.FixedShuntRecord]:
    """One Fixed shunt per uncontrolled shunt that is no line shunt, by key."""
    line_shunts = branch.line_shunts(context)
    shunts = [(shunt, terminal_buses(shunt, context)) for shunt in context.objects(cim.LinearShuntCompensator)
              if shunt.RegulatingControl is None and shunt not in line_shunts]
    ids = keyed_ids([(shunt, PREFIX, buses) for shunt, buses in shunts], ID_WIDTH)
    base_mva = context.network.base_power.to("MVA")
    records = []
    for shunt, (bus,) in shunts:
        admittance = bus_base_admittance(shunt, "actual", context.network.base_power)
        records.append(schema.FixedShuntRecord(
            bus_number=bus, shunt_id=ids[shunt], status=0 if get_in_service(shunt, which="actual") is False else 1,
            gl=mva_from_per_unit(admittance.g, base_mva), bl=mva_from_per_unit(admittance.b, base_mva)))
    return sorted(records, key=lambda record: (record.bus_number, record.shunt_id))
