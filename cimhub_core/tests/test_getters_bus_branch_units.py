"""Getters a bus-branch exporter (RAW) reads in pu or by limit type, on an inline atom with hand numbers.

z_base = 138 kV ** 2 / 100 MVA = 190.44 ohm, so 1.9044 ohm is 0.01 pu and 0.001 S is 0.19044 pu.
"""

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import BusBranchModel, load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.limits_by_type import get_limits_by_type
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_core.getters.shunt import ShuntAdmittance, get_shunt_admittance

ATOM = """Profile = cim18v17
Object BaseVoltage: mRID=bv_138kv, nominalVoltage (kV)=138
Object BasePower: mRID=bp, basePower (MVA)=100
Object Substation: mRID=sub, name=sub
Table OperationalLimitType: mRID, name, direction
    olt_rate1, RATE1, absoluteValue
    olt_rate2, RATE2, absoluteValue
Table TopologicalNode: mRID, name, busNumber, BaseVoltage, ConnectivityNodeContainer
    1, one, 1, bv_138kv, sub
    2, two, 2, bv_138kv, sub
Table SeriesCompensator: mRID, name, bus1, bus2, r (ohm), x (ohm), BaseVoltage
    sc, sc, 1, 2, 1.9044, -9.522, bv_138kv
Table LinearShuntCompensator: mRID, name, bus, gPerSection (S), bPerSection (S), nomU (kV), sections, maximumSections, BaseVoltage
    cap,    cap,    1, 0.0005, 0.001, 138, 2, 2, bv_138kv
    cap_nb, cap_nb, 2,       , 0.001, 138, 1, 1, bv_138kv
Table OperationalLimitSet: mRID, Terminal
    sc_ratings, sc_T1
Table ApparentPowerLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (MVA)
"""


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(tmp_path, limit_rows=()):
    path = tmp_path / "atom.cimtbl"
    path.write_text(ATOM + "".join(f"    {row}\n" for row in limit_rows))
    return load_model(path, model_cls=BusBranchModel)


def _get(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)


def test_series_compensator_in_pu(tmp_path):
    network = _network(tmp_path)
    data = get_series_compensator(_get(network, cim.SeriesCompensator, "sc"), "pu", base_power=network.base_power)
    assert (data.r, data.x) == (pytest.approx(0.01), pytest.approx(-0.05))
    assert get_series_compensator(_get(network, cim.SeriesCompensator, "sc")).r == pytest.approx(1.9044)


def test_series_compensator_unit_is_checked(tmp_path):
    with pytest.raises(ValueError, match="unit must be one of"):
        get_series_compensator(_get(_network(tmp_path), cim.SeriesCompensator, "sc"), "percent")


def test_shunt_admittance_of_the_sections_in_service(tmp_path):
    network = _network(tmp_path)
    shunt = _get(network, cim.LinearShuntCompensator, "cap")
    assert get_shunt_admittance(shunt, sections="actual") == ShuntAdmittance(
        pytest.approx(0.001), pytest.approx(0.002), 2)
    in_pu = get_shunt_admittance(shunt, "pu", sections="actual", base_power=network.base_power)
    assert (in_pu.g, in_pu.b) == (pytest.approx(2 * 0.09522), pytest.approx(2 * 0.19044))


def test_shunt_admittance_unset_g_is_zero(tmp_path):
    shunt = _get(_network(tmp_path), cim.LinearShuntCompensator, "cap_nb")
    assert get_shunt_admittance(shunt, sections="maximum").g == 0.0


def test_limits_by_type(tmp_path):
    network = _network(tmp_path, ["sc_rate1, sc_ratings, olt_rate1, 250", "sc_rate2, sc_ratings, olt_rate2, 300"])
    limits = get_limits_by_type(_get(network, cim.SeriesCompensator, "sc"), cim.ApparentPowerLimit, "MVA")
    assert {limit_type.mRID: value for limit_type, value in limits.items()} == {
        "olt_rate1": pytest.approx(250.0), "olt_rate2": pytest.approx(300.0)}
    assert get_limits_by_type(_get(network, cim.SeriesCompensator, "sc"), cim.CurrentLimit, "A") == {}


def test_limits_of_one_type_that_disagree_raise(tmp_path):
    network = _network(tmp_path, ["a, sc_ratings, olt_rate1, 250", "b, sc_ratings, olt_rate1, 260"])
    with pytest.raises(ValueError, match="SeriesCompensator 'sc': olt_rate1 ApparentPowerLimit limits disagree"):
        get_limits_by_type(_get(network, cim.SeriesCompensator, "sc"), cim.ApparentPowerLimit, "MVA")
