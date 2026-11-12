"""RAW Non-transformer branch -> ``branch.cimtbl``: an ``ACLineSegment`` per branch, or a ``SeriesCompensator`` when
X < 0, with its ratings on terminal 1 and its line shunts as ordinary shunts.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#branch``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.area_interchange import control_area_numbers
from cimhub_raw.importer.cimtbl.ratings import RatingRows
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, listed_off_default, raw_defaults
from cimhub_raw.importer.cimtbl.tie_flow import TieFlowRows, branch_home_end, off_tie_note

NATIVE_CLASS = schema.BranchRecord
LINE_PREFIX = "ln_"
SERIES_CAPACITOR_PREFIX = "sc_"  # requested from the cimtbl-translate table owners (plan C3)
SHUNT_PREFIX = "cap_"

#: ST -> inService
IN_SERVICE = {1: True, 0: False}

_OWNER = "ownership is an asset concept (CIM 18 gap)"
_SHUNT = ("{name}: with {pair}, a LinearShuntCompensator cap_<I>_<J>_<CKT>_{end} on bus {bus} when either is nonzero "
          "(RAW-13): {column} (pu system), nomU (kV) and BaseVoltage = bus {bus}'s BASKV, one section, inService = "
          "ST, the bus's substation")
FIELDS = {
    "from_bus_number": Field("structural", note="I: bus1; BaseVoltage = bus I's bv_<BASKV>, the base of every (pu "
                                                "system) value and of a CurrentLimit; J with another BASKV is listed "
                                                "on the row (R1b-1)"),
    "to_bus_number": Field("structural", note="J: bus2"),
    "circuit": Field("structural", note="CKT: with I and J the key, mRID ln_<I>_<J>_<CKT> (X < 0: sc_); a first "
                                        "character @ or * is a substation merge edge (plan 3.2)"),
    "r": Field("copied", (("ACLineSegment", "r", "pu system"), ("SeriesCompensator", "r", "pu system")), note="R"),
    "x": Field("copied", (("ACLineSegment", "x", "pu system"), ("SeriesCompensator", "x", "pu system")),
               note="X; X < 0: a SeriesCompensator, compensatorType = capacitor, x verbatim (RAW-15)"),
    "b": Field("copied", (("ACLineSegment", "bch", "pu system"),),
               note="B; blank: 0 (defaulted); a series capacitor with B != 0 raises (SeriesCompensator has no bch; no "
                    "case)"),
    "name": Field("copied", (("ACLineSegment", "name", None), ("SeriesCompensator", "name", None)),
                  note="NAME; blank: the key I_J_CKT"),
    "ratings": Field("structural", note="RATE1..RATE12: each nonzero RATEn an ApparentPowerLimit <eq>_rate<n> "
                                        "(normalValue (MVA)) in the set <eq>_ratings on terminal <eq>_T1, type "
                                        "olt_rate<n> (RAW-9, RAW-20); NXFRAT > 0: a CurrentLimit, normalValue (kA) "
                                        "= RATEn / (sqrt(3) x BASKV) (ka_from_rating); 0 is no limit, no row"),
    "g_from": Field("structural", note=_SHUNT.format(name="GI", pair="BI", end="i", bus="I", column="gPerSection")),
    "b_from": Field("structural", note=_SHUNT.format(name="BI", pair="GI", end="i", bus="I", column="bPerSection")),
    "g_to": Field("structural", note=_SHUNT.format(name="GJ", pair="BJ", end="j", bus="J", column="gPerSection")),
    "b_to": Field("structural", note=_SHUNT.format(name="BJ", pair="GJ", end="j", bus="J", column="bPerSection")),
    "status": Field("mapped", note="ST: inService = (ST == 1), also on the line shunts; blank: 1 (defaulted)"),
    "metered_end": Field("structural", note="MET: on a tie (I and J in two AREAs) the home end is the non-metered one "
                                            "(1: J, 2: I), and both TieFlows sit on the metered terminal (R5); "
                                            "another code on a tie raises; elsewhere untranscribed, the loss-"
                                            "allocation end has no CIM home (CIM 18 gap, RAW-22); blank: 1 "
                                            "(defaulted)"),
    "length": Field("copied", (("ACLineSegment", "length", "km"),),
                    note="LEN, 'user-selected units' taken as km (RAW-21); 0 (the default): no length; a series "
                         "capacitor's LEN != 0 is listed on its row (SeriesCompensator is no Conductor, R1b-2)"),
    **{slot: Field("untranscribed", note=_OWNER) for slot in ("o1", "f1", "o2", "f2", "o3", "f3", "o4", "f4")},
}

_PROVENANCE = """PSS/E RAW Non-transformer branch -> ACLineSegment, SeriesCompensator (X < 0), LinearShuntCompensator
(line shunts), OperationalLimitSet + ApparentPowerLimit or CurrentLimit (ratings).
Source table: Non-transformer branch (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#branch"""


def is_series_capacitor(record: schema.BranchRecord) -> bool:
    return record.x < 0.0


def branch_class(record: schema.BranchRecord) -> str:
    return "SeriesCompensator" if is_series_capacitor(record) else "ACLineSegment"


def branch_mrid(record: schema.BranchRecord) -> str:
    return mrid(SERIES_CAPACITOR_PREFIX if is_series_capacitor(record) else LINE_PREFIX, record.ID)


def filled_branches(native) -> list[tuple[schema.BranchRecord, str | None]]:
    """Every branch in (I, J, CKT) order with its blank slots filled from ``raw_default``, and the defaulted comment."""
    defaults = raw_defaults(NATIVE_CLASS)
    records = sorted(native.list_by_class(NATIVE_CLASS),
                     key=lambda branch: (branch.from_bus_number, branch.to_bus_number, str(branch.circuit)))
    return [fill_keyed_defaults(FIELDS, record, defaults) for record in records]


def _other_base(record, base_kv_of: dict[int, float]) -> str | None:
    """``BASKV <kV> at bus J`` when bus J's base differs from bus I's, the branch's (R1b-1)."""
    to_kv = base_kv_of[record.to_bus_number]
    return None if to_kv == base_kv_of[record.from_bus_number] else f"BASKV {cell(to_kv)} at bus J"


def _check_series_capacitor(record) -> None:
    if record.b:
        raise ValueError(f"branch {record.ID}: a series capacitor (X < 0) with B={record.b!r}; SeriesCompensator "
                         "has no bch")


def map_branch(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float], bus_area: dict[int, int],
               ratings_in_current: bool) -> Document:
    branches = filled_branches(native)
    defaults = raw_defaults(NATIVE_CLASS)
    line_rows, capacitor_rows, shunt_rows = [], [], []
    ratings = RatingRows(ratings_in_current)
    ties = TieFlowRows(bus_area, control_area_numbers(native))
    for branch, defaulted in branches:
        base_kv = base_kv_of[branch.from_bus_number]
        voltage = base_voltage_mrid(base_kv)
        in_service = lookup(IN_SERVICE, branch.status, slot="status", record_id=f"branch {branch.ID}")
        first, second = substations_by_bus[branch.from_bus_number], substations_by_bus[branch.to_bus_number]
        container = first if first == second else None
        equipment = branch_mrid(branch)
        common = [equipment, cell(branch.name or branch.ID), str(branch.from_bus_number), str(branch.to_bus_number)]
        if is_series_capacitor(branch):
            _check_series_capacitor(branch)
            notes = [defaulted, listed_off_default(branch, ("length",), defaults), _other_base(branch, base_kv_of)]
            capacitor_rows.append(Row([*common, "capacitor", cell(branch.r), cell(branch.x), cell(in_service), voltage,
                                       container], comment="; ".join(filter(None, notes)) or None))
        else:
            line_values = [cell(branch.r), cell(branch.x), cell(branch.b), cell(branch.length or None)]
            notes = [defaulted, _other_base(branch, base_kv_of)]
            line_rows.append(Row([*common, *line_values, cell(in_service), voltage, container],
                                 comment="; ".join(filter(None, notes)) or None))
        ratings.add(equipment, branch.ratings, base_kv)
        buses = (branch.from_bus_number, branch.to_bus_number)
        if ties.is_tie(buses):
            record_id = f"branch {branch.ID}"
            ties.add(equipment, branch.ID, buses, branch_home_end(branch.metered_end, record_id), record_id)
        for end, bus, g, b in (("i", branch.from_bus_number, branch.g_from, branch.b_from),
                               ("j", branch.to_bus_number, branch.g_to, branch.b_to)):
            if g or b:
                shunt_rows.append(Row([mrid(SHUNT_PREFIX, f"{branch.ID}_{end}"), f"{branch.ID}_{end}", str(bus),
                                       cell(g), cell(b), cell(base_kv_of[bus]), "1", "1", "1", cell(in_service),
                                       base_voltage_mrid(base_kv_of[bus]), substations_by_bus[bus]]))

    statements = []
    untranscribed = off_tie_note(untranscribed_names(FIELDS), "MET")
    if line_rows:
        statements.append(Table(
            "ACLineSegment",
            [Column("mRID"), Column("name"), Column("bus1"), Column("bus2"), Column("r", "pu system"),
             Column("x", "pu system"), Column("bch", "pu system"), Column("length", "km"), Column("inService"),
             Column("BaseVoltage"), Column("EquipmentContainer")],
            line_rows, comment=untranscribed))
        untranscribed = None
    if capacitor_rows:
        statements.append(Table(
            "SeriesCompensator",
            [Column("mRID"), Column("name"), Column("bus1"), Column("bus2"), Column("compensatorType"),
             Column("r", "pu system"), Column("x", "pu system"), Column("inService"), Column("BaseVoltage"),
             Column("EquipmentContainer")],
            capacitor_rows, comment="\n".join(filter(None, [untranscribed, "series capacitors: X < 0 (RAW-15)"]))))
    if shunt_rows:
        statements.append(Table(
            "LinearShuntCompensator",
            [Column("mRID"), Column("name"), Column("bus"), Column("gPerSection", "pu system"),
             Column("bPerSection", "pu system"), Column("nomU", "kV"), Column("sections"), Column("normalSections"),
             Column("maximumSections"), Column("inService"), Column("BaseVoltage"), Column("EquipmentContainer")],
            shunt_rows, comment="line shunts GI + jBI, GJ + jBJ, switched with their line (RAW-13); linked to it by "
                                "the mRID only (CIM 18 gap)"))
    statements.extend(ratings.tables())
    statements.extend(ties.tables("MET"))
    return Document(name="branch", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(branches)))
