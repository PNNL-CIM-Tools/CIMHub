"""ConformLoadSchedule -> GLM ``player`` (``EXPORT_MAPPING.md#x29-load-players``; the importer's S8 inverted).

A conform load group's one regular schedule, with its points in the caller's ``time_points`` (the ``RegularTimePoint``
table), is a player named after the group, its file ``<name>.player`` beside the deck, read as ``<name>.value`` by
the base of each of the group's loads (``load.py``) through the run file's ``class player { double value; }``. The
rows: the first at ``startTime`` in GMT (GridLAB-D reads GMT under any clock zone, ``timestamp.cpp:595``), each later
one ``+<step>s``. ``value2`` other than ``value1`` raises: a GLM base scales p and q together. A group with no
schedule, a schedule with no points, and a NonConformLoad's schedule are not players: their loads are written static,
with one warning (``load.py``). A schedule of a Season or DayType is a day, not a player: ``schedule.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters import describe
from cimhub_core.getters.load_schedule import get_schedule_points
from cimhub_gridlabd.glm_reader import PLAYER_CLASS
from cimhub_gridlabd.glm_writer import format_float
from cimhub_gridlabd.schema import gridlabd as schema

CIM_CLASSES = ()  # a schedule is not conducting equipment
NATIVE_CLASS = schema.Player
#: GMT: GridLAB-D's one zone valid under every clock timezone
ZONE = "GMT"

SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "the group's name (X1)"),
    "file": Slot("written", "<name>.player beside the deck: the schedule's startTime, timeStep and points"),
}, Slot("unset", "not in CIM; GridLAB-D's default (a player read as <name>.value has no parent or property)"))}


def points(context, schedule) -> list[float] | None:
    """The schedule's value1 per point from the context's time points (``get_schedule_points``: its rules raise),
    or None when it has none; a value2 other than value1 raises."""
    found = get_schedule_points(schedule, context.points)
    if found is None:
        return None
    if found.value2 is not None and found.value2 != found.value1:
        raise ValueError(f"{describe(schedule)}: value2 differs from value1; a GLM base scales p and q together")
    return found.value1


def player_name(context, schedule) -> str:
    return context.names.name(schedule.ConformLoadGroup)


def start(schedule) -> datetime:
    """``startTime`` as an aware datetime in UTC; one with no offset raises (its zone is unknown)."""
    if schedule.startTime is None:
        raise ValueError(f"{describe(schedule)}: no startTime")
    instant = datetime.fromisoformat(schedule.startTime)
    if instant.tzinfo is None:
        raise ValueError(f"{describe(schedule)}: startTime {schedule.startTime} has no UTC offset")
    return instant.astimezone(timezone.utc)


def is_day(schedule) -> bool:
    """A schedule of a Season or DayType: a recurring day (a GLM schedule), not a time series."""
    return schedule.Season is not None or schedule.DayType is not None


def export(context) -> list[schema.Player]:
    players = []
    for schedule in context.objects(cim.ConformLoadSchedule):
        if is_day(schedule):
            continue
        values = points(context, schedule)
        if values is None:
            continue
        name = player_name(context, schedule)
        context.model.tapes[name] = _rows(schedule, values)
        players.append(NATIVE_CLASS(name=name, file=f"{name}.player"))
    if players:
        context.model.classes["player"] = dict(PLAYER_CLASS)
        context.model.modules.setdefault("tape", {})
    return players


def _rows(schedule, values: list[float]) -> list[tuple[str, str]]:
    first = f"{start(schedule):%Y-%m-%d %H:%M:%S} {ZONE}"
    if len(values) == 1:
        return [(first, format_float(values[0]))]
    seconds = get_qty(schedule, "timeStep", "s")
    if seconds is None or not seconds.is_integer() or seconds <= 0:
        raise ValueError(f"{describe(schedule)}: timeStep {seconds} s; a player steps in whole seconds")
    return [(first, format_float(values[0])), *((f"+{int(seconds)}s", format_float(value)) for value in values[1:])]
