"""shared.py: units, voltages, phases, containers and names (GDM_MAPPING.md §4-§7)."""

import math

import pytest
from gdm.distribution.components import DistributionBus, DistributionFeeder, DistributionSubstation
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.quantities import ApparentPower, Voltage

from cimhub_gdm.importer import shared

LL, LG = VoltageTypes.LINE_TO_LINE, VoltageTypes.LINE_TO_GROUND
ABC = [Phase.A, Phase.B, Phase.C]


def test_system_voltage_line_to_line_is_unchanged():
    assert shared.system_voltage(Voltage(4.16, "kilovolt"), LL, ABC) == Voltage(4.16, "kilovolt")


def test_system_voltage_line_to_ground_three_phase_is_times_sqrt3():
    v = shared.system_voltage(Voltage(7.2, "kilovolt"), LG, ABC)
    assert v.to("kilovolt").magnitude == pytest.approx(7.2 * math.sqrt(3))


def test_system_voltage_line_to_ground_single_phase_bus_is_times_sqrt3():
    v = shared.system_voltage(Voltage(7.2, "kilovolt"), LG, [Phase.A])
    assert v.to("kilovolt").magnitude == pytest.approx(12.4708, rel=1e-4)


def test_system_voltage_split_phase_is_doubled():
    v = shared.system_voltage(Voltage(0.12, "kilovolt"), LG, [Phase.S1, Phase.S2])
    assert v.to("volt").magnitude == pytest.approx(240)


def test_system_voltage_accepts_ditto_string_voltage_type():
    v = shared.system_voltage(Voltage(2.4, "kilovolt"), "line-to-ground", ABC)
    assert v.to("kilovolt").magnitude == pytest.approx(2.4 * math.sqrt(3))


def test_system_voltage_unknown_type_raises():
    with pytest.raises(ValueError):
        shared.system_voltage(Voltage(2.4, "kilovolt"), "phase-to-moon", ABC)


@pytest.mark.parametrize("voltage, expected", [
    (Voltage(4.16004, "kilovolt"), "bv_4p16kv"),
    (Voltage(12.4704, "kilovolt"), "bv_12p47kv"),
    (Voltage(69.0045, "kilovolt"), "bv_69kv"),
    (Voltage(115000, "volt"), "bv_115kv"),
    (Voltage(0.48003, "kilovolt"), "bv_480v"),
    (Voltage(240.18, "volt"), "bv_240p2v"),
])
def test_base_voltage_mrid(voltage, expected):
    assert shared.base_voltage_mrid(voltage) == expected


def test_round_significant():
    assert shared.round_significant(4.160039) == 4.16
    assert shared.round_significant(12470.4) == 12470
    assert shared.round_significant(0.0) == 0.0


def test_phases_text_in_written_order():
    assert shared.phases_text([Phase.S1, Phase.S2, Phase.N]) == "s1s2N"
    assert shared.phases_text(["C", "A"]) == "CA"


@pytest.mark.parametrize("phases, expected", [
    (ABC, None),
    ([Phase.A, Phase.C, Phase.B], None),
    ([Phase.A, Phase.B, Phase.C, Phase.N], "ABCN"),
    ([Phase.A, Phase.B], "AB"),
    ([Phase.C], "C"),
    ([Phase.S1, Phase.S2], "s1s2"),
])
def test_builder_phases_is_none_only_for_balanced_abc(phases, expected):
    assert shared.builder_phases(phases) == expected


def test_qty_keeps_the_gdm_unit():
    q = shared.qty(Voltage(4.16, "kilovolt"))
    assert (q.value, q.unit) == (4.16, "kilovolt")


def test_qty_respells_kilova():
    q = shared.qty(ApparentPower(75, "kilova"))
    assert (q.value, q.unit) == (75, "kVA")


def _bus(name, **kwargs):
    return DistributionBus(name=name, rated_voltage=Voltage(4.16, "kilovolt"), voltage_type=LL, phases=ABC, **kwargs)


def test_container_mrid_prefers_feeder_then_substation_then_system():
    feeder = DistributionFeeder(name="f")
    substation = DistributionSubstation(name="s", feeders=[feeder])
    assert shared.container_mrid(_bus("b", feeder=feeder, substation=substation), "sys") == "fdr_f"
    assert shared.container_mrid(_bus("b", substation=substation), "sys") == "sub_s"
    assert shared.container_mrid(_bus("b"), "sys") == "fdr_sys"


def test_check_names_rejects_empty_guid_and_clashing_names():
    with pytest.raises(ValueError, match="empty name"):
        shared.check_names([DistributionFeeder(name="")])
    with pytest.raises(ValueError, match="GUID"):
        shared.check_names([DistributionFeeder(name="372a4dea-63f2-4737-bc0f-5549c04b3d54")])
    with pytest.raises(ValueError, match="used by"):
        shared.check_names([DistributionFeeder(name="f"), DistributionFeeder(name="f")])
    shared.check_names([DistributionFeeder(name="f"), DistributionSubstation(name="f", feeders=[])])
