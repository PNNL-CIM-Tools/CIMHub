"""A CIM-first deck (no DSS original): several Feeders of one Substation are one circuit (E10), and a single-phase
transformer by PowerTransformerEnds alone takes its coil kV from ratedU (get_transformer_model), a GIS's can by two
ends and a tank percentImpedance is a DSS Transformer (BY_TANK_IMPEDANCE), and a wind turbine behind an inverter is a
Generator."""
from __future__ import annotations

import math
from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck

ATOM = Path(__file__).parent / "atoms" / "circuit" / "substation.cimtbl"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def test_feeders_of_one_substation_are_one_circuit_that_solves(tmp_path):
    written = tmp_path / "substation.dss"
    cim_to_dss(load_model(ATOM), written, name_source="mrid")
    compile_deck(written)
    dss.Text.Command("Solve")
    assert (dss.Circuit.Name(), dss.Solution.Converged()) == ("sub_1", True)
    for transformer in ("xf_1", "xf_2"):
        dss.Transformers.Name(transformer)
        kvs = []
        for winding in (1, 2):
            dss.Transformers.Wdg(winding)
            kvs.append(dss.Transformers.kV())
        assert kvs == pytest.approx([12.47 / math.sqrt(3), 0.24]), transformer
    # the banks: wye-wye 120 V; the wye-delta and open-delta lighting legs 120 V with c the 208 V power leg
    expected = {"house1": [119.3] * 2, "house2": [119.3] * 2, "house3": [119.4] * 2, "shop": [273.4] * 3,
                "bank5": [119.4] * 3, "bank6": [119.5, 119.5, 206.6], "bank7": [119.4, 119.4, 207.0]}
    for bus, volts in expected.items():
        dss.Circuit.SetActiveBus(bus)
        assert dss.Bus.VMagAngle()[::2] == pytest.approx(volts, abs=0.5), bus
    dss.Circuit.SetActiveElement("Generator.der_w1")
    assert sum(dss.CktElement.Powers()[0:6:2]) == pytest.approx(-10.0)  # 10 kW into the bus
    # V7: the recloser and fuse have no settings in CIM, so they are disabled and do not trip on the default curves
    assert dss.Solution.ControlMode() == 0  # static: controls act in this solve
    dss.Circuit.SetActiveBus("fload")
    assert min(dss.Bus.puVmagAngle()[::2]) > 0.95
    for control in ("Recloser.sw_r1", "Fuse.sw_f1"):
        dss.Circuit.SetActiveElement(control)
        assert not dss.CktElement.Enabled(), control


def test_wind_unit_is_a_generator_at_its_output():
    model = DssExporter().to_model(load_model(ATOM), name_source="mrid")
    [generator] = model.list_by_class(schema.Generator)
    assert (generator.name, generator.bus1, generator.kW, generator.kvar, generator.kVA, generator.kv) == (
        "der_w1", "head.1.2.3", 10.0, 0.0, 10.0, 12.47)
    assert not model.list_by_class(schema.Pvsystem)


def test_feeders_of_two_substations_raise():
    network = load_model(ATOM)
    other = cim.Substation(mRID="sub_2", name="sub2")
    network.add_to_graph(other)
    feeder = next(feeder for feeder in network.graph[cim.Feeder].values() if feeder.mRID == "fdr_2")
    feeder.NormalEnergizingSubstation = other
    with pytest.raises(ValueError, match="the model has 2 Feeders .* one Feeder, or Feeders of one "
                                         "NormalEnergizingSubstation"):
        DssExporter().to_model(network, name_source="mrid")


def test_empty_feeders_of_another_substation_are_not_counted():
    """H2: a frame model declares its area's every Feeder; a deck holds only the feeders whose equipment it has."""
    network = load_model(ATOM)
    other = cim.Substation(mRID="sub_2", name="sub2")
    network.add_to_graph(other)
    network.add_to_graph(cim.Feeder(mRID="fdr_elsewhere", NormalEnergizingSubstation=other))
    [options] = DssExporter().to_model(network, name_source="mrid").list_by_class(schema.Options)
    assert options.circuit == "sub_1"


def _transformer(model, name):
    return next(record for record in model.list_by_class(schema.Transformer) if record.name == name)


def test_tank_impedance_center_tap_is_written_by_hopkinson_s_split():
    """t3: 25 kVA, %Z 2.3, 124 W: R = 0.496 %, X = sqrt(2.3^2 - R^2); halves at the can's kVA."""
    transformer = _transformer(DssExporter().to_model(load_model(ATOM), name_source="mrid"), "xf_3")
    x = math.sqrt(2.3 ** 2 - 0.496 ** 2)
    assert (transformer.buses, transformer.kVs, transformer.kVAs) == (
        ["head.2.0", "house3.1.0", "house3.0.2"], pytest.approx([12.47 / math.sqrt(3), 0.12, 0.12]), [25.0] * 3)
    assert transformer.pct_Rs == pytest.approx([0.248, 0.496, 0.496])
    assert (transformer.XHL, transformer.XHT, transformer.XLT) == pytest.approx((1.2 * x, 1.2 * x, 0.8 * x))


def test_tank_impedance_three_phase_can_halves_r_over_its_windings():
    """t4: 300 kVA, %Z 4.5, 3300 W: R = 1.1 %, %Rs 0.55 each, XHL = sqrt(4.5^2 - 1.1^2)."""
    transformer = _transformer(DssExporter().to_model(load_model(ATOM), name_source="mrid"), "xf_4")
    assert (transformer.phases, transformer.kVs, transformer.kVAs) == (3, [12.47, 0.48], [300.0, 300.0])
    assert transformer.pct_Rs == pytest.approx([0.55, 0.55])
    assert transformer.XHL == pytest.approx(math.sqrt(4.5 ** 2 - 1.1 ** 2))


def test_bank_cans_are_one_transformer_each_in_tank_order():
    """t7, open wye - open delta 2 x 50 kVA: L on A is the a-N-b lighting leg, T on B the b-c power leg. L's numbers
    are the CIMTBL-Models bank_oyod template's (R 1.08 %, X 1.6833 %, Hopkinson's split)."""
    model = DssExporter().to_model(load_model(ATOM), name_source="mrid")
    lighting, power = _transformer(model, "xf_7_l"), _transformer(model, "xf_7_t")
    assert (lighting.buses, lighting.kVs, lighting.kVAs) == (
        ["head.1.0", "bank7.1.0", "bank7.0.2"], pytest.approx([12.47 / math.sqrt(3), 0.12, 0.12]), [50.0] * 3)
    assert lighting.pct_Rs == pytest.approx([0.54, 1.08, 1.08])
    assert (lighting.XHL, lighting.XHT, lighting.XLT) == pytest.approx((2.02, 2.02, 1.3467), abs=1e-4)
    assert (power.buses, power.kVs, power.kVAs) == (["head.2.0", "bank7.2.3"], pytest.approx([12.47 / math.sqrt(3),
                                                                                               0.24]), [50.0] * 2)
    assert {record.name for record in model.list_by_class(schema.Transformer)} >= {"xf_6_a", "xf_6_b", "xf_6_c"}


def _bank6_primary(grounded):
    network = load_model(ATOM)
    end = next(end for end in network.graph[cim.PowerTransformerEnd].values() if end.mRID == "xf_6_1")
    end.grounded = grounded
    return network


def test_floating_wye_bank_shares_a_neutral_on_node_4_and_solves(tmp_path):
    """T6 on the coil path: bank 6's wye primary ungrounded, its three cans' neutrals on head.4, which floats; the
    engine's default antifloat solves it, and the delta's voltages stay those of the grounded bank."""
    network = _bank6_primary(False)
    model = DssExporter().to_model(network, name_source="mrid")
    assert [_transformer(model, f"xf_6_{can}").buses[0] for can in "abc"] == ["head.1.4", "head.2.4", "head.3.4"]
    written = tmp_path / "substation.dss"
    cim_to_dss(network, written, name_source="mrid")
    compile_deck(written)
    dss.Text.Command("Solve")
    assert dss.Solution.Converged()
    dss.Circuit.SetActiveBus("bank6")
    assert dss.Bus.VMagAngle()[::2] == pytest.approx([119.5, 119.5, 206.6], abs=0.5)
    dss.Circuit.SetActiveBus("head")
    assert dss.Bus.Nodes()[-1] == 4 and dss.Bus.VMagAngle()[-2] < 0.01 * 12470 / math.sqrt(3)


def test_coil_neutral_with_grounded_unset_raises():
    with pytest.raises(ValueError, match="a coil neutral with grounded unset"):
        DssExporter().to_model(_bank6_primary(None), name_source="mrid")
