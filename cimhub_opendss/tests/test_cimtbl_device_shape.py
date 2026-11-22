"""Atom tests: a PVSystem's, Storage's or Generator's yearly LoadShape -> its own EnergyConnectionSchedule (S9): the
goldens, the bound schedules, their points in the sidecar with the engine as the oracle for each sample's p and q
(the timing, the PV's irradiance x mult, the battery's follow mode, the generator's kW x mult), and the fail-fast
rules."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_core.time_points import TIME_POINT_CLASS, rows_by_schedule
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl import generator, pvsystem, storage

from conftest import compile_deck

ATOM = Path(__file__).parent / "atoms" / "loadshape" / "devices.dss"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n")
SHAPE = "New Loadshape.s npts=3 interval=1 mult=(0.2 1 0.5)\n"
#: each scheduled device of the atom -> its DSS element and its shape's interval (s)
DEVICES = {"p1": ("PVSystem.p1", 1800), "p2": ("PVSystem.p2", 1800), "s1": ("Storage.s1", 3600),
           "g1": ("Generator.g1", 3600)}
MAPPERS = {"pvsystem": pvsystem.map_pvsystem, "storage": storage.map_storage, "generator": generator.map_generator}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def native():
    return DssReader(ATOM).read_all()


@pytest.fixture
def bound(native):
    """(network, time points) of the atom."""
    time_points = {}
    return dss_to_cim(native, name="atom", time_points=time_points), time_points


@pytest.mark.parametrize("artifact", MAPPERS)
def test_matches_golden(native, artifact):
    site = dss_to_cimtbl.site(native)
    document = MAPPERS[artifact](native, site.buses, site.feeder)
    assert_matches_golden(document, ATOM.with_name(f"devices.{artifact}.cimtbl"))


def test_the_shapes_are_mapped_not_counted(native):
    documents = dss_to_cimtbl.DssImporter("atom").to_cimtbl(native)
    assert "Loadshape" not in documents.master.comment.split("not mapped:")[-1]
    assert not [part for part in documents.parts if part.name == "loadshape"]  # no Load names them: no groups


def test_each_device_has_its_own_schedule(bound):
    network, _ = bound
    schedules = {schedule.EnergyConnection.name: schedule
                 for schedule in network.graph[cim.EnergyConnectionSchedule].values()}
    assert sorted(schedules) == sorted(DEVICES)  # p3 has no shape
    assert {name: schedule.name for name, schedule in schedules.items()} == {"p1": "sun", "p2": "sun", "s1": "cycle",
                                                                            "g1": "run"}
    assert schedules["p1"].mRID == "pv_p1_yearly"
    assert isinstance(schedules["g1"].EnergyConnection, cim.SynchronousMachine)
    assert schedules["s1"].timeSeriesKind is cim.BaseTimeSeriesKind.schedule
    assert schedules["s1"].interpolationKind is cim.TimeSeriesInterpolationKind.previous
    # the snapshot is the deck's, not the shape's: the follow-mode battery idles
    assert schedules["s1"].EnergyConnection.PowerElectronicsUnit[0].batteryState is cim.BatteryStateKind.waiting


def engine_samples(element: str, seconds: int, steps: int) -> list[tuple[float, float]]:
    """The element's (kW, kvar) at each step of a yearly run at the shape's own interval (the load sign)."""
    compile_deck(ATOM)
    dss.Text.Command(f"Set mode=yearly stepsize={seconds}s number=1 controlmode=off tolerance=1e-10 maxiterations=500")
    samples = []
    for _ in range(steps):
        dss.Solution.Solve()
        dss.Circuit.SetActiveElement(element)
        values = dss.CktElement.Powers()
        samples.append((sum(values[0::2]), sum(values[1::2])))
    return samples


@pytest.mark.parametrize("device", DEVICES)
def test_the_engine_gives_each_point(bound, device):
    """Sample k at the epoch + k intervals, its p and q (kW, kvar) the engine's at that step."""
    network, time_points = bound
    [schedule] = [s for s in network.graph[cim.EnergyConnectionSchedule].values() if s.EnergyConnection.name == device]
    rows = rows_by_schedule(time_points[TIME_POINT_CLASS])[schedule.uri()]
    element, seconds = DEVICES[device]
    times = rows.column("atTime").to_pylist()
    assert [(time - datetime(2020, 1, 1, tzinfo=timezone.utc)).total_seconds() for time in times] == [
        seconds * number for number in range(1, len(times) + 1)]
    for number, ((kw, kvar), p, q) in enumerate(zip(engine_samples(element, seconds, len(times)),
                                                    rows.column("p").to_pylist(), rows.column("q").to_pylist()),
                                                start=1):
        assert p / 1000 == pytest.approx(kw, rel=1e-6, abs=1e-6), f"{device} sample {number}: p"
        if q is not None:  # the battery's schedule carries p only (its q is 0)
            assert q / 1000 == pytest.approx(kvar, rel=1e-6, abs=1e-6), f"{device} sample {number}: q"
        else:
            assert kvar == pytest.approx(0, abs=1e-2)


def test_the_points_drop_with_a_warning_without_time_points(native, caplog):
    with caplog.at_level(logging.WARNING, logger="cimhub_opendss.importer.dss_to_cimtbl"):
        network = dss_to_cim(native, name="atom")
    assert len(network.graph[cim.EnergyConnectionSchedule]) == 4
    assert "0 LoadShape(s) and 4 device schedule(s) are dropped" in caplog.text


def test_an_inverter_that_is_off_keeps_a_set_kvar():
    """Off (below %Cutout), a PV gives no kW but its kvar, unless VarFollowInverter (engine-checked)."""
    off = dict(pmpp=100, irradiance=0.05, pct_pmpp=100, kva=100, pct_cutout=20, pf=1)
    assert pvsystem.pv_power("pv", **off, kvar=20) == (0.0, 20.0, True)
    assert pvsystem.pv_power("pv", **off, kvar=20, var_follow=True) == (0.0, 0.0, True)
    assert pvsystem.pv_power("pv", **off, kvar=None) == (0.0, 0.0, True)


def test_follow_power():
    rated = dict(kw_rated=100, kva=80, idling_kw=1)
    assert [storage.follow_power(value, **rated) for value in (0.5, -0.5, 0, 1, -1)] == [-50, 50, 1, -80, 80]


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, devices: str, match: str, *, shape: str = SHAPE):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + shape + devices + "\n")
    native = DssReader(path).read_all()
    with pytest.raises(ValueError, match=match):
        dss_to_cimtbl.DssImporter("atom", time_points={}).to_cim(native, artifact_dir=tmp_path / "artifacts")


@pytest.mark.parametrize(("devices", "match"), (
    ("New PVSystem.x bus1=b1 kV=4.16 kVA=100 Pmpp=100 %cutin=30 %cutout=10 yearly=s",
     "sample 1 of yearly=s puts the panel at 20 kW, between %Cutout"),
    ("New PVSystem.x bus1=b1 kV=4.16 yearly=none", "yearly=none names no LoadShape of the deck"),
    ("New Generator.x bus1=b1 kV=4.16 kW=10 dispmode=loadlevel yearly=s", "with dispmode=Loadlevel"),
    ("New Generator.x bus1=b1 kV=4.16 kW=10 dispvalue=0.4 yearly=s", "with dispvalue=0.4"),
    ("New Generator.x bus1=b1 kV=4.16 kW=10 status=fixed yearly=s", "with status=Fixed"),
    ("New Storage.x bus1=b1 kV=4.16 yearly=s", "DispMode=None with yearly=s"),
    ("New Storage.x bus1=b1 kV=4.16 DispMode=follow", "DispMode=follow with yearly=None"),
    ("New Storage.x bus1=b1 kV=4.16 DispMode=follow kW=10 yearly=s", "DispMode=follow with a kW or State"),
), ids=("pv hysteresis", "no shape", "dispmode", "dispvalue", "fixed", "storage default mode", "follow no shape",
        "follow kW"))
def test_a_device_shape_off_the_mapping_raises(tmp_path, devices, match):
    raises(tmp_path, devices, match)


def test_a_device_shape_with_qmult_raises(tmp_path):
    raises(tmp_path, "New Generator.x bus1=b1 kV=4.16 kW=10 yearly=s", "has a qmult",
           shape="New Loadshape.s npts=2 interval=1 mult=(1 2) qmult=(1 1)\n")
