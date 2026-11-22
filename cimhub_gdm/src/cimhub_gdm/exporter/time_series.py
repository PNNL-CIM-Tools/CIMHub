"""Load schedules + their time point rows → GDM load time series (TIMESERIES_NEEDS.md §5 and §8, export).

Each schedule on an EnergyConsumer gives its DistributionLoad an ``active_power`` series in kilowatt and a
``reactive_power`` series in kilovar, for the columns it carries, in actual values: features ``profile_type``
``PMult`` / ``QMult``, ``use_actual=True``, and ``profile_name`` = the schedule's name when no other schedule has it,
else its uri() (ditto names the OpenDSS LoadShape from it, so a repeat would merge two shapes). Evenly spaced points
give a ``SingleTimeSeries``, any others a ``NonSequentialTimeSeries``.

A load group's one regular schedule (``ConformLoadSchedule``, ``NonConformLoadSchedule``; its ``RegularTimePoint``
rows) is one ``SingleTimeSeries`` shared by the GDM loads of the group's members, as ditto shares an OpenDSS
loadshape: from ``startTime`` (naive UTC) every ``timeStep``, ``profile_name`` the group's name (its uri when two
groups share one). A ConformLoad's are multipliers (``use_actual=False``: value1 ``PMult``, value2 ``QMult``, none
when value2 is unset, so Q follows P as in OpenDSS), labelled kilowatt and kilovar as ditto labels a loadshape's
(its OpenDSS writer needs units; ``use_actual`` says they are multipliers); a NonConformLoad's are actual kW and kvar
(``use_actual=True``). A group with no schedule or no points, or with days by season and day type (a GridLAB-D
schedule's: a GDM series needs absolute times), is written static, named in one WARNING.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

import cimprofiles.cim18.cim18v17 as cim
import numpy as np
import pyarrow as pa
from cimbuilder.object_builder.schedule import TIME_POINT_CLASS
from cimhub_core.getters import describe
from cimhub_core.getters.load_schedule import get_load_schedule, get_schedule_points
from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from gdm.quantities import ActivePower, ReactivePower
from infrasys.time_series_models import NonSequentialTimeSeries, SingleTimeSeries

from cimhub_gdm.exporter.shared import ExportContext

log = logging.getLogger(__name__)

#: Point column → (GDM variable, quantity, SI unit of the column, GDM unit, ditto profile_type).
SERIES = {
    "p": ("active_power", ActivePower, "watt", "kilowatt", "PMult"),
    "q": ("reactive_power", ReactivePower, "var", "kilovar", "QMult"),
}

#: A NonConformLoadSchedule's (unit, multiplier) → its pint unit, per value column.
GROUP_UNITS = {
    "value1": {(cim.UnitSymbol.W, None): "watt", (cim.UnitSymbol.W, cim.UnitMultiplier.none): "watt",
               (cim.UnitSymbol.W, cim.UnitMultiplier.k): "kilowatt"},
    "value2": {(cim.UnitSymbol.VAr, None): "var", (cim.UnitSymbol.VAr, cim.UnitMultiplier.none): "var",
               (cim.UnitSymbol.VAr, cim.UnitMultiplier.k): "kilovar"},
}
#: value column → the SERIES column it feeds
GROUP_COLUMNS = {"value1": "p", "value2": "q"}

#: GDM keeps no interpolation: a sample holds for its interval, as an OpenDSS fixed-interval loadshape.
EXPORTED_INTERPOLATION = (None, cim.TimeSeriesInterpolationKind.previous)


def add_time_series(system, context: ExportContext, time_points: dict | None) -> None:
    """Attach every EnergyConnectionSchedule's points to the GDM load made from its EnergyConsumer."""
    schedules = sorted(context.network.graph.get(cim.EnergyConnectionSchedule, {}).values(), key=lambda s: s.mRID)
    if not schedules:
        return
    table = (time_points or {}).get(TIME_POINT_CLASS)
    if table is None:
        log.warning("%d EnergyConnectionSchedule(s) exported without their time points (no %s table given): %s",
                    len(schedules), TIME_POINT_CLASS, [s.mRID for s in schedules])
        return
    names = Counter(schedule.name for schedule in schedules)
    by_schedule = rows_by_schedule(table)
    empty = []
    for schedule in schedules:
        load = context.gdm(_consumer(schedule))
        rows = by_schedule.get(schedule.uri())
        if rows is None:
            empty.append(schedule.mRID)
            continue
        profile_name = schedule.name if schedule.name and names[schedule.name] == 1 else schedule.uri()
        # GDM times are naive UTC; a naive cast also spares pyarrow a zone lookup per point in to_pylist
        times = rows.column("atTime").cast(pa.timestamp("us")).to_pylist()
        for column, (variable, quantity, si_unit, unit, profile_type) in SERIES.items():
            values = rows.column(column)
            if values.null_count == len(values):
                continue
            if values.null_count:
                raise ValueError(f"{describe(schedule)}: {column} is null at {values.null_count} of {len(values)} "
                                 "times; GDM has no gaps in a series")
            data = quantity(values.to_numpy(), si_unit).to(unit)
            system.add_time_series(_series(variable, data, times), load, profile_type=profile_type,
                                   profile_name=profile_name, use_actual=True)
    if empty:
        log.warning("%d EnergyConnectionSchedule(s) have no time points: %s", len(empty), empty)


def _consumer(schedule) -> cim.EnergyConsumer:
    """The schedule's EnergyConsumer; another EnergyConnection, or an interpolation GDM can't keep, raises."""
    connection = schedule.EnergyConnection
    if not isinstance(connection, cim.EnergyConsumer):
        raise ValueError(f"{describe(schedule)}: no GDM export yet for a schedule on "
                         f"{type(connection).__name__ if connection is not None else 'nothing'}")
    if schedule.interpolationKind not in EXPORTED_INTERPOLATION:
        raise ValueError(f"{describe(schedule)}: interpolationKind {schedule.interpolationKind.value}; a GDM series "
                         "holds each sample until the next (previous)")
    return connection


def _series(variable: str, data, times: list):
    """A ``SingleTimeSeries`` when the times are evenly spaced, else a ``NonSequentialTimeSeries``."""
    steps = {later - earlier for earlier, later in zip(times, times[1:])}
    if len(steps) == 1:
        return SingleTimeSeries.from_array(data=data, name=variable, initial_timestamp=times[0],
                                           resolution=steps.pop())
    return NonSequentialTimeSeries.from_array(data=data, name=variable, timestamps=times)


def add_group_series(system, context: ExportContext, consumers, time_points: dict | None) -> None:
    """Attach each load group's schedule (module docstring) to the GDM loads of its members, one shared series per
    value column; one WARNING names the groups written static."""
    table = (time_points or {}).get(REGULAR_TIME_POINT_CLASS)
    by_schedule = rows_by_schedule(table) if table is not None else {}
    members, static = {}, set()  # schedule uri -> (its LoadSchedule, the GDM loads); group names written static
    for consumer in consumers:
        found = get_load_schedule(consumer)
        if found is None:
            continue
        if found.schedule is None or found.schedule.uri() not in by_schedule:
            static.add(str(found.group.name or found.group.mRID))
            continue
        members.setdefault(found.schedule.uri(), (found, []))[1].append(context.gdm(consumer))
    names = Counter(found.group.name for found, _ in members.values())
    for uri, (found, loads) in members.items():
        points = get_schedule_points(found.schedule, by_schedule)
        profile_name = found.group.name if found.group.name and names[found.group.name] == 1 else uri
        start, resolution = _regular_axis(found)
        for column, values in (("value1", points.value1), ("value2", points.value2)):
            if values is None:
                continue
            variable, quantity, _, unit, profile_type = SERIES[GROUP_COLUMNS[column]]
            data = quantity(np.array(values), unit if found.conform else _group_unit(found.schedule, column)).to(unit)
            series = SingleTimeSeries.from_array(data=data, name=variable, initial_timestamp=start,
                                                 resolution=resolution)
            system.add_time_series(series, *loads, profile_type=profile_type, profile_name=profile_name,
                                   use_actual=not found.conform)
    if static:
        log.warning("%d load group(s) are written static (no schedule, no points, or days by season and day type): "
                    "%s", len(static), sorted(static))


def _regular_axis(found) -> tuple[datetime, timedelta]:
    """(initial timestamp as naive UTC, resolution) of a group schedule; no startTime, no offset or no step raise."""
    if found.start is None or found.step is None or found.step <= 0:
        raise ValueError(f"{describe(found.schedule)}: startTime {found.start}, timeStep {found.step} s; a GDM "
                         "series needs both")
    start = datetime.fromisoformat(found.start)
    if start.tzinfo is None:
        raise ValueError(f"{describe(found.schedule)}: startTime {found.start} has no UTC offset")
    return start.astimezone(timezone.utc).replace(tzinfo=None), timedelta(seconds=found.step)


def _group_unit(schedule, column: str) -> str:
    """The pint unit of a NonConformLoadSchedule's value column; a conform schedule has none (multipliers)."""
    key = (getattr(schedule, f"{column}Unit"), getattr(schedule, f"{column}Multiplier"))
    if key not in GROUP_UNITS[column]:
        raise ValueError(f"{describe(schedule)}: {column} in {key}; a load's actual power is in W or kW, kvar in "
                         "VAr or kVAr")
    return GROUP_UNITS[column][key]
