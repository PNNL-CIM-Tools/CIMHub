"""Export atoms: equipment Locations -> BusCoords / LatLongCoords (EXPORT_MAPPING.md S6f), checked against the
original deck's coordinates in the engine."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.cim_to_dss import DssExporter
from cimhub_opendss.schema import opendss_schema as schema

from engine_compare import assert_same_coordinates, engine_coordinates
from export_atoms import export_atom

ATOMS = Path(__file__).parent / "atoms" / "buscoords"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(stem: str, device_geometry: str = "point"):
    path = ATOMS / f"{stem}.dss"
    return DssImporter(path.stem, device_geometry=device_geometry).to_cim(DssReader(path).read_all())


def _rows(network) -> dict:
    model = DssExporter().to_model(network, name_source="name")
    return {str(row.name): (row.x, row.y, row.geographic) for row in model.list_by_class(schema.Buscoords)}


def _location(network, mrid):
    return next(location for location in network.graph[cim.Location].values() if location.mRID == mrid)


@pytest.mark.parametrize("stem", ["local", "latlong"])
def test_coordinates_match_the_engine(stem, tmp_path):
    """Bus far has no coordinates in either deck; ghost is no bus."""
    atom = ATOMS / f"{stem}.dss"
    assert_same_coordinates(export_atom(atom, tmp_path, name_source="name"), atom)


def test_latlong_is_written_latitude_first(tmp_path):
    written = export_atom(ATOMS / "latlong.dss", tmp_path, name_source="name")
    assert "LatLongCoords latlong_latlongcoords.csv" in written.read_text(encoding="utf-8")
    assert "b1, 46.6971, -119.0702" in written.with_name("latlong_latlongcoords.csv").read_text(
        encoding="utf-8").splitlines()


def test_rows_follow_the_terminals():
    rows = _rows(_network("local"))
    assert rows["b1"] == (50.0, 0.0, False)  # the last row of the original's file
    assert "far" not in rows


def test_two_points_for_one_bus_raise():
    network = _network("local")
    [point] = _location(network, "ld_house_loc").PositionPoints
    point.xPosition = "111"
    with pytest.raises(ValueError, match="bus 'house': .* a DSS bus has one position"):
        _rows(network)


def test_two_points_a_rounding_error_apart_at_zero_are_one():
    """rel_tol alone never matches 0 against 1e-12 (a reflected device point), so positions also agree within
    1e-9 absolute."""
    network = _network("local")
    [point] = _location(network, "src_source_loc").PositionPoints
    point.xPosition = "1e-12"
    assert _rows(network)["sourcebus"][:2] == pytest.approx((0.0, 0.0), abs=1e-9)


def test_unknown_coordinate_system_raises():
    network = _network("local")
    for system in network.graph[cim.CoordinateSystem].values():
        system.crsUrn = "EPSG:2286"
    with pytest.raises(ValueError, match="crsUrn 'EPSG:2286' is not mapped"):
        _rows(network)


def test_two_coordinate_systems_raise():
    network = _network("local")
    other = cim.CoordinateSystem(mRID="crs_other", crsUrn="urn:ogc:def:crs:OGC:1.3:CRS84")
    network.add_to_graph(other)
    _location(network, "ld_house_loc").CoordinateSystem = other
    with pytest.raises(ValueError, match="Locations in 2 coordinate systems"):
        _rows(network)


def test_device_point_reflects_across_its_placed_bus():
    """Only the regulator touches rg: its midpoint (102.5, 2.5) and b2 (the capacitor's) give rg back exactly."""
    assert _rows(_network("local"))["rg"] == (105.0, 5.0, False)


def _without_location(network, mrid):
    location = _location(network, f"{mrid}_loc")
    for resource in location.PowerSystemResources:
        resource.Location = None
    location.PowerSystemResources.clear()


def test_device_point_with_no_placed_bus_places_them_at_the_point():
    """Without the line and the source, only switch sw1 touches b1, so it is reflected from b2 (the capacitor's).
    Without the capacitor and the transformers too, sw1 places both its buses at its point."""
    network = _network("local")
    _without_location(network, "ln_l1")
    _without_location(network, "src_source")
    assert _rows(network)["b1"] == (50.0, 0.0, False)  # reflected across sw1 from b2
    for mrid in ("cap_c1", "xf_ct", "xf_reg"):
        _without_location(network, mrid)
    rows = _rows(network)
    assert rows["b1"] == rows["b2"] == (75.0, 0.0, False)
    assert "rg" not in rows


def test_device_chain_fills_from_its_placed_end():
    """Without the capacitor, b2 is open on sw1, ct and reg. sw1 (or ct) has it as its one open bus and solves it;
    then reg has one open bus, rg, and reflects b2 into it."""
    network = _network("local")
    _without_location(network, "cap_c1")
    rows = _rows(network)
    assert rows["b2"] == (100.0, 0.0, False)
    assert rows["rg"] == (105.0, 5.0, False)


def test_device_linestrings_round_trip_exactly():
    """S5-9: a two-terminal device drawn bus to bus gives each bus its own point, so nothing is reflected and every
    bus comes back as the original deck's, exactly."""
    rows = _rows(_network("local", "linestring"))
    assert {bus: (x, y) for bus, (x, y, _) in rows.items()} == engine_coordinates(ATOMS / "local.dss")
