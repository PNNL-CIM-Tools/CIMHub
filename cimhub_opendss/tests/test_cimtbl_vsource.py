"""Atom tests: OpenDSS Vsource -> vsource.cimtbl -> cim18v17, with the engine as the impedance oracle."""

from __future__ import annotations

import math
from pathlib import Path

import cimtables
import opendssdirect as dss
import pytest
from cimprofiles.units import units

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimtopology.core import walk
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer.cimtbl.vsource import (FIELDS, NATIVE_CLASS, Thevenin, kvasc_from_isc, map_vsource,
                                                   thevenin, thevenin_from_short_circuit, with_defaults)
from cimhub_opendss.importer.topology import dss_network
from cimhub_opendss.schema import opendss_schema as schema

from conftest import ENGINE_DECKS, deck

ATOMS = Path(__file__).parent / "atoms" / "vsource"
CASES = ["mvasc", "ohms", "isc", "defaults", "single_phase"]


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _map(case: str):
    native = DssReader(ATOMS / f"{case}.dss").read_all()
    return map_vsource(native, walk(dss_network(native)), "sub_atom")


def _source(**slots):
    return schema.Vsource(name="s", **slots)


def _engine_thevenin(command: str, name: str = "source") -> Thevenin:
    dss.Text.Command("Clear")
    dss.Text.Command(command)
    return _active_thevenin(name)


def _active_thevenin(name: str) -> Thevenin:
    dss.Circuit.SetActiveElement(f"Vsource.{name}")
    return Thevenin(*(float(dss.Properties.Value(slot)) for slot in ("R1", "X1", "R0", "X0")))


def _ohms(source, group: str) -> Thevenin:
    """``thevenin`` in ohms, as the engine gives it (the mapper's values keep their own unit)."""
    impedance, unit = thevenin(source, group)
    return Thevenin(*(units.Quantity(value, unit).to("ohm").magnitude for value in impedance))


def test_classification_is_complete():
    check_fields(FIELDS, NATIVE_CLASS)


@pytest.mark.parametrize("command, args", [
    ("New Circuit.x basekv=115 MVAsc3=20000 MVAsc1=21000", (115.0, 20000.0, 21000.0, 4.0, 3.0)),
    ("New Circuit.x basekv=12.47", (12.47, 2000.0, 2100.0, 4.0, 3.0)),
    ("New Circuit.x basekv=12.47 MVAsc3=200000", (12.47, 200000.0, 2100.0, 4.0, 3.0)),
    ("New Circuit.x basekv=7.2 phases=1 MVAsc3=100 MVAsc1=90 x1r1=6 x0r0=2", (7.2, 100.0, 90.0, 6.0, 2.0)),
])
def test_thevenin_from_short_circuit_matches_the_engine(command, args):
    assert thevenin_from_short_circuit(*args) == pytest.approx(_engine_thevenin(command), rel=1e-12)


@pytest.mark.parametrize("phases, factor", [(3, math.sqrt(3)), (1, 1.0)])
def test_kvasc_from_isc(phases, factor):
    assert kvasc_from_isc(69.0, 1000.0, 1100.0, phases) == pytest.approx((math.sqrt(3) * 69e3, factor * 69 * 1100))


def test_negative_discriminant_raises():
    with pytest.raises(ValueError, match="gives no real R0"):
        thevenin_from_short_circuit(12.47, 2000.0, 1e9, 4.0, 3.0)


def test_isc_matches_the_engine():
    source, group, _ = with_defaults(_source(basekv=69.0, Isc3=1e6, Isc1=1.1e6))
    engine = _engine_thevenin("New Circuit.x basekv=69 Isc3=1000000 Isc1=1100000")
    assert thevenin(source, group)[1] == "kohm"
    assert _ohms(source, group) == pytest.approx(engine, rel=1e-12)


@pytest.mark.parametrize("slots, message", [
    ({"R1": 0.1, "X1": 1.0, "R0": 0.1, "X0": 1.0, "MVAsc3": 100.0}, "sets the ohms and MVAsc impedance groups"),
    ({"MVAsc3": 100.0, "Isc1": 1000.0}, "sets the MVAsc and Isc impedance groups"),
    ({"R1": 0.1, "X1": 1.0}, "sets only part of R1, X1, R0, X0"),
    ({"puZ1": [0.1, 1.0]}, "puZ1 not mapped yet"),
    ({"bus2": "b.0"}, "bus2 not mapped yet"),
])
def test_impedance_group_rules(slots, message):
    with pytest.raises(ValueError, match=message):
        with_defaults(_source(**slots))


def test_ohms_take_no_impedance_defaults():
    source, group, comment = with_defaults(_source(basekv=4.16, R1=0.0, X1=0.0001, R0=0.0, X0=0.0001))
    assert group == "ohms" and source.MVAsc3 is None and source.x1r1 is None
    assert comment == "defaulted: bus1=sourcebus, pu=1.0, angle=0.0, phases=3"


@pytest.mark.parametrize("bus1, phases, message", [
    ("b.1.3.2", 3, "phases=3 on b.1.3.2"), ("b.1.2", 1, "phases=1 on b.1.2"), ("b", 2, "phases=2 on b"),
])
def test_unmapped_terminals_raise(bus1, phases, message):
    native = type("Native", (), {"list_by_class": staticmethod(
        lambda cls: [_source(bus1=bus1, phases=phases, basekv=7.2)])})()
    with pytest.raises(ValueError, match=message):
        map_vsource(native, {}, "sub_atom")


@pytest.mark.parametrize("case", CASES)
def test_matches_golden(case):
    assert_matches_golden(_map(case), ATOMS / f"{case}.cimtbl")


@pytest.mark.parametrize("case", CASES)
def test_binds_under_cim18v17(case):
    network = cimtbl_to_cim(atom_documents(_map(case)), network=cimtables.load_model(ATOMS / "prereq.cimtbl"))
    [source] = network.graph[network.cim.EnergySource].values()
    [terminal] = source.Terminals
    assert terminal.ConnectivityNode is not None and source.BaseVoltage is not None
    assert source.EquipmentContainer.mRID == "sub_atom"


def test_mvasc_values():
    network = cimtbl_to_cim(atom_documents(_map("mvasc")), network=cimtables.load_model(ATOMS / "prereq.cimtbl"))
    [source] = network.graph[network.cim.EnergySource].values()
    assert float(source.voltageAngle.to("deg")) == pytest.approx(30.0)
    assert float(source.nominalVoltage.to("kV")) == 115.0
    assert float(source.r.to("ohm")) == pytest.approx(0.160376682055275)
    assert float(source.x0.to("ohm")) == pytest.approx(0.538810749037007)


def test_isc_values_bind_in_ohms():
    """The Isc source's kohm header binds to the engine's ohms."""
    network = cimtbl_to_cim(atom_documents(_map("isc")), network=cimtables.load_model(ATOMS / "prereq.cimtbl"))
    [source] = network.graph[network.cim.EnergySource].values()
    engine = _engine_thevenin("New Circuit.x basekv=69 Isc3=1000000 Isc1=1100000")
    ours = Thevenin(*(float(getattr(source, slot).to("ohm")) for slot in ("r", "x", "r0", "x0")))
    assert ours == pytest.approx(engine, rel=1e-12)


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_thevenin_matches_the_engine(relative):
    path = deck(relative)
    sources = DssReader(path).read_all().list_by_class(NATIVE_CLASS)
    dss.Text.Command("Clear")
    dss.Text.Command(f"Compile [{path.resolve()}]")
    for original in sources:
        source, group, _ = with_defaults(original)
        assert _ohms(source, group) == pytest.approx(_active_thevenin(source.name), rel=1e-9, abs=1e-12), \
            source.name
