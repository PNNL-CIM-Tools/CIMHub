"""Atom tests: OpenDSS LineSpacing / LineGeometry -> XYSpacing / WireConfiguration -> cim18v17, with the engine
as the oracle. No impedance is computed (conductor-geometry skill)."""

from __future__ import annotations

from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer.cimtbl import wire
from cimhub_opendss.importer.cimtbl.geometry import map_linegeometry, map_linespacing
from cimhub_opendss.schema import opendss_schema as schema

from conftest import CATALOG_DECKS, ENGINE_UNIT, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "geometry"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def documents(native):
    return [*(wire.map_wires(native, *catalog) for catalog in wire.CATALOGS), map_linespacing(native),
            map_linegeometry(native)]


def _native(**by_class):
    return type("Native", (), {"list_by_class": staticmethod(lambda cls: by_class.get(cls.__name__, []))})()


@pytest.fixture(scope="module")
def assets():
    return DssReader(ATOMS / "assets.dss").read_all()


@pytest.mark.parametrize("mapper", [map_linespacing, map_linegeometry])
def test_matches_golden(assets, mapper):
    document = mapper(assets)
    assert_matches_golden(document, ATOMS / f"assets_{document.name}.cimtbl")


def test_binds_under_cim18v17(assets):
    network = cimtbl_to_cim(atom_documents(*documents(assets)))
    cim = network.cim
    configurations = {wc.name: wc for wc in network.graph[cim.WireConfiguration].values()}
    assert configurations["601"].WireSpacing.mRID == "spc_500"
    mixed = configurations["607"]
    assert mixed.numberOfPhases == 1 and mixed.WireSpacing.mRID == "wc_607_spc"
    infos = [s.WireInfo for s in sorted(mixed.WireSequence, key=lambda s: s.sequenceNumber)]
    assert [type(info).__name__ for info in infos] == ["TapeShieldCableInfo", "OverheadWireInfo"]
    positions = sorted(mixed.WireSpacing.XYConductorPosition, key=lambda p: p.sequenceNumber)
    assert [float(p.xCoord.to("ft")) for p in positions] == pytest.approx([0.0, 0.25])
    assert [p.kind.name for p in positions] == ["phase", "neutral"]
    assert not network.graph.get(cim.PerLengthPhaseImpedance)  # geometry stays geometry


GEOMETRY = {"name": "g", "nconds": 2, "nphases": 1}


@pytest.mark.parametrize("slots, message", [
    ({"wires": ["a", "a"], "cncables": ["c", "c"], "xs": [0, 1], "hs": [9, 9], "units": "ft"}, "sets 2 of wires"),
    ({"wires": ["a"], "xs": [0, 1], "hs": [9, 9], "units": "ft"}, "1 conductor names for nconds=2"),
    ({"wires": ["a", "zz"], "xs": [0, 1], "hs": [9, 9], "units": "ft"}, "'zz' is in no wire catalog"),
    ({"wires": ["a", "a"], "xs": [0], "hs": [9], "units": "ft"}, "1 x and 1 h values for nconds=2"),
    ({"wires": ["a", "a"], "xs": [0, 1], "hs": [9, 9]}, "the positions have no units"),
    ({"wires": ["a", "a"], "spacing": "s", "xs": [0, 1], "hs": [9, 9], "units": "ft"}, "both spacing= and inline"),
    ({"wires": ["a", "a"], "spacing": "nope"}, "spacing='nope' is no LineSpacing"),
    ({"wires": ["a", "a"], "x": 0.0}, "without cond= blocks"),
])
def test_fail_fast(slots, message):
    wire_a = schema.Wiredata(name="a", Rac=0.3, Runits="km", GMRac=0.1, GMRunits="cm", radunits="cm", diam=1.0)
    native = _native(Wiredata=[wire_a], Linespacing=[schema.Linespacing(name="s", nconds=2, nphases=1)],
                     Linegeometry=[schema.Linegeometry(**GEOMETRY, **slots)])
    with pytest.raises(ValueError, match=message):
        map_linegeometry(native)


def test_a_name_in_two_catalogs_raises():
    common = {"Rac": 0.3, "Runits": "km", "GMRac": 0.1, "GMRunits": "cm", "radunits": "cm", "diam": 1.0}
    native = _native(Wiredata=[schema.Wiredata(name="x", **common)], Cndata=[schema.Cndata(name="X", **common)],
                     Linegeometry=[schema.Linegeometry(**GEOMETRY, wires=["x", "x"], xs=[0, 1], hs=[9, 9],
                                                       units="ft")])
    with pytest.raises(ValueError, match=r"'x' is in two catalogs \(wire_x, cn_x\)"):
        map_linegeometry(native)


def test_the_equivalent_distance_spacing_raises():
    native = _native(Linespacing=[schema.Linespacing(name="s", nconds=3, nphases=3, EqDistPhPh=3.0)])
    with pytest.raises(ValueError, match="EqDistPhPh not mapped yet"):
        map_linespacing(native)


@pytest.mark.parametrize("relative", CATALOG_DECKS)
def test_geometries_match_the_engine(relative):
    path = deck(relative)
    network = cimtbl_to_cim(atom_documents(*documents(DssReader(path).read_all())))
    compile_deck(path)
    configurations = network.graph[network.cim.WireConfiguration].values()
    assert configurations
    for configuration in configurations:
        dss.LineGeometries.Name(configuration.name)
        sequence = sorted(configuration.WireSequence, key=lambda s: s.sequenceNumber)
        assert [str(s.WireInfo.name).lower() for s in sequence] == dss.LineGeometries.Conductors()
        assert configuration.numberOfPhases == dss.LineGeometries.Phases()
        [unit] = {ENGINE_UNIT[code] for code in dss.LineGeometries.Units()}
        positions = sorted(configuration.WireSpacing.XYConductorPosition, key=lambda p: p.sequenceNumber)
        assert [float(p.xCoord.to(unit)) for p in positions] == pytest.approx(dss.LineGeometries.Xcoords())
        assert [float(p.yCoord.to(unit)) for p in positions] == pytest.approx(dss.LineGeometries.Ycoords())
