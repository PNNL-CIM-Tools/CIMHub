"""Atom tests: OpenDSS BusCoords / LatLongCoords -> buscoords.cimtbl (wkt) -> cim18v17, with the engine's bus
coordinates as the oracle for every PositionPoint."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer.cimtbl import buscoords
from cimhub_opendss.importer.dss_to_cimtbl import DssImporter

from conftest import ENGINE_DECKS, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "buscoords"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _part(path: Path, device_geometry: str = "point"):
    """``buscoords.cimtbl`` mapped from the network the deck's other parts bind."""
    native = DssReader(path).read_all()
    return buscoords.map_buscoords(native, cimtbl_to_cim(DssImporter("atom").to_cimtbl(native)), device_geometry)


def test_classification_is_complete():
    check_fields(buscoords.FIELDS, buscoords.NATIVE_CLASS)


@pytest.mark.parametrize("stem", ["local", "latlong"])
def test_matches_golden(stem):
    assert_matches_golden(_part(ATOMS / f"{stem}.dss"), ATOMS / f"{stem}.cimtbl")


def test_device_linestrings_match_golden():
    """S5-9: the switch and the two transformers are drawn bus to bus; the line, loads and capacitor are unchanged."""
    assert_matches_golden(_part(ATOMS / "local.dss", "linestring"), ATOMS / "local_linestring.cimtbl")


def test_unknown_device_geometry_fails_fast():
    with pytest.raises(ValueError, match="device_geometry 'polyline' is not one of"):
        DssImporter("atom", device_geometry="polyline")


def test_locations_bind():
    network = dss_to_cim(DssReader(ATOMS / "local.dss").read_all(), name="atom")
    cim = network.cim
    located = {resource.mRID: location for location in network.graph[cim.Location].values()
               for resource in location.PowerSystemResources}

    def points(mrid):
        return [(point.sequenceNumber, point.xPosition, point.yPosition)
                for point in sorted(located[mrid].PositionPoints, key=lambda point: point.sequenceNumber)]

    assert points("ln_l1") == [(0, "0.0", "0.0"), (1, "50.0", "0.0")]  # b1's last row wins
    assert located["ln_l1"].CoordinateSystem.crsUrn == "OpenDSSLocalBusCoordinates"
    assert "ln_far" not in located  # bus far has no coordinates
    assert points("sw_sw1") == [(0, "75.0", "0.0")]  # midway from b1 to b2
    assert points("xf_ct") == [(0, "105.0", "-2.5")]  # the center tap's secondary is one Terminal
    assert points("ld_house") == [(0, "110.0", "-5.0")]


def test_latlong_is_longitude_first():
    network = dss_to_cim(DssReader(ATOMS / "latlong.dss").read_all(), name="atom")
    [location] = [location for location in network.graph[network.cim.Location].values()
                  if location.mRID == "ld_ld_loc"]
    [point] = location.PositionPoints
    assert (float(point.xPosition), float(point.yPosition)) == (-119.0702, 46.6971)
    assert location.CoordinateSystem.crsUrn == "urn:ogc:def:crs:OGC:1.3:CRS84"


def test_comment_counts_what_is_left_out():
    comment = _part(ATOMS / "local.dss").comment
    assert "not located: 1 of 9 equipment" in comment and "no such bus: 1 (ghost)" in comment


def test_both_directives_fail_fast(tmp_path):
    (tmp_path / "xy.csv").write_text("sourcebus, 0, 0\n")
    (tmp_path / "latlong.csv").write_text("b1, 46.7, -119.1\n")
    (tmp_path / "deck.dss").write_text(
        "Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus\nBusCoords xy.csv\nLatLongCoords latlong.csv\n")
    with pytest.raises(ValueError, match="both BusCoords and LatLongCoords"):
        _part(tmp_path / "deck.dss")


def test_unreadable_row_fails_fast(tmp_path):
    (tmp_path / "xy.csv").write_text("sourcebus, 0, 0\nb1, east, 0\n")
    (tmp_path / "deck.dss").write_text("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus\nBusCoords xy.csv\n")
    with pytest.raises(ValueError, match="xy.csv line 2"):
        DssReader(tmp_path / "deck.dss").read_all()


def _engine_differences(network) -> list[str]:
    """Every difference between the equipment Locations and the engine's bus coordinates: a line's points at its
    Terminal buses, other equipment one point at their centroid, when every Terminal bus has coordinates; else no
    Location."""
    differences = []
    for cim_class, objects in network.graph.items():
        if not issubclass(cim_class, network.cim.ConductingEquipment):
            continue
        for equipment in objects.values():
            engine = []
            for terminal in sorted(equipment.Terminals, key=lambda terminal: terminal.sequenceNumber):
                dss.Circuit.SetActiveBus(terminal.ConnectivityNode.name)
                engine.append((dss.Bus.X(), dss.Bus.Y(), dss.Bus.Coorddefined()))
            location = equipment.Location
            if not all(defined for *_, defined in engine):
                if location is not None:
                    differences.append(f"{equipment.mRID}: located, but a bus has no coordinates in the engine")
                continue
            if location is None:
                differences.append(f"{equipment.mRID}: not located")
                continue
            ours = [(float(point.xPosition), float(point.yPosition))
                    for point in sorted(location.PositionPoints, key=lambda point: point.sequenceNumber)]
            theirs = [(x, y) for x, y, _ in engine]
            if not isinstance(equipment, network.cim.ACLineSegment):
                theirs = [(sum(x for x, _ in theirs) / len(theirs), sum(y for _, y in theirs) / len(theirs))]
            if len(ours) != len(theirs) or not all(
                    math.isclose(a[0], b[0], abs_tol=1e-9) and math.isclose(a[1], b[1], abs_tol=1e-9)
                    for a, b in zip(ours, theirs)):
                differences.append(f"{equipment.mRID}: {ours} vs {theirs}")
    return differences


@pytest.mark.parametrize("stem", ["local", "latlong"])
def test_atom_matches_the_engine(stem):
    network = dss_to_cim(DssReader(ATOMS / f"{stem}.dss").read_all(), name="atom")
    compile_deck(ATOMS / f"{stem}.dss")
    assert _engine_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_locations_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the coordinates ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_differences(network) == []
