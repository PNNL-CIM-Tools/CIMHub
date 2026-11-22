"""A load's group schedule: ``ConformLoad → ConformLoadGroup ← ConformLoadSchedule`` (the same for NonConformLoad).

A conform load follows its group's curve as a multiplier of its own p and q (a GridLAB-D player, a DSS LoadShape);
a non-conform load's group schedule is in its value units (``value1Unit``). A group has either one time series (a
schedule with no Season and no DayType: a player's or a DSS LoadShape's, from its ``startTime``) or a recurring day
per season and day type (a GridLAB-D schedule's, ``startTime`` a time of day); two time series, or both kinds, raise.
The points are in the Parquet sidecar
(``cimhub_core.time_points``, ``RegularTimePoint``), not on the schedule: ``get_schedule_points`` reads a schedule's
from the sidecar's rows split by schedule (``time_points.rows_by_schedule``), so this module needs no pyarrow.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe

_log = logging.getLogger(__name__)


class LoadSchedule(NamedTuple):
    conform: bool  # True: ConformLoad (a multiplier); False: NonConformLoad
    group: cim.LoadGroup
    schedule: cim.SeasonDayTypeSchedule | None  # the one time series; None: none (only days, or only the name)
    start: str | None  # the time series' startTime as written (ISO 8601, with its offset)
    step: float | None  # the time series' timeStep in seconds
    days: tuple = ()  # the schedules of a Season or DayType (a recurring day), by mRID


def get_load_schedule(consumer: cim.EnergyConsumer) -> LoadSchedule | None:
    """The consumer's group and its one schedule, or ``None`` for a plain EnergyConsumer or a load with no group."""
    if isinstance(consumer, cim.ConformLoad):
        conform, group = True, consumer.LoadGroup
        schedules = [] if group is None else group.ConformLoadSchedules
    elif isinstance(consumer, cim.NonConformLoad):
        conform, group = False, consumer.LoadGroup
        schedules = [] if group is None else group.NonConformLoadSchedules
    else:
        return None
    if group is None:
        return None
    days = tuple(sorted((schedule for schedule in schedules if schedule.Season is not None
                         or schedule.DayType is not None), key=lambda schedule: schedule.mRID))
    series = [schedule for schedule in schedules if schedule not in days]
    if len(series) > 1 or (series and days):
        raise ValueError(f"{describe(group)}: {len(series)} schedules with no Season or DayType and {len(days)} "
                         "with one; a group has one time series or days by season and day type")
    if not series:
        return LoadSchedule(conform, group, None, None, None, days)
    [schedule] = series
    return LoadSchedule(conform, group, schedule, schedule.startTime, get_qty(schedule, "timeStep", "s"))


class SchedulePoints(NamedTuple):
    value1: list[float]  # one per point, sequenceNumber 0, 1, ...
    value2: list[float] | None  # None: value2 is unset at every point


def get_schedule_points(schedule: cim.RegularIntervalSchedule, rows_by_schedule: dict) -> SchedulePoints | None:
    """The schedule's points from its ``RegularTimePoint`` rows (``rows_by_schedule``: ``{uri: rows}``), or ``None``
    when it has none. Sequence numbers other than 0, 1, ... in order, or a value2 set at only some points, raise."""
    rows = rows_by_schedule.get(schedule.uri())
    if rows is None:
        return None
    numbers = rows.column("sequenceNumber").to_pylist()
    if numbers != list(range(len(numbers))):
        raise ValueError(f"{describe(schedule)}: points numbered {numbers[:5]}...; every step from 0 is read, in order")
    value1, value2 = rows.column("value1").to_pylist(), rows.column("value2").to_pylist()
    if None in value1:
        raise ValueError(f"{describe(schedule)}: value1 is unset at {value1.count(None)} of {len(value1)} points")
    unset = value2.count(None)
    if unset == len(value2):
        return SchedulePoints(value1, None)
    if unset:
        raise ValueError(f"{describe(schedule)}: value2 is unset at {unset} of {len(value2)} points")
    return SchedulePoints(value1, value2)


def log_dropped_schedules(consumers, target: str) -> None:
    """One WARNING naming the groups whose schedules ``target`` does not export (it writes the loads static)."""
    groups = sorted({str(found.group.name or found.group.mRID) for found in map(get_load_schedule, consumers)
                     if found is not None and (found.schedule is not None or found.days)})
    if groups:
        _log.warning("%s: the schedules of %d load group(s) are not exported; their loads are written static: %s",
                     target, len(groups), groups)
