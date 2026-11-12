"""Line (a path of branch sections) -> Multi-section line grouping (``EXPORT_MAPPING.md#multi-section-line``).

A Line's sections are the ACLineSegments and SeriesCompensators it contains or groups: a section that sits in one
substation stays contained there and is grouped in its Line (``AdditionalGroupedEquipment``, import R1b-3; E1-1).
They must form one path I, DUM1, ..., J of one to nine dummy buses, each joining exactly two branches, as on import.
A Line that is not such a path writes no record and is counted on the log line (the one fallback: the grouping is
lost, its sections are written as branches either way).
"""

from __future__ import annotations

import logging
from collections import Counter

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_raw.exporter import branch
from cimhub_raw.exporter.identity import keyed_ids, terminal_buses
from cimhub_raw.importer.cimtbl.multi_section_line import DUMMY_SLOTS, PREFIX

NATIVE_CLASS = schema.MultiSectionLineRecord
CIM_CLASSES = ()  # a Line is a container, not conducting equipment
ID_WIDTH = 2
ID_PREFIX = "&"  # PSS/E's first character of a multi-section line ID

_DUMMY = Slot("written", "the path's next dummy bus, blank past its end")
SLOTS = {NATIVE_CLASS: {
    "i": Slot("written", "I: the path's first bus (by the msl_<I>_<J>_<ID> key, else the lower end)"),
    "j": Slot("written", "J: the path's last bus"),
    "dum1": Slot("written", "DUM1: the path's first dummy bus"),
    "line_id": Slot("written", "ID: the msl_<I>_<J>_<ID> key, else the next free &1, &2, ... (X2)"),
    "met": Slot("unset", "MET: the loss-allocation end has no CIM home (CIM 18 gap, RAW-22)"),
    **{slot: _DUMMY for slot in DUMMY_SLOTS[1:]},
}}

_log = logging.getLogger(__name__)


def export(context) -> list[schema.MultiSectionLineRecord]:
    """One record per Line whose sections form one path, by key."""
    at_bus = _branches_at_bus(context)
    paths = []
    skipped = 0
    for line in context.objects(cim.Line):
        path = _section_path(line, context, at_bus)
        if path is None:
            skipped += 1
        else:
            paths.append((line, _oriented(line, path)))
    if skipped:
        _log.info("%d Line(s) whose sections are not one path write no multi-section line", skipped)
    ids = keyed_ids([(line, PREFIX, (path[0], path[-1])) for line, path in paths], ID_WIDTH, ID_PREFIX)
    records = []
    for line, path in paths:
        dummies = dict(zip(DUMMY_SLOTS, path[1:-1]))
        records.append(schema.MultiSectionLineRecord(i=path[0], j=path[-1], line_id=ids[line], **dummies))
    return sorted(records, key=lambda record: (record.i, record.j, record.line_id))


def _branches_at_bus(context) -> dict[int, set]:
    """bus number -> the ACLineSegments and SeriesCompensators on it."""
    at_bus: dict[int, set] = {}
    for device in context.objects(*branch.CIM_CLASSES):
        for bus in terminal_buses(device, context):
            at_bus.setdefault(bus, set()).add(device)
    return at_bus


def _section_path(line, context, at_bus: dict[int, set]) -> list[int] | None:
    """The buses of the Line's path; None when its sections are not one path."""
    edges = {device: terminal_buses(device, context) for device in [*line.Equipments, *line.AdditionalGroupedEquipment]
             if isinstance(device, branch.CIM_CLASSES)}
    return _walk(edges, at_bus) if edges else None


def _walk(edges: dict, at_bus: dict[int, set]) -> list[int] | None:
    """The path from one loose end to the other through every section; None when there is no such path, a dummy
    bus has another branch, or the path has no dummy bus or more than nine."""
    counts = Counter(bus for buses in edges.values() for bus in buses)
    ends = [bus for bus, count in counts.items() if count == 1]
    if len(ends) != 2 or any(count > 2 for count in counts.values()):
        return None
    if any(len(at_bus[bus]) != 2 for bus, count in counts.items() if count == 2):
        return None
    path, unused = [min(ends)], set(edges)
    while unused:
        step = [device for device in unused if path[-1] in edges[device]]
        if len(step) != 1:
            return None
        [device] = step
        unused.remove(device)
        first, second = edges[device]
        path.append(second if first == path[-1] else first)
    return path if 1 <= len(path) - 2 <= len(DUMMY_SLOTS) else None


def _oriented(line, path: list[int]) -> list[int]:
    """The path as the mRID msl_<I>_<J>_ names it; from its lower end otherwise (``_walk`` starts there)."""
    reverse = f"{PREFIX}{path[-1]}_{path[0]}_"
    return path[::-1] if line.mRID.startswith(reverse) else path
