"""shared.py: units, voltages, phases, containers and names (GDM_MAPPING.md §4-§7)."""

import math

import pytest
from cimhub_gdm.importer import shared
from gdm.systems.distribution.components import DistributionBus, DistributionFeeder, DistributionSubstation
from gdm.systems.distribution.enums import Phase, VoltageTypes
from gdm.quantities import ActivePower, ApparentPower, CapacitancePULength, ReactivePower, Voltage

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


NAMING = shared.Naming("sys")
GUID = "372a4dea-63f2-4737-bc0f-5549c04b3d54"


def test_container_mrid_prefers_feeder_then_substation_then_system():
    feeder = DistributionFeeder(name="f")
    substation = DistributionSubstation(name="s", feeders=[feeder])
    assert shared.container_mrid(_bus("b", feeder=feeder, substation=substation), NAMING) == "fdr_f"
    assert shared.container_mrid(_bus("b", substation=substation), NAMING) == "sub_s"
    assert shared.container_mrid(_bus("b"), NAMING) == "fdr_sys"


def test_name_clashes_are_empty_or_shared_names_within_a_class():
    empty, f1, f2, other = (DistributionFeeder(name=""), DistributionFeeder(name="f"), DistributionFeeder(name="f"),
                            DistributionFeeder(name="g"))
    substation = DistributionSubstation(name="f", feeders=[])
    assert shared.name_clashes([empty, f1, f2, other, substation]) == {empty.uuid, f1.uuid, f2.uuid}


def test_object_mrid_is_the_prefixed_name():
    assert shared.object_mrid("ln_", _bus("l1"), "ACLineSegment", NAMING) == "ln_l1"


def test_object_mrid_rehashes_a_guid_name_per_class():
    bus = _bus(GUID)
    first = shared.object_mrid("ln_", bus, "ACLineSegment", NAMING)
    assert first != GUID and not first.startswith("ln_")
    assert first == shared.object_mrid("ln_", _bus(GUID), "ACLineSegment", NAMING)  # seeded: stable
    assert first != shared.object_mrid("lc_", bus, "PerLengthPhaseImpedance", NAMING)


def test_object_mrid_rehashes_the_uuid_of_a_clashing_name():
    a, b = _bus("x"), _bus("x")
    naming = shared.Naming("sys", shared.name_clashes([a, b]))
    mrids = {shared.object_mrid("", bus, "ConnectivityNode", naming) for bus in (a, b)}
    assert len(mrids) == 2 and "x" not in mrids


def test_check_shell_name_rejects_guid_and_clashing_names():
    with pytest.raises(ValueError, match="not supported"):
        shared.check_shell_name(DistributionFeeder(name=GUID), NAMING)
    clashing = DistributionFeeder(name="")
    with pytest.raises(ValueError, match="not supported"):
        shared.check_shell_name(clashing, shared.Naming("sys", frozenset({clashing.uuid})))
    shared.check_shell_name(DistributionFeeder(name="f"), NAMING)


def test_power_qty_rejects_a_power_of_the_wrong_kind():
    assert shared.power_qty(ReactivePower(5, "kilovar"), "reactive", label="x").value == 5
    with pytest.raises(ValueError, match="not an reactive power unit"):
        shared.power_qty(ReactivePower(5, "kilowatt"), "reactive", label="x")
    with pytest.raises(ValueError, match="not an active power unit"):
        shared.power_qty(ActivePower(5, "kilova"), "active", label="x")


def test_susceptance_is_omega_c():
    """10 nF/km at 60 Hz: 2π·60·10e-9 S/km = 3.7699e-6 S/km = 3.7699e-9 S/m."""
    b = shared.susceptance(CapacitancePULength(10, "nanofarad / kilometer"))
    assert b.value == pytest.approx(2 * math.pi * 60 * 10)
    assert b.unit == "hertz * nanofarad / kilometer"
