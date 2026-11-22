"""X29: players on export. The player atom (S8) through the exporter's rules, then the IEEE 13 Java export with
GridAPPS-D's 1,440-point zipload player through CIM and back, solved in GridLAB-D 6.0 at two of its instants."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import cimtables
import pyarrow as pa
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from conftest import deck, defines
from gridlabd_engine import RUN_FILE, solve, worst_difference
from cimhub_gridlabd.exporter.cim_to_glm import GlmExporter
from cimhub_gridlabd.glm_reader import GlmReader, read_tape
from cimhub_gridlabd.glm_writer import GlmWriter
from cimhub_gridlabd.importer.glm_to_cimtbl import glm_to_cim

ATOM = Path(__file__).parent / "atoms" / "player" / "player.glm"
ZIPLOAD = Path(__file__).parent / "decks" / "IEEE" / "zipload_schedule.player"
EXPORT_LOG = "cimhub_gridlabd.exporter.load"


@pytest.fixture
def atom(scope, tmp_path):
    """(network, time points, the artifact directory) of the player atom."""
    time_points = {}
    network = glm_to_cim(GlmReader(ATOM).read_all(), name="atom", time_points=time_points,
                         artifact_dir=tmp_path / "atom")
    return network, time_points, tmp_path / "atom"


def test_the_loads_read_the_player(atom):
    network, time_points, _ = atom
    model = GlmExporter(time_points).to_model(network, name_source="name")
    assert model.expressions == {("ld_play", "base_power_A"): "zipload.value*19723.08",
                                 ("tl_play", "base_power_1"): "zipload.value*2941.18",
                                 ("tl_play", "base_power_2"): "zipload.value*2941.18"}
    assert model.by_name("ld_play").base_power_A is None  # the expression stands for it
    assert model.tapes["zipload"][0] == ("2009-07-21 04:00:00 GMT", "0.425364")  # 00:00 EDT
    assert model.clock["starttime"] == model.clock["stoptime"] == "'2009-07-21 04:00:00'"


def test_without_points_the_loads_are_static(atom, caplog):
    network, _, _ = atom
    with caplog.at_level(logging.WARNING, logger=EXPORT_LOG):
        model = GlmExporter().to_model(network, name_source="name")
    assert model.expressions == {} and model.tapes == {}
    assert model.by_name("ld_play").base_power_A == pytest.approx(19723.08)
    assert "1 load group(s) are written static" in caplog.text and "['zipload']" in caplog.text


def test_a_value2_other_than_value1_raises(atom):
    network, time_points, _ = atom
    table = time_points[REGULAR_TIME_POINT_CLASS]
    changed = table.set_column(3, "value2", pa.array([2.0] * table.num_rows, pa.float64()))
    with pytest.raises(ValueError, match="value2 differs from value1"):
        GlmExporter({REGULAR_TIME_POINT_CLASS: changed}).to_model(network)


def test_a_gap_in_the_points_raises(atom):
    network, time_points, _ = atom
    table = time_points[REGULAR_TIME_POINT_CLASS]
    with pytest.raises(ValueError, match="every step from 0 is read"):
        GlmExporter({REGULAR_TIME_POINT_CLASS: table.take([0, 2, 3])}).to_model(network)


def test_a_non_conform_load_is_static(atom, caplog):
    """The atom's artifacts with the group, schedule and loads made NonConform: GLM has no form for a schedule in
    power units, so the loads are written static and their group is named once."""
    _, time_points, directory = atom
    for artifact in directory.glob("*.cimtbl"):
        text = artifact.read_text().replace("ConformLoad", "NonConformLoad")
        artifact.write_text(text.replace("NonNonConformLoad", "NonConformLoad"))
    with cim_scope():
        network = cimtables.load_model(directory / "atom.cimtbl")
        assert len(network.graph[cim.NonConformLoad]) == 2
        with caplog.at_level(logging.WARNING, logger=EXPORT_LOG):
            model = GlmExporter(time_points).to_model(network, name_source="name")
    assert model.expressions == {} and model.tapes == {}
    assert "1 load group(s) are written static" in caplog.text


# -- IEEE 13 with GridAPPS-D's zipload player ----------------------------------------------------------------------

def run_deck(directory: Path) -> Path:
    """GridAPPS-D's run file for the Java IEEE 13 export, its player the vendored 1,440-point zipload schedule."""
    shutil.copy(deck("IEEE/IEEE13_cdpsm.glm"), directory / "IEEE13_cdpsm.glm")
    shutil.copy(ZIPLOAD, directory / "ieeezipload.player")
    text = RUN_FILE.format(vsource=defines("IEEE/IEEE13_cdpsm.glm")["VSOURCE"], body="IEEE13_cdpsm.glm")
    path = directory / "run.glm"
    path.write_text(text.replace("  file ieeezipload.player;\n", "  file ieeezipload.player;\n  loop 0;\n"))
    return path


@pytest.fixture
def ieee13(scope, tmp_path):
    """(network, time points) of the run file read with its player."""
    (tmp_path / "run").mkdir()
    time_points = {}
    network = glm_to_cim(GlmReader(run_deck(tmp_path / "run")).read_all(), name="IEEE13_cdpsm",
                         time_points=time_points)
    return network, time_points


def test_the_ieee13_loads_are_one_group_with_the_whole_schedule(ieee13):
    network, time_points = ieee13
    [schedule] = network.graph[cim.ConformLoadSchedule].values()
    assert schedule.startTime == "2009-07-21T00:00:00-04:00"
    loads = network.graph[cim.ConformLoad].values()
    assert len(loads) == 10 and {load.LoadGroup.name for load in loads} == {"ieeezipload"}
    rows = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS])[schedule.uri()]
    expected = [float(value) for _, value in read_tape(ZIPLOAD)]
    assert len(expected) == 1440 and rows.column("value1").to_pylist() == expected


@pytest.mark.parametrize("step", (0, 1))
def test_gridlabd_plays_the_exported_player(ieee13, tmp_path, step):
    """The exported deck at the schedule's first and second instants solves as the same deck with each base fixed
    at K times that point: GridLAB-D reads the GMT rows and the +60s step as the schedule means them."""
    network, time_points = ieee13
    model = GlmExporter(time_points).to_model(network, name_source="name")
    instant = f"'2009-07-21 04:0{step}:00'"
    model.clock.update(starttime=instant, stoptime=instant)
    played = tmp_path / "played" / "exported.glm"
    GlmWriter().write(model, played)
    value = float(model.tapes["ieeezipload"][step][1])
    for (name, slot), text in list(model.expressions.items()):
        setattr(model.by_name(name), slot, float(text.split("*")[1]) * value)
        del model.expressions[(name, slot)]
    fixed = tmp_path / "fixed" / "exported.glm"
    GlmWriter().write(model, fixed)
    worst, where = worst_difference(solve(fixed), solve(played))
    assert worst < 1e-9, f"{where} differs by {worst:.2e}"
