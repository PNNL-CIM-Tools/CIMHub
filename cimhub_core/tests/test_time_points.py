"""cimhub_core.time_points: the Parquet sidecar of nc_schedule time points (the ``time-points`` extra).

Two schedules on the ``load`` shape's consumers, made by CIM-Builder as a spoke makes them; the sidecar writes their
points beside an XML path and reads them back against the network.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pytest
from cimbuilder.object_builder.schedule import TIME_POINT_CLASS, EnergyConnectionScheduleBuilder
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.time_points import read_time_points, rows_by_schedule, time_points_path, write_time_points

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
HOURS = [datetime(2020, 1, 1) + timedelta(hours=hour) for hour in range(3)]


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture
def scheduled():
    """(network, its two schedules, their points): y1 has p and q, c1 only p."""
    network = load_model(SHAPES / "load.cimtbl")
    builder = EnergyConnectionScheduleBuilder(network=network, container=network.container)
    schedules, tables = [], []
    for consumer, q in (("ld_y1", [0.5, 0.6, 0.7]), ("ld_c1", None)):
        schedule = builder.create(mRID=f"{consumer}_pq", name=consumer)
        builder.add_schedule(schedule, EnergyConnection=consumer, timeSeriesKind="actual")
        schedules.append(schedule)
        tables.append(builder.time_points(schedule, times=HOURS, p=[1.0, 2.0, 3.0], q=q, p_unit="kW", q_unit="kVAr"))
    return network, schedules, {TIME_POINT_CLASS: pa.concat_tables(tables)}


def test_points_round_trip_beside_the_xml(tmp_path, scheduled):
    network, _, points = scheduled
    xml_path = tmp_path / "feeder.xml"
    assert write_time_points(points, xml_path) == [tmp_path / "feeder.EnergyConnectionTimePoint.parquet"]
    read = read_time_points(xml_path, network)[TIME_POINT_CLASS]
    assert read.schema.equals(points[TIME_POINT_CLASS].schema, check_metadata=True)
    assert read.to_pylist() == points[TIME_POINT_CLASS].to_pylist()


def test_rows_by_schedule_in_time_order(scheduled):
    _, (y1, c1), points = scheduled
    reversed_rows = points[TIME_POINT_CLASS].take(list(reversed(range(6))))
    groups = rows_by_schedule(reversed_rows)
    assert groups.keys() == {y1.uri(), c1.uri()}
    assert groups[y1.uri()].column("p").to_pylist() == [3000.0, 2000.0, 1000.0]  # each schedule keeps its row order
    assert groups[c1.uri()].column("q").to_pylist() == [None, None, None]


def test_an_orphan_row_raises(tmp_path, scheduled):
    network, (_, c1), points = scheduled
    xml_path = tmp_path / "feeder.xml"
    write_time_points(points, xml_path)
    network.graph[type(c1)].pop(c1.identifier)
    with pytest.raises(ValueError, match="rows for 1 schedule"):
        read_time_points(xml_path, network)


def test_a_repeated_point_raises(tmp_path, scheduled):
    network, _, points = scheduled
    xml_path = tmp_path / "feeder.xml"
    table = points[TIME_POINT_CLASS]
    write_time_points({TIME_POINT_CLASS: pa.concat_tables([table, table.slice(0, 1)])}, xml_path)
    with pytest.raises(ValueError, match="1 repeated"):
        read_time_points(xml_path, network)


def test_a_schedule_with_no_points_warns(tmp_path, scheduled, caplog):
    network, _, _ = scheduled
    with caplog.at_level(logging.WARNING, logger="cimhub_core.time_points"):
        assert read_time_points(tmp_path / "feeder.xml", network) == {}
    assert "2 EnergyConnectionSchedule(s) have no time points: ['ld_c1_pq', 'ld_y1_pq']" in caplog.text
    assert not time_points_path(tmp_path / "feeder.xml", TIME_POINT_CLASS).exists()


def test_a_table_off_the_schema_raises(tmp_path, scheduled):
    _, _, points = scheduled
    table = points[TIME_POINT_CLASS].drop_columns(["q"])
    with pytest.raises(ValueError, match="not the builder's TIME_POINT_SCHEMA"):
        write_time_points({TIME_POINT_CLASS: table}, tmp_path / "feeder.xml")


def test_an_unknown_time_point_class_raises(tmp_path, scheduled):
    _, _, points = scheduled
    with pytest.raises(ValueError, match="no time point table for 'LoadTimePoint'"):
        write_time_points({"LoadTimePoint": points[TIME_POINT_CLASS]}, tmp_path / "feeder.xml")
