"""cimhub_core.getters.control: regulating-control targets, tap changer control and regulated-device controls."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.control import (
    LineDrop,
    get_equipment_control,
    get_regulating_control,
    get_tap_changer_control,
)

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
A, C = cim.SinglePhaseKind.A, cim.SinglePhaseKind.C


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _get(shape, cls, mrid):
    network = load_model(SHAPES / f"{shape}.cimtbl")
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)


def _tap(shape="regulator", mrid="xf_reg1_tap"):
    return _get(shape, cim.RatioTapChanger, mrid)


def _machine_control():
    return _get("synchronous_machine", cim.RegulatingControl, "gen_g3_ctrl")


# get_regulating_control --------------------------------------------------------------------------------------------


def test_voltage_targets_in_the_callers_unit():
    settings = get_regulating_control(_get("shunt", cim.RegulatingControl, "cc_c2"), "kV")
    assert (settings.mode, settings.unit) == (cim.RegulatingControlModeKind.voltage, "kV")
    assert (settings.target, settings.deadband) == pytest.approx((2.225, 0.55))
    assert (settings.terminal.mRID, settings.monitored_phases) == ("cap_c2_T1", (C,))
    assert (settings.enabled, settings.discrete, settings.pt_ratio, settings.ct_ratio) == (True, True, 1.0, None)


def test_default_unit_is_the_modes_si_unit():
    settings = get_regulating_control(_machine_control())
    assert (settings.unit, settings.target, settings.monitored_phases) == ("V", 4160.0, None)


def test_unit_multiplier_applies():
    control = _machine_control()
    control.targetValue, control.targetValueUnitMultiplier = 4.16, cim.UnitMultiplier.k
    assert get_regulating_control(control).target == pytest.approx(4160)


def test_reactive_power_mode():
    control = _machine_control()
    control.mode, control.targetValue, control.targetValueUnitMultiplier = (cim.RegulatingControlModeKind.reactivePower,
                                                                            150, cim.UnitMultiplier.k)
    settings = get_regulating_control(control, "kVAr")
    assert (settings.unit, settings.target) == ("kVAr", pytest.approx(150))


def test_mode_without_a_quantity_is_as_stored():
    control = _machine_control()
    control.mode, control.targetValue = cim.RegulatingControlModeKind.powerFactor, 0.95
    assert get_regulating_control(control)[1:3] == (None, 0.95)
    with pytest.raises(ValueError, match="a powerFactor target is read as stored"):
        get_regulating_control(control, "V")


@pytest.mark.parametrize(("attribute", "message"), [("mode", "mode is unset"), ("Terminal", "monitors no Terminal"),
                                                    ("targetValue", "targetValue is unset")])
def test_required_settings_raise(attribute, message):
    control = _machine_control()
    setattr(control, attribute, None)
    with pytest.raises(ValueError, match=f"RegulatingControl 'gen_g3_ctrl': {message}"):
        get_regulating_control(control)


# get_tap_changer_control -------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("shape", "mrid"), [("regulator", "xf_reg1_tap"), ("voltage_regulator", "rc_reg1_tap")])
def test_regulator(shape, mrid):
    settings = get_tap_changer_control(_tap(shape, mrid), unit="kV")
    control = settings.control
    assert (control.target, control.deadband, control.monitored_phases) == (pytest.approx(2.44),
                                                                           pytest.approx(0.04), (A,))
    assert control.terminal.mRID == "xf_reg1_T2"
    # regulator.cimtbl sets ptRatio only on the tap changer, voltage_regulator.cimtbl on both
    assert (control.pt_ratio, control.ct_ratio) == (20.0, 3500.0)
    assert (settings.control_enabled, settings.ltc, settings.ct_rating) == (True, True, 700.0)
    assert (settings.initial_delay, settings.subsequent_delay) == (15.0, 2.0)
    assert settings.line_drop_compensation is True
    assert settings.line_drop == pytest.approx(LineDrop(0.085714, 0.257143))
    assert settings.reverse_line_drop == LineDrop(None, None)


def test_delays_in_the_callers_unit():
    assert get_tap_changer_control(_tap(), time_unit="min").initial_delay == pytest.approx(0.25)


def test_tap_changer_without_a_control():
    tap = _tap()
    tap.TapChangerControl = None
    settings = get_tap_changer_control(tap)
    assert (settings.control, settings.line_drop, settings.initial_delay) == (None, LineDrop(None, None), 15.0)


def test_pt_ratio_on_both_sides_must_agree():
    tap = _tap("voltage_regulator", "rc_reg1_tap")
    tap.TapChangerControl.ptRatio = 60
    with pytest.raises(ValueError, match="RatioTapChanger 'rc_reg1_tap' and TapChangerControl 'rc_reg1': ptRatio 20.0 "
                                         "and 60 differ"):
        get_tap_changer_control(tap)


# get_equipment_control ---------------------------------------------------------------------------------------------


def test_shunt_control_with_its_delay():
    settings = get_equipment_control(_get("shunt", cim.LinearShuntCompensator, "cap_c1"))
    assert (settings.control.terminal.mRID, settings.control.target) == ("sw_j1_T1", 2400.0)
    assert (settings.control_enabled, settings.delay) == (True, 15.0)


def test_machine_control_has_no_delay():
    settings = get_equipment_control(_get("synchronous_machine", cim.SynchronousMachine, "gen_g3"))
    assert (settings.control.target, settings.control_enabled, settings.delay) == (4160.0, True, None)


def test_uncontrolled_equipment_is_none():
    assert get_equipment_control(_get("synchronous_machine", cim.SynchronousMachine, "gen_g1")) is None
