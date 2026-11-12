"""RAW Zone -> ``zone.cimtbl``: one ``SubGeographicalRegion`` per zone, in the case's GeographicalRegion.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#zone``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, schema_defaults

NATIVE_CLASS = schema.ZoneRecord
PREFIX = "srgn_"

FIELDS = {
    "zone_number": Field("structural", note="I: mRID = srgn_ + I, Region = the case's rgn_; the name when ZONAME is "
                                            "blank"),
    "zone_name": Field("copied", (("SubGeographicalRegion", "name", None),), note="ZONAME; blank: the zone number"),
}

_PROVENANCE = """PSS/E RAW Zone -> SubGeographicalRegion.
Source table: Zone (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#zone"""


def zone_mrid(number: int) -> str:
    return mrid(PREFIX, number)


def bus_zones(native) -> dict[int, int]:
    """Bus number -> its zone; a blank ZONE takes the spec default."""
    default = schema_defaults(schema.BusRecord, "raw_default")["zone"]
    return {bus.bus_number: int(bus.zone if bus.zone is not None else default)
            for bus in native.list_by_class(schema.BusRecord)}


def map_zone(native, region: str) -> Document:
    """Every Zone record, then a synthesized region for each zone a bus names that has no Zone record."""
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda zone: zone.zone_number)
    columns = [Column("mRID"), Column("name"), Column("Region", default=region)]
    rows = [Row([zone_mrid(zone.zone_number), cell(zone.zone_name or str(zone.zone_number))]) for zone in records]
    statements = [Table("SubGeographicalRegion", columns, rows)] if rows else []
    named = {zone.zone_number for zone in records}
    missing = sorted(set(bus_zones(native).values()) - named)
    if missing:
        statements.append(Table("SubGeographicalRegion", columns,
                                [Row([zone_mrid(number), str(number)]) for number in missing],
                                comment="synthesized: zones that buses name but the Zone data does not"))
    return Document(name="zone", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
