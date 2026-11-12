"""The SUBSTATION blocks of a RAW case, indexed for the mappers (R6): which block a bus is in, each block's nodes,
and the terminal a control regulating a node names (RAW-11).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#node-breaker-substations-r6``.
"""

from __future__ import annotations

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.importer.cimtbl.bus import block_mrid, busbar_mrid

NODE_BUSBAR_PREFIX = "bb_s"  # requested from the cimtbl-translate table owners (plan C3)


def node_mrid(block: int, node: int) -> str:
    """``sub_s<IS>_n<NI>``: node numbers are unique only within their block."""
    return f"{block_mrid(block)}_n{node}"


def node_busbar_mrid(block: int, node: int) -> str:
    """``bb_s<IS>_n<NI>``: the BusbarSection a control regulating the node names (RAW-11)."""
    return f"{NODE_BUSBAR_PREFIX}{block}_n{node}"


class NodeBreaker:
    """The case's SUBSTATION blocks: ``blocks`` (IS -> record), ``nodes`` ((IS, NI) -> node record) and
    ``block_of_bus`` (bus -> IS). A node on no bus, a node number twice in a block, or a bus in two blocks raises."""

    def __init__(self, native, buses):
        self.blocks = {record.substation_number: record for record in native.list_by_class(schema.SubstationRecord)}
        self.nodes: dict[tuple[int, int], schema.SubstationNodeRecord] = {}
        self.block_of_bus: dict[int, int] = {}
        for node in native.list_by_class(schema.SubstationNodeRecord):
            key = (node.substation_number, node.node_number)
            record_id = f"SUBSTATION block {key[0]} node {key[1]}"
            if key in self.nodes:
                raise ValueError(f"{record_id}: the node number is given twice in the block")
            if node.bus_number not in buses:
                raise ValueError(f"{record_id}: bus {node.bus_number} is no bus")
            if self.block_of_bus.setdefault(node.bus_number, key[0]) != key[0]:
                raise ValueError(f"{record_id}: bus {node.bus_number} also has nodes in block "
                                 f"{self.block_of_bus[node.bus_number]}")
            self.nodes[key] = node

    def node(self, bus: int, number: int, record_id: str) -> tuple[int, schema.SubstationNodeRecord]:
        """``(IS, node record)`` of node ``number`` of ``bus``; a bus with no block, or no such node of the bus,
        raises."""
        if bus not in self.block_of_bus:
            raise ValueError(f"{record_id}: node {number} of bus {bus}, which has no SUBSTATION block")
        block = self.block_of_bus[bus]
        node = self.nodes.get((block, number))
        if node is None or node.bus_number != bus:
            raise ValueError(f"{record_id}: SUBSTATION block {block} has no node {number} of bus {bus}")
        return block, node

    def regulated_terminal(self, bus: int, number: int | None, record_id: str) -> str:
        """The Terminal a control regulating ``bus`` names: the bus's busbar ``bb_<I>_T1``, or, for a nonzero node
        ``number`` (NREG, NODk), that node's busbar ``bb_s<IS>_n<NI>_T1``."""
        if not number:
            return f"{busbar_mrid(bus)}_T1"
        block, _ = self.node(bus, number, record_id)
        return f"{node_busbar_mrid(block, number)}_T1"
