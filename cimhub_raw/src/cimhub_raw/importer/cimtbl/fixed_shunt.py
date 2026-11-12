"""RAW Fixed shunt -> ``fixed_shunt.cimtbl``: one always-in ``LinearShuntCompensator`` per shunt.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#fixed-shunt``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid
from cimhub_raw.importer.cimtbl.derived import per_unit_from_mva
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults

NATIVE_CLASS = schema.FixedShuntRecord
PREFIX = "cap_"

#: STATUS -> inService
IN_SERVICE = {1: True, 0: False}

FIELDS = {
    "bus_number": Field("structural", note="I: bus; nomU (kV) = bus I's BASKV, the (pu system) base; BaseVoltage = "
                                           "bus I's bv_<BASKV>; EquipmentContainer = bus I's substation"),
    "shunt_id": Field("structural", note="ID: with I the key, mRID cap_<I>_<ID>, name I_ID"),
    "status": Field("mapped", note="STATUS: inService = (STATUS == 1); blank: 1 (defaulted)"),
    "gl": Field("derived", note="GL (MW at 1 pu): gPerSection (pu system) = GL / SBASE (per_unit_from_mva); blank: 0 "
                                "(defaulted)"),
    "bl": Field("derived", note="BL (Mvar at 1 pu, > 0 a capacitor in RAW and CIM): bPerSection (pu system) = BL / "
                                "SBASE (per_unit_from_mva); blank: 0 (defaulted)"),
}

_PROVENANCE = """PSS/E RAW Fixed shunt -> LinearShuntCompensator (one section, always in).
Source table: Fixed shunt (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#fixed-shunt"""


def map_fixed_shunt(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                    base_mva: float) -> Document:
    defaults = raw_defaults(NATIVE_CLASS)
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda shunt: (shunt.bus_number, str(shunt.shunt_id)))
    rows = []
    for record in records:
        shunt, defaulted = fill_keyed_defaults(FIELDS, record, defaults)
        bus = shunt.bus_number
        rows.append(Row([
            mrid(PREFIX, shunt.ID), shunt.ID, str(bus), cell(per_unit_from_mva(shunt.gl, base_mva)),
            cell(per_unit_from_mva(shunt.bl, base_mva)), cell(base_kv_of[bus]), "1", "1", "1",
            cell(lookup(IN_SERVICE, shunt.status, slot="status", record_id=f"fixed shunt {shunt.ID}")),
            base_voltage_mrid(base_kv_of[bus]), substations_by_bus[bus]], comment=defaulted))
    columns = [Column("mRID"), Column("name"), Column("bus"), Column("gPerSection", "pu system"),
               Column("bPerSection", "pu system"), Column("nomU", "kV"), Column("maximumSections"),
               Column("normalSections"), Column("sections"), Column("inService"), Column("BaseVoltage"),
               Column("EquipmentContainer")]
    statements = [Table("LinearShuntCompensator", columns, rows)] if rows else []
    return Document(name="fixed_shunt", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
