"""EnergyConnectionSchedule + its time point rows → GDM load time series (TIMESERIES_NEEDS.md §5, export).

Each schedule on an EnergyConsumer gives its DistributionLoad an ``active_power`` series in kilowatt and a
``reactive_power`` series in kilovar, for the columns it carries, in actual values: features ``profile_type``
``PMult`` / ``QMult``, ``use_actual=True``, and ``profile_name`` = the schedule's name when no other schedule has it,
else its uri() (ditto names the OpenDSS LoadShape from it, so a repeat would merge two shapes). Evenly spaced points
give a ``SingleTimeSeries``, any others a ``NonSequentialTimeSeries``.
"""

from __future__ import annotations

import logging
from collections import Counter

import cimprofiles.cim18.cim18v17 as cim
import pyarrow as pa
from cimbuilder.object_builder.schedule import TIME_POINT_CLASS
from cimhub_core.getters import describe
from gdm.quantities import ActivePower, ReactivePower
from infrasys.time_series_models import NonSequentialTimeSeries, SingleTimeSeries

from cimhub_gdm.exporter.shared import ExportContext
from cimhub_gdm.time_points import rows_by_schedule

log = logging.getLogger(__name__)

#: Point column → (GDM variable, quantity, SI unit of the column, GDM unit, ditto profile_type).
SERIES = {
    "p": ("active_power", ActivePower, "watt", "kilowatt", "PMult"),
    "q": ("reactive_power", ReactivePower, "var", "kilovar", "QMult"),
}

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
