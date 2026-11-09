"""RAW Substation data -> ``substation.cimtbl``: a ``ConnectivityNode`` per node, in its bus's ``TopologicalNode``;
a ``Switch``, ``Breaker`` or ``Disconnector`` per substation switching device (by TYPE); the ``Location`` of a
located substation; and a ``BusbarSection`` on each node a control regulates (RAW-11). The block's ``Substation``
row is in ``bus.cimtbl`` (its buses' nodes bind to it first); the equipment terminals are placed on the nodes by
``equipment_terminal.cimtbl``.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#node-breaker-substations-r6``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, ObjectStatement, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.bus import block_mrid
from cimhub_raw.importer.cimtbl.ratings import RatingRows
from cimhub_raw.importer.cimtbl.records import fill_keyed_defaults, raw_defaults
from cimhub_raw.importer.cimtbl.switch import OPEN, SWITCH_CLASS
from cimhub_raw.importer.node_breaker import NodeBreaker, node_busbar_mrid, node_mrid

NATIVE_CLASS = schema.SubstationRecord
NODE_CLASS = schema.SubstationNodeRecord
DEVICE_CLASS = schema.StationSwitchingDeviceRecord
DEVICE_PREFIX = "sw_s"  # requested from the cimtbl-translate table owners (plan C3)

#: (CoordinateSystem mRID, name, crsUrn): degrees, x = longitude, y = latitude (CRS84's axis order), as the OpenDSS
#: spoke writes LatLongCoords
COORDINATE_SYSTEM = ("crs_latlong", "LatLongCoords", "urn:ogc:def:crs:OGC:1.3:CRS84")

FIELDS = {
    "substation_number": Field("structural", note="IS: the key, Substation sub_s<IS> (in bus.cimtbl, R6); the scope "
                                                  "of its node numbers"),
    "name": Field("structural", note="NAME: the Substation's name (bus.cimtbl); blank: IS"),
    "latitude": Field("copied", (("PositionPoint", "yPosition", None),),
                      note="LATI (deg): the point sub_s<IS>_loc_1 of Location sub_s<IS>_loc; LATI = LONG = 0 (the "
                           "default) writes no Location (user, 2026-11-09)"),
    "longitude": Field("copied", (("PositionPoint", "xPosition", None),), note="LONG (deg): as LATI"),
    "grounding_resistance": Field("untranscribed", note="SGR (ohm): a substation's DC grounding resistance (GIC) has "
                                                        "no CIM 18 home (gap)"),
}

NODE_FIELDS = {
    "substation_number": Field("structural", note="IS: the enclosing block (filled by the reader); "
                                                  "ConnectivityNodeContainer = sub_s<IS>"),
    "node_number": Field("structural", note="NI: with IS the key, ConnectivityNode sub_s<IS>_n<NI>; a node number "
                                            "twice in one block raises"),
    "name": Field("copied", (("ConnectivityNode", "name", None),), note="NAME; blank: <IS>_<NI>"),
    "bus_number": Field("structural", note="I: TopologicalNode = I (bare), BaseVoltage = bus I's; a bus with nodes "
                                           "in two blocks raises"),
    "status": Field("untranscribed", note="STATUS: a ConnectivityNode has no in-service flag (CIM 18 gap); 0 is "
                                          "listed on the row"),
    "vm": Field("untranscribed", note="VM (pu): SvVoltage attaches only to a TopologicalNode (the bus's VM); a VM "
                                      "other than the default -1.0 (not given) is listed on the row"),
    "va": Field("untranscribed", note="VA (deg): as VM; listed when not 0.0"),
}

DEVICE_FIELDS = {
    "substation_number": Field("structural", note="IS: EquipmentContainer = sub_s<IS>"),
    "from_node": Field("structural", note="NI: node1 = sub_s<IS>_n<NI>, bus1 = that node's bus; BaseVoltage = its "
                                          "bus's"),
    "to_node": Field("structural", note="NJ: node2, bus2; NI = NJ raises"),
    "circuit": Field("structural", note="CKT: with IS, NI and NJ the key, mRID sw_s<IS>_<NI>_<NJ>_<CKT>; blank: 1 "
                                        "(defaulted)"),
    "name": Field("copied", (("Switch", "name", None), ("Breaker", "name", None), ("Disconnector", "name", None)),
                  note="NAME; blank: the key <IS>_<NI>_<NJ>_<CKT>"),
    "device_type": Field("mapped", note="TYPE: the class, as a system switching device's STYPE: 1 Switch (generic "
                                        "connector), 2 Breaker, 3 Disconnector; another code raises"),
    "status": Field("mapped", note="STATUS: open = (STATUS == 0); blank: 1 (defaulted)"),
    "normal_status": Field("mapped", note="NSTAT: normalOpen = (NSTAT == 0); blank: 1 (defaulted)"),
    "reactance": Field("untranscribed", note="X: as a system switching device's (a Switch has no impedance); the "
                                             "exporter writes the default 0.0001 back"),
    "rate1": Field("structural", note="RATE1..RATE3: as a system switching device's ratings (RatingRows, units by "
                                      "NXFRAT), the set sw_s<key>_ratings on terminal 1; zero is no limit"),
    "rate2": Field("structural", note="RATE2: as RATE1"),
    "rate3": Field("structural", note="RATE3: as RATE1"),
}

_PROVENANCE = """PSS/E RAW Substation data -> ConnectivityNode, Switch / Breaker / Disconnector (by TYPE), Location,
BusbarSection per regulated node; each block's Substation is in bus.cimtbl, its equipment terminals in
equipment_terminal.cimtbl.
Source table: Substation (blocks: {blocks}, nodes: {nodes}, switching devices: {devices})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#node-breaker-substations-r6"""


def _node_note(node) -> str | None:
    """``untranscribed: status=0, vm=..., va=...`` for what the row cannot carry, or ``None``."""
    vm_default, va_default = raw_defaults(NODE_CLASS)["vm"], raw_defaults(NODE_CLASS)["va"]
    items = []
    if node.status == 0:
        items.append("status=0")
    if node.vm is not None and node.vm != vm_default:
        items.append(f"vm={cell(node.vm)}")
    if node.va is not None and node.va != va_default:
        items.append(f"va={cell(node.va)}")
    return f"untranscribed: {', '.join(items)}" if items else None


def _location_statements(blocks: dict[int, object]) -> tuple[list, list[int]]:
    """The located blocks' ``CoordinateSystem``, ``Location``, ``PositionPoint`` and ``Update Substation`` rows, and
    the blocks at LATI = LONG = 0."""
    defaults = raw_defaults(NATIVE_CLASS)
    locations, points, updates, unlocated = [], [], [], []
    for number, record in sorted(blocks.items()):
        block, defaulted = fill_defaults(FIELDS, record, defaults)
        if not block.latitude and not block.longitude:
            unlocated.append(number)
            continue
        location = f"{block_mrid(number)}_loc"
        locations.append(Row([location], comment=defaulted))
        points.append(Row([f"{location}_1", location, "1", cell(block.longitude), cell(block.latitude)]))
        updates.append(Row([block_mrid(number), location]))
    if not locations:
        return [], unlocated
    crs, name, urn = COORDINATE_SYSTEM
    return [
        ObjectStatement("CoordinateSystem", [(Column("mRID"), crs), (Column("name"), name), (Column("crsUrn"), urn)]),
        Table("Location", [Column("mRID"), Column("CoordinateSystem", default=crs)], locations),
        Table("PositionPoint", [Column("identifier"), Column("Location"), Column("sequenceNumber"),
                                Column("xPosition"), Column("yPosition")], points,
              comment="copied: xPosition = LONG, yPosition = LATI (deg)"),
        Table("Substation", [Column("mRID"), Column("Location")], updates, update=True),
    ], unlocated


def _busbar_rows(node_breaker: NodeBreaker, regulated, base_kv_of: dict[int, float]) -> list[Row]:
    """One BusbarSection per node a control regulates: ``regulated`` = ``(bus, NI, record id)``."""
    rows: dict[str, Row] = {}
    for bus, number, record_id in regulated:
        block, node = node_breaker.node(bus, number, record_id)
        busbar = node_busbar_mrid(block, number)
        rows.setdefault(busbar, Row([busbar, cell(node.name or f"{block}_{number}"), node_mrid(block, number),
                                     str(bus), base_voltage_mrid(base_kv_of[bus]), block_mrid(block)]))
    return [rows[key] for key in sorted(rows)]


def map_substation(native, node_breaker: NodeBreaker, base_kv_of: dict[int, float], bus_area: dict[int, int],
                   ratings_in_current: bool, regulated: list[tuple[int, int, str]]) -> Document:
    """``regulated``: ``(bus, NI, record id)`` of every control that names a node (the generator, switched-shunt and
    transformer ``regulated_nodes``)."""
    if not node_breaker.blocks:
        return Document(name="substation", statements=[], profile=CIM_PROFILE)
    statements, unlocated = _location_statements(node_breaker.blocks)

    node_rows = []
    for (block, number), node in sorted(node_breaker.nodes.items()):
        node_rows.append(Row([node_mrid(block, number), cell(node.name or f"{block}_{number}"), str(node.bus_number),
                              base_voltage_mrid(base_kv_of[node.bus_number]), block_mrid(block)],
                             comment=_node_note(node)))
    statements.append(Table("ConnectivityNode", [Column("mRID"), Column("name"), Column("TopologicalNode"),
                                                 Column("BaseVoltage"), Column("ConnectivityNodeContainer")],
                            node_rows, comment=untranscribed_names(NODE_FIELDS)))

    defaults = raw_defaults(DEVICE_CLASS)
    rows_by_class: dict[str, list[Row]] = {name: [] for name in SWITCH_CLASS.values()}
    ratings = RatingRows(ratings_in_current)
    devices = sorted(native.list_by_class(DEVICE_CLASS),
                     key=lambda device: (device.substation_number, device.from_node, device.to_node,
                                         str(device.circuit)))
    for record in devices:
        device, defaulted = fill_keyed_defaults(DEVICE_FIELDS, record, defaults)
        record_id = f"substation switching device {device.ID}"
        if device.from_node == device.to_node:
            raise ValueError(f"{record_id}: NI = NJ = {device.from_node}")
        block = device.substation_number
        ends = [node_breaker.nodes[(block, number)] for number in (device.from_node, device.to_node)]
        buses = [node.bus_number for node in ends]
        if bus_area[buses[0]] != bus_area[buses[1]]:
            raise NotImplementedError(f"{record_id}: joins buses {buses[0]} and {buses[1]} of AREAs "
                                      f"{bus_area[buses[0]]} and {bus_area[buses[1]]}, a tie inside a substation "
                                      "(no case has one yet)")
        switch_class = lookup(SWITCH_CLASS, device.device_type, slot="device_type", record_id=record_id)
        equipment = mrid(DEVICE_PREFIX, device.ID)
        base_kv = base_kv_of[buses[0]]
        rows_by_class[switch_class].append(Row([
            equipment, cell(device.name or device.ID), node_mrid(block, device.from_node),
            node_mrid(block, device.to_node), str(buses[0]), str(buses[1]),
            cell(lookup(OPEN, device.status, slot="status", record_id=record_id)),
            cell(lookup(OPEN, device.normal_status, slot="normal_status", record_id=record_id)),
            base_voltage_mrid(base_kv), block_mrid(block)], comment=defaulted))
        ratings.add(equipment, [device.rate1, device.rate2, device.rate3], base_kv)

    columns = [Column("mRID"), Column("name"), Column("node1"), Column("node2"), Column("bus1"), Column("bus2"),
               Column("open"), Column("normalOpen"), Column("BaseVoltage"), Column("EquipmentContainer")]
    device_tables = [Table(name, columns, rows) for name, rows in rows_by_class.items() if rows]
    if device_tables:
        device_tables[0].comment = untranscribed_names(DEVICE_FIELDS)
    statements += device_tables + ratings.tables()

    busbars = _busbar_rows(node_breaker, regulated, base_kv_of)
    if busbars:
        statements.append(Table("BusbarSection", [Column("mRID"), Column("name"), Column("node"), Column("bus"),
                                                  Column("BaseVoltage"), Column("EquipmentContainer")], busbars,
                                comment="one per node a control regulates (NREG, NODk; RAW-11); RAW does not say "
                                        "which nodes are busbars"))

    comment = [_PROVENANCE.format(blocks=len(node_breaker.blocks), nodes=len(node_breaker.nodes),
                                  devices=len(devices)), untranscribed_names(FIELDS)]
    if unlocated:
        comment.append(f"no Location: block{'s' if len(unlocated) > 1 else ''} {', '.join(map(str, unlocated))} at "
                       "LATI = LONG = 0 (the default)")
    return Document(name="substation", statements=statements, profile=CIM_PROFILE,
                    comment="\n".join(filter(None, comment)))
