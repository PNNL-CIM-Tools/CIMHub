"""cimhub_core.getters.shunt: Q = bPerSection x V^2 x sections on a declared voltage and section count."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.shunt import get_shunt_reactive_power

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
A, B, C = (cim.SinglePhaseKind(token) for token in "ABC")


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _shunt(mrid):
    network = load_model(SHAPES / "shunt.cimtbl")
    return next(obj for obj in network.graph[cim.LinearShuntCompensator].values() if obj.mRID == mrid)


def test_three_phase_at_nominal():
    q = get_shunt_reactive_power(_shunt("cap_c1"), "kVAr", sections="actual", voltage="nominal", voltage_unit="kV")
    assert (q.phases, q.connection, q.grounded, q.sections) == ((A, B, C), cim.PhaseShuntConnectionKind.Y, True, 1)
    assert q.voltage == pytest.approx(4.16)
    # bPerSection is written to 6 digits: 0.0346709 S x 4160^2 V^2
    assert q.total == pytest.approx(600, rel=1e-5)
    assert q.per_phase == pytest.approx({A: 200, B: 200, C: 200}, rel=1e-5)


def test_one_phase_at_nominal():
    q = get_shunt_reactive_power(_shunt("cap_c2"), "kVAr", sections="actual", voltage="nominal")
    assert (q.phases, q.voltage) == ((C,), pytest.approx(2400))
    assert q.per_phase == pytest.approx({C: 100}, rel=1e-5)


def test_one_phase_at_base_is_phase_to_neutral():
    # nomU 2400 V is across the unit; the base is 4160 / sqrt 3, read in the same form
    q = get_shunt_reactive_power(_shunt("cap_c2"), "kVAr", sections="actual", voltage="base")
    assert q.voltage == pytest.approx(4160 / 3 ** 0.5)
    assert q.total == pytest.approx(100 * (4160 / 3 ** 0.5 / 2400) ** 2, rel=1e-5)


def test_sections_multiply():
    shunt = _shunt("cap_c1")
    shunt.maximumSections, shunt.sections = 3, 0.0
    assert get_shunt_reactive_power(shunt, "kVAr", sections="maximum", voltage="nominal").total == pytest.approx(
        1800, rel=1e-5)
    assert get_shunt_reactive_power(shunt, sections="actual", voltage="nominal").total == 0.0


def test_unset_sections_raise():
    shunt = _shunt("cap_c1")
    shunt.normalSections = None
    with pytest.raises(ValueError, match="LinearShuntCompensator 'cap_c1': normalSections is unset"):
        get_shunt_reactive_power(shunt, sections="normal", voltage="nominal")


def test_conductance_raises():
    shunt = _shunt("cap_c1")
    shunt.gPerSection = cim.Conductance(1e-4)
    with pytest.raises(ValueError, match="gPerSection is not read"):
        get_shunt_reactive_power(shunt, sections="actual", voltage="nominal")


def test_per_phase_susceptance_raises():
    shunt = _shunt("cap_c2")
    shunt.ShuntCompensatorPhase[0].bPerSection = cim.Susceptance(0.01)
    with pytest.raises(ValueError, match="a per-phase bPerSection is not read"):
        get_shunt_reactive_power(shunt, sections="actual", voltage="nominal")


@pytest.mark.parametrize(("options", "message"), [({"sections": "all", "voltage": "nominal"}, "sections must be"),
                                                  ({"sections": "actual", "voltage": "rated"}, "voltage must be")])
def test_factors_are_checked(options, message):
    with pytest.raises(ValueError, match=message):
        get_shunt_reactive_power(_shunt("cap_c1"), **options)
