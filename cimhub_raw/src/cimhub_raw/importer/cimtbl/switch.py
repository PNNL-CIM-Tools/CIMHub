"""RAW System switching device -> ``switch.cimtbl``: a ``Switch``, ``Breaker`` or ``Disconnector`` by STYPE, in the
substation of bus I, with its ratings on terminal 1.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#system-switching-device``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import control_area_numbers
from cimhub_raw.importer.cimtbl.ratings import RatingRows
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults
from cimhub_raw.importer.cimtbl.tie_flow import TieFlowRows, branch_home_end, off_tie_note

NATIVE_CLASS = schema.SwitchRecord
PREFIX = "sw_"  # shared by every Switch subclass, so a change of class keeps the mRID

#: STYPE -> CIM class (code table in the spec)
SWITCH_CLASS = {1: "Switch", 2: "Breaker", 3: "Disconnector"}
#: STATUS / NSTATUS -> open / normalOpen
OPEN = {1: False, 0: True}

FIELDS = {
    "from_bus_number": Field("structural", note="I: bus1; BaseVoltage = bus I's bv_<BASKV>; EquipmentContainer = "
                                                "bus I's substation"),
    "to_bus_number": Field("structural", note="J: bus2"),
    "circuit": Field("structural", note="CKT: with I and J the key, mRID sw_<I>_<J>_<CKT>"),
    "x": Field("untranscribed", note="X: the solver's stand-in for zero impedance (X < THRSHZ); a Switch has none; "
                                     "the exporter writes THRSHZ back (expected difference)"),
    "ratings": Field("structural", note="RATE1..RATE12: as a branch's, the set sw_<key>_ratings on sw_<key>_T1 (RAW-9, "
                                        "RAW-20)"),
    "status": Field("mapped", note="STATUS: open = (STATUS == 0); blank: 1 (defaulted)"),
    "nstat": Field("mapped", note="NSTATUS: normalOpen = (NSTATUS == 0); blank: 1 (defaulted)"),
    "metered_end": Field("structural", note="METERED: as a branch's MET, the TieFlows of a tie on its metered "
                                            "terminal (R5); elsewhere untranscribed (CIM 18 gap, RAW-22); blank: 1 "
                                            "(defaulted)"),
    "stype": Field("mapped", note="STYPE: the class, 1 Switch (generic connector), 2 Breaker, 3 Disconnector; blank "
                                  "or another code raises (the spec gives no default)"),
    "name": Field("copied", (("Switch", "name", None), ("Breaker", "name", None), ("Disconnector", "name", None)),
                  note="NAME; blank: the key I_J_CKT"),
}

_PROVENANCE = """PSS/E RAW System switching device -> Switch, Breaker, Disconnector (by STYPE), OperationalLimitSet +
ApparentPowerLimit or CurrentLimit (ratings).
Source table: System switching device (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#system-switching-device"""


def map_switch(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float], bus_area: dict[int, int],
               ratings_in_current: bool) -> Document:
    defaults = raw_defaults(NATIVE_CLASS)
    records = sorted(native.list_by_class(NATIVE_CLASS),
                     key=lambda switch: (switch.from_bus_number, switch.to_bus_number, str(switch.circuit)))
    rows_by_class: dict[str, list[Row]] = {name: [] for name in SWITCH_CLASS.values()}
    ratings = RatingRows(ratings_in_current)
    ties = TieFlowRows(bus_area, control_area_numbers(native))
    for record in records:
        switch, defaulted = fill_keyed_defaults(FIELDS, record, defaults)
        record_id = f"switch {switch.ID}"
        switch_class = lookup(SWITCH_CLASS, switch.stype, slot="stype", record_id=record_id)
        equipment = mrid(PREFIX, switch.ID)
        base_kv = base_kv_of[switch.from_bus_number]
        rows_by_class[switch_class].append(Row([
            equipment, cell(switch.name or switch.ID), str(switch.from_bus_number), str(switch.to_bus_number),
            cell(lookup(OPEN, switch.status, slot="status", record_id=record_id)),
            cell(lookup(OPEN, switch.nstat, slot="nstat", record_id=record_id)),
            base_voltage_mrid(base_kv), substations_by_bus[switch.from_bus_number]], comment=defaulted))
        ratings.add(equipment, switch.ratings, base_kv)
        buses = (switch.from_bus_number, switch.to_bus_number)
        if ties.is_tie(buses):
            ties.add(equipment, switch.ID, buses, branch_home_end(switch.metered_end, record_id), record_id)

    columns = [Column("mRID"), Column("name"), Column("bus1"), Column("bus2"), Column("open"), Column("normalOpen"),
               Column("BaseVoltage"), Column("EquipmentContainer")]
    statements = [Table(name, columns, rows) for name, rows in rows_by_class.items() if rows]
    if statements:
        statements[0].comment = off_tie_note(untranscribed_names(FIELDS), "METERED")
    statements.extend(ratings.tables())
    statements.extend(ties.tables("METERED"))
    return Document(name="switch", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
