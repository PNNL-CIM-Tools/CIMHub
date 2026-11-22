"""Atom tests: OpenDSS LoadShape -> loadshape.cimtbl (S8): classification, the golden, the bound schedules and their
points in the sidecar, with the engine as the oracle for each shape's multipliers and interval; the fail-fast rules."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pytest
from cimtables.graph_write import get_qty

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_core.getters.load_schedule import get_load_schedule
from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl import load, loadshape

from conftest import compile_deck

ATOM = Path(__file__).parent / "atoms" / "loadshape" / "loadshapes.dss"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n")
LOAD = "New Load.x bus1=b1 phases=3 kV=4.16 kW=10 kvar=5 yearly=s\n"


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


def test_classification_is_complete():
    check_fields(loadshape.FIELDS, loadshape.NATIVE_CLASS)


@pytest.mark.parametrize("artifact", ("loadshape", "load"))
def test_matches_golden(native, artifact):
    site = dss_to_cimtbl.site(native)
    document = loadshape.map_loadshape(native) if artifact == "loadshape" else load.map_load(
        native, site.buses, site.feeder)
    assert_matches_golden(document, ATOM.with_name(f"loadshapes.{artifact}.cimtbl"))


def test_a_shape_no_load_names_is_counted_not_mapped(native):
    documents = dss_to_cimtbl.DssImporter("atom").to_cimtbl(native)
    assert "not mapped: Loadshape 1" in documents.master.comment  # pv


def test_the_engine_reads_each_shape_as_the_mapper(native):
    """mult (normalized for com), qmult (Q follows mult without one) and the interval in hours, from the engine;
    flat, with no npts, has no points there."""
    compile_deck(ATOM)
    for record in native.list_by_class(loadshape.NATIVE_CLASS):
        shape = loadshape.read_shape(native, record)
        dss.LoadShape.Name(str(record.name))
        if shape is None:
            assert dss.LoadShape.Npts() == 0
            continue
        assert list(dss.LoadShape.PMult()) == pytest.approx(shape.mult)
        if shape.qmult is not None:
            assert list(dss.LoadShape.QMult()) == pytest.approx(shape.qmult)
        hours = timedelta(**{dict(loadshape.INTERVALS.values())[shape.unit]: shape.interval}) / timedelta(hours=1)
        assert dss.LoadShape.HrInterval() == pytest.approx(hours)


def test_the_loads_bind_to_their_groups_with_their_points(bound):
    network, time_points = bound
    loads = {consumer.name: consumer for consumer in network.graph[cim.ConformLoad].values()}
    assert sorted(loads) == ["c1", "f1", "i1", "r1", "r2"]
    assert [consumer.name for consumer in network.graph[cim.EnergyConsumer].values()] == ["static"]
    found = get_load_schedule(loads["r2"])
    assert (found.group.name, found.schedule.mRID) == ("res", "ls_res")
    assert found.group is loads["r1"].LoadGroup  # one group per shape, shared
    # sample 1 is in force one interval into the run (engine-checked, test_export_loadshape)
    assert datetime.fromisoformat(found.start) == datetime(2020, 1, 1, 1, tzinfo=timezone.utc)
    schedules = {schedule.name: schedule for schedule in network.graph[cim.ConformLoadSchedule].values()}
    assert get_qty(schedules["com"], "timeStep", "s") == pytest.approx(900)  # minterval=15
    assert schedules["com"].startTime == "2020-01-01T00:15:00+00:00"
    rows = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS])
    res = rows[schedules["res"].uri()]
    assert res.column("value1").to_pylist() == [0.5, 0.75, 1.0, 0.8]
    assert res.column("value2").to_pylist() == [0.4, 0.6, 0.9, 0.7]
    assert rows[schedules["com"].uri()].column("value1").to_pylist() == [0.25, 0.5, 1.0, 0.75]  # 2 4 8 6 over 8
    assert rows[schedules["ind"].uri()].column("value2").to_pylist() == [None, None, None]
    flat = get_load_schedule(loads["f1"])  # no npts: the engine reads no points, so the group has no schedule
    assert (flat.group.name, flat.schedule) == ("flat", None)


def test_without_time_points_the_points_drop_with_a_warning(native, caplog):
    with caplog.at_level(logging.WARNING, logger="cimhub_opendss.importer.dss_to_cimtbl"):
        network = dss_to_cim(native, name="atom")
    assert len(network.graph[cim.ConformLoadSchedule]) == 3
    assert "the points of 3 LoadShape(s) are dropped" in caplog.text


def test_derived_values():
    assert loadshape.normalized([2.0, -8.0, 4.0]) == [0.25, -1.0, 0.5]
    assert loadshape.normalized([0.0, 0.0]) == [0.0, 0.0]
    assert loadshape.start_time(loadshape.Shape(15.0, "min", [1.0], None)) == "2020-01-01T00:15:00+00:00"


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, shape: str, match: str, *, loads: str = LOAD):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + shape + "\n" + loads)
    native = DssReader(path).read_all()
    with pytest.raises(ValueError, match=match):
        dss_to_cimtbl.DssImporter("atom").to_cimtbl(native)


@pytest.mark.parametrize(("shape", "match"), (
    ("New Loadshape.s npts=2 interval=1 mult=(50 60) useactual=yes", "UseActual=Yes"),
    ("New Loadshape.s npts=2 interval=0 mult=(1 2) hour=(0 5)", "hour not mapped yet"),
    ("New Loadshape.s npts=2 interval=0 mult=(1 2)", "interval=0.0; an hour array"),
    ("New Loadshape.s npts=3 interval=1 mult=(1 2)", "npts=3 but mult has 2 values"),
    ("New Loadshape.s npts=2 interval=1 mult=(1 2) qmult=(1)", "qmult has 1 values and mult 2"),
    ("New Loadshape.s npts=2 interval=1 mult=(1 2) Pbase=4", "Pbase not mapped yet"),
    ("New Loadshape.s npts=2 interval=1 action=normalize mult=(1 2)", "mult assigned after action=normalize"),
    ("New Loadshape.s npts=2 interval=1 mult=(1 2) action=other", "action=other is not mapped"),
    ("New Loadshape.s npts=2 interval=1", "no mult"),
), ids=("useactual", "hour", "interval 0", "npts", "qmult length", "pbase", "normalize order", "action", "no mult"))
def test_a_shape_off_the_mapping_raises(tmp_path, shape, match):
    raises(tmp_path, shape, match)


def test_a_yearly_naming_no_shape_raises(tmp_path):
    raises(tmp_path, "", "Load x: yearly=s names no LoadShape of the deck")


def test_a_shape_no_load_names_is_not_checked(tmp_path):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + "New Loadshape.s npts=2 interval=1 mult=(50 60) useactual=yes\n")
    assert not [part for part in dss_to_cimtbl.DssImporter("atom").to_cimtbl(DssReader(path).read_all()).parts
                if part.name == "loadshape"]
