"""S9: GLM schedules: the atom's goldens, its groups, seasons, day types and points in the sidecar with GridLAB-D as
the oracle for each value (a week of winter and a week of summer), the rule helpers, and the fail-fast rules."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import gridlabd
import pytest

from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.load_schedule import get_load_schedule
from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import schedule
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim

ATOM = Path(__file__).parent / "atoms" / "schedule"
MODEL = "atom"
#: a week of winter and a week of summer, every 30 minutes
WEEKS = ("2020-01-01 00:00:00", "2020-07-01 00:00:00")
ENGINE_DECK = """clock {{ timezone UTC0; starttime '{start}'; stoptime '{stop}'; }}
#set relax_naming_rules=1
module powerflow {{ solver_method NR; }}
module tape;
{schedules}
object substation {{ name src; bustype SWING; phases ABCN; nominal_voltage 7200; }}
{loads}
"""


def read(path: Path):
    return GlmReader(path).read_all()


@pytest.mark.parametrize("artifact", ("schedule", "load", "triplex_load"))
def test_atom_goldens(artifact):
    parts = {document.name: document for document in GlmImporter(MODEL).to_cimtbl(read(ATOM / "schedule.glm")).parts}
    assert_matches_golden(parts[artifact], ATOM / f"schedule.{artifact}.cimtbl")


def test_a_schedule_no_load_reads_is_counted_not_mapped():
    documents = GlmImporter(MODEL).to_cimtbl(read(ATOM / "schedule.glm"))
    assert "not mapped: schedule 1" in documents.master.comment  # waterdemand


def test_atom_binds_by_season_and_day_type(scope):
    time_points = {}
    network = glm_to_cim(read(ATOM / "schedule.glm"), name=MODEL, time_points=time_points)
    loads = {load.name: load for load in network.graph[cim.ConformLoad].values()}
    heat = get_load_schedule(loads["tl_heat"])
    assert heat.schedule is None and heat.group.name == "heat"
    assert [(day.Season.startDate, day.Season.endDate, day.DayType.name) for day in heat.days] == [
        ("--03-01", "--11-30", "weekday"), ("--03-01", "--11-30", "weekend"), ("--12-01", "--02-29", "weekday"),
        ("--12-01", "--02-29", "weekend")]
    [zip1] = get_load_schedule(loads["ld_zip"]).days
    assert (zip1.mRID, zip1.startTime, zip1.Season.name, zip1.DayType.name) == ("ls_zip1", "00:00:00", "01-12", "all")
    rows = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS])
    values = rows[zip1.uri()].column("value1").to_pylist()
    assert len(values) == 48 and values[:2] == [1.686360, 1.616535] and set(values[12:]) == {0.0}  # 30 min steps
    summer_weekend = rows[heat.days[1].uri()].column("value1").to_pylist()
    assert summer_weekend == [0.0]  # no rule: GridLAB-D's 0, one point for the day


# -- GridLAB-D as the oracle -----------------------------------------------------------------------------------------

def engine_values(schedules: dict[str, list[str]], directory: Path, start: str) -> dict[str, dict[datetime, float]]:
    """GridLAB-D's value of each schedule every 30 minutes for a week from ``start``: a load's base_power_A at
    K = 1000 VA, read by a recorder."""
    blocks = "\n".join(f"schedule {name} {{\n" + "".join(f"  {line.strip()};\n" for statement in statements
                                                        for line in statement.splitlines() if line.strip()) + "}"
                       for name, statements in schedules.items())
    loads = "\n".join(f"object load {{ name l_{name}; parent src; phases ABCN; nominal_voltage 7200; "
                      f"base_power_A {name}*1000; power_fraction_A 1.0; power_pf_A 1.0; }}\n"
                      f"object recorder {{ parent l_{name}; property base_power_A; interval 1800; file {name}.csv; }}"
                      for name in schedules)
    stop = start.replace("-01 ", "-08 ")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "deck.glm").write_text(ENGINE_DECK.format(start=start, stop=stop, schedules=blocks, loads=loads))
    engine = gridlabd.GridLabD()
    engine.set_working_directory(str(directory))
    assert engine.load_glm(["deck.glm"]) == 0 and engine.run() == 0
    engine.finalize()  # the worker writes the recorders' files out as it ends
    found = {}
    for name in schedules:
        with open(directory / f"{name}.csv", newline="") as file:
            rows = [row for row in csv.reader(file) if row and not row[0].startswith("#")]
        found[name] = {datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S UTC"): float(row[1]) / 1000 for row in rows}
    return found


def cim_value(days, rows: dict, instant: datetime) -> float:
    """The group's value at ``instant`` from its CIM days alone: the one whose Season months and DayType weekdays
    hold the instant, at its step (independent of the mapper's helpers)."""
    weekday = (instant.weekday() + 1) % 7  # Python's Monday 0 -> GridLAB-D's Sunday 0
    names = {"all": set(range(7)), "weekday": {1, 2, 3, 4, 5}, "weekend": {0, 6}}
    matches = []
    for day in days:
        first, last = int(day.Season.startDate[2:4]), int(day.Season.endDate[2:4])
        months = set(range(first, last + 1)) if first <= last else set(range(first, 13)) | set(range(1, last + 1))
        if instant.month in months and weekday in names[day.DayType.name]:
            matches.append(day)
    [day] = matches
    values = rows[day.uri()].column("value1").to_pylist()
    step = 1440 // len(values)
    return values[(instant.hour * 60 + instant.minute) // step]


@pytest.mark.parametrize("start", WEEKS)
def test_gridlabd_gives_each_value_the_days_give(scope, tmp_path, start):
    model = read(ATOM / "schedule.glm")
    time_points = {}
    network = glm_to_cim(model, name=MODEL, time_points=time_points)
    rows = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS])
    groups = {group.name: get_load_schedule(group.EnergyConsumers[0]).days
              for group in network.graph[cim.ConformLoadGroup].values()}
    engine = engine_values({name: model.schedules[name] for name in groups}, tmp_path, start)
    for name, days in groups.items():
        assert len(engine[name]) == 7 * 48
        for instant, value in engine[name].items():
            # the recorder writes 6 significant digits (1616.54 for 1616.535)
            assert cim_value(days, rows, instant) == pytest.approx(value, rel=1e-5), f"{name} at {instant}"


# -- the rule helpers ------------------------------------------------------------------------------------------------

def test_a_rule_reads_each_field_form():
    rule = schedule.parse_rule("s", "0-29 6,8-9 * 12,1-2 0,6")
    assert rule == (frozenset(range(30)), frozenset({6, 8, 9}), frozenset({12, 1, 2}), frozenset({0, 6}), 1.0)
    assert schedule.parse_rule("s", "* * * * * 0.25").value == 0.25


def test_the_coarsest_step_keeps_every_change():
    day = tuple([1.0] * 420 + [2.0] * 1020)
    assert schedule.coarsest_step(day) == 60  # a change at 07:00
    assert schedule.coarsest_step(tuple([0.0] * 1440)) == 1440


def test_december_wraps_to_january():
    weeks = {month: ("winter",) if month in (12, 1, 2) else ("summer",) for month in range(1, 13)}
    assert schedule.seasons(weeks) == [(12, 1, 2), (3, 4, 5, 6, 7, 8, 9, 10, 11)]


def test_day_type_names():
    assert [schedule.day_type_name(frozenset(days)) for days in (range(7), range(1, 6), (0, 6), (3,), (1, 3))] == [
        "all", "weekday", "weekend", "wednesday", "monday_wednesday"]


# -- fail fast -------------------------------------------------------------------------------------------------------

LINE = '#include "' + str(Path(__file__).parent / "atoms" / "line" / "line.glm") + '"\n'
LOAD = ("object load { name ld; parent n5; phases AN; nominal_voltage 2401.78; base_power_A s*1000; "
        "power_fraction_A 1.0; power_pf_A 1.0; }\n")


@pytest.mark.parametrize(("block", "match"), (
    ("schedule s { * * 1-15 * * 1.0; }", "names days of the month 1-15"),
    ("schedule s { * 0-12 * * * 1.0; * 12-23 * * * 2.0; }", "two rules cover sunday of month 1 at 12:00"),
    ("schedule s { * 0-24 * * * 1.0; }", "0-24 is outside 0-23"),
    ("schedule s { * * * * * high; }", "the value 'high' is not a number"),
    ("schedule s { * * * *; }", "'minutes hours days months weekdays \\[value\\]' is mapped"),
    ("schedule s { weekday { * * * * 1-5 1.0; } }", "a nested block"),
    ("", "schedules \\['s'\\] are read by loads"),
), ids=("day of month", "overlap", "out of range", "not a number", "four fields", "nested", "undefined"))
def test_a_schedule_off_the_mapping_raises(tmp_path, block, match):
    path = tmp_path / "deck.glm"
    path.write_text(LINE + block + "\n" + LOAD)
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


def test_a_schedule_and_a_player_of_one_name_raise(tmp_path):
    path = tmp_path / "deck.glm"
    (tmp_path / "s.player").write_text("2020-01-01 00:00:00 UTC,1\n")
    path.write_text(LINE + "module tape;\nclass player { double value; }\nobject player { name s; file s.player; }\n"
                    "schedule s { * * * * * 1.0; }\n" + LOAD)
    with pytest.raises(ValueError, match="both a schedule and a player"):
        GlmImporter(MODEL).to_cimtbl(read(path))
