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
from cimhub_opendss.importer.cimtbl.geometry import earth_statement, map_linegeometry, map_linespacing
from cimhub_opendss.schema import opendss_schema as schema

from conftest import CATALOG_DECKS, limits, ENGINE_UNIT, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "geometry"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def documents(native):
    return [limits(), *(wire.map_wires(native, *catalog) for catalog in wire.CATALOGS), map_linespacing(native),
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
    ({"wires": ["a", "a"], "spacing": "s", "x": 0.0}, "both spacing= and inline"),
    ({"wires": ["a", "a"], "spacing": "s", "cond": 2}, "both spacing= and inline"),
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


_EARTH_DECK = """Clear
New Circuit.atom basekv=4.16 bus1=sourcebus
{options}
New Wiredata.w Rac=0.3 Runits=mi GMRac=0.03 GMRunits=ft Diam=0.7 Radunits=in
New LineSpacing.s nconds=1 nphases=1 x=[0] h=[30] units=ft
New Line.a bus1=sourcebus.1 bus2=b.1 phases=1 spacing=s wires=[w] length=1 units=kft {rho_a}
New Line.b bus1=b.1 bus2=c.1 phases=1 spacing=s wires=[w] length=1 units=kft {rho_b}
"""


def _earth(tmp_path, options="", rho_a="", rho_b=""):
    path = tmp_path / "deck.dss"
    path.write_text(_EARTH_DECK.format(options=options, rho_a=rho_a, rho_b=rho_b))
    return earth_statement(DssReader(path).read_all())


def test_earth_is_the_decks_model_and_rho(tmp_path):
    earth = _earth(tmp_path, "Set earthmodel=carson", "rho=30", "rho=30")
    assert dict((column.name, value) for column, value in earth.cells) == {
        "mRID": "earth", "name": "carson", "earthModelType": "carson", "rho": "30.0"}
    assert "defaulted" not in earth.comment


def test_earth_defaults_to_the_engines(tmp_path):
    assert "defaulted: earthmodel=Deri, rho=100.0" in _earth(tmp_path).comment


@pytest.mark.parametrize("options, rho_b, message", [
    ("Set earthmodel=fullcarson", "", "EarthModelKind has"),
    ("", "rho=50", r"geometry lines give rho \[30.0, 50.0\]"),
])
def test_earth_fails_fast(tmp_path, options, rho_b, message):
    with pytest.raises(ValueError, match=message):
        _earth(tmp_path, options, "rho=30", rho_b)


def _no_geometry(tmp_path, options):
    path = tmp_path / "deck.dss"
    path.write_text(f"Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus\n{options}\n"
                    "New Line.a bus1=sourcebus bus2=b r1=0.1 x1=0.2\n")
    return earth_statement(DssReader(path).read_all())


def test_no_geometry_keeps_a_set_earthmodel(tmp_path):
    earth = _no_geometry(tmp_path, "Set earthmodel=carson")  # a floating EarthResistivity, so the export writes it
    assert dict((column.name, value) for column, value in earth.cells) == {
        "mRID": "earth", "name": "carson", "earthModelType": "carson", "rho": "100.0"}
    assert earth.comment.startswith("the deck's earthmodel; no line names it")
    assert "defaulted: rho=100.0" in earth.comment


def test_no_geometry_and_no_earthmodel_has_no_earth(tmp_path):
    assert _no_geometry(tmp_path, "") is None


def test_a_switch_gives_the_earth_no_rho(tmp_path):
    """A switch drops its spacing and rho (DSS-8), so its rho is not one of the geometry lines'."""
    earth = _earth(tmp_path, "", "rho=30", "rho=50 switch=y")
    assert dict((column.name, value) for column, value in earth.cells)["rho"] == "30.0"


def test_a_switch_by_spacing_is_no_geometry(tmp_path):
    path = tmp_path / "deck.dss"
    path.write_text("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus\n"
                    "New LineSpacing.s nconds=1 nphases=1 x=[0] h=[30] units=ft\n"
                    "New Line.a bus1=sourcebus.1 bus2=b.1 phases=1 switch=y spacing=s\n")
    assert earth_statement(DssReader(path).read_all()) is None


SPACING = {"name": "s", "nconds": 3, "nphases": 3, "x": [0.0, 1.0, 2.0], "h": [9.0, 9.0, 9.0], "units": "ft"}


def test_a_detailed_spacing_maps_its_positions():
    """``detailed=Yes`` is the engine's default: the positions give the distances (LineSpacing.pas:213 sets
    FEquivalentSpacing := not detailed, default FALSE at :327; LineConstants.pas:218 uses the x, y positions). So it
    maps exactly as an unset ``detailed`` does. opendssdirect 0.9.4 does not know the slot, so this is mapper-only."""
    detailed = map_linespacing(_native(Linespacing=[schema.Linespacing(**SPACING, detailed=True)]))
    plain = map_linespacing(_native(Linespacing=[schema.Linespacing(**SPACING)]))
    assert detailed.statements == plain.statements


@pytest.mark.parametrize("slots, message", [
    ({"detailed": False}, "detailed=No"),
    ({"EqDistPhPh": "0"}, "EqDistPhPh not mapped yet"),
    ({"EqDistPhN": "3"}, "EqDistPhN not mapped yet"),
    ({"AvgPhaseHeight": "28"}, "AvgPhaseHeight not mapped yet"),
    ({"AvgNeutralHeight": "24"}, "AvgNeutralHeight not mapped yet"),
])
def test_the_equivalent_spacing_form_raises(slots, message):
    """``detailed=No`` takes every phase-phase and neutral-neutral distance from EqDistPhPh, every phase-neutral
    one from EqDistPhN, and the image distances from 2 x AvgPhaseHeight, 2 x AvgNeutralHeight or their sum
    (LineConstants.pas:218-297). In general no set of XY positions reproduces that, so it raises, and so does each
    of the four slots, at any value, 0 included."""
    native = _native(Linespacing=[schema.Linespacing(**SPACING, **slots)])
    with pytest.raises(ValueError, match=message):
        map_linespacing(native)
