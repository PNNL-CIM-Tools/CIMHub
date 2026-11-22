"""X30: GLM schedules on export. The schedule atom (S9) through the exporter: its rules, GridLAB-D giving the exported
schedules the original's value every 30 minutes over a winter and a summer week, the deck read back to the same
points, and the rule helpers and fail-fast rules."""
from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pytest

from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from cimhub_gridlabd.exporter import schedule
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter, cim_to_glm
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim
from test_cimtbl_schedule import WEEKS, engine_values

ATOM = Path(__file__).parent / "atoms" / "schedule" / "schedule.glm"
EXPORT_LOG = "cimhub_gridlabd.exporter.load"


@pytest.fixture
def atom(scope):
    """(network, time points) of the schedule atom."""
    time_points = {}
    return glm_to_cim(GlmReader(ATOM).read_all(), name="atom", time_points=time_points), time_points


def test_the_loads_read_the_schedules(atom):
    network, time_points = atom
    model = GlmExporter(time_points).to_model(network, name_source="name")
    assert model.expressions == {("ld_zip", "base_power_A"): "zip1*19723.08",
                                 ("tl_heat", "base_power_1"): "heat*2941.18",
                                 ("tl_heat", "base_power_2"): "heat*2941.18"}
    assert model.schedules["heat"] == ["* 6-21 * 3-11 1-5 0.6", "* 0-6 * 12,1-2 1-5 1.2", "* 7-23 * 12,1-2 1-5 0.9",
                                       "* * * 12,1-2 0,6 1.1"]
    assert model.schedules["zip1"][:2] == ["0-29 0 * * * 1.68636", "30-59 0 * * * 1.616535"]
    assert not model.tapes  # days are not players


@pytest.mark.parametrize("start", WEEKS)
def test_gridlabd_gives_the_exported_schedules_the_original_values(atom, tmp_path, start):
    network, time_points = atom
    exported = GlmExporter(time_points).to_model(network, name_source="name").schedules
    original = GlmReader(ATOM).read_all().schedules
    assert engine_values(exported, tmp_path / "exported", start) == engine_values(
        {name: original[name] for name in exported}, tmp_path / "original", start)


def test_the_written_schedules_read_back_to_the_same_points(atom, tmp_path):
    """The written deck's schedule blocks, on the atom's line and loads, import to the atom's points."""
    network, time_points = atom
    cim_to_glm(network, tmp_path / "out" / "atom.glm", time_points=time_points, name_source="name")
    written = GlmReader(tmp_path / "out" / "atom.glm").read_all().schedules
    blocks = "".join(f"schedule {name} {{\n" + "".join(f"  {rule};\n" for rule in rules) + "}\n"
                     for name, rules in written.items())
    loads = ATOM.read_text()[ATOM.read_text().index("// IEEE13"):]
    deck = tmp_path / "back.glm"
    deck.write_text(f'#include "{ATOM.parent.parent / "line" / "line.glm"}"\n' + blocks + loads)
    again = {}
    glm_to_cim(GlmReader(deck).read_all(), name="atom", time_points=again)
    assert values_by_schedule(again) == values_by_schedule(time_points)


def values_by_schedule(time_points: dict) -> dict:
    """Each schedule's values by its uri (deterministic from its mRID)."""
    table = time_points[REGULAR_TIME_POINT_CLASS]
    return {key: rows.column("value1").to_pylist() for key, rows in rows_by_schedule(table).items()}


def test_without_points_the_loads_are_static(atom, caplog):
    network, _ = atom
    with caplog.at_level(logging.WARNING, logger=EXPORT_LOG):
        model = GlmExporter().to_model(network, name_source="name")
    assert model.expressions == {} and model.schedules == {}
    assert "2 load group(s) are written static" in caplog.text and "['heat', 'zip1']" in caplog.text


# -- the rule helpers ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize(("begin", "end", "rules"), (
    (0, 1440, ["* *"]),
    (0, 30, ["0-29 0"]),
    (30, 60, ["30-59 0"]),
    (420, 1440, ["* 7-23"]),
    (90, 200, ["30-59 1", "* 2", "0-19 3"]),
    (75, 135, ["15-59 1", "0-14 2"]),
))
def test_a_run_of_minutes_splits_at_the_hours(begin, end, rules):
    assert schedule._clock_rules(begin, end) == rules


def test_a_season_and_a_day_type_read_back():
    day = SimpleNamespace(mRID="d", Season=SimpleNamespace(startDate="--12-01", endDate="--02-28"),
                          DayType=SimpleNamespace(name="monday_wednesday"))
    assert schedule.season_months(day) == (12, 1, 2)  # a non-leap February ends a season too
    assert schedule.day_type_weekdays(day) == frozenset({1, 3})
    day.Season.endDate = "--02-15"
    with pytest.raises(ValueError, match="months are whole"):
        schedule.season_months(day)


def test_two_days_on_one_weekday_raise(atom):
    network, time_points = atom
    for day_type in network.graph[network.cim.DayType].values():
        if day_type.name == "weekend":
            day_type.name = "all"  # the winter weekend now covers the weekdays too
    with pytest.raises(ValueError, match="both cover"):
        GlmExporter(time_points).to_model(network, name_source="name")


def test_a_day_not_from_midnight_raises(atom):
    network, time_points = atom
    for day in network.graph[network.cim.ConformLoadSchedule].values():
        day.startTime = "06:00:00"
    with pytest.raises(ValueError, match="a GLM schedule's day starts at 00:00:00"):
        GlmExporter(time_points).to_model(network, name_source="name")


def test_a_day_of_the_wrong_length_raises(atom):
    network, time_points = atom
    table = time_points[REGULAR_TIME_POINT_CLASS]
    [zip1] = [day for day in network.graph[network.cim.ConformLoadSchedule].values() if day.mRID == "ls_zip1"]
    keys, numbers = table.column(0).cast(pa.string()).to_pylist(), table.column("sequenceNumber").to_pylist()
    rows = [row for row, (key, number) in enumerate(zip(keys, numbers)) if (key, number) != (zip1.uri(), 47)]
    with pytest.raises(ValueError, match="47 points of 30.0 min"):
        GlmExporter({REGULAR_TIME_POINT_CLASS: table.take(rows)}).to_model(network, name_source="name")
