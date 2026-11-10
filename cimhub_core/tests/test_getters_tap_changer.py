"""cimhub_core.getters.tap_changer: tap positions and the turns ratio at one."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.tap_changer import TapSteps, get_tap_ratio, get_tap_steps

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _tap(shape="regulator"):
    network = load_model(SHAPES / f"{shape}.cimtbl")
    [tap] = network.graph[cim.RatioTapChanger].values()
    return tap


def test_steps():
    assert get_tap_steps(_tap(), "kV") == TapSteps(-16, 16, 0, 0, 10.0, 0.625, pytest.approx(2.4))


@pytest.mark.parametrize(("which", "ratio"), [("actual", 1.0625), ("normal", 1.0), ("low", 0.9), ("high", 1.1)])
def test_ratio(which, ratio):
    assert get_tap_ratio(_tap(), which=which) == pytest.approx(ratio)


def test_increment_in_percent_either_spelling():
    # voltage_regulator writes stepVoltageIncrement (percent), regulator a bare 0.625: both are 0.625 %
    assert get_tap_ratio(_tap("voltage_regulator"), which="actual") == pytest.approx(1.0625)


def test_ratio_from_a_shifted_neutral():
    tap = _tap()
    tap.neutralStep, tap.lowStep, tap.highStep, tap.step = 16, 0, 32, 26.0
    assert get_tap_ratio(tap, which="actual") == pytest.approx(1.0625)


def test_unset_position_raises():
    with pytest.raises(ValueError, match="RatioTapChanger 'rc_reg1_tap': normalStep is unset"):
        get_tap_ratio(_tap("voltage_regulator"), which="normal")


def test_unset_increment_raises():
    tap = _tap()
    tap.stepVoltageIncrement = None
    with pytest.raises(ValueError, match="stepVoltageIncrement is unset"):
        get_tap_ratio(tap, which="actual")


def test_fixed_tap_has_no_increment():
    # one step at neutralU, no stepVoltageIncrement (a RAW step-up's GTAP, its fixed taps)
    tap = _tap()
    tap.lowStep = tap.highStep = tap.neutralStep = tap.normalStep = 1
    tap.step, tap.stepVoltageIncrement = 1.0, None
    assert get_tap_steps(tap, "kV") == TapSteps(1, 1, 1, 1, 1.0, None, pytest.approx(2.4))
    assert get_tap_ratio(tap, which="actual") == 1.0


def test_which_is_required_and_checked():
    with pytest.raises(ValueError, match="which must be one of"):
        get_tap_ratio(_tap(), which="neutral")
