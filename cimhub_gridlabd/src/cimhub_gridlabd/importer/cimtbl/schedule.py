"""GLM ``schedule`` -> ``schedule.cimtbl``: a ``ConformLoadGroup`` per schedule a load's base reads
(``<schedule>*K``), and one ``ConformLoadSchedule`` per ``Season`` and ``DayType`` (S9, CGMES's
SeasonDayTypeSchedule; shape ``load_schedule``).

A schedule's rules (``minutes hours days months weekdays [value]``, GridLAB-D's cron form; engine-checked: ranges
inclusive, months from 1, weekdays from 0 = Sunday, an omitted value 1, a time no rule covers 0, overlapping rules a
load error) give each (month, weekday) a day of multipliers (``day_profiles``). The months whose seven days agree, in
runs of consecutive months (December wraps to January), are a ``Season``: ``startDate`` ``--MM-01``, ``endDate`` the
run's last day. Within a season the weekdays whose days agree are a ``DayType``, named in nc_schedule's
``DayOfWeekKind`` words (``all``, ``weekday``, ``weekend``, ``sunday`` ... ``saturday``; another set joins the day
names with ``_``). Each (season, day type) is a ``ConformLoadSchedule`` of that day: ``startTime`` ``00:00:00`` (a
time of day, as CIM allows for a season and day-type schedule), ``timeStep`` the coarsest step in minutes the day
keeps, its multipliers in the Parquet sidecar (``schedule_points``). A day of the month other than ``*`` raises (no
Season or DayType holds it), as do a nested block, a rule off the cron form, and a load reading a schedule the deck
does not define. A schedule no load reads (a house's) is not mapped: the master counts it.

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s9-load-schedules``.
"""

from __future__ import annotations

from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, cell, mrid
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.importer.cimtbl.player import GROUP_PREFIX, SCHEDULE_PREFIX
from cimhub_gridlabd.schema import gridlabd as schema

SEASON_PREFIX = "season_"
DAY_TYPE_PREFIX = "dt_"
ANCHOR = "s9-load-schedules"
MINUTES_PER_DAY = 1440
#: GridLAB-D's weekdays 0..6, in nc_schedule's DayOfWeekKind words
DAY_NAMES = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")
#: the weekday sets DayOfWeekKind names as one word
DAY_SETS = {frozenset(range(7)): "all", frozenset(range(1, 6)): "weekday", frozenset({0, 6}): "weekend"}
#: each month's last day (February's 29th, so a season covers a leap year)
LAST_DAY = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
#: a rule's fields in order, and each one's range
FIELD_RANGES = (("minutes", 0, 59), ("hours", 0, 23), ("days", 1, 31), ("months", 1, 12), ("weekdays", 0, 6))

_PROVENANCE = """GridLAB-D schedule -> ConformLoadGroup + one ConformLoadSchedule per Season and DayType (S9): the
schedules the loads' bases read. A day of multipliers of each load's p and q; the points are in the Parquet sidecar,
not here. startTime: midnight, a time of day.
Source table: schedule (blocks: {count}; {mapped} read by a load's base)
Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#{anchor}"""


class Rule(NamedTuple):
    minutes: frozenset[int]
    hours: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]
    value: float


class DaySchedule(NamedTuple):
    """One (season, day type) of a schedule: its months in order, its weekdays, the step and its values."""
    months: tuple[int, ...]
    weekdays: frozenset[int]
    step: int  # minutes
    values: list[float]


def parse_rule(name: str, text: str) -> Rule:
    """One rule, ``minutes hours days months weekdays [value]``; a day of the month other than ``*`` raises."""
    parts = text.split()
    if len(parts) not in (5, 6):
        raise ValueError(f"schedule {name}: rule {text!r}; 'minutes hours days months weekdays [value]' is mapped")
    fields = [_field(name, text, part, low, high) for part, (_, low, high) in zip(parts, FIELD_RANGES)]
    if fields[2] != frozenset(range(1, 32)):
        raise ValueError(f"schedule {name}: rule {text!r} names days of the month {parts[2]}; no Season or DayType "
                         "holds them (S9)")
    try:
        value = float(parts[5]) if len(parts) == 6 else 1.0  # GridLAB-D's value when the rule gives none
    except ValueError:
        raise ValueError(f"schedule {name}: rule {text!r}: the value {parts[5]!r} is not a number") from None
    return Rule(fields[0], fields[1], fields[3], fields[4], value)


def _field(name: str, text: str, part: str, low: int, high: int) -> frozenset[int]:
    """``*``, a number, ``a-b``, or a comma list of them, inclusive."""
    if part == "*":
        return frozenset(range(low, high + 1))
    values = set()
    for item in part.split(","):
        first, _, last = item.partition("-")
        if not first.isdigit() or not (last.isdigit() or not last):
            raise ValueError(f"schedule {name}: rule {text!r}: {part!r} is not *, a number, a range or a list of them")
        start, end = int(first), int(last or first)
        if not low <= start <= end <= high:
            raise ValueError(f"schedule {name}: rule {text!r}: {item} is outside {low}-{high}")
        values.update(range(start, end + 1))
    return frozenset(values)


def day_profiles(name: str, statements: list[str]) -> dict[tuple[int, int], tuple[float, ...]]:
    """``{(month, weekday): the value of each minute of the day}``; overlapping rules and nested blocks raise."""
    nested = [statement for statement in statements if statement.endswith("{") or statement == "}"]
    if nested:
        raise ValueError(f"schedule {name}: a nested block ({nested[0]!r}) is not mapped (S9)")
    # a rule ends at ';' or at the end of its line (IEEE13_houses writes no ';'); the reader keeps the text as written
    rules = [parse_rule(name, line.strip()) for statement in statements for line in statement.splitlines()
             if line.strip()]
    profiles = {}
    for month in range(1, 13):
        for weekday in range(7):
            values: list[float | None] = [None] * MINUTES_PER_DAY
            for rule in rules:
                if month not in rule.months or weekday not in rule.weekdays:
                    continue
                for minute in (hour * 60 + minute for hour in rule.hours for minute in rule.minutes):
                    if values[minute] is not None:
                        raise ValueError(f"schedule {name}: two rules cover {DAY_NAMES[weekday]} of month {month} at "
                                         f"{minute // 60:02d}:{minute % 60:02d}; GridLAB-D rejects the overlap")
                    values[minute] = rule.value
            profiles[(month, weekday)] = tuple(0.0 if value is None else value for value in values)
    return profiles


def coarsest_step(profile: tuple[float, ...]) -> int:
    """The largest step (minutes, a divisor of a day) on which the day's value only changes at step boundaries."""
    for step in sorted((step for step in range(1, MINUTES_PER_DAY + 1) if MINUTES_PER_DAY % step == 0), reverse=True):
        if all(profile[minute] == profile[minute - minute % step] for minute in range(MINUTES_PER_DAY)):
            return step
    raise AssertionError("a step of 1 minute always fits")


def seasons(weeks: dict[int, tuple]) -> list[tuple[int, ...]]:
    """The runs of consecutive months whose weeks agree (``weeks``: month -> its seven days); December's run joins
    January's when they agree."""
    runs: list[list[int]] = []
    for month in range(1, 13):
        if runs and weeks[runs[-1][-1]] == weeks[month]:
            runs[-1].append(month)
        else:
            runs.append([month])
    if len(runs) > 1 and weeks[12] == weeks[1]:
        runs[0] = runs.pop() + runs[0]
    return [tuple(run) for run in runs]


def day_schedules(name: str, statements: list[str]) -> list[DaySchedule]:
    """The schedule as (season, day type) days, by season then by first weekday."""
    profiles = day_profiles(name, statements)
    weeks = {month: tuple(profiles[(month, weekday)] for weekday in range(7)) for month in range(1, 13)}
    found = []
    for months in seasons(weeks):
        days: dict[tuple[float, ...], set[int]] = {}
        for weekday, profile in enumerate(weeks[months[0]]):
            days.setdefault(profile, set()).add(weekday)
        for profile, weekdays in days.items():
            step = coarsest_step(profile)
            found.append(DaySchedule(months, frozenset(weekdays), step, list(profile[::step])))
    return found


def day_type_name(weekdays: frozenset[int]) -> str:
    """The DayType name of a weekday set (DayOfWeekKind words; another set joins the day names with ``_``)."""
    return DAY_SETS.get(weekdays) or "_".join(DAY_NAMES[day] for day in sorted(weekdays))


def season_id(months: tuple[int, ...]) -> str:
    return f"{months[0]:02d}_{months[-1]:02d}"


def schedule_id(name: str, day: DaySchedule, count: int) -> str:
    """``ls_<name>`` for a schedule of one day, else ``ls_<name>_<first month>_<last month>_<day type>``."""
    base = mrid(SCHEDULE_PREFIX, name)
    return base if count == 1 else f"{base}_{season_id(day.months)}_{day_type_name(day.weekdays)}"


def _read(model: GlmModel, references: dict[str, list[str]]) -> dict[str, list[DaySchedule]]:
    """The days of each schedule a load reads, by name; one the deck does not define, or a player of the same name
    (their groups would share ``lg_<name>``), raises."""
    undefined = sorted(set(references) - set(model.schedules))
    if undefined:
        raise ValueError(f"schedules {undefined} are read by loads {[references[name] for name in undefined]} but "
                         "not defined in the deck")
    players = sorted(set(references) & {str(player.name) for player in model.list_by_class(schema.Player)})
    if players:
        raise ValueError(f"{players} are both a schedule and a player; their load groups would share lg_<name>")
    return {name: day_schedules(name, model.schedules[name]) for name in sorted(references)}


def schedule_points(model: GlmModel, references: dict[str, list[str]]) -> dict[str, list[float]]:
    """``{ConformLoadSchedule mRID: its values}``: the points the sidecar holds (``RegularTimePoint`` value1)."""
    return {schedule_id(name, day, len(days)): day.values for name, days in _read(model, references).items()
            for day in days}


def map_schedules(model: GlmModel, references: dict[str, list[str]]) -> Document:
    """The schedules the loads read (``references``: schedule name -> its loads) as one ``schedule`` document: the
    seasons, the day types, the groups, then their schedules."""
    read = _read(model, references)
    if not read:
        return Document(name="schedule", statements=[], profile=CIM_PROFILE)
    seasons_used, day_types, groups, rows = {}, {}, [], []
    for name, days in read.items():
        group = mrid(GROUP_PREFIX, name)
        groups.append(Row([group, name]))
        for day in days:
            season = SEASON_PREFIX + season_id(day.months)
            seasons_used[season] = Row([season, season_id(day.months).replace("_", "-"), f"--{day.months[0]:02d}-01",
                                        f"--{day.months[-1]:02d}-{LAST_DAY[day.months[-1]]:02d}"])
            day_type = DAY_TYPE_PREFIX + day_type_name(day.weekdays)
            day_types[day_type] = Row([day_type, day_type_name(day.weekdays)])
            rows.append(Row([schedule_id(name, day, len(days)), name, "00:00:00", cell(day.step), "none", season,
                             day_type, group]))
    statements = [
        Table("Season", [Column("mRID"), Column("name"), Column("startDate"), Column("endDate")],
              [seasons_used[key] for key in sorted(seasons_used)],
              comment="the months whose days agree, in a run (December wraps to January)"),
        Table("DayType", [Column("mRID"), Column("name")], [day_types[key] for key in sorted(day_types)],
              comment="the weekdays whose days agree in a season, in DayOfWeekKind words"),
        Table("ConformLoadGroup", [Column("mRID"), Column("name")], groups),
        Table("ConformLoadSchedule", [Column("mRID"), Column("name"), Column("startTime"), Column("timeStep", "min"),
                                      Column("value1Unit"), Column("Season"), Column("DayType"),
                                      Column("ConformLoadGroup")], rows,
              comment="value1: the schedule's value, a multiplier of each load's p and q, at each step from "
                      "midnight (S9)"),
    ]
    return Document(name="schedule", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(model.schedules), mapped=len(read), anchor=ANCHOR))
