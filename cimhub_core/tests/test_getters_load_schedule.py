"""cimhub_core.getters.load_schedule on the ``load_schedule`` shape: a load's group and its one schedule."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.load_schedule import get_load_schedule, log_dropped_schedules

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


def test_dropped_schedules_warn_once_naming_the_groups(network, caplog):
    consumers = [consumer for cls in (network.cim.ConformLoad, network.cim.NonConformLoad)
                 for consumer in network.graph[cls].values()]
    with caplog.at_level(logging.WARNING, logger="cimhub_core.getters.load_schedule"):
        log_dropped_schedules(consumers, "RAW")
    assert caplog.text.count("WARNING") == 1
    assert "RAW: the schedules of 2 load group(s) are not exported" in caplog.text
    assert "['plant', 'zipload']" in caplog.text
