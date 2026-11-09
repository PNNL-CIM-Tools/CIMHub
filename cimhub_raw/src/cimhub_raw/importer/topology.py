"""Substations of a bus-branch RAW case: buses joined by equipment that sits inside a substation (plan 3.2).

The merge equipment, never across a zone boundary:
- every system switching device;
- a zero-impedance branch, R = 0 and |X| <= THRSHZ;
- a branch whose CKT starts with ``@`` or ``*``;
- a series capacitor, X < 0 (RAW-15);
- every transformer, all of its windings' buses.

A SUBSTATION block (R6) joins every bus its nodes name, and takes precedence: the group holding it is the block's
substation. A group holding two blocks, or a block across two zones, raises.

The grouping is ``cimtopology.core.Topology(...).islands()`` over a network of only the merge edges, with every bus
listed, so a bus on no merge edge is its own substation. No union-find here.
"""

from __future__ import annotations

from typing import NamedTuple

from cimtopology.core.network import Branch, Network, Topology

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import schema_defaults


class SubstationGroup(NamedTuple):
    buses: tuple[int, ...]  # ascending; the first names the substation unless it holds a block
    merged_by: tuple[str, ...]  # the merge edges inside the group, as equipment mRIDs
    block: int | None = None  # the SUBSTATION block (IS) the group holds (R6)


def _value(record, slot: str):
    """A slot's value, or its ``raw_default`` when blank; a blank with no default raises."""
    value = getattr(record, slot)
    if value is None:
        defaults = schema_defaults(type(record), "raw_default")
        if slot not in defaults:
            raise ValueError(f"{type(record).__name__} {record.ID}: {slot} is blank and has no default")
        value = defaults[slot]
    return value


def _merge_edges(native, threshold: float) -> list[tuple[str, int, int]]:
    """``(equipment mRID, bus, bus)`` for every merge edge."""
    edges = [(f"sw_{switch.ID}", switch.from_bus_number, switch.to_bus_number)
             for switch in native.list_by_class(schema.SwitchRecord)]
    for branch in native.list_by_class(schema.BranchRecord):
        r, x = float(_value(branch, "r")), float(_value(branch, "x"))
        circuit = str(_value(branch, "circuit")).strip()
        if x < 0.0:  # a series capacitor, mapped as a SeriesCompensator (RAW-15)
            edges.append((f"sc_{branch.ID}", branch.from_bus_number, branch.to_bus_number))
        elif (r == 0.0 and abs(x) <= threshold) or circuit[:1] in ("@", "*"):
            edges.append((f"ln_{branch.ID}", branch.from_bus_number, branch.to_bus_number))
    for transformer in native.list_by_class(schema.TransformerRecord):
        windings = [transformer.i, transformer.j] + ([transformer.k] if transformer.k else [])
        edges.extend((f"xf_{transformer.ID}", windings[0], bus) for bus in windings[1:])
    return edges


def _islands(buses, edges: list[tuple[str, int, int]]) -> list[list[int]]:
    """The bus groups joined by ``edges``, each in ascending order; a bus on no edge is its own group."""
    # cimtopology wants unique equipment names; a 3-winding transformer gives two edges
    network = Network(sources=(), transformers=(), nodes=tuple(str(bus) for bus in sorted(buses)),
                      branches=tuple(Branch(f"{name}#{index}", str(first), str(second))
                                     for index, (name, first, second) in enumerate(edges)))
    members: dict[str, list[int]] = {}
    for bus, root in Topology(network).islands().items():
        members.setdefault(root, []).append(int(bus))
    return [sorted(group) for group in members.values()]


def _block_edges(block_of_bus: dict[int, int], zones: dict[int, int]) -> list[tuple[str, int, int]]:
    """``(None, bus, bus)`` joining each block's buses; a block across two zones raises."""
    buses_of: dict[int, list[int]] = {}
    for bus, block in sorted(block_of_bus.items()):
        buses_of.setdefault(block, []).append(bus)
    edges = []
    for block, buses in sorted(buses_of.items()):
        block_zones = sorted({zones[bus] for bus in buses})
        if len(block_zones) > 1:
            raise ValueError(f"SUBSTATION block {block}: buses {buses} are in zones {block_zones}; a Substation has "
                             "one Region")
        edges.extend((None, buses[0], bus) for bus in buses[1:])
    return edges


def substation_groups(native, zones: dict[int, int], threshold: float,
                      block_of_bus: dict[int, int]) -> list[SubstationGroup]:
    """The case's substations, ordered by their lowest bus number. ``block_of_bus``: bus -> its SUBSTATION block
    (``NodeBreaker.block_of_bus``)."""
    edges = [edge for edge in _merge_edges(native, threshold) if zones[edge[1]] == zones[edge[2]]]
    edges += _block_edges(block_of_bus, zones)
    groups = []
    for buses in _islands(zones, edges):
        inside = set(buses)
        merged_by = sorted({name for name, first, _ in edges if name and first in inside})
        blocks = sorted({block_of_bus[bus] for bus in buses if bus in block_of_bus})
        if len(blocks) > 1:
            raise ValueError(f"buses {buses} form one substation holding SUBSTATION blocks {blocks} (merged by "
                             f"{', '.join(merged_by)})")
        groups.append(SubstationGroup(tuple(buses), tuple(merged_by), blocks[0] if blocks else None))
    return sorted(groups, key=lambda group: group.buses[0])


def _devices(native, node_bus: dict[tuple[int, int], int]) -> list[tuple[str, tuple[int, ...]]]:
    """``(record ID, its terminals' buses)`` of every branch, switching device (system or substation) and
    transformer. ``node_bus``: (IS, NI) -> the node's bus."""
    devices = [(switch.ID, (switch.from_bus_number, switch.to_bus_number))
               for switch in native.list_by_class(schema.SwitchRecord)]
    devices += [(branch.ID, (branch.from_bus_number, branch.to_bus_number))
                for branch in native.list_by_class(schema.BranchRecord)]
    devices += [(transformer.ID, (transformer.i, transformer.j) + ((transformer.k,) if transformer.k else ()))
                for transformer in native.list_by_class(schema.TransformerRecord)]
    for device in native.list_by_class(schema.StationSwitchingDeviceRecord):
        ends = []
        for node in (device.from_node, device.to_node):
            if (device.substation_number, node) not in node_bus:
                raise ValueError(f"substation switching device {device.ID}: node {node} is not in SUBSTATION block "
                                 f"{device.substation_number}")
            ends.append(node_bus[(device.substation_number, node)])
        devices.append((device.ID, tuple(ends)))
    return devices


def untraced_area_buses(native, bus_area: dict[int, int], node_bus: dict[tuple[int, int], int]) -> set[int]:
    """The buses whose AREA the export trace cannot recover (R5, RAW-2).

    The trace seeds a generator's bus and every bus of a tie (a device whose buses are in more than one AREA: its
    TieFlows name them), then spreads across the devices whose buses share one AREA. A group of buses with no seed
    is untraced. Loads are no seed: a load's AREA is its own (R2). ``node_bus``: (IS, NI) -> the node's bus (R6).
    """
    seeds = {generator.bus_number for generator in native.list_by_class(schema.GeneratorRecord)}
    edges = []
    for record_id, buses in _devices(native, node_bus):
        if len({bus_area[bus] for bus in buses}) > 1:
            seeds.update(buses)
        else:
            # a substation switching device between two nodes of one bus joins nothing
            edges.extend((record_id, buses[0], bus) for bus in buses[1:] if bus != buses[0])
    return {bus for group in _islands(bus_area, edges) if not seeds.intersection(group) for bus in group}
