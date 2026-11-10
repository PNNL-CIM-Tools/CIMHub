"""OpenDSS bus coordinates (``BusCoords`` / ``LatLongCoords`` files) -> ``buscoords.cimtbl`` (shape ``location``).

A ConnectivityNode is not a PowerSystemResource, so a bus cannot hold a Location. Each piece of equipment gets one
``Location`` with a ``PositionPoint`` per Terminal at its bus's coordinates (S5-1), numbered by the Terminal's
``sequenceNumber`` (S5-5), as the engine's CIM export writes them. The Terminals are the ones binding made from the
other parts, so this is the importer's ``bound_parts`` part, imported last (S5-2). Equipment with a Terminal bus that
has no coordinates gets no Location (S5-3); coordinates for a bus the circuit does not have are ignored, as the
engine ignores them. Both are counted in the file comment.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#buscoords``.
"""

from __future__ import annotations

from collections.abc import Iterable

from cimtables.document import Column, Document, ObjectStatement, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Buscoords

#: ``geographic`` -> (CoordinateSystem mRID, name, crsUrn) (S5-4). BusCoords are the deck's own projection, which
#: it does not name (the engine's URN); LatLongCoords are WGS84 degrees, which the reader puts in x, y =
#: longitude, latitude order, CRS84's axis order.
COORDINATE_SYSTEMS = {
    False: ("crs_bus", "BusCoords", "OpenDSSLocalBusCoordinates"),
    True: ("crs_latlong", "LatLongCoords", "urn:ogc:def:crs:OGC:1.3:CRS84"),
}
_LISTED = 5

FIELDS = {
    "name": Field("structural", note="picks the bus: every Terminal on it gets a PositionPoint; a name the circuit "
                                     "has no bus for is ignored, as in the engine (counted in the file comment)"),
    "x": Field("copied", (("PositionPoint", "xPosition", None),), "on every point at the bus"),
    "y": Field("copied", (("PositionPoint", "yPosition", None),), "on every point at the bus"),
    "geographic": Field("mapped", note="the directive (LatLongCoords -> true) picks the CoordinateSystem: "
                                       "COORDINATE_SYSTEMS"),
}

_PROVENANCE = """OpenDSS bus coordinates -> a Location per equipment, a PositionPoint per Terminal at its bus.
Source table: Buscoords (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#buscoords"""


def _coordinate_system(coordinates) -> ObjectStatement:
    kinds = {bool(point.geographic) for point in coordinates}
    if len(kinds) > 1:
        raise ValueError("Buscoords: the deck gives both BusCoords and LatLongCoords, which is not mapped (one "
                         "coordinate system per model)")
    crs, name, urn = COORDINATE_SYSTEMS[kinds.pop()]
    return ObjectStatement("CoordinateSystem", [(Column("mRID"), crs), (Column("name"), name),
                                                (Column("crsUrn"), urn)])


def _listed(names: Iterable[str]) -> str:
    names = sorted(names)
    shown = ", ".join(repr(name) if not name else name for name in names[:_LISTED])
    return f"{len(names)} ({shown}{', ...' if len(names) > _LISTED else ''})"


def terminal_buses(network) -> list[tuple[object, dict[int, str]]]:
    """Each piece of equipment with a Terminal on a ConnectivityNode, in the order its first Terminal bound, with
    Terminal ``sequenceNumber`` -> ConnectivityNode mRID in sequence order."""
    equipment, buses = {}, {}
    for terminal in network.graph.get(network.cim.Terminal, {}).values():
        if terminal.ConnectivityNode is None:
            continue
        key = terminal.ConductingEquipment.uri()
        equipment[key] = terminal.ConductingEquipment
        buses.setdefault(key, {})[int(terminal.sequenceNumber)] = terminal.ConnectivityNode.mRID
    return [(equipment[key], dict(sorted(nodes.items()))) for key, nodes in buses.items()]


def map_buscoords(native, network) -> Document:
    """The coordinates of a DSS model as one ``buscoords`` document. ``network`` is what every other DSS part bound
    (``DssImporter.bound_parts``); its ConnectivityNodes are the circuit's buses."""
    coordinates = native.list_by_class(NATIVE_CLASS)
    if not coordinates:
        return Document(name="buscoords", statements=[], profile=CIM_PROFILE)
    crs = _coordinate_system(coordinates)
    by_bus = {str(point.name): point for point in coordinates}
    equipment = terminal_buses(network)
    locations, points, updates = [], [], []
    for item, nodes in equipment:
        if not all(node in by_bus for node in nodes.values()):
            continue
        location = f"{item.mRID}_loc"
        locations.append(Row([location, f"{item.name}_Loc" if item.name is not None else None]))
        for sequence, node in nodes.items():
            point = by_bus[node]
            points.append(Row([f"{location}_{sequence}", location, str(sequence), cell(point.x), cell(point.y)]))
        updates.append(Row([item.mRID, location]))
    comment = _PROVENANCE.format(count=len(coordinates))
    if len(locations) < len(equipment):
        comment += (f"\nnot located: {len(equipment) - len(locations)} of {len(equipment)} equipment (a terminal "
                    "bus without coordinates)")
    unknown = set(by_bus) - {node.mRID for node in network.graph.get(network.cim.ConnectivityNode, {}).values()}
    if unknown:
        comment += f"\nno such bus: {_listed(unknown)}"
    statements = [
        crs,
        Table("Location", [Column("mRID"), Column("name"), Column("CoordinateSystem", default=crs.cells[0][1])],
              locations),
        Table("PositionPoint", [Column("identifier"), Column("Location"), Column("sequenceNumber"),
                                Column("xPosition"), Column("yPosition")], points,
              comment="copied: x, y of the Terminal's bus; sequenceNumber = the Terminal's"),
        Table("PowerSystemResource", [Column("mRID"), Column("Location")], updates, update=True),
    ]
    return Document(name="buscoords", statements=statements, profile=CIM_PROFILE, comment=comment)
