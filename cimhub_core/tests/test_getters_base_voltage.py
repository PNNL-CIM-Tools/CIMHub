"""cimhub_core.getters.base_voltage on the core shapes."""

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import BusBranchModel, load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.base_voltage import get_base_voltage

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _shape(name, **kwargs):
    return load_model(SHAPES / f"{name}.cimtbl", **kwargs)


def _get(network, cls, mrid):
    return next(obj for obj in network.graph[cls].values() if obj.mRID == mrid)



def test_base_voltage_line_to_line_and_line_to_neutral():
    network = _shape("line_by_impedance")
    line = _get(network, cim.ACLineSegment, "ln_l1")
    assert get_base_voltage(line, "kV", form="LL") == pytest.approx(4.16)
    assert get_base_voltage(line, "V", form="LN") == pytest.approx(4160 / math.sqrt(3))


def test_base_voltage_of_a_topological_node():
    network = _shape("line_bus_branch", model_cls=BusBranchModel)
    bus = _get(network, cim.TopologicalNode, "bus_1")
    assert get_base_voltage(bus, "kV", form="LL") == pytest.approx(115)
    assert get_base_voltage(bus, "kV", form="LN") == pytest.approx(115 / math.sqrt(3))


def _atom(tmp_path, body):
    path = tmp_path / "atom.cimtbl"
    path.write_text("""Profile = cim18v17
Table BaseVoltage: mRID, nominalVoltage (kV)
    bv_12p47kv, 12.47
    bv_4p16kv,  4.16
Object Feeder: mRID=fdr, name=fdr
Object Substation: mRID=sub, name=sub
Object VoltageLevel: mRID=vl_12p47kv, name=12.47 kV, Substation=sub, BaseVoltage=bv_12p47kv
""" + body)
    return load_model(path)


def test_connectivity_node_outside_a_voltage_level_has_its_own(tmp_path):
    network = _atom(tmp_path, """Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer
    n1, n1, bv_4p16kv, fdr
""")
    assert get_base_voltage(_get(network, cim.ConnectivityNode, "n1"), "kV", form="LL") == pytest.approx(4.16)


def test_voltage_level_overrides_its_contents(tmp_path):
    # CIM: inside a VoltageLevel, use VoltageLevel.BaseVoltage and disregard the node's or equipment's own
    network = _atom(tmp_path, """Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer
    n1, n1, bv_4p16kv, vl_12p47kv
    n2, n2, bv_4p16kv, vl_12p47kv
Object ACLineSegment: mRID=ln_x, name=x, node1=n1, node2=n2, r (ohm)=1, x (ohm)=2, BaseVoltage=bv_4p16kv, EquipmentContainer=vl_12p47kv
""")
    assert get_base_voltage(_get(network, cim.ConnectivityNode, "n1"), "kV", form="LL") == pytest.approx(12.47)
    assert get_base_voltage(_get(network, cim.ACLineSegment, "ln_x"), "kV", form="LL") == pytest.approx(12.47)


def test_voltage_level_without_a_base_voltage_raises(tmp_path):
    network = _atom(tmp_path, """Object VoltageLevel: mRID=vl_bare, name=bare, Substation=sub
Table ConnectivityNode: mRID, name, BaseVoltage, ConnectivityNodeContainer
    n1, n1, bv_4p16kv, vl_bare
""")
    with pytest.raises(ValueError, match="VoltageLevel 'vl_bare': has no BaseVoltage"):
        get_base_voltage(_get(network, cim.ConnectivityNode, "n1"), "kV", form="LL")


def test_shape_node_without_a_base_voltage_raises():
    # line_by_impedance puts BaseVoltage on equipment only (the DSS importer writes it on nodes too)
    network = _shape("line_by_impedance")
    with pytest.raises(ValueError, match="ConnectivityNode 'n1': has no BaseVoltage"):
        get_base_voltage(_get(network, cim.ConnectivityNode, "n1"), "kV", form="LL")


def test_transformer_base_voltage_is_on_its_ends():
    network = _shape("transformer_by_ends")
    assert get_base_voltage(_get(network, cim.PowerTransformerEnd, "xf_sub_2"), "kV", form="LL") == pytest.approx(4.16)
    with pytest.raises(ValueError, match="PowerTransformer 'xf_sub': has no BaseVoltage"):
        get_base_voltage(_get(network, cim.PowerTransformer, "xf_sub"), "kV", form="LL")


def test_split_phase_line_to_neutral_raises():
    network = _shape("load")
    load = _get(network, cim.EnergyConsumer, "ld_s1")
    assert get_base_voltage(load, "V", form="LL") == pytest.approx(240)
    with pytest.raises(ValueError, match="EnergyConsumer 'ld_s1': a split-phase leg voltage is not LL / sqrt"):
        get_base_voltage(load, "V", form="LN")


def test_unknown_form_raises():
    network = _shape("line_by_impedance")
    with pytest.raises(ValueError, match="form must be one of"):
        get_base_voltage(_get(network, cim.ACLineSegment, "ln_l1"), "kV", form="LG")
