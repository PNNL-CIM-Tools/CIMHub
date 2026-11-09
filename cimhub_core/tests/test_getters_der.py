"""cimhub_core.getters.der: an inverter's or machine's p and q in a declared sign."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.der import get_der_output
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
