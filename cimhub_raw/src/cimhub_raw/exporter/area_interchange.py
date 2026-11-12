"""ControlArea -> Area (``EXPORT_MAPPING.md#zone-area-owner``)."""

from __future__ import annotations

from cimtables.graph_write import get_qty

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_raw.exporter.identity import raw_name
from cimhub_raw.importer.cimtbl.derived import net_export

NATIVE_CLASS = schema.AreaInterchangeRecord
CIM_CLASSES = ()
NAME_WIDTH = 12

SLOTS = {NATIVE_CLASS: {
    "area_number": Slot("written", "I: the ca_<n> key (X2)"),
    "bus_number": Slot("unset", "ISW: no ControlArea slack association (CIM 18 gap)"),
    "pdes": Slot("written", "PDES = -netInterchange (MW, net_export)"),
    "ptol": Slot("written", "PTOL: pTolerance (MW)"),
    "name": Slot("written", "ARNAME: name; blank when it is the number"),
}}


def export(context) -> list[schema.AreaInterchangeRecord]:
    """One Area per ControlArea, by number."""
    records = []
    for area, number in sorted(context.area_numbers.items(), key=lambda item: item[1]):
        net_interchange = get_qty(area, "netInterchange", "MW")
        records.append(schema.AreaInterchangeRecord(
            area_number=number, pdes=None if net_interchange is None else net_export(net_interchange),
            ptol=get_qty(area, "pTolerance", "MW"), name=raw_name(area, str(number), NAME_WIDTH)))
    return records
