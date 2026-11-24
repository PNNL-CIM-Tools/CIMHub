"""cimhub_core.time_points: the Parquet sidecar of schedule time points (the ``time-points`` extra).

Two nc_schedule schedules on the ``load`` shape's consumers, made by CIM-Builder as a spoke makes them, and the
``load_schedule`` shape's regular group schedules; the sidecar writes their points beside an XML path and reads them
back against the network.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pytest
from cimbuilder.object_builder.schedule import TIME_POINT_CLASS, EnergyConnectionScheduleBuilder
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.device_schedule import get_device_schedule
from cimhub_core.time_points import (REGULAR_TIME_POINT_CLASS, add_device_time_points, add_regular_time_points,
                                     read_time_points, regular_time_points, rows_by_schedule, time_points_path,
                                     write_time_points)

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
    with pytest.raises(ValueError, match="not its TimePoint schema"):
        write_time_points({TIME_POINT_CLASS: table}, tmp_path / "feeder.xml")


def test_an_unknown_time_point_class_raises(tmp_path, scheduled):
    _, _, points = scheduled
    with pytest.raises(ValueError, match="no time point table for 'LoadTimePoint'"):
        write_time_points({"LoadTimePoint": points[TIME_POINT_CLASS]}, tmp_path / "feeder.xml")


@pytest.fixture
def regular():
    """(network, its two group schedules by mRID, their points): ls_zipload 3 multipliers, ls_plant 2 powers."""
    network = load_model(SHAPES / "load_schedule.cimtbl")
    schedules = {schedule.mRID: schedule for cls in (network.cim.ConformLoadSchedule, network.cim.NonConformLoadSchedule)
                 for schedule in network.graph[cls].values()}
    points = regular_time_points({schedules["ls_zipload"].uri(): [0.5, 0.75, 1.0],
                                  schedules["ls_plant"].uri(): [400.0, 450.0]})
    return network, schedules, {REGULAR_TIME_POINT_CLASS: points}


def test_regular_points_are_numbered_from_zero(regular):
    _, schedules, points = regular
    groups = rows_by_schedule(points[REGULAR_TIME_POINT_CLASS])
    zipload = groups[schedules["ls_zipload"].uri()]
    assert zipload.column("sequenceNumber").to_pylist() == [0, 1, 2]
    assert zipload.column("value1").to_pylist() == [0.5, 0.75, 1.0]
    assert zipload.column("value2").to_pylist() == [None, None, None]


def test_regular_points_round_trip_for_every_schedule_subclass(tmp_path, regular):
    network, _, points = regular
    xml_path = tmp_path / "feeder.xml"
    assert write_time_points(points, xml_path) == [tmp_path / "feeder.RegularTimePoint.parquet"]
    read = read_time_points(xml_path, network)  # ConformLoad and NonConformLoad schedules: RegularIntervalSchedules
    assert read[REGULAR_TIME_POINT_CLASS].to_pylist() == points[REGULAR_TIME_POINT_CLASS].to_pylist()


def test_a_repeated_sequence_number_raises(tmp_path, regular):
    network, _, points = regular
    table = points[REGULAR_TIME_POINT_CLASS]
    write_time_points({REGULAR_TIME_POINT_CLASS: pa.concat_tables([table, table.slice(1, 1)])}, tmp_path / "f.xml")
    with pytest.raises(ValueError, match=r"1 repeated \(schedule, sequenceNumber\)"):
        read_time_points(tmp_path / "f.xml", network)


def test_a_group_schedule_with_no_points_warns(tmp_path, regular, caplog):
    network, _, _ = regular
    with caplog.at_level(logging.WARNING, logger="cimhub_core.time_points"):
        read_time_points(tmp_path / "feeder.xml", network)
    assert "2 RegularIntervalSchedule(s) have no time points: ['ls_plant', 'ls_zipload']" in caplog.text


def test_regular_points_keep_a_second_value(regular):
    _, schedules, _ = regular
    plant = schedules["ls_plant"].uri()
    table = regular_time_points({plant: [400.0, 450.0]}, {plant: [100.0, 120.0]})
    assert table.column("value2").to_pylist() == [100.0, 120.0]


@pytest.mark.parametrize(("value2", "match"), (
    ({"other": [1.0]}, r"value2 for schedules with no value1: \['other'\]"),
    ({"plant": [1.0]}, "2 value1 and 1 value2 points"),
), ids=("unknown schedule", "length"))
def test_a_second_value_off_its_points_raises(value2, match):
    with pytest.raises(ValueError, match=match):
        regular_time_points({"plant": [400.0, 450.0]}, value2)


def test_points_are_added_by_mrid(regular):
    network, schedules, _ = regular
    time_points = {}
    add_regular_time_points(time_points, network, {"ls_plant": [400.0, 450.0]}, {"ls_plant": [100.0, 120.0]})
    [rows] = rows_by_schedule(time_points[REGULAR_TIME_POINT_CLASS]).items()
    assert rows[0] == schedules["ls_plant"].uri()
    assert rows[1].column("value2").to_pylist() == [100.0, 120.0]


def test_points_added_twice_or_for_no_schedule_raise(regular):
    network, _, points = regular
    with pytest.raises(ValueError, match="already holds a RegularTimePoint table"):
        add_regular_time_points(dict(points), network, {"ls_plant": [1.0]})
    with pytest.raises(ValueError, match=r"no RegularIntervalSchedule with mRID \['ls_none'\]"):
        add_regular_time_points({}, network, {"ls_none": [1.0]})
    with pytest.raises(ValueError, match=r"no RegularIntervalSchedule with mRID \['ls_none'\]"):
        add_regular_time_points({}, network, {"ls_plant": [1.0]}, {"ls_none": [1.0]})


def test_device_points_are_added_by_mrid(scheduled):
    """The DSS importer's path: (times, p kW, q kVAr) per schedule mRID, the builder's rows in SI."""
    network, (y1, c1), _ = scheduled
    points = {}
    add_device_time_points(points, network, {"ld_y1_pq": (HOURS, [1.0, 2.0, 3.0], [0.5, 0.6, 0.7]),
                                             "ld_c1_pq": (HOURS[:2], [-4.0, 0.0], None)})
    rows = rows_by_schedule(points[TIME_POINT_CLASS])
    assert rows[y1.uri()].column("q").to_pylist() == pytest.approx([500.0, 600.0, 700.0])
    assert rows[c1.uri()].column("p").to_pylist() == [-4000.0, 0.0]
    with pytest.raises(ValueError, match="already holds"):
        add_device_time_points(points, network, {"ld_c1_pq": (HOURS, [1.0] * 3, None)})
    with pytest.raises(ValueError, match="no EnergyConnectionSchedule with mRID \\['nope'\\]"):
        add_device_time_points({}, network, {"nope": (HOURS, [1.0] * 3, None)})


def test_a_device_schedule_reads_in_the_callers_units_and_sign(scheduled):
    network, (y1, c1), points = scheduled
    rows = rows_by_schedule(points[TIME_POINT_CLASS])
    found = get_device_schedule(y1.EnergyConnection, rows, "kW", "kVAr", sign="generation")
    assert (found.schedule, found.step) == (y1, 3600.0)
    assert found.p == pytest.approx([-1.0, -2.0, -3.0]) and found.q == pytest.approx([-0.5, -0.6, -0.7])
    only_p = get_device_schedule(c1.EnergyConnection, rows, "W", "VAr", sign="load")
    assert (only_p.p, only_p.q) == ([1000.0, 2000.0, 3000.0], None)
    assert get_device_schedule(y1.EnergyConnection, {}, "kW", "kVAr", sign="load") is None  # no points


def test_a_device_schedule_off_the_rules_raises(scheduled):
    network, (y1, _), points = scheduled
    rows = rows_by_schedule(points[TIME_POINT_CLASS])
    with pytest.raises(ValueError, match="sign must be one of"):
        get_device_schedule(y1.EnergyConnection, rows, "kW", "kVAr", sign="up")
    y1.interpolationKind = network.cim.TimeSeriesInterpolationKind.linear
    with pytest.raises(ValueError, match="interpolationKind linear"):
        get_device_schedule(y1.EnergyConnection, rows, "kW", "kVAr", sign="load")
