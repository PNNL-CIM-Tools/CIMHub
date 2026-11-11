"""Time points beside the CIM XML: one Parquet table per TimePoint class (TIMESERIES_NEEDS.md T6).

``ieee13.xml`` holds the schedules; ``ieee13.EnergyConnectionTimePoint.parquet`` holds their points, one row each,
keyed by the schedule's uri(). With ``gdm_reader.py`` and ``gdm_writer.py``, the only modules in the spoke that touch
the filesystem. Generic to any spoke: it moves to cimhub_core once a second one has schedules.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from cimbuilder.object_builder.schedule import TIME_POINT_CLASS, TIME_POINT_SCHEMA

log = logging.getLogger(__name__)

#: TimePoint class name → (its table's schema, the schedule class whose uri its first column holds).
TIME_POINT_TABLES = {TIME_POINT_CLASS: (TIME_POINT_SCHEMA, cim.EnergyConnectionSchedule)}


def time_points_path(xml_path, class_name: str) -> Path:
    """``<stem>.<class>.parquet`` beside the XML: ``ieee13.xml`` → ``ieee13.EnergyConnectionTimePoint.parquet``."""
    return Path(xml_path).with_suffix(f".{class_name}.parquet")


def write_time_points(time_points: dict[str, pa.Table], xml_path) -> list[Path]:
    """Write each table beside ``xml_path``, replacing any there; returns the paths written."""
    written = []
    for class_name, table in time_points.items():
        schema, _ = _table_kind(class_name)
        _check_schema(table, schema, class_name)
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
    for class_name, (schema, schedule_class) in TIME_POINT_TABLES.items():
        path = time_points_path(xml_path, class_name)
        schedules = {schedule.uri(): schedule for schedule in network.graph.get(schedule_class, {}).values()}
        table = pq.read_table(path) if path.exists() else None
        if table is not None:
            _check_schema(table, schema, class_name)
            _check_rows(table, schedules, path)
            time_points[class_name] = table
        _warn_empty(schedules, table, schedule_class)
    return time_points


def rows_by_schedule(table: pa.Table) -> dict[str, pa.Table]:
    """Each schedule's rows, keyed by its uri(), in time order, split in one sort (a filter per schedule would be
    quadratic on a feeder's worth of schedules)."""
    keys = table.column(0).cast(pa.string())
    order = pc.sort_indices(keys)  # stable: each schedule's rows keep their time order
    rows, runs = table.take(order), pc.run_end_encode(keys.take(order).combine_chunks())
    groups, start = {}, 0
    for end, uri in zip(runs.run_ends.to_pylist(), runs.values.to_pylist()):
        groups[uri] = rows.slice(start, end - start)
        start = end
    return groups


def _table_kind(class_name: str):
    if class_name not in TIME_POINT_TABLES:
        raise ValueError(f"no time point table for {class_name!r} (known: {sorted(TIME_POINT_TABLES)})")
    return TIME_POINT_TABLES[class_name]


def _check_schema(table: pa.Table, schema: pa.Schema, class_name: str) -> None:
    if not table.schema.equals(schema, check_metadata=True):
        raise ValueError(f"{class_name} table schema is not the builder's TIME_POINT_SCHEMA:\n{table.schema}")


def _check_rows(table: pa.Table, schedules: dict, path: Path) -> None:
    keys = table.column(0).cast(pa.string())  # row groups may carry different dictionaries
    orphans = sorted(set(pc.unique(keys).to_pylist()) - set(schedules))
    if orphans:
        raise ValueError(f"{path.name}: rows for {len(orphans)} schedule(s) not in the XML: {orphans[:5]}")
    pairs = pa.table({"schedule": keys, "atTime": table.column("atTime")})
    counts = pairs.group_by(["schedule", "atTime"]).aggregate([([], "count_all")])
    repeated = counts.filter(pc.greater(counts.column("count_all"), 1))
    if repeated.num_rows:
        first = repeated.slice(0, 1).to_pylist()[0]
        raise ValueError(f"{path.name}: {repeated.num_rows} repeated (schedule, atTime) pairs, e.g. {first}")


def _warn_empty(schedules: dict, table: pa.Table | None, schedule_class: type) -> None:
    keys = set() if table is None else set(pc.unique(table.column(0).cast(pa.string())).to_pylist())
    empty = sorted(schedule.mRID for uri, schedule in schedules.items() if uri not in keys)
    if empty:
        log.warning("%d %s(s) have no time points: %s", len(empty), schedule_class.__name__, empty)
