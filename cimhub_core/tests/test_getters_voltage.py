"""cimhub_core.getters.voltage on an inline bus-branch atom (hand numbers)."""

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import BusBranchModel, load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.voltage import NodeVoltage, VoltageLimits, get_node_voltage, get_voltage_limits

# two 138 kV buses, each with a busbar; bus 1 has a solved voltage and limits, bus 2 neither
ATOM = """Profile = cim18v17
Object BaseVoltage: mRID=bv_138kv, nominalVoltage (kV)=138
Object Substation: mRID=sub, name=sub
Table OperationalLimitType: mRID, name, durationKind, isInfiniteDuration, direction
    olt_normal_high,    normal high,    normal,    true,  high
    olt_normal_low,     normal low,     normal,    true,  low
    olt_emergency_high, emergency high, emergency, false, high
    olt_short_high,     short high,     shortTerm, false, high
Table TopologicalNode: mRID, name, busNumber, BaseVoltage, ConnectivityNodeContainer
    1, one, 1, bv_138kv, sub
    2, two, 2, bv_138kv, sub
Table BusbarSection: mRID, name, bus, BaseVoltage, EquipmentContainer
    bb_1, one, 1, bv_138kv, sub
    bb_2, two, 2, bv_138kv, sub
Table SvVoltage: identifier, TopologicalNode, v (kV), angle (deg)
    1_sv, 1, 144.9, -4.5
Table OperationalLimitSet: mRID, Terminal
    bb_1_limits, bb_1_T1
Table VoltageLimit: mRID, OperationalLimitSet, OperationalLimitType, normalValue (kV)
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


def test_node_voltage(tmp_path):
    node = _get(_network(tmp_path), cim.TopologicalNode, "1")
    assert get_node_voltage(node, "kV") == NodeVoltage(pytest.approx(144.9), pytest.approx(-4.5))
    assert get_node_voltage(node).v == pytest.approx(144900.0)


def test_no_node_voltage_is_none(tmp_path):
    assert get_node_voltage(_get(_network(tmp_path), cim.TopologicalNode, "2")) is None


def test_voltage_limits_by_kind(tmp_path):
    network = _network(tmp_path, ["bb_1_nvhi, bb_1_limits, olt_normal_high, 151.8",
                                  "bb_1_nvlo, bb_1_limits, olt_normal_low, 124.2",
                                  "bb_1_evhi, bb_1_limits, olt_emergency_high, 155.25"])
    limits = get_voltage_limits(_get(network, cim.BusbarSection, "bb_1"), "kV")
    assert limits == VoltageLimits(pytest.approx(151.8), pytest.approx(124.2), pytest.approx(155.25), None)


def test_no_voltage_limits_is_all_none(tmp_path):
    assert get_voltage_limits(_get(_network(tmp_path), cim.BusbarSection, "bb_2")) == VoltageLimits(None, None, None,
                                                                                                    None)


def test_voltage_limits_that_disagree_raise(tmp_path):
    network = _network(tmp_path, ["a, bb_1_limits, olt_normal_high, 151.8", "b, bb_1_limits, olt_normal_high, 150"])
    with pytest.raises(ValueError, match="BusbarSection 'bb_1': normal_high voltage limits disagree"):
        get_voltage_limits(_get(network, cim.BusbarSection, "bb_1"))


def test_a_short_term_voltage_limit_raises(tmp_path):
    network = _network(tmp_path, ["a, bb_1_limits, olt_short_high, 151.8"])
    with pytest.raises(ValueError, match="olt_short_high.*not a normal or emergency high or low limit"):
        get_voltage_limits(_get(network, cim.BusbarSection, "bb_1"))
