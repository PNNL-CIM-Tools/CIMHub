"""GDM time series → nc_schedule ``EnergyConnectionSchedule`` + time point rows (TIMESERIES_NEEDS.md T1-T6).

A DistributionLoad's ``active_power`` / ``reactive_power`` series become one schedule on its EnergyConsumer, in actual
values (T1): a multiplier series is scaled by the consumer's p or q, and a load with only a P multiplier gets
q(t) = multiplier(t) × q, as OpenDSS does with a loadshape that has no QMult. The points are rows of a pyarrow table
(T6), never graph objects. Every other series has no CIM home yet and is dropped with one WARNING (T2, T3).
"""

from __future__ import annotations

import logging

import pyarrow as pa
from cimbuilder.object_builder import EnergyConnectionScheduleBuilder
from gdm.systems.distribution.components import DistributionLoad
from infrasys.time_series_models import Deterministic, NonSequentialTimeSeries, SingleTimeSeries

from cimhub_gdm.importer import load as load_family
from cimhub_gdm.importer.shared import Naming, object_mrid

log = logging.getLogger(__name__)

#: Mapped series types: sampled at a fixed resolution, or at listed timestamps.
MAPPED_TYPES = (SingleTimeSeries, NonSequentialTimeSeries)
#: infrasys types that raise: forecasts are out of scope (TIMESERIES_NEEDS.md §1). infrasys stores a
#: ``SingleTimeSeriesScalingFactor`` as a ``SingleTimeSeries``, so it is read as one.
UNMAPPED_TYPES = (Deterministic,)

#: GDM variable → (schedule column, which is also the EnergyConsumer attribute a multiplier scales; the GDM unit of
#: actual values; the CIM unit they are passed in).
LOAD_VARIABLES = {
    "active_power": ("p", "kilowatt", "kW"),
    "reactive_power": ("q", "kilovar", "kVAr"),
}
CIM_UNITS = {column: cim_unit for column, _, cim_unit in LOAD_VARIABLES.values()}

#: How the schedule's points are read (TIMESERIES_NEEDS.md §5 import step 4): a sample holds until the next.
TIME_SERIES_KIND = "schedule"
INTERPOLATION_KIND = "previous"


def time_series_metadata(system, component) -> list:
    """Every series on ``component``: infrasys lists one type at a time (``SingleTimeSeries`` by default)."""
    return [metadata for series_type in MAPPED_TYPES + UNMAPPED_TYPES
            for metadata in system.list_time_series_metadata(component, time_series_type=series_type)]


def describe(component, metadata) -> str:
    return (f"{type(component).__name__} {component.name!r}: {metadata.name} ({metadata.type}, "
            f"{metadata.time_series_uuid}, {metadata.features})")


def add_time_series(network, system, naming: Naming) -> pa.Table | None:
    """The schedules of every load's series, built on ``network``; returns their points, or None when there are
    none. Raises on a series type out of scope, or on two series of one variable on a load (X5: their roles,
    OpenDSS yearly / daily / duty, cannot be told apart yet)."""
    dropped, tables = [], []
    for component in system.iter_all_components():
        if not system.has_time_series(component):
            continue
        metadata = time_series_metadata(system, component)
        for item in metadata:
            if item.type not in {t.__name__ for t in MAPPED_TYPES}:
                raise ValueError(f"{describe(component, item)}: {item.type} is not mapped (TIMESERIES_NEEDS.md §1)")
        if not isinstance(component, DistributionLoad):
            dropped += [describe(component, item) for item in metadata]
            continue
        dropped += [describe(component, item) for item in metadata if item.name not in LOAD_VARIABLES]
        mapped = [item for item in metadata if item.name in LOAD_VARIABLES]
        if mapped:
            tables += load_schedules(network, system, component, mapped, naming)
    warn_dropped(dropped, "no CIM schedule for them yet (TIMESERIES_NEEDS.md T2, T3)")
    return pa.concat_tables(tables) if tables else None


def warn_dropped(dropped: list[str], reason: str) -> None:
    """One WARNING listing every dropped series (I8)."""
    if dropped:
        log.warning("dropping %d time series (%s):\n  %s", len(dropped), reason, "\n  ".join(dropped))


def load_schedules(network, system, load, metadata: list, naming: Naming) -> list[pa.Table]:
    """The load's schedules: one with p and q when they share their times, else one each."""
    label = f"DistributionLoad {load.name!r}"
    by_variable = {}
    for item in metadata:
        if item.name in by_variable:
            raise ValueError(f"{label}: two {item.name} series ({by_variable[item.name].features}, {item.features}); "
                             "a schedule's role (OpenDSS yearly / daily / duty) has no CIM home yet (X5)")
        by_variable[item.name] = item
    consumer = network.find_by_mRID(object_mrid(load_family.PREFIX, load, "EnergyConsumer", naming))
    series = {}  # column → (times, samples, whether they are multipliers)
    for variable, item in by_variable.items():
        column, gdm_unit, _ = LOAD_VARIABLES[variable]
        data = system.get_time_series(load, variable, time_series_type=_series_type(item), **item.features)
        series[column] = (_times(data), *_values(data, item, gdm_unit, label))
    if set(series) == {"p"} and series["p"][2]:
        series["q"] = series["p"]  # a P multiplier with no Q series scales q as well (OpenDSS, §7)

    name = _profile_name(by_variable) or load.name
    times = {column: times for column, (times, _, _) in series.items()}
    columns = {column: _actual(samples, multiplier, consumer, column)
               for column, (_, samples, multiplier) in series.items()}
    if len(series) == 2 and times["p"] == times["q"]:
        return [_schedule(network, consumer, "pq", name, times["p"], columns)]
    return [_schedule(network, consumer, column, name, times[column], {column: columns[column]})
            for column in series]


def _series_type(metadata) -> type:
    return next(t for t in MAPPED_TYPES if t.__name__ == metadata.type)


def _times(data) -> list:
    """When each sample takes effect: start + i × resolution, or the listed timestamps (naive times are UTC)."""
    if isinstance(data, SingleTimeSeries):
        return [data.initial_timestamp + i * data.resolution for i in range(len(data.data))]
    return list(data.timestamps)


def _values(data, metadata, unit: str, label: str) -> tuple[list[float], bool]:
    """The samples, and whether they are multipliers: ``use_actual`` when ditto sets it, else whether the data have
    units. Actual values are given in ``unit``; multipliers are bare (ditto labels them kilowatt all the same)."""
    has_units = hasattr(data.data, "units")
    actual = metadata.features.get("use_actual", has_units)
    if not actual:
        values = data.data.magnitude if has_units else data.data
        return [float(v) for v in values], True
    if not has_units:
        raise ValueError(f"{label}: {metadata.name} is use_actual but has no units")
    return [float(v) for v in data.data.to(unit).magnitude], False


def _actual(samples: list[float], multiplier: bool, consumer, column: str) -> list[float]:
    """Actual values in the column's CIM unit: multipliers times the consumer's p or q (T1)."""
    if not multiplier:
        return samples
    base = getattr(consumer, column).to(CIM_UNITS[column])
    return [sample * base for sample in samples]


def _profile_name(by_variable: dict) -> str | None:
    """The OpenDSS loadshape name ditto keeps as ``profile_name``, from the P series first."""
    for variable in LOAD_VARIABLES:
        if variable in by_variable and by_variable[variable].features.get("profile_name"):
            return by_variable[variable].features["profile_name"]
    return None


def _schedule(network, consumer, suffix: str, name: str, times: list, columns: dict) -> pa.Table:
    """The schedule ``<consumer>_<suffix>`` and its points."""
    builder = EnergyConnectionScheduleBuilder(network, network.container)
    schedule = builder.create(mRID=f"{consumer.mRID}_{suffix}", name=name)
    builder.add_schedule(schedule, EnergyConnection=consumer.mRID, timeSeriesKind=TIME_SERIES_KIND,
                         interpolationKind=INTERPOLATION_KIND)
    return builder.time_points(schedule, times=times, p=columns.get("p"), q=columns.get("q"),
                               p_unit=CIM_UNITS["p"], q_unit=CIM_UNITS["q"])
