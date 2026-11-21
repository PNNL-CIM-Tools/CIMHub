"""cimhub_core.getters.load: per-phase p and q (children, else the total split) and the voltage response."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.load import LoadResponse, get_load_response, get_phase_loads
from cimhub_core.getters.phase_power import PhasePower

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"
A, B, C, S1, S2 = (cim.SinglePhaseKind(token) for token in ("A", "B", "C", "s1", "s2"))


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _load(mrid):
    network = load_model(SHAPES / "load.cimtbl")
    return next(obj for obj in network.graph[cim.EnergyConsumer].values() if obj.mRID == mrid)


def _phase(phase, p, q):
    return cim.EnergyConsumerPhase(mRID=f"ph_{phase.value}", phase=phase, p=cim.ActivePower(p, "kW"),
                                   q=cim.ReactivePower(q, "kVAr"))


@pytest.mark.parametrize(("mrid", "phases", "share"), [
    ("ld_y1", (A, B, C), (385, 220)),
    ("ld_d1", (B, C), (85, 40)),
    ("ld_c1", (C,), (170, 80)),  # its EnergyConsumerPhase C holds no values
    ("ld_s1", (S1, S2), (2.5, 0.5)),
])
def test_total_split_evenly(mrid, phases, share):
    loads = get_phase_loads(_load(mrid), "kW", "kVAr")
    assert loads.split
    assert loads.phases == phases
    assert loads.per_phase == {phase: pytest.approx(PhasePower(*share)) for phase in phases}


def test_unbalanced_shape_rows():
    loads = get_phase_loads(_load("ld_u1"), "kW", "kVAr")
    assert not loads.split
    assert loads.per_phase == {A: pytest.approx(PhasePower(17, 10)), B: pytest.approx(PhasePower(66, 38)),
                               C: pytest.approx(PhasePower(117, 68))}


def test_240_volt_part_is_delta_across_the_legs():
    loads = get_phase_loads(_load("ld_s12"), "kW", "kVAr")
    assert (loads.connection, loads.phases, loads.total) == (cim.PhaseShuntConnectionKind.D, (S1, S2),
                                                             pytest.approx(PhasePower(4, 1.5)))


def test_connection_and_total():
    loads = get_phase_loads(_load("ld_d1"), "kW", "kVAr")
    assert (loads.connection, loads.grounded, loads.total) == (cim.PhaseShuntConnectionKind.D, False,
                                                               pytest.approx(PhasePower(170, 80)))


def test_phase_values_when_every_child_has_them():
    load = _load("ld_y1")
    load.EnergyConsumerPhase += [_phase(A, 400, 200), _phase(B, 385, 220), _phase(C, 370, 240)]
    loads = get_phase_loads(load, "kW", "kVAr")
    assert not loads.split
    assert loads.per_phase == {A: pytest.approx(PhasePower(400, 200)), B: pytest.approx(PhasePower(385, 220)),
                               C: pytest.approx(PhasePower(370, 240))}


def test_phase_values_must_sum_to_the_total():
    load = _load("ld_y1")
    load.EnergyConsumerPhase += [_phase(A, 400, 200), _phase(B, 385, 220), _phase(C, 380, 240)]
    with pytest.raises(ValueError, match="EnergyConsumer 'ld_y1': its phases' p sum to 1165"):
        get_phase_loads(load, "kW", "kVAr")


def test_some_children_without_values_raise():
    load = _load("ld_y1")
    load.EnergyConsumerPhase += [_phase(A, 400, 200), cim.EnergyConsumerPhase(mRID="ph_b", phase=B)]
    with pytest.raises(ValueError, match="some of its phases have p and q and some do not"):
        get_phase_loads(load)


def test_children_on_other_conductors_raise():
    load = _load("ld_d1")
    load.EnergyConsumerPhase[:] = [_phase(A, 85, 40), _phase(B, 85, 40)]
    with pytest.raises(ValueError, match=r"its phases \['A', 'B'\] are not its conductors \['B', 'C'\]"):
        get_phase_loads(load)


def test_unset_p_raises():
    load = _load("ld_y1")
    load.p = None
    with pytest.raises(ValueError, match="EnergyConsumer 'ld_y1': p is unset"):
        get_phase_loads(load)


def test_zip_response_as_stored():
    assert get_load_response(_load("ld_c1")) == LoadResponse(False, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, None, None)


def test_exponential_response():
    assert get_load_response(_load("ld_s1")) == LoadResponse(True, *[None] * 6, 0.8, 3.0)


def test_zip_fractions_must_sum_to_one():
    load = _load("ld_y1")
    load.LoadResponse.pConstantImpedance = 0.5
    with pytest.raises(ValueError, match="the p fractions .* do not sum to 1"):
        get_load_response(load)


def test_no_response_raises():
    load = _load("ld_y1")
    load.LoadResponse = None
    with pytest.raises(ValueError, match="EnergyConsumer 'ld_y1': has no LoadResponse"):
        get_load_response(load)
