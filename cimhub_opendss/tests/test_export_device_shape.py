"""S9 on export: the device-shape atom through import and export, its deck checked against its golden and, in the
engine, against the original deck in yearly mode: every device's p and q at every 30-minute step over 8 hours (both
intervals, the PVs off and cut to fit, the battery capped, the wrap-around), so the exported shapes, %Cutin/%Cutout,
pf and DispMode give the original's output."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pyarrow as pa
import pyarrow.compute as pc
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.time_points import TIME_POINT_CLASS
from cimhub_opendss import DssReader
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.importer.dss_to_cimtbl import DssImporter
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck
from export_atoms import assert_matches_dss_golden

ATOM = Path(__file__).parent / "atoms" / "loadshape" / "devices.dss"
STEPS, STEP_SECONDS = 16, 1800
DEVICE_CLASSES = ("pvsystem", "storage", "generator", "load")


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture
def atom(tmp_path):
    """(network, time points) of the atom."""
    time_points = {}
    network = DssImporter("atom", time_points=time_points).to_cim(DssReader(ATOM).read_all(),
                                                                  artifact_dir=tmp_path / "atom")
    return network, time_points


def yearly_powers(path: Path) -> list[dict[str, tuple[float, float]]]:
    """Each device's (kW, kvar) at each step of a yearly run, the engine's own clock."""
    compile_deck(path)
    dss.Text.Command(f"Set mode=yearly stepsize={STEP_SECONDS}s number=1 controlmode=off tolerance=1e-10 "
                     "maxiterations=500")
    steps = []
    for _ in range(STEPS):
        dss.Solution.Solve()
        powers = {}
        for name in dss.Circuit.AllElementNames():
            if name.split(".")[0].lower() in DEVICE_CLASSES:
                dss.Circuit.SetActiveElement(name)
                values = dss.CktElement.Powers()
                powers[name.lower()] = (sum(values[0::2]), sum(values[1::2]))
        steps.append(powers)
    return steps


def test_the_deck_matches_its_golden(atom, tmp_path):
    network, time_points = atom
    written = tmp_path / "out" / "devices.dss"
    cim_to_dss(network, written, time_points=time_points, name_source="name")
    assert_matches_dss_golden(written, ATOM.parent / "export" / "devices.dss")


def test_the_engine_runs_the_export_as_the_original(atom, tmp_path):
    network, time_points = atom
    written = tmp_path / "out" / "devices.dss"
    cim_to_dss(network, written, time_points=time_points, name_source="name")
    original, exported = yearly_powers(ATOM), yearly_powers(written)
    assert set(original[0]) == set(exported[0])
    assert len({round(step["pvsystem.p2"][0], 3) for step in original}) == 5  # off, cut to fit, and between
    for number, (before, after) in enumerate(zip(original, exported), start=1):
        for name, power in before.items():
            assert after[name] == pytest.approx(power, rel=1e-6, abs=1e-6), f"step {number}: {name}"


def test_devices_sharing_a_shape_share_it_when_their_multipliers_agree(atom):
    network, time_points = atom
    model = DssExporter(time_points).to_model(network, name_source="name")
    shapes = {str(shape.name): shape for shape in model.list_by_class(schema.Loadshape)}
    assert sorted(shapes) == ["cycle", "run", "sun", "sun_2"]  # p2 is cut to fit at the peak: its own multipliers
    assert {str(pv.name): pv.yearly for pv in model.list_by_class(schema.Pvsystem)} == {"p1": "sun", "p2": "sun_2",
                                                                                       "p3": None}
    assert shapes["cycle"].mult == [0.5, -0.5, 0.0, 0.8]  # the battery's 1 is capped at its 80 kVA


def test_without_points_the_devices_are_static(atom):
    network, _ = atom
    model = DssExporter().to_model(network, name_source="name")
    assert not model.list_by_class(schema.Loadshape)
    for cls in (schema.Pvsystem, schema.Storage, schema.Generator):
        assert {record.yearly for record in model.list_by_class(cls)} == {None}


def schedule_uri(network, device: str) -> str:
    [schedule] = [s for s in network.graph[cim.EnergyConnectionSchedule].values() if s.EnergyConnection.name == device]
    return schedule.uri()


@pytest.mark.parametrize(("device", "column", "values", "match"), (
    ("g1", "q", [-1e4, -1e4, -1e4, -1e4], "point 1 has q 10.0 kVAr, not kvar 96.86"),
    ("p1", "q", [0, -1e4, -1e4, 0, 0, 0], "neither the PV's 29.58"),
    ("p2", "p", [0, -1e4, -4e4, -5e4, 0, 0], "points \\[4\\] are above the 48.9898 kW"),
    ("s1", "q", [1e3, 0, 0, 0], "q other than 0"),
    ("s1", "p", [-9e4, 0, 0, 0], "points \\[1\\] are above the battery's 80 kVA"),
))
def test_a_schedule_off_the_mapping_raises(atom, device, column, values, match):
    network, time_points = atom
    table = time_points[TIME_POINT_CLASS]
    uri = schedule_uri(network, device)
    mask = pc.equal(table.column(0).cast(pa.string()), uri).to_pylist()
    changed = table.column(column).to_pylist()
    for row in [number for number, hit in enumerate(mask) if hit]:
        changed[row] = values.pop(0)
    points = {TIME_POINT_CLASS: table.set_column(table.schema.get_field_index(column), column,
                                                 pa.array(changed, pa.float64()))}
    with pytest.raises(ValueError, match=match):
        DssExporter(points).to_model(network, name_source="name")


def test_uneven_points_raise(atom):
    network, time_points = atom
    table = time_points[TIME_POINT_CLASS]
    uri = schedule_uri(network, "g1")
    times = table.column("atTime").to_pylist()
    keys = table.column(0).cast(pa.string()).to_pylist()
    last = max(number for number, key in enumerate(keys) if key == uri)
    times[last] = times[last].replace(minute=30)
    points = {TIME_POINT_CLASS: table.set_column(1, "atTime", pa.array(times, table.schema.field("atTime").type))}
    with pytest.raises(ValueError, match="4 points not evenly spaced"):
        DssExporter(points).to_model(network, name_source="name")
