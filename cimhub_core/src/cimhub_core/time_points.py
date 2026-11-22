"""Time points beside the CIM XML: one Parquet table per TimePoint class, for any spoke with schedules.

``ieee13.xml`` holds the schedules; ``ieee13.EnergyConnectionTimePoint.parquet`` holds their points, one row each,
keyed by the schedule's uri() (CIM issue #7963: too many points for one graph object each). Two tables:

- ``EnergyConnectionTimePoint`` (nc_schedule, an instant and actual p, q): CIM-Builder's ``TIME_POINT_SCHEMA``, as
  its schedule builders make them (GDM's per-device series);
- ``RegularTimePoint`` (``REGULAR_TIME_POINT_SCHEMA``, a ``sequenceNumber`` and ``value1..3``): the points of any
  ``RegularIntervalSchedule``, a ``ConformLoadSchedule`` or ``NonConformLoadSchedule`` included. A point's time is
  the schedule's ``startTime`` + ``sequenceNumber`` x ``timeStep``, so the first point is 0 (the CIM definition);
  its units are the schedule's ``value1Unit``.. (GridLAB-D players, ``GLM_REWRITE_PLAN.md`` §8.9).

A reader/writer module: with a spoke's own reader and writer, the only code that touches the filesystem. Moved from
cimhub_gdm (its ``docs/TIMESERIES_NEEDS.md`` T6) so that GridLAB-D players can use it too.

Needs the ``time-points`` extra (``cimhub-core[time-points]``: pyarrow and cim-builder).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from cimbuilder.object_builder.schedule import TIME_POINT_CLASS, TIME_POINT_SCHEMA, EnergyConnectionScheduleBuilder

log = logging.getLogger(__name__)

REGULAR_TIME_POINT_CLASS = "RegularTimePoint"
#: A RegularTimePoint's attributes, its schedule as a uri column. No builder makes these tables, so the schema is here.
REGULAR_TIME_POINT_SCHEMA = pa.schema(
    [
        pa.field("IntervalSchedule", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("sequenceNumber", pa.int32(), nullable=False),
        pa.field("value1", pa.float64()),
        pa.field("value2", pa.float64()),
        pa.field("value3", pa.float64()),
    ],
    metadata={"cim:profile": "cim18v17", "cim:class": REGULAR_TIME_POINT_CLASS},
)


class TimePointTable(NamedTuple):
    schema: pa.Schema
    schedule_class: type  # the class (subclasses included) whose uri the first column holds
    position: str  # the column that orders a schedule's points; a repeated (schedule, position) raises


#: TimePoint class name → its table.
TIME_POINT_TABLES = {
    TIME_POINT_CLASS: TimePointTable(TIME_POINT_SCHEMA, cim.EnergyConnectionSchedule, "atTime"),
    REGULAR_TIME_POINT_CLASS: TimePointTable(REGULAR_TIME_POINT_SCHEMA, cim.RegularIntervalSchedule,
                                             "sequenceNumber"),
}


def time_points_path(xml_path, class_name: str) -> Path:
    """``<stem>.<class>.parquet`` beside the XML: ``ieee13.xml`` → ``ieee13.EnergyConnectionTimePoint.parquet``."""
    return Path(xml_path).with_suffix(f".{class_name}.parquet")


def write_time_points(time_points: dict[str, pa.Table], xml_path) -> list[Path]:
    """Write each table beside ``xml_path``, replacing any there; returns the paths written."""
    written = []
    for class_name, table in time_points.items():
        _check_schema(table, _table_kind(class_name).schema, class_name)
        path = time_points_path(xml_path, class_name)
        pq.write_table(table, path, compression="zstd")
        written.append(path)
    return written


def read_time_points(xml_path, network) -> dict[str, pa.Table]:
    """The tables beside ``xml_path``, checked against ``network`` (the model read from that XML).

    Raises on a table whose schema is not its class's, on a row whose schedule is not in the network (an orphan), or
    on a schedule with two points at one time. A schedule with no rows gets one WARNING.
    """
    time_points = {}
    for class_name, kind in TIME_POINT_TABLES.items():
        path = time_points_path(xml_path, class_name)
        schedules = _schedules(network, kind.schedule_class)
        table = pq.read_table(path) if path.exists() else None
        if table is not None:
            _check_schema(table, kind.schema, class_name)
            _check_rows(table, schedules, path, kind.position)
            time_points[class_name] = table
        _warn_empty(schedules, table, kind.schedule_class)
    return time_points


def regular_time_points(values: dict[str, list[float]], value2: dict[str, list[float]] | None = None) -> pa.Table:
    """``{schedule uri: value1 per point}`` as a ``RegularTimePoint`` table, the points numbered from 0 (pure).
    ``value2`` gives the second value per point of the schedules it names (null elsewhere); another length raises."""
    value2 = value2 or {}
    unknown = sorted(set(value2) - set(values))
    if unknown:
        raise ValueError(f"value2 for schedules with no value1: {unknown[:5]}")
    keys, numbers, first, second = [], [], [], []
    for uri, points in values.items():
        seconds = value2.get(uri, [None] * len(points))
        if len(seconds) != len(points):
            raise ValueError(f"schedule {uri}: {len(points)} value1 and {len(seconds)} value2 points")
        keys += [uri] * len(points)
        numbers += range(len(points))
        first += points
        second += seconds
    columns = {"IntervalSchedule": keys, "sequenceNumber": numbers, "value1": first, "value2": second,
               "value3": [None] * len(keys)}
    return pa.table(columns, schema=REGULAR_TIME_POINT_SCHEMA)


def add_regular_time_points(time_points: dict, network, values: dict[str, list[float]],
                            value2: dict[str, list[float]] | None = None) -> None:
    """Put the ``RegularTimePoint`` table of ``values`` (``{schedule mRID: value1 per point}``, ``value2`` likewise)
    into the caller's ``time_points``, keyed by each schedule's uri in ``network`` (an importer's, once bound). A
    table there already raises, as does an mRID no ``RegularIntervalSchedule`` of the network has."""
    if REGULAR_TIME_POINT_CLASS in time_points:
        raise ValueError(f"time_points already holds a {REGULAR_TIME_POINT_CLASS} table")
    uris = {schedule.mRID: uri for uri, schedule in _schedules(network, cim.RegularIntervalSchedule).items()}
    missing = sorted(set(values) - set(uris))
    if missing:
        raise ValueError(f"no RegularIntervalSchedule with mRID {missing[:5]} in the network")
    time_points[REGULAR_TIME_POINT_CLASS] = regular_time_points(
        {uris[mrid]: points for mrid, points in values.items()},
        {uris[mrid]: points for mrid, points in (value2 or {}).items()})


def add_device_time_points(time_points: dict, network, points: dict[str, tuple]) -> None:
    """Put the ``EnergyConnectionTimePoint`` table of ``points`` (``{schedule mRID: (times, p, q)}``: when each point
    takes effect, p in kW and q in kVAr in the load sign, None for a column the schedule does not carry) into the
    caller's ``time_points``, through CIM-Builder's ``EnergyConnectionScheduleBuilder.time_points`` (its schema; kW
    and kVAr to SI). A table there already raises, as does an mRID no ``EnergyConnectionSchedule`` of the network
    has."""
    if TIME_POINT_CLASS in time_points:
        raise ValueError(f"time_points already holds a {TIME_POINT_CLASS} table")
    schedules = {schedule.mRID: schedule for schedule in _schedules(network, cim.EnergyConnectionSchedule).values()}
    missing = sorted(set(points) - set(schedules))
    if missing:
        raise ValueError(f"no EnergyConnectionSchedule with mRID {missing[:5]} in the network")
    builder = EnergyConnectionScheduleBuilder(network, None)  # time_points adds nothing to the graph
    tables = [builder.time_points(schedules[mrid], times=times, p=p, q=q, p_unit="kW", q_unit="kVAr")
              for mrid, (times, p, q) in points.items()]
    time_points[TIME_POINT_CLASS] = pa.concat_tables(tables)


def rows_by_schedule(table: pa.Table) -> dict[str, pa.Table]:
    """Each schedule's rows, keyed by its uri(), in the table's order (time or sequence order as written), split in
    one sort (a filter per schedule would be quadratic on a feeder's worth of schedules)."""
    keys = table.column(0).cast(pa.string())
    order = pc.sort_indices(keys)  # stable: each schedule's rows keep their time order
    rows, runs = table.take(order), pc.run_end_encode(keys.take(order).combine_chunks())
    groups, start = {}, 0
    for end, uri in zip(runs.run_ends.to_pylist(), runs.values.to_pylist()):
        groups[uri] = rows.slice(start, end - start)
        start = end
    return groups


def _schedules(network, schedule_class: type) -> dict:
    """``{uri: schedule}`` of every ``schedule_class`` object in ``network``, subclasses included (the graph is keyed
    by exact class)."""
    return {schedule.uri(): schedule for cls, objects in network.graph.items() if issubclass(cls, schedule_class)
            for schedule in objects.values()}


def _table_kind(class_name: str) -> TimePointTable:
    if class_name not in TIME_POINT_TABLES:
        raise ValueError(f"no time point table for {class_name!r} (known: {sorted(TIME_POINT_TABLES)})")
    return TIME_POINT_TABLES[class_name]


def _check_schema(table: pa.Table, schema: pa.Schema, class_name: str) -> None:
    if not table.schema.equals(schema, check_metadata=True):
        raise ValueError(f"{class_name} table schema is not its TimePoint schema:\n{table.schema}")


def _check_rows(table: pa.Table, schedules: dict, path: Path, position: str) -> None:
    keys = table.column(0).cast(pa.string())  # row groups may carry different dictionaries
    orphans = sorted(set(pc.unique(keys).to_pylist()) - set(schedules))
    if orphans:
        raise ValueError(f"{path.name}: rows for {len(orphans)} schedule(s) not in the XML: {orphans[:5]}")
    pairs = pa.table({"schedule": keys, position: table.column(position)})
    counts = pairs.group_by(["schedule", position]).aggregate([([], "count_all")])
    repeated = counts.filter(pc.greater(counts.column("count_all"), 1))
    if repeated.num_rows:
        first = repeated.slice(0, 1).to_pylist()[0]
        raise ValueError(f"{path.name}: {repeated.num_rows} repeated (schedule, {position}) pairs, e.g. {first}")


def _warn_empty(schedules: dict, table: pa.Table | None, schedule_class: type) -> None:
    keys = set() if table is None else set(pc.unique(table.column(0).cast(pa.string())).to_pylist())
    empty = sorted(schedule.mRID for uri, schedule in schedules.items() if uri not in keys)
    if empty:
        log.warning("%d %s(s) have no time points: %s", len(empty), schedule_class.__name__, empty)
