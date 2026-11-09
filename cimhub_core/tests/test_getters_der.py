"""cimhub_core.getters.der: an inverter's or machine's p and q, ratings and unit data in a declared sign."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.der import (
    BatteryRating,
    InverterRating,
    MachineImpedance,
    get_battery_unit,
    get_der_output,
    get_inverter_rating,
    get_inverter_unit,
    get_machine_impedance,
    get_machine_rating,
    get_photovoltaic_unit,
)
from cimhub_core.getters.phase_power import PhasePower

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
A, B, C, S1, S2 = (cim.SinglePhaseKind(token) for token in ("A", "B", "C", "s1", "s2"))


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _get(shape, cls, mrid):
    network = load_model(SHAPES / f"{shape}.cimtbl")
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


def _inverter(mrid):
    return _get("der", cim.PowerElectronicsConnection, mrid)


def _machine(mrid="gen_g3"):
    return _get("synchronous_machine", cim.SynchronousMachine, mrid)


# get_der_output ----------------------------------------------------------------------------------------------------


def test_generation_sign_is_positive_output():
    output = get_der_output(_inverter("pv_p1"), "kW", "kVAr", sign="generation")
    assert (output.phases, output.connection, output.split) == ((A, B, C), cim.PhaseShuntConnectionKind.Y, True)
    assert output.total == PhasePower(240.0, 0.0)
    assert str(output.total.q) == "0.0"  # a zero stays 0.0, never -0.0
    assert output.per_phase == {phase: pytest.approx(PhasePower(80, 0)) for phase in (A, B, C)}


def test_load_sign_is_as_stored():
    assert get_der_output(_inverter("pv_p1"), "kW", "kVAr", sign="load").total == PhasePower(-240.0, 0.0)


def test_charging_battery_is_negative_generation():
    output = get_der_output(_inverter("storage_b2"), "kW", "kVAr", sign="generation")
    assert output.per_phase == {S1: pytest.approx(PhasePower(-2.5, 0)), S2: pytest.approx(PhasePower(-2.5, 0))}


def test_inverter_phase_values():
    inverter = _inverter("pv_p1")
    inverter.PowerElectronicsConnectionPhase += [
        cim.PowerElectronicsConnectionPhase(mRID=f"ph_{phase.value}", phase=phase, p=cim.ActivePower(p, "kW"),
                                            q=cim.ReactivePower(0, "kVAr"))
        for phase, p in ((A, -100), (B, -80), (C, -60))]
    output = get_der_output(inverter, "kW", "kVAr", sign="generation")
    assert not output.split
    assert [value.p for value in output.per_phase.values()] == pytest.approx([100, 80, 60])


def test_machine():
    output = get_der_output(_get("synchronous_machine", cim.SynchronousMachine, "gen_g2"), "kW", "kVAr",
                            sign="generation")
    assert (output.phases, output.connection) == ((A,), None)
    assert output.total == pytest.approx(PhasePower(10, 3.3))


def test_sign_is_required_and_checked():
    with pytest.raises(ValueError, match="sign must be one of"):
        get_der_output(_inverter("pv_p1"), sign="injection")


def test_other_equipment_raises():
    with pytest.raises(ValueError, match="is not a PowerElectronicsConnection or RotatingMachine"):
        get_der_output(cim.EnergyConsumer(mRID="ld_x"), sign="load")


# get_inverter_rating, get_inverter_unit ----------------------------------------------------------------------------


def test_inverter_rating():
    rating = get_inverter_rating(_inverter("pv_p1"), "kVA", "kVAr", sign="generation", voltage_unit="kV")
    assert rating == pytest.approx(InverterRating(300, 0.48, -300, 300, 1.111111))


def test_load_sign_limits_are_negated_and_swapped():
    inverter = _inverter("pv_p1")
    inverter.maxQ = cim.ReactivePower(200, "kVAr")
    assert get_inverter_rating(inverter, "kVA", "kVAr", sign="generation")[2:4] == pytest.approx((-300, 200))
    assert get_inverter_rating(inverter, "kVA", "kVAr", sign="load")[2:4] == pytest.approx((-200, 300))


def test_unset_limits_and_fault_current_are_none():
    inverter = _inverter("pv_p1")
    inverter.minQ = inverter.maxIFault = None
    rating = get_inverter_rating(inverter, sign="load")
    assert (rating.min_q, rating.max_q, rating.max_fault_current) == (pytest.approx(-300000), None, None)


def test_inverter_rating_required():
    inverter = _inverter("pv_p1")
    inverter.ratedS = None
    with pytest.raises(ValueError, match="PowerElectronicsConnection 'pv_p1': ratedS is unset"):
        get_inverter_rating(inverter, sign="generation")


def test_minimum_above_maximum_raises():
    inverter = _inverter("pv_p1")
    inverter.minQ, inverter.maxQ = cim.ReactivePower(300, "kVAr"), cim.ReactivePower(-300, "kVAr")
    with pytest.raises(ValueError, match="'pv_p1': minQ 300.0 is above maxQ -300.0"):
        get_inverter_rating(inverter, "kVA", "kVAr", sign="load")


def test_inverter_unit():
    assert get_inverter_unit(_inverter("pv_p1")).mRID == "pv_p1_unit"
    inverter = _inverter("pv_p1")
    inverter.PowerElectronicsUnit = []
    with pytest.raises(ValueError, match="'pv_p1': has 0 PowerElectronicsUnits; one is read"):
        get_inverter_unit(inverter)


# get_photovoltaic_unit, get_battery_unit ---------------------------------------------------------------------------


def test_photovoltaic_limits_in_either_sign():
    unit = get_inverter_unit(_inverter("pv_p1"))
    assert get_photovoltaic_unit(unit, "kW", sign="generation") == (0.0, 300.0)
    load = get_photovoltaic_unit(unit, "kW", sign="load")
    assert (load, str(load.max_p)) == ((-300.0, 0.0), "0.0")


def test_battery():
    unit = get_inverter_unit(_inverter("storage_b1"))
    assert get_battery_unit(unit, "kW", "kWh", sign="generation") == pytest.approx(BatteryRating(
        -100, 100, 200, 100, 40, 90, 90, 1, cim.BatteryStateKind.discharging))


def test_battery_idling_loss_is_as_stored_in_either_sign():
    unit = get_inverter_unit(_inverter("storage_b2"))
    assert get_battery_unit(unit, "kW", sign="load").idling_p == pytest.approx(0.05)
    assert get_battery_unit(unit, "kW", sign="generation").idling_p == pytest.approx(0.05)


def test_unit_class_is_checked():
    with pytest.raises(ValueError, match="BatteryUnit 'storage_b1_unit': is not a PhotoVoltaicUnit"):
        get_photovoltaic_unit(get_inverter_unit(_inverter("storage_b1")), sign="load")
    with pytest.raises(ValueError, match="PhotoVoltaicUnit 'pv_p1_unit': is not a BatteryUnit"):
        get_battery_unit(get_inverter_unit(_inverter("pv_p1")), sign="load")


# get_machine_rating, get_machine_impedance -------------------------------------------------------------------------


def test_machine_rating():
    machine = _machine()
    machine.minQ = cim.ReactivePower(-500, "kVAr")
    rating = get_machine_rating(machine, "kVA", "kVAr", sign="generation", voltage_unit="kV")
    assert (rating.rated_s, rating.rated_u, rating.min_q, rating.max_q) == pytest.approx((4000, 4.16, -500, 1080))
    assert (rating.type, rating.operating_mode, rating.earthing) == (
        cim.SynchronousMachineKind.generator, cim.SynchronousMachineOperatingMode.generator, True)
    assert (rating.rated_power_factor, rating.q_percent, rating.reference_priority) == (None, None, None)
    assert get_machine_rating(machine, "kVA", "kVAr", sign="load")[3:5] == pytest.approx((-1080, 500))


def test_machine_without_limits():
    rating = get_machine_rating(_machine("gen_g1"), sign="load")
    assert (rating.min_q, rating.max_q) == (None, None)


def test_machine_impedance_in_pu_on_its_rating():
    machine = _machine()
    machine.r, machine.x2 = cim.Resistance(0.043264), cim.Reactance(0.86528)  # base 4.16 kV² / 4 MVA = 4.3264 ohm
    assert get_machine_impedance(machine, "pu") == pytest.approx(MachineImpedance(0.01, None, None, None, 0.2))
    assert get_machine_impedance(machine).r == pytest.approx(0.043264)


def test_machine_impedance_unit_is_checked():
    with pytest.raises(ValueError, match="unit must be one of"):
        get_machine_impedance(_machine(), "percent")


def test_other_machines_raise():
    with pytest.raises(ValueError, match="AsynchronousMachine 'mot_m1': is not a SynchronousMachine"):
        get_machine_rating(cim.AsynchronousMachine(mRID="mot_m1"), sign="load")
