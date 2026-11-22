"""A device's own schedule: nc_schedule's ``EnergyConnectionSchedule`` on an EnergyConnection (a PV's, a battery's or
a machine's output over time, as a DSS yearly shape gives it).

The points are in the Parquet sidecar (``cimhub_core.time_points``, ``EnergyConnectionTimePoint``: an instant and p,
q in W and VAr, the load sign), not on the schedule. ``get_device_schedule`` reads them from the sidecar's rows split
by schedule (``time_points.rows_by_schedule``), so this module needs no pyarrow. The caller names the units and the
sign, as ``getters.der`` does.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimprofiles.units.units import ureg

from cimhub_core.getters import describe

#: a sample holds until the next one (unset reads as that, the sidecar's convention)
HELD = (None, cim.TimeSeriesInterpolationKind.previous)
#: sign -> the factor from CIM's load sign
SIGNS = {"load": 1.0, "generation": -1.0}


class DeviceSchedule(NamedTuple):
    schedule: cim.EnergyConnectionSchedule
    times: list[datetime]  # when each point takes effect (UTC)
    step: float | None  # the one interval between points, in seconds; None when uneven or a single point
    p: list[float] | None  # in the caller's unit and sign; None when the schedule carries no p
    q: list[float] | None


def get_device_schedule(equipment: cim.EnergyConnection, rows_by_schedule: dict, p_unit: str, q_unit: str, *,
                        sign: str) -> DeviceSchedule | None:
    """The equipment's one ``EnergyConnectionSchedule`` that has points, or None when it has none. Two with points
    raise, as do an interpolation other than ``previous`` (a sample holds until the next), a column null at some
    points only, and no p and no q."""
    if sign not in SIGNS:
        raise ValueError(f"sign must be one of {sorted(SIGNS)}, not {sign!r}")
    scheduled = [schedule for schedule in equipment.EnergyConnectionSchedule if schedule.uri() in rows_by_schedule]
    if not scheduled:
        return None
    if len(scheduled) > 1:
        raise ValueError(f"{describe(equipment)}: {len(scheduled)} EnergyConnectionSchedules with points; one is "
                         "mapped")
    schedule = scheduled[0]
    if schedule.interpolationKind not in HELD:
        raise ValueError(f"{describe(schedule)}: interpolationKind {schedule.interpolationKind.value}; a sample "
                         "holds until the next (previous)")
    rows = rows_by_schedule[schedule.uri()]
    times = rows.column("atTime").to_pylist()
    steps = {(later - earlier).total_seconds() for earlier, later in zip(times, times[1:])}
    p = _column(schedule, rows, "p", "W", p_unit, SIGNS[sign])
    q = _column(schedule, rows, "q", "VAr", q_unit, SIGNS[sign])
    if p is None and q is None:
        raise ValueError(f"{describe(schedule)}: its points carry no p and no q")
    return DeviceSchedule(schedule, times, steps.pop() if len(steps) == 1 else None, p, q)


def _column(schedule, rows, column: str, si_unit: str, unit: str, factor: float) -> list[float] | None:
    values = rows.column(column).to_pylist()
    missing = sum(value is None for value in values)
    if missing == len(values):
        return None
    if missing:
        raise ValueError(f"{describe(schedule)}: {column} is null at {missing} of {len(values)} points")
    return [factor * value + 0.0 for value in ureg.Quantity(values, si_unit).to(unit).magnitude.tolist()]
