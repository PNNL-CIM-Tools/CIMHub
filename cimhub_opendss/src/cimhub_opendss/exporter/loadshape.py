"""ConformLoadSchedule -> OpenDSS ``LoadShape`` (``EXPORT_MAPPING.md#s8-load-shapes``; the importer's S8 inverted).

A conform load group's one regular schedule, with its points in the caller's ``time_points`` (the
``RegularTimePoint`` table), is a LoadShape named after the group, which each of the group's loads names as
``yearly`` (``load.py``): ``mult`` its value1 and ``qmult`` its value2 (unset: Q follows mult, the engine's rule),
``sinterval`` its timeStep. DSS has no date, so ``startTime`` is not written: the first point is sample 1, in force
one interval into the run. A group with no schedule, a schedule with no points, and a NonConformLoad's schedule
(UseActual: CIMTBL_MAPPING.md S8) are not shapes: their loads are written static, with one warning (``load.py``).

A PV's, battery's or machine's own ``EnergyConnectionSchedule`` (S9) is a LoadShape too, its multipliers made by
that device's exporter (``pvsystem.py``, ``storage.py``, ``generator.py``) and claimed here (``ShapeRegistry``):
owners whose name, interval and multipliers agree share one LoadShape, as the deck's devices shared it; another with
that name but other points takes a suffix ``_2``, ``_3``.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters import describe
from cimhub_core.getters.device_schedule import DeviceSchedule, get_device_schedule
from cimhub_core.getters.load_schedule import get_schedule_points
from cimhub_core.names import export_name
from cimhub_opendss.dss_writer import dss_safe_name
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


class ShapeRegistry:
    """The LoadShapes claimed so far: by content (export name, interval, mult, qmult) and by owner uri."""

    def __init__(self):
        self.by_content: dict[tuple, str] = {}
        self.by_owner: dict[str, str] = {}

    def claim(self, names, owner, seconds: float, mult: list[float],
              qmult: list[float] | None = None) -> tuple[str, schema.Loadshape | None]:
        """The name of the LoadShape that gives ``owner``'s points, and its record when it is new."""
        base = dss_safe_name(export_name(owner, names.source)).lower()
        content = (base, seconds, tuple(mult), tuple(qmult or ()))
        if content in self.by_content:
            name, record = self.by_content[content], None
        else:
            used = {existing.lower() for existing in self.by_content.values()}
            suffix = ""
            n = 2
            while dss_safe_name(export_name(owner, names.source) + suffix).lower() in used:
                suffix = f"_{n}"
                n += 1
            name = names.name(owner, NAMESPACE, suffix=suffix)
            self.by_content[content] = name
            record = NATIVE_CLASS(name=name, npts=len(mult), sinterval=seconds, mult=mult, qmult=qmult)
        self.by_owner[owner.uri()] = name
        return name, record


def shape_name(context, schedule) -> str:
    """The LoadShape a group's loads name (claimed by ``export``)."""
    return context.shapes.by_owner[schedule.ConformLoadGroup.uri()]


def export(context) -> list[schema.Loadshape]:
    """One LoadShape per non-recurring ConformLoadSchedule with points (shared when two agree, ``ShapeRegistry``)."""
    shapes = []
    for schedule in context.objects(cim.ConformLoadSchedule):
        if schedule.Season is not None or schedule.DayType is not None:
            continue
        points = get_schedule_points(schedule, context.points)
        if points is None:
            continue
        if schedule.ConformLoadGroup is None:
            raise ValueError(f"{describe(schedule)}: ConformLoadGroup is unset")
        checks = [(schedule.value1Unit, schedule.value1Multiplier)]
        if points.value2 is not None:
            checks.append((schedule.value2Unit, schedule.value2Multiplier))
        for unit, multiplier in checks:
            if unit not in MULTIPLIER_UNITS:
                raise ValueError(f"{describe(schedule)}: values in {unit.value}; a conform schedule holds multipliers")
            if multiplier not in (None, cim.UnitMultiplier.none):
                raise ValueError(f"{describe(schedule)}: multiplier {multiplier.value}; a conform schedule holds unscaled multipliers")
        seconds = get_qty(schedule, "timeStep", "s")
        if seconds is None or seconds <= 0:
            raise ValueError(f"{describe(schedule)}: timeStep {seconds} s; a LoadShape needs a positive interval")
        _, record = context.shapes.claim(context.names, schedule.ConformLoadGroup, seconds, points.value1,
                                         points.value2)
        shapes += [record] if record is not None else []
    return shapes


def device_schedule(context, equipment, devices: int) -> DeviceSchedule | None:
    """The equipment's own schedule with points (kW and kVAr, the generation sign), or None (S9). Uneven points raise
    (a LoadShape has one interval), and so does a schedule on equipment written as ``devices`` != 1 DSS objects (one
    shape would scale them all by one multiplier, which CIM does not say)."""
    found = get_device_schedule(equipment, context.device_points, "kW", "kVAr", sign="generation")
    if found is None:
        return None
    if found.step is None or found.step <= 0:
        raise ValueError(f"{describe(found.schedule)}: {len(found.times)} points not evenly spaced; a LoadShape has "
                         "one interval")
    if devices != 1:
        raise ValueError(f"{describe(found.schedule)}: on {describe(equipment)}, written as {devices} DSS objects; "
                         "a schedule is mapped on one")
    return found


def device_yearly(context, found: DeviceSchedule, mult: list[float]) -> tuple[str, list[schema.Loadshape]]:
    """The name a device's ``yearly`` gives, and the LoadShape record to write when it is new."""
    name, record = context.shapes.claim(context.names, found.schedule, found.step, mult)
    return name, [record] if record is not None else []
