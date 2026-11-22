"""S8: players: classification, the atom, the schedule and its points in the sidecar, the tape rules, fail fast."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.load_schedule import get_load_schedule
from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from cimhub_gridlabd.glm_reader import GlmParseError, GlmReader
from cimhub_gridlabd.importer.cimtbl import player
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "player"
MODEL = "atom"
#: the atom's four rows (zipload.player), the last written with GridLAB-D's trailing ';'
VALUES = [0.425364, 0.421530, 0.418488, 0.399880]


def read(path: Path):
    return GlmReader(path).read_all()


def test_every_slot_is_classified():
    check_fields(player.FIELDS, schema.Player)


def test_the_reader_keeps_the_rows_as_written():
    model = read(ATOM / "player.glm")
    assert model.classes == {"player": {"value": "double"}}
    assert model.tapes["zipload"] == [("2009-07-21 00:00:00 EDT", "0.425364"), ("+1m", "0.421530"),
                                      ("+1m", "0.418488"), ("+1m", "0.399880")]


@pytest.mark.parametrize("artifact", ("player", "load", "triplex_load"))
def test_atom_goldens(artifact):
    parts = {document.name: document for document in GlmImporter(MODEL).to_cimtbl(read(ATOM / "player.glm")).parts}
    assert_matches_golden(parts[artifact], ATOM / f"player.{artifact}.cimtbl")


def test_atom_binds_with_its_points(scope):
    time_points = {}
    network = glm_to_cim(read(ATOM / "player.glm"), name=MODEL, time_points=time_points)
    [schedule] = network.graph[cim.ConformLoadSchedule].values()
    loads = sorted(network.graph[cim.ConformLoad].values(), key=lambda load: load.mRID)
    assert [load.mRID for load in loads] == ["ld_ld_play", "ld_tl_play"]
    found = get_load_schedule(loads[0])
    assert (found.group.name, found.schedule.mRID) == ("zipload", "ls_zipload")
    # 00:00 EDT is 04:00 UTC; +1m is one 60 s step
    assert datetime.fromisoformat(found.start) == datetime(2009, 7, 21, 4, tzinfo=timezone.utc)
    assert found.step == pytest.approx(60.0)
    assert schedule.value1Unit == cim.UnitSymbol.none
    rows = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS])[schedule.uri()]
    assert rows.column("sequenceNumber").to_pylist() == [0, 1, 2, 3]
    assert rows.column("value1").to_pylist() == VALUES
    # the load's p is K's split, as for an unscheduled base (S4a-2): 19723.08 VA at pf 0.861934
    assert float(loads[0].p.to("W")) == pytest.approx(19723.08 * 0.861934)


def test_without_time_points_the_points_drop_with_a_warning(scope, caplog):
    with caplog.at_level(logging.WARNING, logger="cimhub_gridlabd.importer.glm_to_cimtbl"):
        network = glm_to_cim(read(ATOM / "player.glm"), name=MODEL)
    assert len(network.graph[cim.ConformLoadSchedule]) == 1
    assert "the points of 1 player(s) are dropped" in caplog.text


# -- the tape rules (S8-3) -------------------------------------------------------------------------------------------

def tape(*rows: tuple[str, str]):
    return player.read_tape(schema.Player(name="p", file="p.player"), list(rows))


@pytest.mark.parametrize(("relative", "seconds"), (("+30s", 30), ("+15m", 900), ("+1h", 3600), ("+1d", 86400)))
def test_a_relative_row_is_its_step(relative, seconds):
    assert tape(("2009-07-21 00:00:00 UTC", "1"), (relative, "2")).step == seconds


def test_absolute_rows_give_their_step():
    read_back = tape(("2009-07-21 00:00:00 PST", "1"), ("2009-07-21 01:00:00 PST", "2"))
    assert (read_back.start, read_back.step, read_back.values) == (
        datetime(2009, 7, 21, tzinfo=timezone(timedelta(hours=-8))), 3600, [1.0, 2.0])


def test_one_row_has_no_step():
    assert tape(("2009-07-21 00:00:00 GMT", "0.5")).step is None


@pytest.mark.parametrize(("rows", "match"), (
    ((("2009-07-21 00:00:00 UTC", "1"), ("+1m", "2"), ("+2m", "3")), r"steps of \[60.0, 120.0\] s"),
    ((("2009-07-21 00:00:00 AEST", "1"),), "zone AEST"),
    ((("2009-07-21 00:00:00", "1"),), "row time '2009-07-21 00:00:00'"),
    ((("+1m", "1"),), "row time '\\+1m'"),
    ((("2009-07-21 00:00:00 UTC", "high"),), "row value 'high' is not a number"),
    ((), "has no rows"),
), ids=("steps differ", "unknown zone", "no zone", "relative first row", "not a number", "empty"))
def test_a_tape_off_the_rules_raises(rows, match):
    with pytest.raises(ValueError, match=match):
        tape(*rows)


# -- fail fast -------------------------------------------------------------------------------------------------------

HEADER = 'module tape;\nclass player { double value; }\n'


def deck(tmp_path, text: str, *, header: str = HEADER, rows: str = "2009-07-21 00:00:00 UTC,1\n") -> Path:
    (tmp_path / "p.player").write_text(rows)
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM.parent / "line" / "line.glm"}"\n{header}{text}')
    return path


def raises(tmp_path, text: str, match: str, **kwargs):
    model = read(deck(tmp_path, text, **kwargs))
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(model)


@pytest.mark.parametrize(("slots", "match"), (
    ("parent n5; property base_power_A;", "parent n5; only a player read as p.value is mapped"),
    ("property value;", "property value; only a player read as p.value"),
    ("loop 2;", "loop 2; a repeated tape is not mapped"),
), ids=("parent", "property", "loop"))
def test_a_player_off_the_run_file_pattern_raises(tmp_path, slots, match):
    raises(tmp_path, f"object player {{ name p; file p.player; {slots} }}", match)


def test_a_player_with_no_class_block_raises(tmp_path):
    raises(tmp_path, "object player { name p; file p.player; }", "no class player", header="module tape;\n")


def test_two_players_on_one_load_raise(tmp_path):
    raises(tmp_path, "object player { name p; file p.player; }\nobject player { name q; file p.player; }\n"
                     "object load { name x; parent n2; phases ABN; base_power_A p.value*10; base_power_B q.value*10; }",
           r"its bases name \['p', 'q'\]; a ConformLoad follows one player")


def test_a_phase_off_the_player_raises(tmp_path):
    raises(tmp_path, "object player { name p; file p.player; }\n"
                     "object load { name x; parent n2; phases ABN; base_power_A p.value*10; base_power_B 10; }",
           r"its bases name \['None', 'p'\]")


def test_another_class_block_raises(tmp_path):
    with pytest.raises(GlmParseError, match="only class player { double value; } is read"):
        read(deck(tmp_path, "", header="class player { double value; double other; }\n"))


def test_a_row_with_no_comma_raises(tmp_path):
    with pytest.raises(GlmParseError, match="player row '0.5' is not time,value"):
        read(deck(tmp_path, "object player { name p; file p.player; }", rows="# comment\n\n0.5\n"))


def test_a_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="player file not found"):
        read(deck(tmp_path, "object player { name p; file none.player; }"))
