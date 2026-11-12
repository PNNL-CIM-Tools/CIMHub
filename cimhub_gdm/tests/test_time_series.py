"""Load time series ↔ EnergyConnectionSchedule + EnergyConnectionTimePoint rows (TIMESERIES_NEEDS.md T1-T6).

Atoms: ``bal`` (300 kW, 150 kVAr) and ``one`` (50 kW, 25 kVAr) from ``gdm_atoms.add_loads``, with series attached as
ditto attaches an OpenDSS loadshape. The expected points are written out here; the schedules' XML is checked by the
reload diff.
"""

import logging
from datetime import datetime, timedelta, timezone

import gdm_atoms
import pyarrow as pa
import pytest
from cimgraph.databases import XMLFile
from cimgraph.models import FeederModel
from cimgraph.utils import write_xml
from cimtables.diff import diff_models
from gdm.quantities import ActivePower, Irradiance, ReactivePower
from gdm.systems.distribution.components import DistributionLoad, DistributionSolar
from infrasys.normalization import NormalizationMax
from infrasys.time_series_models import NonSequentialTimeSeries, SingleTimeSeries

from cimhub_gdm import GdmExporter, gdm_to_cim, read_time_points, write_time_points
from cimhub_gdm.time_points import rows_by_schedule, time_points_path

POINTS = "EnergyConnectionTimePoint"
START = datetime(2020, 1, 1)
HOUR = timedelta(hours=1)
HOURS = [START + i * HOUR for i in range(3)]
UTC_HOURS = [t.replace(tzinfo=timezone.utc) for t in HOURS]


def _system():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_source(system)
    gdm_atoms.add_loads(system)
    return system


def _load(system, name: str) -> DistributionLoad:
    return system.get_component(DistributionLoad, name)


def _single(name, data):
    return SingleTimeSeries.from_array(data=data, name=name, initial_timestamp=START, resolution=HOUR)


def _import(system):
    time_points = {}
    return gdm_to_cim(system, time_points=time_points), time_points


def _schedule(network, mrid: str):
    schedule = network.find_by_mRID(mrid)
    assert type(schedule).__name__ == "EnergyConnectionSchedule"
    return schedule


def _rows(time_points, schedule) -> tuple[list, list, list]:
    """The schedule's (atTime, p, q) columns."""
    rows = rows_by_schedule(time_points[POINTS])[schedule.uri()]
    return tuple(rows.column(name).to_pylist() for name in ("atTime", "p", "q"))


def test_a_p_multiplier_becomes_actual_p_and_q_on_one_schedule():
    """ditto's PMult-only loadshape (normalized, labelled kilowatt): q(t) = multiplier(t) × q too (T1, §7)."""
    system = _system()
    series = _single("active_power", ActivePower([0.5, 1.0, 2.0], "kilowatt"))
    system.add_time_series(series, _load(system, "bal"), profile_type="PMult", profile_name="ls1", use_actual=False)
    network, time_points = _import(system)

    schedule = _schedule(network, "ld_bal_pq")
    assert schedule.EnergyConnection is network.find_by_mRID("ld_bal")
    assert schedule.name == "ls1"
    assert (schedule.timeSeriesKind.value, schedule.interpolationKind.value) == ("schedule", "previous")
    times, p, q = _rows(time_points, schedule)
    assert times == UTC_HOURS
    assert (p, q) == (pytest.approx([150e3, 300e3, 600e3]), pytest.approx([75e3, 150e3, 300e3]))


def test_a_normalized_multiplier_is_already_scaled():
    """NormalizationMax divides the stored data by its max when the series is made, so it needs no extra step."""
    system = _system()
    series = SingleTimeSeries.from_array(data=[1.0, 2.0, 4.0], name="active_power", initial_timestamp=START,
                                         resolution=HOUR, normalization=NormalizationMax())
    system.add_time_series(series, _load(system, "one"), use_actual=False)
    network, time_points = _import(system)
    assert _rows(time_points, _schedule(network, "ld_one_pq"))[1] == pytest.approx([12.5e3, 25e3, 50e3])


def test_actual_p_and_q_on_one_time_base_share_a_schedule():
    system = _system()
    load = _load(system, "one")
    system.add_time_series(_single("active_power", ActivePower([10, 20, 30], "kilowatt")), load,
                           profile_type="PMult", profile_name="ls2", use_actual=True)
    system.add_time_series(_single("reactive_power", ReactivePower([1, 2, 3], "kilovar")), load,
                           profile_type="QMult", profile_name="ls2", use_actual=True)
    network, time_points = _import(system)
    times, p, q = _rows(time_points, _schedule(network, "ld_one_pq"))
    assert times == UTC_HOURS
    assert (p, q) == (pytest.approx([10e3, 20e3, 30e3]), pytest.approx([1e3, 2e3, 3e3]))


def test_an_actual_p_alone_leaves_q_null():
    system = _system()
    system.add_time_series(_single("active_power", ActivePower([10, 20, 30], "kilowatt")), _load(system, "one"),
                           use_actual=True)
    network, time_points = _import(system)
    schedule = _schedule(network, "ld_one_p")
    assert schedule.name == "one"  # no profile_name: the load's
    assert _rows(time_points, schedule)[2] == [None, None, None]


def test_p_and_q_on_different_times_get_a_schedule_each():
    system = _system()
    load = _load(system, "one")
    system.add_time_series(_single("active_power", ActivePower([10, 20, 30], "kilowatt")), load)
    system.add_time_series(NonSequentialTimeSeries.from_array(
        data=ReactivePower([1, 2], "kilovar"), name="reactive_power", timestamps=[START, START + 5 * HOUR]), load)
    network, time_points = _import(system)
    assert _rows(time_points, _schedule(network, "ld_one_p"))[1] == pytest.approx([10e3, 20e3, 30e3])
    times, p, q = _rows(time_points, _schedule(network, "ld_one_q"))
    assert times == [UTC_HOURS[0], UTC_HOURS[0] + 5 * HOUR]
    assert (p, q) == ([None, None], pytest.approx([1e3, 2e3]))


def test_two_series_of_one_variable_raise():
    """A DSS load's yearly and daily shapes: their roles have no CIM home yet (X5)."""
    system = _system()
    load = _load(system, "one")
    for profile in ("yearly_ls", "daily_ls"):
        system.add_time_series(_single("active_power", [1.0, 0.5, 1.0]), load, profile_name=profile,
                               use_actual=False)
    with pytest.raises(ValueError, match="two active_power series"):
        _import(system)


def test_repeated_times_raise():
    """ditto gives an Hour-array loadshape SInterval 0, so every sample is at one time (X10)."""
    system = _system()
    series = SingleTimeSeries.from_time_array(ActivePower([1, 2], "kilowatt"), "active_power", [START, START])
    system.add_time_series(series, _load(system, "one"), use_actual=True)
    with pytest.raises(ValueError, match="ld_one_p.*repeated times"):
        _import(system)


def test_other_series_are_dropped_with_one_warning(caplog):
    """PV irradiance (T2) and source pu_voltage (T3) have no schedule class yet."""
    system = _system()
    gdm_atoms.add_lines(system)
    gdm_atoms.add_transformers(system)
    gdm_atoms.add_der(system)
    system.add_time_series(_single("irradiance", Irradiance([0.2, 0.9, 0.4], "kilowatt/meter**2")),
                           system.get_component(DistributionSolar, "roof"))
    system.add_time_series(_single("active_power", ActivePower([10, 20, 30], "kilowatt")), _load(system, "one"),
                           use_actual=True)
    with caplog.at_level(logging.WARNING, logger="cimhub_gdm"):
        _, time_points = _import(system)
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "dropping 1 time series" in warnings[0] and "DistributionSolar 'roof': irradiance" in warnings[0]
    assert time_points[POINTS].num_rows == 3


def test_without_time_points_nothing_is_scheduled():
    system = _system()
    system.add_time_series(_single("active_power", ActivePower([10, 20, 30], "kilowatt")), _load(system, "one"),
                           use_actual=True)
    network = gdm_to_cim(system)
    assert not network.graph.get(network.cim.EnergyConnectionSchedule)


def _with_series(system):
    load = _load(system, "bal")
    system.add_time_series(_single("active_power", ActivePower([0.5, 1.0, 2.0], "kilowatt")), load,
                           profile_type="PMult", profile_name="ls1", use_actual=False)
    system.add_time_series(_single("active_power", ActivePower([10, 20, 30], "kilowatt")), _load(system, "one"),
                           profile_type="PMult", profile_name="ls2", use_actual=True)
    return system


def test_schedules_and_points_survive_xml_and_parquet(tmp_path):
    network, time_points = _import(_with_series(_system()))
    xml_path = tmp_path / "loads.xml"
    write_xml(network, str(xml_path))
    assert write_time_points(time_points, xml_path) == [tmp_path / "loads.EnergyConnectionTimePoint.parquet"]

    reloaded = FeederModel(connection=XMLFile(filename=str(xml_path)), container=None, distributed=False)
    assert diff_models(network, reloaded) == []
    read = read_time_points(xml_path, reloaded)[POINTS]
    assert read.schema.equals(time_points[POINTS].schema, check_metadata=True)
    assert read.to_pylist() == time_points[POINTS].to_pylist()


def test_an_orphan_row_raises(tmp_path):
    network, time_points = _import(_with_series(_system()))
    xml_path = tmp_path / "loads.xml"
    write_xml(network, str(xml_path))
    write_time_points(time_points, xml_path)
    stray = network.find_by_mRID("ld_one_p")
    network.graph[type(stray)].pop(stray.identifier)
    with pytest.raises(ValueError, match="rows for 1 schedule"):
        read_time_points(xml_path, network)


def test_a_repeated_point_in_the_file_raises(tmp_path):
    network, time_points = _import(_with_series(_system()))
    xml_path = tmp_path / "loads.xml"
    doubled = pa.concat_tables([time_points[POINTS], time_points[POINTS].slice(0, 1)])
    write_time_points({POINTS: doubled}, xml_path)
    with pytest.raises(ValueError, match="1 repeated"):
        read_time_points(xml_path, network)


def test_a_schedule_with_no_points_warns(tmp_path, caplog):
    network, _ = _import(_with_series(_system()))
    with caplog.at_level(logging.WARNING, logger="cimhub_gdm"):
        assert read_time_points(tmp_path / "loads.xml", network) == {}
    assert "2 EnergyConnectionSchedule(s) have no time points: ['ld_bal_pq', 'ld_one_p']" in caplog.text
    assert not time_points_path(tmp_path / "loads.xml", POINTS).exists()


def test_the_export_gives_back_actual_series():
    """GDM → CIM → GDM: every series comes back in actual values (use_actual=True), named by its schedule."""
    network, time_points = _import(_with_series(_system()))
    exported = GdmExporter(time_points).to_model(network, name_source="name", system_name="atom")

    bal = exported.get_component(DistributionLoad, "bal")
    keys = {(m.name, m.features["profile_name"], m.features["use_actual"])
            for m in exported.list_time_series_metadata(bal)}
    assert keys == {("active_power", "ls1", True), ("reactive_power", "ls1", True)}
    active = exported.get_time_series(bal, "active_power")
    assert (active.initial_timestamp, active.resolution) == (START, HOUR)
    assert active.data.to("kilowatt").magnitude == pytest.approx([150, 300, 600])
    assert exported.get_time_series(bal, "reactive_power").data.to("kilovar").magnitude == pytest.approx([75, 150, 300])

    one = exported.get_component(DistributionLoad, "one")
    assert [m.name for m in exported.list_time_series_metadata(one)] == ["active_power"]


def test_a_shared_schedule_name_exports_as_the_uri():
    """Two loads on one loadshape give two schedules named ls1; ditto would merge their LoadShapes by name."""
    system = _system()
    for name in ("bal", "one"):
        system.add_time_series(_single("active_power", [1.0, 0.5, 1.0]), _load(system, name),
                               profile_name="ls1", use_actual=False)
    network, time_points = _import(system)
    exported = GdmExporter(time_points).to_model(network, name_source="name", system_name="atom")
    for name in ("bal", "one"):
        [metadata, _] = exported.list_time_series_metadata(exported.get_component(DistributionLoad, name))
        assert metadata.features["profile_name"] == _schedule(network, f"ld_{name}_pq").uri()


def test_schedules_without_points_export_with_one_warning(caplog):
    network, _ = _import(_with_series(_system()))
    with caplog.at_level(logging.WARNING, logger="cimhub_gdm"):
        exported = GdmExporter().to_model(network, name_source="name", system_name="atom")
    assert "2 EnergyConnectionSchedule(s) exported without their time points" in caplog.text
    assert not exported.has_time_series(exported.get_component(DistributionLoad, "bal"))
