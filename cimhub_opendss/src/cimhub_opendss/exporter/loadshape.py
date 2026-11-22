"""ConformLoadSchedule -> OpenDSS ``LoadShape`` (``EXPORT_MAPPING.md#s8-load-shapes``; the importer's S8 inverted).

A conform load group's one regular schedule, with its points in the caller's ``time_points`` (the
``RegularTimePoint`` table), is a LoadShape named after the group, which each of the group's loads names as
``yearly`` (``load.py``): ``mult`` its value1 and ``qmult`` its value2 (unset: Q follows mult, the engine's rule),
``sinterval`` its timeStep. DSS has no date, so ``startTime`` is not written: the first point is sample 1, in force
one interval into the run. A group with no schedule, a schedule with no points, and a NonConformLoad's schedule
(UseActual: CIMTBL_MAPPING.md S8) are not shapes: their loads are written static, with one warning (``load.py``).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters import describe
from cimhub_core.getters.load_schedule import get_schedule_points
from cimhub_opendss.dss_writer import format_float
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = ()  # a schedule is not conducting equipment
NATIVE_CLASS = schema.Loadshape
NAMESPACE = "Loadshape"
#: the units a conform schedule's values may carry: multipliers
MULTIPLIER_UNITS = (None, cim.UnitSymbol.none)

SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "the group's name (Names)"),
    "npts": Slot("written", "the number of points"),
    "sinterval": Slot("written", "timeStep (s)"),
    "mult": Slot("written", "value1 of each point, in sequence order"),
    "qmult": Slot("written", "value2 of each point; unset when value2 is (Q follows mult)"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "not in CIM; the engine's default"))}


def shape_name(context, schedule) -> str:
    return context.names.name(schedule.ConformLoadGroup, NAMESPACE)


def export(context) -> list[schema.Loadshape]:
    """One LoadShape per ConformLoadSchedule with points."""
    shapes = []
    for schedule in context.objects(cim.ConformLoadSchedule):
        points = get_schedule_points(schedule, context.points)
        if points is None:
            continue
        for unit in (schedule.value1Unit, schedule.value2Unit if points.value2 is not None else None):
            if unit not in MULTIPLIER_UNITS:
                raise ValueError(f"{describe(schedule)}: values in {unit.value}; a conform schedule holds multipliers")
        seconds = get_qty(schedule, "timeStep", "s")
        if seconds is None or seconds <= 0:
            raise ValueError(f"{describe(schedule)}: timeStep {seconds} s; a LoadShape needs a positive interval")
        shapes.append(NATIVE_CLASS(name=shape_name(context, schedule), npts=len(points.value1),
                                   sinterval=format_float(seconds), mult=points.value1, qmult=points.value2))
    return shapes
