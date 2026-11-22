"""cimhub_core.getters.load_schedule on the ``load_schedule`` shape: a load's group and its one schedule."""

from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.load_schedule import get_load_schedule, get_schedule_points, log_dropped_schedules
from cimhub_core.time_points import regular_time_points, rows_by_schedule

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture
def network():
    return load_model(SHAPES / "load_schedule.cimtbl")


def _consumer(network, mrid):
    for cls in (network.cim.ConformLoad, network.cim.NonConformLoad, network.cim.EnergyConsumer):
        for consumer in network.graph.get(cls, {}).values():
            if consumer.mRID == mrid:
                return consumer
    raise KeyError(mrid)


def test_a_conform_load_reads_its_group_schedule(network):
    found = get_load_schedule(_consumer(network, "ld_z2"))
    assert found.conform and found.group.mRID == "lg_zipload" and found.schedule.mRID == "ls_zipload"
    assert found.start == "2009-07-21T00:00:00-04:00"
    assert found.step == pytest.approx(60.0)


def test_a_group_with_no_schedule_keeps_its_name(network):
    found = get_load_schedule(_consumer(network, "ld_z3"))
    assert found.group.name == "unknown"
    assert (found.schedule, found.start, found.step) == (None, None, None)


def test_a_non_conform_load_reads_its_group_schedule(network):
    found = get_load_schedule(_consumer(network, "ld_p1"))
    assert not found.conform and found.schedule.mRID == "ls_plant"
    assert found.step == pytest.approx(3600.0)


def test_a_plain_consumer_has_none():
    network = load_model(SHAPES / "load.cimtbl")
    assert get_load_schedule(_consumer(network, "ld_y1")) is None


def test_two_schedules_on_a_group_raise(network):
    group = _consumer(network, "ld_z1").LoadGroup
    group.ConformLoadSchedules.append(group.ConformLoadSchedules[0])
    with pytest.raises(ValueError, match="2 schedules"):
        get_load_schedule(_consumer(network, "ld_z1"))


def test_schedules_by_season_or_day_type_are_days(network):
    """A GridLAB-D schedule's form: several schedules, each of a DayType (or Season), and no time series."""
    group = _consumer(network, "ld_z1").LoadGroup
    [series] = group.ConformLoadSchedules
    weekend = network.cim.ConformLoadSchedule(mRID="ls_zipload_weekend", DayType=network.cim.DayType(name="weekend"))
    group.ConformLoadSchedules.append(weekend)
    with pytest.raises(ValueError, match="1 schedules with no Season or DayType and 1 with one"):
        get_load_schedule(_consumer(network, "ld_z1"))
    series.DayType = network.cim.DayType(name="weekday")
    found = get_load_schedule(_consumer(network, "ld_z1"))
    assert (found.schedule, found.start, found.step) == (None, None, None)
    assert found.days == (series, weekend)  # by mRID


def test_dropped_schedules_warn_once_naming_the_groups(network, caplog):
    consumers = [consumer for cls in (network.cim.ConformLoad, network.cim.NonConformLoad)
                 for consumer in network.graph[cls].values()]
    with caplog.at_level(logging.WARNING, logger="cimhub_core.getters.load_schedule"):
        log_dropped_schedules(consumers, "RAW")
    assert caplog.text.count("WARNING") == 1
    assert "RAW: the schedules of 2 load group(s) are not exported" in caplog.text
    assert "['plant', 'zipload']" in caplog.text


def _rows(schedule, value1, value2=None, numbers=None):
    table = regular_time_points({schedule.uri(): value1}, {schedule.uri(): value2} if value2 else None)
    if numbers is not None:
        table = table.set_column(1, "sequenceNumber", pa.array(numbers, pa.int32()))
    return rows_by_schedule(table)


def test_schedule_points_in_sequence_order(network):
    schedule = _consumer(network, "ld_p1").LoadGroup.NonConformLoadSchedules[0]
    assert get_schedule_points(schedule, _rows(schedule, [400.0, 450.0], [100.0, 120.0])) == (
        [400.0, 450.0], [100.0, 120.0])
    assert get_schedule_points(schedule, _rows(schedule, [400.0, 450.0])).value2 is None


def test_a_schedule_with_no_rows_has_no_points(network):
    schedule = _consumer(network, "ld_z1").LoadGroup.ConformLoadSchedules[0]
    assert get_schedule_points(schedule, {}) is None


@pytest.mark.parametrize(("value1", "value2", "numbers", "match"), (
    ([1.0, 2.0], None, [0, 2], r"points numbered \[0, 2\]"),
    ([1.0, 2.0], None, [1, 0], r"points numbered \[1, 0\]"),
    ([1.0, None], None, None, "value1 is unset at 1 of 2 points"),
    ([1.0, 2.0], [3.0, None], None, "value2 is unset at 1 of 2 points"),
), ids=("gap", "out of order", "value1 unset", "value2 at some points"))
def test_points_off_the_rules_raise(network, value1, value2, numbers, match):
    schedule = _consumer(network, "ld_z1").LoadGroup.ConformLoadSchedules[0]
    with pytest.raises(ValueError, match=match):
        get_schedule_points(schedule, _rows(schedule, value1, value2, numbers))
