"""S8 on export: the LoadShape atom through import and export, its deck checked against its golden and, in the
engine, against the original deck in yearly mode: every load's power at every 5-minute step over 6 hours (each
shape's interval, the normalized shape, the wrap-around), so the exported sinterval and multipliers are the
original's."""
from __future__ import annotations

import logging
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import cimtables
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssReader
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.importer.dss_to_cimtbl import DssImporter
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck
from export_atoms import assert_matches_dss_golden

ATOM = Path(__file__).parent / "atoms" / "loadshape" / "loadshapes.dss"
EXPORT_LOG = "cimhub_opendss.exporter.load"
STEPS, STEP_SECONDS = 72, 300


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture
def atom(tmp_path):
    """(network, time points, the artifact directory) of the atom."""
    time_points = {}
    importer = DssImporter("atom", time_points=time_points)
    network = importer.to_cim(DssReader(ATOM).read_all(), artifact_dir=tmp_path / "atom")
    return network, time_points, tmp_path / "atom"


def yearly_powers(path: Path) -> list[dict[str, tuple[float, float]]]:
    """Each load's (kW, kvar) at each step of a yearly run, the engine's own clock."""
    compile_deck(path)
    dss.Text.Command(f"Set mode=yearly stepsize={STEP_SECONDS}s number=1 controlmode=off")
    steps = []
    for _ in range(STEPS):
        dss.Solution.Solve()
        powers = {}
        for name in dss.Loads.AllNames():
            dss.Circuit.SetActiveElement(f"Load.{name}")
            values = dss.CktElement.Powers()
            powers[name] = (sum(values[0::2]), sum(values[1::2]))
        steps.append(powers)
    return steps


def test_the_deck_matches_its_golden(atom, tmp_path):
    network, time_points, _ = atom
    written = tmp_path / "out" / "loadshapes.dss"
    cim_to_dss(network, written, time_points=time_points, name_source="name")
    assert_matches_dss_golden(written, ATOM.parent / "export" / "loadshapes.dss")


def test_the_engine_runs_the_export_as_the_original(atom, tmp_path):
    network, time_points, _ = atom
    written = tmp_path / "out" / "loadshapes.dss"
    cim_to_dss(network, written, time_points=time_points, name_source="name")
    original, exported = yearly_powers(ATOM), yearly_powers(written)
    assert {name for name, (kw, _) in original[0].items()} == set(exported[0])
    assert {round(step["r1"][0]) for step in original} == {50, 75, 100, 80}  # res scales r1 over the run
    for number, (before, after) in enumerate(zip(original, exported)):
        for name, (kw, kvar) in before.items():
            assert after[name] == pytest.approx((kw, kvar), rel=1e-9), f"step {number + 1}: load {name}"


def test_without_points_the_loads_are_static(atom, caplog):
    network, _, _ = atom
    with caplog.at_level(logging.WARNING, logger=EXPORT_LOG):
        model = DssExporter().to_model(network, name_source="name")
    assert not model.list_by_class(schema.Loadshape)
    assert {load.yearly for load in model.list_by_class(schema.Load)} == {None}
    assert "4 load group(s) are written static" in caplog.text and "['com', 'flat', 'ind', 'res']" in caplog.text


def test_a_non_conform_load_is_static(atom, caplog):
    """The atom's artifacts with groups, schedules and loads made NonConform: a UseActual shape's snapshot depends on
    the command order (CIMTBL_MAPPING.md S8), so the loads are written static and their groups named once."""
    _, time_points, directory = atom
    for artifact in directory.glob("*.cimtbl"):
        text = artifact.read_text().replace("ConformLoad", "NonConformLoad")
        artifact.write_text(text.replace("NonNonConformLoad", "NonConformLoad"))
    network = cimtables.load_model(directory / "atom.cimtbl")
    assert len(network.graph[cim.NonConformLoad]) == 5
    with caplog.at_level(logging.WARNING, logger=EXPORT_LOG):
        model = DssExporter(time_points).to_model(network, name_source="name")
    assert {load.yearly for load in model.list_by_class(schema.Load)} == {None}
    assert "4 load group(s) are written static" in caplog.text


def test_a_schedule_in_power_units_raises(atom):
    _, time_points, directory = atom
    shapes = directory / "loadshape.cimtbl"
    shapes.write_text(shapes.read_text().replace("none, none, lg_res", "W, none, lg_res"))
    network = cimtables.load_model(directory / "atom.cimtbl")
    with pytest.raises(ValueError, match="values in W; a conform schedule holds multipliers"):
        DssExporter(time_points).to_model(network)
