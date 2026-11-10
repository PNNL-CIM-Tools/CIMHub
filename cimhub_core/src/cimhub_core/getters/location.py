"""Equipment coordinates: its Location's PositionPoints and the point of each Terminal (skill `export-getters`).

A ConnectivityNode is not a PowerSystemResource, so CIM puts coordinates on the equipment: one Location with its
PositionPoints in ``sequenceNumber`` order (CIM17's ``PositionPoint.Location``, as the importers write it). A spoke
with bus coordinates (DSS BusCoords, GLM latitude/longitude) needs each Terminal's point. With one point per
Terminal they pair in order (the importers' form, S5-1); a two-terminal polyline gives its ends to its Terminals
(CIM's line route). Positions are text in CIM; they are read as floats in the CoordinateSystem's own units.
``zPosition`` is not read: no spoke has a height.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.terminals import get_terminal_nodes

Point = tuple[float, float]


class LocationCoordinates(NamedTuple):
    crs_urn: str | None  # the Location's CoordinateSystem.crsUrn; None when it has none
    points: tuple[Point, ...]  # (x, y) in PositionPoint sequenceNumber order
    terminals: tuple[Point, ...]  # each Terminal's point, in Terminal sequenceNumber order


def get_location_coordinates(equipment: cim.ConductingEquipment) -> LocationCoordinates | None:
    """The equipment's points and its Terminals' points; None when it has no Location or the Location no points.
    Raises on a point without a sequenceNumber or a position, on two points with one sequenceNumber, and on a point
    count its Terminals cannot pair with."""
    location = equipment.Location
    if location is None or not location.PositionPoints:
        return None
    numbered = {}
    for point in location.PositionPoints:
        if point.sequenceNumber is None or point.xPosition is None or point.yPosition is None:
            raise ValueError(f"{describe(location)} of {describe(equipment)}: a PositionPoint without sequenceNumber, "
                             f"xPosition or yPosition ({point.sequenceNumber}, {point.xPosition}, {point.yPosition})")
        if point.sequenceNumber in numbered:
            raise ValueError(f"{describe(location)} of {describe(equipment)}: two PositionPoints numbered "
                             f"{point.sequenceNumber}")
        numbered[point.sequenceNumber] = (float(point.xPosition), float(point.yPosition))
    points = tuple(numbered[number] for number in sorted(numbered))
    terminals = len(get_terminal_nodes(equipment))
    if len(points) == terminals:
        by_terminal = points
    elif terminals == 2 and len(points) > 2:
        by_terminal = (points[0], points[-1])
    else:
        raise ValueError(f"{describe(location)} of {describe(equipment)}: {len(points)} PositionPoints for "
                         f"{terminals} Terminals (one per Terminal, or a polyline between two)")
    system = location.CoordinateSystem
    return LocationCoordinates(system.crsUrn if system is not None else None, points, by_terminal)
