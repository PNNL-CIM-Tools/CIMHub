"""RAW Area interchange -> ``area_interchange.cimtbl``: one ``ControlArea`` per area.

Members join their area in later slices (generating units R3, loads R2, tie flows R5); a bus's own AREA and the
area's slack bus ISW have no CIM home (CIM 18 gap). Mapping spec:
``cimhub_raw/docs/CIMTBL_MAPPING.md#area-interchange``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, schema_defaults, untranscribed_names

NATIVE_CLASS = schema.AreaInterchangeRecord
PREFIX = "ca_"  # requested from the cimtbl-translate table owners (plan C3)

FIELDS = {
    "area_number": Field("structural", note="I: mRID = ca_ + I (prefix requested, C3); the name when ARNAME is blank"),
    "bus_number": Field("untranscribed", note="ISW, the area slack bus: no ControlArea slack association (CIM 18 "
                                              "gap)"),
    "pdes": Field("copied", (("ControlArea", "netInterchange", "MW"),), note="PDES; blank: 0 (defaulted)"),
    "ptol": Field("copied", (("ControlArea", "pTolerance", "MW"),), note="PTOL; blank: 10 (defaulted)"),
    "name": Field("copied", (("ControlArea", "name", None),), note="ARNAME; blank: the area number"),
}

_PROVENANCE = """PSS/E RAW Area interchange -> ControlArea.
Source table: Area interchange (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#area-interchange"""


def area_mrid(number: int) -> str:
    return mrid(PREFIX, number)


def map_area_interchange(native) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda area: area.area_number)
    defaults = schema_defaults(NATIVE_CLASS, "raw_default")
    rows = []
    for record in records:
        area, defaulted = fill_defaults(FIELDS, record, defaults)
        rows.append(Row([area_mrid(area.area_number), cell(area.name or str(area.area_number)), cell(area.pdes),
                         cell(area.ptol)], comment=defaulted))
    columns = [Column("mRID"), Column("name"), Column("netInterchange", "MW"), Column("pTolerance", "MW")]
    statements = [Table("ControlArea", columns, rows, comment=untranscribed_names(FIELDS))] if rows else []
    return Document(name="area_interchange", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
