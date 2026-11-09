"""cimhub_core.getters.wire and get_asset_info_current_limits on an inline wire catalog (IEEE13_Assets' values,
as the DSS importer writes them).

Expected values are hand-computed from the atom text, not from the getter.
"""

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.current_limits import CurrentLimits, get_asset_info_current_limits
from cimhub_core.getters.wire import get_configuration_wires, get_wire_info

INCH = 0.0254
MILE = 1609.344

ATOM = """Profile = cim18v17
Object Feeder: mRID=fdr, name=fdr
Table OperationalLimitType: mRID, name, durationKind, isInfiniteDuration, direction
    olt_normal,    normal,    normal,    true,  absoluteValue
    olt_emergency, emergency, emergency, false, absoluteValue
Table OperationalLimitSet: mRID
    cn_limits
Table CurrentLimit: mRID, normalValue (A), OperationalLimitType, OperationalLimitSet
    cn_norm,  260.0, olt_normal,    cn_limits
    cn_emerg, 390.0, olt_emergency, cn_limits
Table OverheadWireInfo: mRID, name, rDC20 (ohm/mi), gmr (in), radius (in), ratedCurrent (A)
    wire_cu, CU_1/0, 0.607, 0.13356, 0.184, 100.0
Table ConcentricNeutralCableInfo: mRID, name, rAC25 (ohm/mi), gmr (in), radius (in), ratedCurrent (A), insulationThickness (in), diameterOverInsulation (in), diameterOverJacket (in), diameterOverNeutral (in), neutralStrandCount, neutralStrandRadius (in), neutralStrandGmr (in), neutralStrandRDC20 (ohm/mi), OperationalLimitSet
    cn_250, CN_250, 0.41, 0.2052, 0.2835, 260.0, 0.22, 1.06, 1.29, 1.29, 13, 0.03205, 0.02496, 14.8722, cn_limits
Table TapeShieldCableInfo: mRID, name, rAC25 (ohm/mi), gmr (in), radius (in), diameterOverJacket (in), diameterOverScreen (in), tapeThickness (in), tapeLap (percent)
    ts_1, TS_1/0, 0.97, 0.1332, 0.184, 1.06, 0.87, 0.005, 20.0
Object XYSpacing: mRID=spc, name=spc, isTemplate=true
Object WireConfiguration: mRID=wc, name=wc, numberOfPhases=1, WireSpacing=spc
Table WireSequenceConfiguration: mRID, WireConfiguration=wc, sequenceNumber, WireInfo
    wc_2, 2, wire_cu
    wc_1, 1, ts_1
"""


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture
def network(tmp_path):
    path = tmp_path / "wires.cimtbl"
    path.write_text(ATOM)
    return load_model(path)


def _wire(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)


def test_overhead_wire(network):
    values = get_wire_info(_wire(network, cim.OverheadWireInfo, "wire_cu"))
    assert values.kind is cim.OverheadWireInfo and values.cable is None
    assert (values.r_dc20, values.r_ac25) == (pytest.approx(0.607 / MILE), None)
    assert (values.gmr, values.radius) == (pytest.approx(0.13356 * INCH), pytest.approx(0.184 * INCH))
    assert values.rated_current == 100.0 and values.limits == CurrentLimits(None, None, None)


def test_concentric_neutral_cable_in_the_callers_units(network):
    values = get_wire_info(_wire(network, cim.ConcentricNeutralCableInfo, "cn_250"), "in", "ohm/mi")
    cable = values.cable
    assert values.r_ac25 == pytest.approx(0.41)
    assert (cable.neutral_strand_count, cable.neutral_strand_radius, cable.neutral_strand_gmr) == \
        (13, pytest.approx(0.03205), pytest.approx(0.02496))
    assert cable.neutral_strand_r_dc20 == pytest.approx(14.8722)
    assert (cable.diameter_over_neutral, cable.diameter_over_jacket, cable.tape_thickness) == \
        (pytest.approx(1.29), pytest.approx(1.29), None)
    assert values.limits == CurrentLimits(260.0, None, 390.0)


def test_tape_shield_cable(network):
    cable = get_wire_info(_wire(network, cim.TapeShieldCableInfo, "ts_1"), "in").cable
    assert (cable.diameter_over_screen, cable.tape_thickness, cable.tape_lap) == \
        (pytest.approx(0.87), pytest.approx(0.005), pytest.approx(20.0))
    assert cable.neutral_strand_count is None


def test_rated_current_that_disagrees_with_the_normal_limit_raises(network):
    cable = _wire(network, cim.ConcentricNeutralCableInfo, "cn_250")
    cable.ratedCurrent = cim.CurrentFlow(300.0)
    with pytest.raises(ValueError, match="ratedCurrent 300.0 disagrees with its normal limit 260.0"):
        get_wire_info(cable)


def test_unread_ac_resistance_raises(network):
    wire = _wire(network, cim.OverheadWireInfo, "wire_cu")
    wire.rAC50 = cim.ResistancePerLength(0.001)
    with pytest.raises(ValueError, match=r"\['rAC50'\] are set; only rAC25 is read"):
        get_wire_info(wire)


def test_other_wire_kind_raises():
    with pytest.raises(ValueError, match="is not one of"):
        get_wire_info(cim.WireInfo(mRID="w"))


def test_asset_info_limits_without_a_set(network):
    assert get_asset_info_current_limits(_wire(network, cim.OverheadWireInfo, "wire_cu")) == \
        CurrentLimits(None, None, None)


def test_configuration_wires_in_sequence_order(network):
    [configuration] = network.graph[cim.WireConfiguration].values()
    assert [(number, wire.mRID) for number, wire in get_configuration_wires(configuration)] == \
        [(1, "ts_1"), (2, "wire_cu")]


def test_configuration_repeated_sequence_number_raises(network):
    [configuration] = network.graph[cim.WireConfiguration].values()
    for sequence in configuration.WireSequence:
        sequence.sequenceNumber = 1
    with pytest.raises(ValueError, match="unset or repeated"):
        get_configuration_wires(configuration)
