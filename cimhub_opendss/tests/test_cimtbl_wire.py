"""Atom tests: OpenDSS WireData / CNData / TSData -> wire catalogs -> cim18v17, with the engine as the oracle."""

from __future__ import annotations

from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer.cimtbl.wire import (CATALOGS, ac_from_dc, map_wires, radius_from_diameter,
                                                screen_diameter)
from cimhub_opendss.schema import opendss_schema as schema

from conftest import CATALOG_DECKS, limits, ENGINE_UNIT, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "wire"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def documents(native):
    return [limits(), *(map_wires(native, *catalog) for catalog in CATALOGS)]


def _native(**by_class):
    return type("Native", (), {"list_by_class": staticmethod(lambda cls: by_class.get(cls.__name__, []))})()


def test_derived_values():
    assert ac_from_dc(0.2) == pytest.approx(0.204)
    assert radius_from_diameter(0.398) == 0.199
    assert screen_diameter(0.88, 0.005) == pytest.approx(0.87)


@pytest.mark.parametrize("case", ["assets", "metric"])
def test_matches_golden(case):
    native = DssReader(ATOMS / f"{case}.dss").read_all()
    for document in documents(native)[1:]:
        if document.statements:
            assert_matches_golden(document, ATOMS / f"{case}_{document.name}.cimtbl")


def test_binds_under_cim18v17():
    network = cimtbl_to_cim(atom_documents(*documents(DssReader(ATOMS / "assets.dss").read_all())))
    cim = network.cim
    acsr = network.graph[cim.OverheadWireInfo]
    assert len(acsr) == 4 and len(network.graph[cim.ConcentricNeutralCableInfo]) == 1
    [wire] = [w for w in acsr.values() if w.mRID == "wire_acsr_556_5"]
    assert float(wire.rAC25.to("ohm/kft")) == pytest.approx(1.02 * 0.035227273)  # defaulted from Rdc
    assert float(wire.radius.to("in")) == pytest.approx(0.4635)
    limits = {limit.mRID: float(limit.normalValue.to("A")) for limit in wire.OperationalLimitSet.OperationalLimitValue}
    assert limits == {"wire_acsr_556_5_norm": 730, "wire_acsr_556_5_emerg": pytest.approx(1095)}  # 1.5 x normamps
    [tape] = network.graph[cim.TapeShieldCableInfo].values()
    assert float(tape.diameterOverScreen.to("in")) == pytest.approx(0.87) and float(tape.tapeLap) == 20.0


@pytest.mark.parametrize("slots, message", [
    ({"radius": 0.2, "diam": 0.4}, "give one of radius and diam"),
    ({}, "give one of radius and diam"),
    ({"diam": 0.4, "GMRac": None}, "GMRac unset"),
    ({"diam": 0.4, "Rac": None}, "sets neither Rac nor Rdc"),
    ({"diam": 0.4, "Runits": None}, "Runits unset"),
    ({"diam": 0.4, "Capradius": 0.1}, "Capradius not mapped yet"),
])
def test_fail_fast(slots, message):
    values = {"Rac": 0.3, "Runits": "km", "GMRac": 0.1, "GMRunits": "cm", "radunits": "cm", **slots}
    native = _native(Wiredata=[schema.Wiredata(name="w", **values)])
    with pytest.raises(ValueError, match=message):
        map_wires(native, *CATALOGS[0])


def test_a_shield_without_its_tape_raises():
    cable = schema.Tsdata(name="t", Rac=0.9, Runits="mi", GMRac=0.1, GMRunits="in", radunits="in", diam=0.4,
                          DiaShield=0.9)
    with pytest.raises(ValueError, match="DiaShield without TapeLayer"):
        map_wires(_native(Tsdata=[cable]), *CATALOGS[2])


def _engine_checks(cim):
    """``(CIM class, engine interface, [(CIM attribute, engine value, unit slot)])`` per catalog; the unit slot
    names the engine's units property, ``None`` for a count or a percent."""
    conductor = [("rAC25", "Rac", "ResistanceUnits"), ("gmr", "GMRac", "GMRUnits"), ("radius", "Radius", "RadiusUnits")]
    cable = [("insulationThickness", "InsLayer", "RadiusUnits"), ("diameterOverInsulation", "DiaIns", "RadiusUnits"),
             ("diameterOverJacket", "DiaCable", "RadiusUnits")]
    return [
        (cim.OverheadWireInfo, dss.WireData, conductor),
        (cim.ConcentricNeutralCableInfo, dss.CNData, conductor + cable + [
            ("neutralStrandGmr", "GmrStrand", "GMRUnits"), ("neutralStrandRDC20", "RStrand", "ResistanceUnits"),
            ("neutralStrandCount", "k", None)]),
        (cim.TapeShieldCableInfo, dss.TSData, conductor + cable + [
            ("tapeThickness", "TapeLayer", "RadiusUnits"), ("tapeLap", "TapeLap", None)]),
    ]


def _in_engine_units(value, interface, unit_slot):
    if unit_slot is None:
        return float(value)
    unit = ENGINE_UNIT[getattr(interface, unit_slot)()]
    return float(value.to(f"ohm/{unit}" if unit_slot == "ResistanceUnits" else unit))


@pytest.mark.parametrize("relative", CATALOG_DECKS)
def test_values_match_the_engine(relative):
    path = deck(relative)
    network = cimtbl_to_cim(atom_documents(*documents(DssReader(path).read_all())))
    compile_deck(path)
    checked = 0
    for cim_class, interface, checks in _engine_checks(network.cim):
        for info in network.graph.get(cim_class, {}).values():
            interface.Name(info.name)
            for attribute, engine_slot, unit_slot in checks:
                ours = _in_engine_units(getattr(info, attribute), interface, unit_slot)
                assert ours == pytest.approx(getattr(interface, engine_slot)(), rel=1e-12), (info.name, attribute)
            if cim_class is network.cim.ConcentricNeutralCableInfo:
                assert float(info.neutralStrandRadius.to(ENGINE_UNIT[interface.RadiusUnits()])) * 2 == \
                    pytest.approx(interface.DiaStrand())
            if cim_class is network.cim.TapeShieldCableInfo:
                inside = float(info.diameterOverScreen.to(ENGINE_UNIT[interface.RadiusUnits()]))
                assert inside + 2 * interface.TapeLayer() == pytest.approx(interface.DiaShield())
            limits = {limit.OperationalLimitType.mRID: float(limit.normalValue.to("A"))
                      for limit in info.OperationalLimitSet.OperationalLimitValue} if info.OperationalLimitSet else {}
            assert (limits.get("olt_normal", 400.0), limits.get("olt_emergency", 600.0)) == pytest.approx(
                (interface.NormAmps(), interface.EmergAmps())), (info.name, "ratings")
            checked += 1
    assert checked
