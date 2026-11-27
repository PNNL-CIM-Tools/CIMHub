"""Equipment Locations -> OpenDSS bus coordinates, ``Buscoords`` rows (``EXPORT_MAPPING.md#buscoords``).

The importer's geometry inverted (S5-8, F8). A point per Terminal, or a line's polyline ends, place their buses
directly (``get_location_coordinates``); two such points for one bus raise, naming both. A GIS device point (one
POINT on a switch, fuse or transformer) is its buses' centroid, so it places only the buses nothing else placed:
next to one placed bus it reflects it across the point, which gives back the importer's midpoint exactly; with none
placed every bus goes at the point. Equipment without a Location gives none, so a bus no located equipment touches
has no coordinates, as on import (S5-3). The CoordinateSystem picks the file: CRS84 is ``LatLongCoords``
(x = longitude), the importer's local URN ``BusCoords``; another URN, or two systems in one model, raise.
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
#: float noise allowed between two points of one bus.
#: GIS device symbols are positioned by a drafter and may be tens of metres from the span endpoint
#: they logically occupy the same bus as; 1e-4 relative (≈ 7–11 m at mid-latitudes) accepts that.
POINT_REL_TOL = 1e-4
#: and 1e-9 absolute, since no relative tolerance matches 0 against a reflected device point's 1e-12
POINT_ABS_TOL = 1e-9

SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "the bus (Names.bus) of each Terminal of located equipment"),
    "x": Slot("written", "the Terminal's PositionPoint xPosition (get_location_coordinates); a bus only a device "
                         "point touches is solved from it as the centroid of the device's buses"),
    "y": Slot("written", "as x, from yPosition"),
    "geographic": Slot("written", "crsUrn CRS84 -> true (LatLongCoords), OpenDSSLocalBusCoordinates -> false; others "
                                  "raise"),
}, Slot("unset", ""))}


def export(context) -> list[schema.Buscoords]:
    """One row per bus some located equipment touches, in the network's ConnectivityNode order."""
    found = {}  # node mRID -> (x, y, the equipment that gave it)
    devices = []  # (equipment, its Terminal nodes, its one point)
    systems = set()
    for location in context.objects(*CIM_CLASSES):
        for equipment in location.PowerSystemResources:
            if not isinstance(equipment, cim.ConductingEquipment):
                continue  # a Substation or a pole has no bus
            coordinates = get_location_coordinates(equipment)
            if coordinates is None:
                continue
            systems.add(coordinates.crs_urn)
            nodes = get_terminal_nodes(equipment)
            if coordinates.terminals is None:
                devices.append((equipment, nodes, coordinates.points[0]))
                continue
            for node, point in zip(nodes, coordinates.terminals, strict=True):
                _place(found, node, point, equipment)
    _place_devices(found, devices)
    if not found:
        return []
    geographic = _geographic(systems)
    nodes = context.network.graph.get(cim.ConnectivityNode, {}).values()
    return [NATIVE_CLASS(name=context.names.bus(node), x=found[node.mRID][0], y=found[node.mRID][1],
                         geographic=geographic) for node in nodes if node.mRID in found]


def _unplaced(found: dict, nodes: list) -> list:
    return [node for node in nodes if node.mRID not in found]


def _place_devices(found: dict, devices: list) -> None:
    """Place the buses device points leave open. A device with one open bus goes first, as the importer's midpoint solves it,
    so a chain of devices fills from its placed end; when none is left, the first remaining device places all of
    its open buses, and the chain goes on from there."""
    pending = devices
    while True:
        pending = [device for device in pending if _unplaced(found, device[1])]
        if not pending:
            return
        exact = [device for device in pending if len(_unplaced(found, device[1])) == 1]
        device = exact[0] if exact else pending[0]
        pending.remove(device)
        _fill_open_buses(found, *device)


def _fill_open_buses(found: dict, equipment, nodes: list, point: tuple[float, float]) -> None:
    """The point is the centroid of the N Terminal buses, so with k of them open each goes at (N * point - the sum of
    the placed ones) / k: 2 * point - the other bus for a two-terminal device, the point itself when none is placed."""
    placed = [found[node.mRID] for node in nodes if node.mRID in found]
    unplaced = _unplaced(found, nodes)
    x = (len(nodes) * point[0] - sum(position[0] for position in placed)) / len(unplaced)
    y = (len(nodes) * point[1] - sum(position[1] for position in placed)) / len(unplaced)
    for node in unplaced:
        found[node.mRID] = (x, y, equipment)


def _place(found: dict, node, point: tuple[float, float], equipment) -> None:
    if node.mRID not in found:
        found[node.mRID] = (*point, equipment)
        return
    x, y, other = found[node.mRID]
    if not (math.isclose(x, point[0], rel_tol=POINT_REL_TOL, abs_tol=POINT_ABS_TOL)
            and math.isclose(y, point[1], rel_tol=POINT_REL_TOL, abs_tol=POINT_ABS_TOL)):
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
