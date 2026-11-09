"""cimhub_core.getters.source: an EnergySource's voltage, angle and impedance."""

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.source import SourceImpedance, get_source

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network():
    return load_model(SHAPES / "source.cimtbl")


def _source(network=None):
    [source] = (network or _network()).graph[cim.EnergySource].values()
    return source


def test_voltage_and_ohms():
    source = get_source(_source(), angle_unit="deg", voltage_unit="kV")
    assert (source.nominal_u, source.magnitude, source.magnitude_pu) == pytest.approx((115, 115, 1.0))
    assert source.angle == pytest.approx(30)
    assert source.impedance == pytest.approx(SourceImpedance(0.160377, 0.641507, 0.179604, 0.538811, None, None))


def test_angle_in_radians():
    assert get_source(_source(), angle_unit="rad").angle == pytest.approx(math.pi / 6)


def test_pu_on_base_voltage_and_system_power():
    network = _network()
    impedance = get_source(_source(network), angle_unit="deg", impedance_unit="pu",
                           base_power=network.base_power).impedance
    z_base = 115e3 ** 2 / 100e6
    assert (impedance.r, impedance.x0) == pytest.approx((0.160377 / z_base, 0.538811 / z_base))


def test_magnitude_off_nominal():
    source = _source()
    source.voltageMagnitude = cim.Voltage(117.3, "kV")
    assert get_source(source, angle_unit="deg").magnitude_pu == pytest.approx(1.02)


def test_unset_magnitude_raises():
    source = _source()
    source.voltageMagnitude = None
    with pytest.raises(ValueError, match="EnergySource 'src_source': voltageMagnitude is unset"):
        get_source(source, angle_unit="deg")


def test_percent_is_not_an_impedance_unit():
    with pytest.raises(ValueError, match="impedance_unit must be one of"):
        get_source(_source(), angle_unit="deg", impedance_unit="percent")
