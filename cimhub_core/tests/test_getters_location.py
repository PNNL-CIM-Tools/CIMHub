"""cimhub_core.getters.location: equipment coordinates and each Terminal's point."""

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest
from cimtables import load_model

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_core.getters.location import LocationCoordinates, get_location_coordinates

SHAPES = Path(__file__).parents[1] / "src" / "cimhub_core" / "shapes"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _equipment(mrid):
    network = load_model(SHAPES / "location.cimtbl")
    return next(obj for objects in network.graph.values() for obj in objects.values()
                if isinstance(obj, cim.ConductingEquipment) and obj.mRID == mrid)


def _add_point(location, number, x, y):
    location.PositionPoints.append(cim.PositionPoint(sequenceNumber=number, xPosition=x, yPosition=y,
                                                     Location=location))


def test_one_point_per_terminal():
    assert get_location_coordinates(_equipment("rx_hsb")) == LocationCoordinates(
        "OpenDSSLocalBusCoordinates", ((200.0, 400.0), (200.0, 350.0)), ((200.0, 400.0), (200.0, 350.0)))
    assert get_location_coordinates(_equipment("ld_y1")).terminals == ((200.0, 350.0),)


def test_polyline_gives_its_ends_to_two_terminals():
    compensator = _equipment("rx_hsb")
    location = compensator.Location
    _add_point(location, 3, "250.0", "300.0")
    _add_point(location, 0, "150.0", "450.0")  # the first vertex, numbered below the others
    coordinates = get_location_coordinates(compensator)
    assert coordinates.points == ((150.0, 450.0), (200.0, 400.0), (200.0, 350.0), (250.0, 300.0))
    assert coordinates.terminals == ((150.0, 450.0), (250.0, 300.0))


def test_no_location_is_none():
    load = _equipment("ld_y1")
    load.Location = None
    assert get_location_coordinates(load) is None


def test_points_a_load_cannot_pair_raise():
    load = _equipment("ld_y1")
    _add_point(load.Location, 2, "1", "1")
    with pytest.raises(ValueError, match="2 PositionPoints for 1 Terminals"):
        get_location_coordinates(load)


def test_two_points_with_one_number_raise():
    load = _equipment("ld_y1")
    _add_point(load.Location, 1, "1", "1")
    with pytest.raises(ValueError, match="two PositionPoints numbered 1"):
        get_location_coordinates(load)


def test_point_without_position_raises():
    load = _equipment("ld_y1")
    load.Location.PositionPoints[0].yPosition = None
    with pytest.raises(ValueError, match="without sequenceNumber, xPosition or yPosition"):
        get_location_coordinates(load)
