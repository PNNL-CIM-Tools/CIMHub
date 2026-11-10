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

from engine_compare import engine_coordinates
from export_atoms import export_atom

ATOMS = Path(__file__).parent / "atoms" / "buscoords"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(stem: str):
    path = ATOMS / f"{stem}.dss"
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def _rows(network) -> dict:
    model = DssExporter().to_model(network, name_source="name")
    return {str(row.name): (row.x, row.y, row.geographic) for row in model.list_by_class(schema.Buscoords)}


def _location(network, mrid):
    return next(location for location in network.graph[cim.Location].values() if location.mRID == mrid)


@pytest.mark.parametrize("stem", ["local", "latlong"])
def test_coordinates_match_the_engine(stem, tmp_path):
    """Bus far has no coordinates in either deck; ghost is no bus."""
    atom = ATOMS / f"{stem}.dss"
    assert engine_coordinates(export_atom(atom, tmp_path, name_source="name")) == engine_coordinates(atom)


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
