"""GLM ``player`` -> ``player.cimtbl``: one ``ConformLoadGroup`` and one ``ConformLoadSchedule`` per player (S8,
shape ``load_schedule``).

A load base ``<player>.value*K`` scales K by the player's value over time, as the GridAPPS-D run file declares it
(``class player { double value; }``, then ``object player { name ...; file ...; }``). So a player is a group of
conform loads with one regular schedule of multipliers (``value1Unit`` none): ``startTime`` the first row's time, its
zone an offset (S8-3), ``timeStep`` the one step between rows. The points go to the Parquet sidecar
(``player_points``), not the artifact. A player a load names but the deck does not define (the Java exports' run
file defines ``ieeezipload``) is a group with no schedule, with one warning, so its name survives (S8-5).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s8-load-players``.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.importer.cimtbl.catalog import label
from cimhub_gridlabd.importer.cimtbl.link import provenance
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.Player
GROUP_PREFIX = "lg_"
SCHEDULE_PREFIX = "ls_"
ANCHOR = "s8-load-players"

_GROUP, _SCHEDULE = "ConformLoadGroup", "ConformLoadSchedule"
_MUST_BE_UNSET = Field("structural", note="unset: a player read as <name>.value plays into its own value; set raises")

FIELDS = {
    "name": Field("copied", ((_GROUP, "name", None), (_SCHEDULE, "name", None)), "mRID = lg_ / ls_ + name"),
    "parent": _MUST_BE_UNSET,
    "property": _MUST_BE_UNSET,
    "file": Field("structural", note="its rows: startTime, timeStep and the points (the sidecar); unset raises"),
    "filetype": _MUST_BE_UNSET,
    "mode": _MUST_BE_UNSET,
    "loop": Field("structural", note="unset or 0; a repeated tape raises (a schedule has one pass)"),
    "all_events_delta": Field("untranscribed", note="deltamode: an engine option"),
    **{slot: Field("untranscribed", note="object header: a player has no place or service state")
       for slot in ("groupid", "latitude", "longitude", "in_svc", "out_svc", "rank", "flags")},
}

#: A zone abbreviation GridLAB-D writes in a player row -> its UTC offset in hours (S8-3); others raise.
ZONES = {"UTC": 0, "GMT": 0, "EST": -5, "EDT": -4, "CST": -6, "CDT": -5, "MST": -7, "MDT": -6, "PST": -8, "PDT": -7}
_ABSOLUTE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+([A-Z]{3,4})$")
_RELATIVE = re.compile(r"^\+(\d+)([smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

_log = logging.getLogger(__name__)


class Tape(NamedTuple):
    """One player's rows read as a regular schedule."""
    start: datetime  # the first row's time, zone-aware
    step: float | None  # seconds between rows; None for a one-row tape
    values: list[float]


def read_tape(player, rows: list[tuple[str, str]]) -> Tape:
    """The rows as one start, one step and the values: the first row absolute, each later one ``+N[smhd]`` after
    the row before it or absolute (``player.cpp:346-468``); steps that differ raise (S8-3)."""
    if not rows:
        raise ValueError(f"{label(player)}: its file {player.file} has no rows")
    times = [_absolute(player, rows[0][0])]
    for text, _ in rows[1:]:
        relative = _RELATIVE.match(text)
        if relative is None:
            times.append(_absolute(player, text))
        else:
            times.append(times[-1] + timedelta(seconds=int(relative.group(1)) * _UNIT_SECONDS[relative.group(2)]))
    steps = {(later - earlier).total_seconds() for earlier, later in zip(times, times[1:])}
    if len(steps) > 1 or any(step <= 0 for step in steps):
        raise ValueError(f"{label(player)}: steps of {sorted(steps)} s; a ConformLoadSchedule has one step (S8-3)")
    return Tape(times[0], steps.pop() if steps else None, [_value(player, text) for _, text in rows])


def _absolute(player, text: str) -> datetime:
    match = _ABSOLUTE.match(text)
    if match is None:
        raise ValueError(f"{label(player)}: row time {text!r}; an absolute 'YYYY-MM-DD HH:MM:SS ZONE' or +N[smhd] "
                         "after the first row is mapped (S8-3)")
    if match.group(2) not in ZONES:
        raise ValueError(f"{label(player)}: zone {match.group(2)}; mapped: {', '.join(ZONES)} (S8-3)")
    zone = timezone(timedelta(hours=ZONES[match.group(2)]))
    return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone)


def _value(player, text: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{label(player)}: row value {text!r} is not a number") from None


def _check(model: GlmModel, player) -> None:
    for slot in ("parent", "property", "filetype", "mode"):
        if getattr(player, slot) is not None:
            raise ValueError(f"{label(player)}: {slot} {getattr(player, slot)}; only a player read as "
                             f"{player.name}.value is mapped (S8-6)")
    if player.loop not in (None, 0):
        raise ValueError(f"{label(player)}: loop {player.loop}; a repeated tape is not mapped (S8-6)")
    if player.file is None:
        raise ValueError(f"{label(player)}: no file; its rows are the schedule")
    if "player" not in model.classes:
        raise ValueError(f"{label(player)}: read as {player.name}.value, but the deck has no "
                         "class player { double value; } (S8-6)")


def tapes(model: GlmModel) -> dict[str, Tape]:
    """Each player's tape, by name; a player off the run-file pattern raises."""
    found = {}
    for player in model.list_by_class(NATIVE_CLASS):
        _check(model, player)
        found[str(player.name)] = read_tape(player, model.tapes[str(player.name)])
    return found


def player_points(model: GlmModel) -> dict[str, list[float]]:
    """``{ConformLoadSchedule mRID: its values}``: the points the sidecar holds (``RegularTimePoint`` value1)."""
    return {mrid(SCHEDULE_PREFIX, name): tape.values for name, tape in tapes(model).items()}


def map_players(model: GlmModel, references: dict[str, list[str]]) -> Document:
    """Every player as a group and its schedule, and a group for each player the loads name (``references``: player
    name -> the loads naming it) that the deck does not define."""
    defined = tapes(model)
    undefined = sorted(set(references) - set(defined))
    if undefined:
        _log.warning("%d player(s) named by loads are not in the deck: %s; their groups have no schedule",
                     len(undefined), undefined)
    players = {str(player.name): player for player in model.list_by_class(NATIVE_CLASS)}
    groups = [Row([mrid(GROUP_PREFIX, name), name],
                  comment=None if name in defined else "not in the deck: no schedule (S8-5)")
              for name in sorted({*defined, *references})]
    schedules = [Row([mrid(SCHEDULE_PREFIX, name), name, tape.start.isoformat(),
                      None if tape.step is None else cell(tape.step), "none", mrid(GROUP_PREFIX, name)],
                     comment=untranscribed_values(FIELDS, players[name]) or None)
                 for name, tape in sorted(defined.items())]
    if not groups:
        return Document(name=NATIVE_CLASS.class_name, statements=[], profile=CIM_PROFILE)
    statements = [Table(_GROUP, [Column("mRID"), Column("name")], groups,
                        comment="one group per player: the loads whose base is <player>.value*K")]
    if schedules:
        statements.append(Table(_SCHEDULE, [Column("mRID"), Column("name"), Column("startTime"),
                                            Column("timeStep", "s"), Column("value1Unit"), Column(_GROUP)],
                                schedules, comment="value1: the player's value, a multiplier of each load's p and q; "
                                                   "the points are RegularTimePoints in the Parquet sidecar"))
    return Document(name=NATIVE_CLASS.class_name, statements=statements, profile=CIM_PROFILE,
                    comment=provenance(NATIVE_CLASS.class_name, f"{_GROUP} + {_SCHEDULE}", len(defined), ANCHOR))
