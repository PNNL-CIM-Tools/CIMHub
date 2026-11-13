"""RAW Multi-section line grouping -> ``multi_section_line.cimtbl``: a ``Line`` per record, and an ``Update`` row
moving each of its sections (ordinary branches in ``branch.cimtbl``) into it (RAW-12). A section with both buses in one
substation (a series capacitor merges its buses) stays in that substation and joins the Line as additional grouped
equipment (``AdditionalEquipmentContainer``; R1b-3).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#multi-section-line``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.branch import branch_class, branch_mrid
from cimhub_raw.importer.cimtbl.zone import zone_mrid

NATIVE_CLASS = schema.MultiSectionLineRecord
PREFIX = "msl_"  # requested from the cimtbl-translate table owners (plan C3)
DUMMY_SLOTS = tuple(f"dum{number}" for number in range(1, 10))

FIELDS = {
    "i": Field("structural", note="I: the path's first bus; with J and ID the key, mRID msl_<I>_<J>_<ID>; the Line's "
                                  "Region is bus I's zone"),
    "j": Field("structural", note="J: the path's last bus"),
    "line_id": Field("copied", (("Line", "name", None),), note="ID: the key"),
    "met": Field("untranscribed", note="MET: the loss-allocation end has no CIM home (CIM 18 gap, RAW-22)"),
    "dum1": Field("structural", note="DUM1: the path I, DUM1, .., J names the sections, one branch per step; each "
                                     "section's EquipmentContainer becomes the Line (an Update row), except a "
                                     "section in one substation, which stays there and joins the Line as "
                                     "AdditionalEquipmentContainer (R1b-3)"),
    **{slot: Field("structural", note="as DUM1") for slot in DUMMY_SLOTS[1:]},
}

_PROVENANCE = """PSS/E RAW Multi-section line grouping -> Line, holding its sections (Update rows on the branches).
Source table: Multi-section line grouping (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#multi-section-line"""


def _path(record) -> list[int]:
    return [record.i, *(getattr(record, slot) for slot in DUMMY_SLOTS if getattr(record, slot)), record.j]


def _sections(record, branches_at: dict[frozenset, list], degree: dict[int, int], used: set) -> list:
    """The branch of each step of the record's path; an ambiguous or missing step, or a dummy bus with other than
    two branches, raises."""
    path = _path(record)
    for dummy in path[1:-1]:
        if degree.get(dummy, 0) != 2:
            raise ValueError(f"multi-section line {record.ID}: dummy bus {dummy} has {degree.get(dummy, 0)} branches; "
                             "the spec requires exactly two")
    sections = []
    for first, second in zip(path, path[1:]):
        candidates = [branch for branch in branches_at.get(frozenset((first, second)), []) if branch.ID not in used]
        if len(candidates) != 1:
            raise ValueError(f"multi-section line {record.ID}: {len(candidates)} unused branches join buses {first} "
                             f"and {second}; a section needs exactly one")
        used.add(candidates[0].ID)
        sections.append(candidates[0])
    return sections


def map_multi_section_line(native, bus_zones: dict[int, int], substations_by_bus: dict[int, str]) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda line: (line.i, line.j, str(line.line_id)))
    if not records:
        return Document(name="multi_section_line", statements=[], profile=CIM_PROFILE)
    branches_at: dict[frozenset, list] = {}
    degree: dict[int, int] = {}
    for branch in native.list_by_class(schema.BranchRecord):
        branches_at.setdefault(frozenset((branch.from_bus_number, branch.to_bus_number)), []).append(branch)
        for bus in (branch.from_bus_number, branch.to_bus_number):
            degree[bus] = degree.get(bus, 0) + 1

    line_rows, updates_by_class, additions_by_class = [], {}, {}
    used: set = set()
    for record in records:
        line = mrid(PREFIX, record.ID)
        in_substations = []
        for section in _sections(record, branches_at, degree, used):
            if substations_by_bus[section.from_bus_number] == substations_by_bus[section.to_bus_number]:
                in_substations.append(branch_mrid(section))
                additions_by_class.setdefault(branch_class(section), []).append(Row([branch_mrid(section), line]))
            else:
                updates_by_class.setdefault(branch_class(section), []).append(Row([branch_mrid(section), line]))
        notes = [f"path {', '.join(map(str, _path(record)))}"]
        if in_substations:
            notes.append(f"in substations: {', '.join(in_substations)}")
        line_rows.append(Row([line, cell(record.line_id), zone_mrid(bus_zones[record.i])], comment="; ".join(notes)))

    statements = [Table("Line", [Column("mRID"), Column("name"), Column("Region")], line_rows,
                        comment=untranscribed_names(FIELDS))]
    statements.extend(Table(name, [Column("mRID"), Column("EquipmentContainer")], rows, update=True)
                      for name, rows in updates_by_class.items())
    statements.extend(Table(name, [Column("mRID"), Column("AdditionalEquipmentContainer")], rows, update=True,
                            comment="sections in one substation: grouped in their Line, contained by the substation "
                                    "(R1b-3)")
                      for name, rows in additions_by_class.items())
    return Document(name="multi_section_line", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
