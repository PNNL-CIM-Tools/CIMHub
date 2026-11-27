"""OpenDSS bus coordinates (``BusCoords`` / ``LatLongCoords`` files) -> ``buscoords.cimtbl`` (shape ``location``).

A ConnectivityNode is not a PowerSystemResource, so a bus cannot hold a Location. The equipment is drawn as a GIS
draws it, through the ``wkt`` column (S5-8): a line is a ``LINESTRING`` through its Terminals' buses, in
``sequenceNumber`` order; any other equipment is one ``POINT``, at its bus for one Terminal and at its buses'
centroid for more (a switch, fuse or transformer midway between its buses). With ``device_geometry="linestring"``
a two-terminal device is drawn bus to bus like a line instead (S5-9). cimtables makes the Location and its
PositionPoints. The Terminals are the ones binding made from the other parts, so this is the importer's
``bound_parts`` part, imported last (S5-2). Equipment with a Terminal bus that has no coordinates gets no Location
(S5-3); coordinates for a bus the circuit does not have are ignored, as the engine ignores them. Both are counted in
the file comment.

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
#: how ``map_buscoords`` draws a two-terminal device (a switch, fuse, transformer, regulator, series reactor): a POINT
#: midway between its buses, as a GIS draws one, or a LINESTRING from bus to bus, as a line (S5-9)
DEVICE_GEOMETRIES = ("point", "linestring")

FIELDS = {
    "name": Field("structural", note="picks the bus: every Terminal on it takes its coordinates; a name the circuit "
                                     "has no bus for is ignored, as in the engine (counted in the file comment)"),
    "x": Field("derived", note="geometry: a line's LINESTRING vertex at each Terminal bus, verbatim; other equipment's "
                               "POINT at its Terminal buses' centroid (the bus itself for one Terminal)"),
    "y": Field("derived", note="as x"),
    "geographic": Field("mapped", note="the directive (LatLongCoords -> true) picks the CoordinateSystem: "
                                       "COORDINATE_SYSTEMS"),
}

_GEOMETRY_COMMENT = {
    "point": "a line's LINESTRING through its Terminal buses; other equipment a POINT at their centroid",
    "linestring": "a line's or two-terminal device's LINESTRING through its Terminal buses; other equipment a POINT "
                  "at their centroid",
}

_PROVENANCE = """OpenDSS bus coordinates -> a wkt geometry per equipment: a line's LINESTRING, others a POINT.
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


def _wkt_geometry(equipment, points: list[tuple[float, float]], cim, device_geometry: str) -> str:
    """The equipment's WKT from its Terminal buses' points, in Terminal order: a line, and under ``"linestring"`` any
    two-terminal device, is the LINESTRING through them; anything else one POINT at their centroid, the bus itself
    for one Terminal and the midpoint for two."""
    if isinstance(equipment, cim.ACLineSegment) or (device_geometry == "linestring" and len(points) == 2):
        return "LINESTRING (" + ", ".join(f"{cell(x)} {cell(y)}" for x, y in points) + ")"
    x = sum(x for x, _ in points) / len(points)
    y = sum(y for _, y in points) / len(points)
    return f"POINT ({cell(x)} {cell(y)})"


def map_buscoords(native, network, device_geometry: str = "point") -> Document:
    """The coordinates of a DSS model as one ``buscoords`` document. ``network`` is what every other DSS part bound
    (``DssImporter.bound_parts``); its ConnectivityNodes are the circuit's buses. ``device_geometry`` is one of
    ``DEVICE_GEOMETRIES``."""
    coordinates = native.list_by_class(NATIVE_CLASS)
    if not coordinates:
        return Document(name="buscoords", statements=[], profile=CIM_PROFILE)
    by_bus: dict[str, tuple[float, float]] = {}
    for point in coordinates:
        if point.x is None or point.y is None:
            raise ValueError(f"Buscoords {point.name!r}: x and y must both be set (got x={point.x!r}, y={point.y!r})")
        by_bus[str(point.name).lower()] = (float(point.x), float(point.y))
    equipment = terminal_buses(network)
    rows = []
    for item, nodes in equipment:
        if not all(node in by_bus for node in nodes.values()):
            continue
        points = [by_bus[node] for node in nodes.values()]
        rows.append(Row([item.mRID, _wkt_geometry(item, points, network.cim, device_geometry)]))
    comment = _PROVENANCE.format(count=len(coordinates))
    if len(rows) < len(equipment):
        comment += (f"\nnot located: {len(equipment) - len(rows)} of {len(equipment)} equipment (a terminal "
                    "bus without coordinates)")
    unknown = set(by_bus) - {node.mRID for node in network.graph.get(network.cim.ConnectivityNode, {}).values()}
    if unknown:
        comment += f"\nno such bus: {_listed(unknown)}"
    if not rows:
        return Document(name="buscoords", statements=[], profile=CIM_PROFILE, comment=comment)
    statements = [
        _coordinate_system(coordinates),
        Table("PowerSystemResource", [Column("mRID"), Column("wkt")], rows, update=True,
              comment=_GEOMETRY_COMMENT[device_geometry]),
    ]
    return Document(name="buscoords", statements=statements, profile=CIM_PROFILE, comment=comment)
