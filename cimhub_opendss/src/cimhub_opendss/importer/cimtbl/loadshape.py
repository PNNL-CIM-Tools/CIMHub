"""OpenDSS ``LoadShape`` -> ``loadshape.cimtbl``: a ``ConformLoadGroup`` and its ``ConformLoadSchedule`` per shape a
Load names as ``yearly`` (S8, shape ``load_schedule``).

A Load's yearly shape scales its kW and kvar over time (Q by ``qmult``, else by ``mult``), as a GridLAB-D player
scales a base: so a shape is a group of conform loads with one regular schedule of multipliers (``value1Unit``
none). The points go to the Parquet sidecar (``shape_points``), not the artifact. DSS has no date: sample k (from 1)
is in force from k x interval (engine-checked), so ``startTime`` is the epoch 2020-01-01T00:00Z (ditto's) plus one
interval (TIMESERIES_NEEDS.md X2), and the shape's wrap-around has no CIM form (X4). Without ``npts`` the engine
reads none of ``mult``, inline or from a file (engine-checked: the load stays constant), so such a shape is a group
with no schedule, its name kept (EPRI M1's ``mult=1`` shapes). A shape no Load names as ``yearly`` (a PVSystem's
irradiance) is not mapped: the master counts it.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#s8-load-shapes``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Loadshape
GROUP_PREFIX = "lg_"
SCHEDULE_PREFIX = "ls_"
#: ditto's epoch for a DSS run's time 0 (TIMESERIES_NEEDS.md X2)
EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)
#: the engine's interval when the deck gives none (LoadShape.pas: Interval := 1.0, hours)
DEFAULT_INTERVAL_H = 1.0
#: each interval slot -> its unit (the timeStep header) and the timedelta keyword of that unit
INTERVALS = {"interval": ("h", "hours"), "minterval": ("min", "minutes"), "sinterval": ("s", "seconds")}

_GROUP, _SCHEDULE, _POINT = "ConformLoadGroup", "ConformLoadSchedule", "RegularTimePoint"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_INTERVAL = "the interval slot the deck assigned last (the engine's rule); 0 (an hour array) raises; none: 1 h"
_FILE = _NOT_MAPPED + " (the reader reads mult=(file=...))"

FIELDS = {
    "name": Field("copied", ((_GROUP, "name", None), (_SCHEDULE, "name", None)), "mRID = lg_ / ls_ + name, lowercased"),
    "npts": Field("structural", note="the number of points the engine reads: unset, none of mult (inline or "
                                     "from a file; engine-checked), so the group has no schedule; else it must equal "
                                     "the number of mult values"),
    "interval": Field("copied", ((_SCHEDULE, "timeStep", "h"),), _INTERVAL),
    "mult": Field("copied", ((_POINT, "value1", None),),
                  "the points, in the Parquet sidecar (S8-4); action=normalize divides them by their peak"),
    "hour": Field("structural", note=_NOT_MAPPED + " (an irregular shape has no RegularIntervalSchedule)"),
    "mean": Field("untranscribed", note="a Monte Carlo statistic; the engine computes it from mult"),
    "stddev": Field("untranscribed", note="a Monte Carlo statistic; the engine computes it from mult"),
    "csvfile": Field("structural", note=_FILE),
    "sngfile": Field("structural", note=_FILE),
    "dblfile": Field("structural", note=_FILE),
    "action": Field("derived", note="normalize: mult and qmult each divided by its largest magnitude, as the engine "
                                    "does (one assigned after it raises); DblSave, SngSave write files and are "
                                    "untranscribed; others raise"),
    "qmult": Field("copied", ((_POINT, "value2", None),),
                   "in the sidecar; unset: Q follows mult (the engine's rule), value2 unset"),
    "UseActual": Field("structural", note="Yes raises: a Load naming it takes the shape's peak as its kW, or keeps "
                                          "its own, by command order, which the record does not keep "
                                          "(engine-checked); default No"),
    "Pmax": Field("untranscribed", note="used only with UseActual"),
    "Qmax": Field("untranscribed", note="used only with UseActual"),
    "sinterval": Field("copied", ((_SCHEDULE, "timeStep", "s"),), _INTERVAL),
    "minterval": Field("copied", ((_SCHEDULE, "timeStep", "min"),), _INTERVAL),
    "Pbase": Field("structural", note=_NOT_MAPPED + " (a normalize base)"),
    "Qbase": Field("structural", note=_NOT_MAPPED + " (a normalize base)"),
    "Pmult": Field("structural", note=_NOT_MAPPED + " (a synonym of mult)"),
    "PQCSVFile": Field("structural", note=_FILE),
    "MemoryMapping": Field("untranscribed", note="how the engine stores the points"),
    "Mode": Field("untranscribed", note="generator dispatch; no effect on a Load"),
    "Interpolation": Field("untranscribed", note="AVG and EDGE agree at the solution steps, which are on the "
                                                 "interval grid (TIMESERIES_NEEDS.md X3)"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = tuple(slot for slot, field in FIELDS.items() if field.note.startswith(_NOT_MAPPED))
_FILE_ACTIONS = ("dblsave", "sngsave")

_PROVENANCE = """OpenDSS LoadShape -> ConformLoadGroup + ConformLoadSchedule (S8): the shapes Loads name as yearly.
Multipliers of each Load's kW and kvar; the points are in the Parquet sidecar, not here. startTime: the epoch
2020-01-01T00:00Z plus one interval, when the engine's sample 1 is in force (DSS has no date).
Source table: LoadShape (records: {count}; {mapped} named by a Load's yearly)
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#s8-load-shapes"""


_NO_POINTS = "npts unset: the engine reads none of mult (S8), so no schedule"


class Shape(NamedTuple):
    """A shape as the engine reads it: its interval (in ``unit``), multipliers, and Q multipliers or None."""
    interval: float
    unit: str  # a key of INTERVALS' units: h, min, s
    mult: list[float]
    qmult: list[float] | None


def yearly_shapes(native) -> set[str]:
    """The lowercased names of the shapes the deck's Loads name as ``yearly``."""
    return {str(load.yearly).lower() for load in native.list_by_class(schema.Load) if load.yearly is not None}


def unmapped_count(native) -> int:
    """How many of the deck's shapes no Load names as ``yearly`` (the master lists them as not mapped)."""
    named = yearly_shapes(native)
    return sum(1 for shape in native.list_by_class(NATIVE_CLASS) if str(shape.name).lower() not in named)


def normalized(values: list[float]) -> list[float]:
    """``values`` over their largest magnitude, as the engine's ``action=normalize`` (all zero: unchanged)."""
    peak = max(abs(value) for value in values)
    return list(values) if peak == 0 else [value / peak for value in values]


def start_time(shape: Shape) -> str:
    """``startTime``: the epoch plus one interval, when sample 1 is in force (ISO 8601, UTC)."""
    keyword = next(keyword for unit, keyword in INTERVALS.values() if unit == shape.unit)
    return (EPOCH + timedelta(**{keyword: shape.interval})).isoformat()


def read_shape(native, shape) -> Shape | None:
    """The shape as the engine reads it, or None when it reads no points (``npts`` unset); what the mapping does not
    cover raises."""
    label = f"LoadShape {shape.name}"
    unmapped = [slot for slot in _UNMAPPED if getattr(shape, slot) not in (None, [])]
    if unmapped:
        raise ValueError(f"{label}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets them)")
    if shape.UseActual:
        raise ValueError(f"{label}: UseActual=Yes; a Load naming it takes the shape's peak as its kW or keeps its own "
                         "by command order, which the record does not keep")
    if not shape.mult:
        raise ValueError(f"{label}: no mult; only a shape of multipliers is mapped")
    if shape.npts is None:
        return None
    if int(shape.npts) != len(shape.mult):
        raise ValueError(f"{label}: npts={shape.npts} but mult has {len(shape.mult)} values")
    if shape.qmult and len(shape.qmult) != len(shape.mult):
        raise ValueError(f"{label}: qmult has {len(shape.qmult)} values and mult {len(shape.mult)}")
    slot = native.last_of(shape, *INTERVALS)
    interval = DEFAULT_INTERVAL_H if slot is None else float(getattr(shape, slot))
    if interval <= 0:
        raise ValueError(f"{label}: {slot or 'interval'}={interval}; an hour array (interval 0) is not mapped")
    unit = INTERVALS[slot or "interval"][0]
    mult, qmult = list(shape.mult), list(shape.qmult) if shape.qmult else None
    action = str(shape.action).lower() if shape.action is not None else None
    if action == "normalize":
        later = _assigned_after(native, shape, "action", ("mult", "qmult"))
        if later:
            raise ValueError(f"{label}: {', '.join(later)} assigned after action=normalize; the engine normalizes "
                             "only the values before it")
        mult, qmult = normalized(mult), normalized(qmult) if qmult else None
    elif action is not None and action not in _FILE_ACTIONS:
        raise ValueError(f"{label}: action={shape.action} is not mapped (normalize, DblSave, SngSave are)")
    return Shape(interval, unit, mult, qmult)


def _assigned_after(native, record, slot: str, others: tuple[str, ...]) -> list[str]:
    """Which of ``others`` the deck assigned to ``record`` after its last ``slot``."""
    later, seen = [], False
    for assigned, _ in native.assignments(record):
        if assigned == slot:
            seen, later = True, []
        elif seen and assigned in others and assigned not in later:
            later.append(assigned)
    return later


def _mapped(native) -> list:
    named = yearly_shapes(native)
    return sorted((shape for shape in native.list_by_class(NATIVE_CLASS) if str(shape.name).lower() in named),
                  key=lambda shape: str(shape.name).lower())


def shape_points(native) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """``(value1, value2)``: each mapped shape's mult and qmult, keyed by its schedule's mRID (``ls_<name>``)."""
    value1, value2 = {}, {}
    for record in _mapped(native):
        shape = read_shape(native, record)
        if shape is None:
            continue
        key = mrid(SCHEDULE_PREFIX, record.name, lowercase=True)
        value1[key] = shape.mult
        if shape.qmult is not None:
            value2[key] = shape.qmult
    return value1, value2


def map_loadshape(native) -> Document:
    """The deck's yearly shapes as one ``loadshape`` document: the groups, then one schedule table per interval
    unit (a column has one unit)."""
    records = _mapped(native)
    if not records:
        return Document(name="loadshape", statements=[], profile=CIM_PROFILE)
    groups, schedules = [], {}
    for record in records:
        shape = read_shape(native, record)
        group = mrid(GROUP_PREFIX, record.name, lowercase=True)
        groups.append(Row([group, str(record.name)], comment=_NO_POINTS if shape is None else None))
        if shape is None:
            continue
        comment = untranscribed_values(FIELDS, record) or None
        schedules.setdefault(shape.unit, []).append(Row([
            mrid(SCHEDULE_PREFIX, record.name, lowercase=True), str(record.name), start_time(shape),
            cell(shape.interval), "none", "none" if shape.qmult is not None else None, group], comment=comment))
    statements = [Table(_GROUP, [Column("mRID"), Column("name")], groups)]  # schedules: none when no shape has npts
    for unit, _ in INTERVALS.values():
        if unit in schedules:
            statements.append(Table(_SCHEDULE, [
                Column("mRID"), Column("name"), Column("startTime"), Column("timeStep", unit), Column("value1Unit"),
                Column("value2Unit"), Column(_GROUP)], schedules[unit]))
    return Document(name="loadshape", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=native.count(NATIVE_CLASS), mapped=len(records)))
