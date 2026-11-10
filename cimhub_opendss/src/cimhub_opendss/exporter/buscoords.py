"""Equipment Locations -> OpenDSS bus coordinates, ``Buscoords`` rows (``EXPORT_MAPPING.md#buscoords``).

The importer's S5-1 inverted: each located piece of equipment gives each of its Terminals' buses that Terminal's
point (``get_location_coordinates``). Equipment without a Location gives none, so a bus no located equipment touches
has no coordinates, as on import (S5-3). Two points for one bus raise, naming both. The CoordinateSystem picks the
file: CRS84 is ``LatLongCoords`` (x = longitude), the importer's local URN ``BusCoords``; another URN, or two
systems in one model, raise.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.location import get_location_coordinates
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.importer.cimtbl.buscoords import COORDINATE_SYSTEMS
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.Location,)
NATIVE_CLASS = schema.Buscoords
#: crsUrn -> geographic (LatLongCoords), the importer's COORDINATE_SYSTEMS inverted
GEOGRAPHIC = {urn: geographic for geographic, (_, _, urn) in COORDINATE_SYSTEMS.items()}
#: float noise allowed between two points of one bus
POINT_REL_TOL = 1e-9

SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "the bus (Names.bus) of each Terminal of located equipment"),
    "x": Slot("written", "the Terminal's PositionPoint xPosition (get_location_coordinates)"),
    "y": Slot("written", "the Terminal's PositionPoint yPosition"),
    "geographic": Slot("written", "crsUrn CRS84 -> true (LatLongCoords), OpenDSSLocalBusCoordinates -> false; others "
                                  "raise"),
}, Slot("unset", ""))}


def export(context) -> list[schema.Buscoords]:
    """One row per bus some located equipment touches, in the network's ConnectivityNode order."""
    found = {}  # node mRID -> (x, y, the equipment that gave it)
    systems = set()
    for location in context.objects(*CIM_CLASSES):
        for equipment in location.PowerSystemResources:
            if not isinstance(equipment, cim.ConductingEquipment):
                continue  # a Substation or a pole has no bus
            coordinates = get_location_coordinates(equipment)
            if coordinates is None:
                continue
            systems.add(coordinates.crs_urn)
            for node, point in zip(get_terminal_nodes(equipment), coordinates.terminals, strict=True):
                _place(found, node, point, equipment)
    if not found:
        return []
    geographic = _geographic(systems)
    nodes = context.network.graph.get(cim.ConnectivityNode, {}).values()
    return [NATIVE_CLASS(name=context.names.bus(node), x=found[node.mRID][0], y=found[node.mRID][1],
                         geographic=geographic) for node in nodes if node.mRID in found]


def _place(found: dict, node, point: tuple[float, float], equipment) -> None:
    if node.mRID not in found:
        found[node.mRID] = (*point, equipment)
        return
    x, y, other = found[node.mRID]
    if not (math.isclose(x, point[0], rel_tol=POINT_REL_TOL) and math.isclose(y, point[1], rel_tol=POINT_REL_TOL)):
        raise ValueError(f"bus {node.mRID!r}: {describe(other)} puts it at ({x}, {y}) and {describe(equipment)} at "
                         f"{point}; a DSS bus has one position")


def _geographic(systems: set[str | None]) -> bool:
    if len(systems) != 1:
        raise ValueError(f"Locations in {len(systems)} coordinate systems {sorted(map(str, systems))}; a DSS deck "
                         f"holds one (BusCoords or LatLongCoords)")
    [urn] = systems
    if urn not in GEOGRAPHIC:
        raise ValueError(f"CoordinateSystem crsUrn {urn!r} is not mapped ({sorted(GEOGRAPHIC)} are)")
    return GEOGRAPHIC[urn]
