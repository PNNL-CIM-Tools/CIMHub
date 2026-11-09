"""RAW Area interchange -> ``area_interchange.cimtbl``: one ``ControlArea`` per area.

Members join their area through equipment: generating units (R3), loads (R2) and tie flows (R5). A bus's own AREA
is traced from them on export, and the area's slack bus ISW has no CIM home (CIM 18 gap). The inter-area transfers
have none either, so they are listed on the table comment (R5). Mapping spec:
``cimhub_raw/docs/CIMTBL_MAPPING.md#area-interchange``.
"""

from __future__ import annotations

import textwrap

from cimtables.document import Column, Document, Row, Table

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, schema_defaults, untranscribed_names
from cimhub_raw.importer.cimtbl import interarea_transfer
from cimhub_raw.importer.cimtbl.derived import net_import

NATIVE_CLASS = schema.AreaInterchangeRecord
PREFIX = "ca_"  # requested from the cimtbl-translate table owners (plan C3)

FIELDS = {
    "area_number": Field("structural", note="I: mRID = ca_ + I (prefix requested, C3); the name when ARNAME is blank"),
    "bus_number": Field("untranscribed", note="ISW, the area slack bus: no ControlArea slack association (CIM 18 "
                                              "gap)"),
    "pdes": Field("derived", note="PDES (MW, the desired net export): ControlArea.netInterchange (MW, positive into "
                                  "the area) = -PDES (net_import, R5); blank: 0 (defaulted)"),
    "ptol": Field("copied", (("ControlArea", "pTolerance", "MW"),), note="PTOL; blank: 10 (defaulted)"),
    "name": Field("copied", (("ControlArea", "name", None),), note="ARNAME; blank: the area number"),
}

_PROVENANCE = """PSS/E RAW Area interchange -> ControlArea.
Source table: Area interchange (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#area-interchange"""


def area_mrid(number: int) -> str:
    return mrid(PREFIX, number)


def control_area_numbers(native) -> set[int]:
    """The AREA numbers that have an area-interchange record, so a ControlArea ``ca_<I>``."""
    return {area.area_number for area in native.list_by_class(NATIVE_CLASS)}


def map_area_interchange(native) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda area: area.area_number)
    defaults = schema_defaults(NATIVE_CLASS, "raw_default")
    rows = []
    for record in records:
        area, defaulted = fill_defaults(FIELDS, record, defaults)
        rows.append(Row([area_mrid(area.area_number), cell(area.name or str(area.area_number)),
                         cell(net_import(area.pdes)), cell(area.ptol)], comment=defaulted))
    columns = [Column("mRID"), Column("name"), Column("netInterchange", "MW"), Column("pTolerance", "MW")]
    transfers = interarea_transfer.transfer_lines(native, control_area_numbers(native))
    comment = [untranscribed_names(FIELDS), "derived: netInterchange = -PDES (net_import)"]
    if transfers:
        comment.append(textwrap.fill("untranscribed: inter-area transfers (CIM 18 gap): " + "; ".join(transfers),
                                     width=116, break_long_words=False))
    statements = [Table("ControlArea", columns, rows, comment="\n".join(filter(None, comment)))] if rows else []
    return Document(name="area_interchange", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
