"""ConformLoadSchedules by Season and DayType -> a GLM ``schedule`` (``EXPORT_MAPPING.md#x30-load-schedules``; the
importer's S9 inverted).

A conform load group whose schedules each hold a Season or a DayType (a recurring day, ``get_load_schedule``'s
``days``), with their points in the caller's ``time_points``, is a schedule block named after the group, which the
base of each of the group's loads reads as ``<name>*K`` (``load.py``). Each day becomes cron rules (``minutes hours
days months weekdays value``): a run of equal values, split at the hours, on the season's months and the day type's
weekdays (nc_schedule's DayOfWeekKind words, as the importer names them; no DayType: every day; no Season: every
month). A zero value is no rule (GridLAB-D's value where none applies). The day must start at midnight and fill 24 h;
a season off whole months, a day type of another name, two days on one (month, weekday), and a value2 other than
value1 raise. A group one of whose days has no points is written static, with the load module's one warning.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.load_schedule import get_load_schedule
from cimhub_gridlabd.exporter.player import points
from cimhub_gridlabd.glm_writer import format_float
from cimhub_gridlabd.importer.cimtbl.schedule import DAY_NAMES, DAY_SETS, LAST_DAY, MINUTES_PER_DAY

CIM_CLASSES = ()  # a schedule is not conducting equipment
SLOTS: dict = {}  # a GLM schedule is a block of rules, not a schema class
#: a day schedule's startTime: midnight, as a time of day
MIDNIGHT = "00:00:00"
_ALL_MONTHS = tuple(range(1, 13))
_ALL_DAYS = frozenset(range(7))


def schedule_name(context, group) -> str:
    return context.names.name(group)


def season_months(schedule) -> tuple[int, ...]:
    """The months of the schedule's Season, in order from its start (a run past December wraps); no Season: all."""
    season = schedule.Season
    if season is None:
        return _ALL_MONTHS
    start, end = _month_day(schedule, season.startDate), _month_day(schedule, season.endDate)
    last_days = {LAST_DAY[end[0]], 28} if end[0] == 2 else {LAST_DAY[end[0]]}  # February: leap or not
    if start[1] != 1 or end[1] not in last_days:
        raise ValueError(f"{describe(schedule)}: season {season.startDate} to {season.endDate}; a GLM schedule's "
                         "months are whole")
    return tuple((start[0] - 1 + offset) % 12 + 1 for offset in range((end[0] - start[0]) % 12 + 1))


def _month_day(schedule, text: str | None) -> tuple[int, int]:
    """``--MM-DD`` as (month, day)."""
    if text is None or len(text) != 7 or not text.startswith("--") or text[4] != "-":
        raise ValueError(f"{describe(schedule)}: season date {text!r}; --MM-DD is read")
    return int(text[2:4]), int(text[5:7])


def day_type_weekdays(schedule) -> frozenset[int]:
    """The weekdays (0 = Sunday) of the schedule's DayType, by its name in DayOfWeekKind words; no DayType: all."""
    if schedule.DayType is None:
        return _ALL_DAYS
    name = str(schedule.DayType.name)
    named = {word: weekdays for weekdays, word in DAY_SETS.items()}
    if name in named:
        return named[name]
    words = name.split("_")
    if not set(words) <= set(DAY_NAMES):
        raise ValueError(f"{describe(schedule)}: day type {name!r}; all, weekday, weekend or day names joined by _ "
                         "are read")
    return frozenset(DAY_NAMES.index(word) for word in words)


def day_rules(schedule, values: list[float]) -> list[str]:
    """One day's cron rules: each run of equal values (0 written as no rule), split at the hours."""
    if schedule.startTime != MIDNIGHT:
        raise ValueError(f"{describe(schedule)}: startTime {schedule.startTime}; a GLM schedule's day starts at "
                         f"{MIDNIGHT}")
    minutes = get_qty(schedule, "timeStep", "min")
    if minutes is None or not float(minutes).is_integer() or minutes * len(values) != MINUTES_PER_DAY:
        raise ValueError(f"{describe(schedule)}: {len(values)} points of {minutes} min; a GLM schedule's day is "
                         f"{MINUTES_PER_DAY} whole minutes")
    step = int(minutes)
    dates = f"* {_list(season_months(schedule))} {_list(day_type_weekdays(schedule), every=_ALL_DAYS)}"
    rules, start = [], 0
    for index in range(1, len(values) + 1):
        if index < len(values) and values[index] == values[start]:
            continue
        if values[start] != 0:
            rules += [f"{clock} {dates} {format_float(values[start])}"
                      for clock in _clock_rules(start * step, index * step)]
        start = index
    return rules


def _clock_rules(begin: int, end: int) -> list[str]:
    """``minutes hours`` fields covering the minutes ``[begin, end)`` of a day."""
    first, last = begin // 60, (end - 1) // 60
    if first == last:
        return [f"{_range(begin % 60, (end - 1) % 60, 59)} {first}"]
    rules = []
    if begin % 60:
        rules.append(f"{begin % 60}-59 {first}")
        first += 1
    tail = f"0-{(end - 1) % 60} {last}" if end % 60 else None
    if tail:
        last -= 1
    if first <= last:
        rules.append(f"* {_range(first, last, 23)}")
    return rules + ([tail] if tail else [])


def _range(low: int, high: int, top: int) -> str:
    if (low, high) == (0, top):
        return "*"
    return str(low) if low == high else f"{low}-{high}"


def _list(values, *, every=_ALL_MONTHS) -> str:
    """A month or weekday set as a cron field: ``*`` for all, else ranges in the given order (``12,1-2``)."""
    ordered = list(values) if isinstance(values, tuple) else sorted(values)
    if set(ordered) == set(every):
        return "*"
    runs: list[list[int]] = []
    for value in ordered:
        if runs and value == runs[-1][-1] + 1:
            runs[-1].append(value)
        else:
            runs.append([value])
    return ",".join(str(run[0]) if len(run) == 1 else f"{run[0]}-{run[-1]}" for run in runs)


def group_rules(context, found) -> list[str] | None:
    """A group's days as one schedule's rules, or None when one of them has no points; two days on one (month,
    weekday) raise."""
    covered: dict[tuple[int, int], str] = {}
    rules = []
    for schedule in found.days:
        values = points(context, schedule)
        if values is None:
            return None
        for month in season_months(schedule):
            for weekday in day_type_weekdays(schedule):
                other = covered.setdefault((month, weekday), schedule.mRID)
                if other != schedule.mRID:
                    raise ValueError(f"{describe(schedule)} and {other!r} both cover {DAY_NAMES[weekday]} of month "
                                     f"{month}; a GLM schedule gives one value at a time")
        rules += day_rules(schedule, values)
    return rules


def export(context) -> list:
    """Each conform group of days with points as ``model.schedules[name]``; no records (a schedule is a block)."""
    for group in context.objects(cim.ConformLoadGroup):
        if not group.EnergyConsumers:
            continue
        found = get_load_schedule(group.EnergyConsumers[0])
        if not found.days:
            continue
        rules = group_rules(context, found)
        if rules is not None:
            context.model.schedules[schedule_name(context, group)] = rules
    return []
