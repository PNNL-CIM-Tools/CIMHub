"""SubGeographicalRegion -> Zone (``EXPORT_MAPPING.md#zone-area-owner``)."""

from __future__ import annotations

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_raw.exporter.identity import raw_name

NATIVE_CLASS = schema.ZoneRecord
CIM_CLASSES = ()
NAME_WIDTH = 12

SLOTS = {NATIVE_CLASS: {
    "zone_number": Slot("written", "I: the srgn_<n> key (X2)"),
    "zone_name": Slot("written", "ZONAME: name; blank when it is the number"),
}}


def export(context) -> list[schema.ZoneRecord]:
    """One Zone per SubGeographicalRegion, by number."""
    return [schema.ZoneRecord(zone_number=number, zone_name=raw_name(region, str(number), NAME_WIDTH))
            for region, number in sorted(context.zone_numbers.items(), key=lambda item: item[1])]
