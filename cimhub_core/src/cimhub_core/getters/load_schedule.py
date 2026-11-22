"""A load's group schedule: ``ConformLoad → ConformLoadGroup ← ConformLoadSchedule`` (the same for NonConformLoad).

A conform load follows its group's curve as a multiplier of its own p and q (a GridLAB-D player, a DSS LoadShape);
a non-conform load's group schedule is in its value units (``value1Unit``). One schedule per group: CIM allows one
per season and day type, which no format here holds yet, so several raise. The points are in the Parquet sidecar
(``cimhub_core.time_points``, ``RegularTimePoint``), not on the schedule.
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
    schedule: cim.SeasonDayTypeSchedule | None  # None: the group has no schedule (only its name is known)
    start: str | None  # startTime as written (ISO 8601, with its offset)
    step: float | None  # timeStep in seconds


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
    if len(schedules) > 1:
        raise ValueError(f"{describe(group)}: {len(schedules)} schedules (seasons or day types); one is read")
    if not schedules:
        return LoadSchedule(conform, group, None, None, None)
    [schedule] = schedules
    return LoadSchedule(conform, group, schedule, schedule.startTime, get_qty(schedule, "timeStep", "s"))


def log_dropped_schedules(consumers, target: str) -> None:
    """One WARNING naming the groups whose schedules ``target`` does not export (it writes the loads static)."""
    groups = sorted({str(found.group.name or found.group.mRID) for found in map(get_load_schedule, consumers)
                     if found is not None and found.schedule is not None})
    if groups:
        _log.warning("%s: the schedules of %d load group(s) are not exported; their loads are written static: %s",
                     target, len(groups), groups)
