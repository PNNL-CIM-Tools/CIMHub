"""The exporter's framework (EXPORT_MAPPING.md S6a): names, bus references, options, the circuit source, and
equipment no module exports yet."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_opendss.exporter.cim_to_dss import EXPORT_ORDER, DssExporter
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.exporter.slots import check_slots
from cimhub_opendss.schema import opendss_schema as schema

ATOMS = Path(__file__).parent / "atoms"
A, B, C, N, S1, S2 = (cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C, cim.SinglePhaseKind.N,
                      cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2)


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(atom: str):
    path = ATOMS / atom
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def test_names_are_sanitized_for_dss():
    names = Names("name")
    assert names.name(cim.EnergyConsumer(mRID="ld_1", name="Load 1 (east)"), "Load") == "Load_1_east_"
    assert names.bus(cim.ConnectivityNode(mRID="cn_1", name="7674067.786")) == "7674067_786"


def test_one_object_may_be_named_again():
    names, node = Names("mrid"), cim.ConnectivityNode(mRID="650")
    assert names.bus(node) == names.bus(node) == "650"


def test_two_objects_on_one_sanitized_name_raise():
    names = Names("name")
    names.name(cim.EnergyConsumer(mRID="ld_a", name="Load 1"), "Load")
    with pytest.raises(ValueError, match="'ld_b' and 'ld_a' are both named 'load_1' in DSS Load"):
        names.name(cim.EnergyConsumer(mRID="ld_b", name="load_1"), "Load")


def test_namespaces_are_separate():
    names = Names("name")
    names.name(cim.ACLineSegment(mRID="ln_x", name="x"), "Line")
    assert names.name(cim.EnergyConsumer(mRID="ld_x", name="x"), "Load") == "x"


def test_per_phase_suffix_is_its_own_name():
    names, load = Names("name"), cim.EnergyConsumer(mRID="ld_x", name="x")
    assert [names.name(load, "Load", suffix=f"_{p}") for p in "ab"] == ["x_a", "x_b"]


def test_bus_ref_writes_phase_conductors_and_never_bare():
    names, node = Names("mrid"), cim.ConnectivityNode(mRID="650")
    assert bus_ref(node, (A, B, C), names) == "650.1.2.3"
    assert bus_ref(node, (C, B), names) == "650.3.2"
    assert bus_ref(node, (S1, S2), names) == "650.1.2"
    assert bus_ref(node, (N, S2), names, neutral=0) == "650.0.2"
    with pytest.raises(ValueError, match="have no DSS node here"):
        bus_ref(node, (A, N), names)


@pytest.mark.parametrize("module", EXPORT_ORDER, ids=lambda module: module.__name__.rsplit(".", 1)[-1])
def test_slots_are_complete(module):
    for native_class, slots in module.SLOTS.items():
        check_slots(slots, native_class)


def test_options_carry_circuit_frequency_and_voltage_bases():
    model = DssExporter().to_model(_network("vsource/mvasc.dss"), name_source="name")
    [options] = model.list_by_class(schema.Options)
    assert (options.circuit, options.defaultbasefreq, options.voltagebases) == ("IEEE13Nodeckt", 60.0, [115.0])


def test_unexported_equipment_raises():
    with pytest.raises(ValueError, match=r"no DSS export yet for \{'EnergyConsumer': 9"):
        DssExporter().to_model(_network("load/loads.dss"))


def test_several_sources_need_the_circuit_source_named():
    network = _network("vsource/mvasc.dss")
    [bus] = network.graph[cim.ConnectivityNode].values()
    [base] = network.graph[cim.BaseVoltage].values()
    second = cim.EnergySource(mRID="src_two", name="two", nominalVoltage=cim.Voltage(115, "kV"),
                              voltageMagnitude=cim.Voltage(115, "kV"), r=cim.Resistance(1), x=cim.Reactance(2),
                              r0=cim.Resistance(1), x0=cim.Reactance(2), BaseVoltage=base)
    terminal = cim.Terminal(mRID="src_two_t1", ConductingEquipment=second, ConnectivityNode=bus, sequenceNumber=1)
    second.Terminals.append(terminal)
    network.add_to_graph(second)
    network.add_to_graph(terminal)
    model = DssExporter().to_model(network, name_source="name")
    assert sorted(record.name for record in model.list_by_class(schema.Vsource)) == ["source", "two"]
    # "two" as the circuit is Vsource.source, so the other one's own name `source` collides with it
    with pytest.raises(ValueError, match="both named 'source' in DSS Vsource"):
        DssExporter().to_model(network, name_source="name", circuit_source="two")
    model = DssExporter().to_model(network, name_source="mrid", circuit_source="src_two")
    assert sorted(record.name for record in model.list_by_class(schema.Vsource)) == ["source", "src_source"]
    with pytest.raises(ValueError, match="2 EnergySources and 0 exported as 'nope'"):
        DssExporter().to_model(network, name_source="name", circuit_source="nope")
