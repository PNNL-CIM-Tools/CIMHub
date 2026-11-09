"""Substations of a bus-branch RAW case: buses joined by equipment that sits inside a substation (plan 3.2).

The merge equipment, never across a zone boundary:
- every system switching device;
- a zero-impedance branch, R = 0 and |X| <= THRSHZ;
- a branch whose CKT starts with ``@`` or ``*``;
- a series capacitor, X < 0 (RAW-15);
- every transformer, all of its windings' buses.

The grouping is ``cimtopology.core.Topology(...).islands()`` over a network of only the merge edges, with every bus
listed, so a bus on no merge edge is its own substation. No union-find here.
"""

from __future__ import annotations

from typing import NamedTuple

from cimtopology.core.network import Branch, Network, Topology

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import schema_defaults


class SubstationGroup(NamedTuple):
    buses: tuple[int, ...]  # ascending; the first names the substation
    merged_by: tuple[str, ...]  # the merge edges inside the group, as equipment mRIDs


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


def substation_groups(native, zones: dict[int, int], threshold: float) -> list[SubstationGroup]:
    """The case's substations, ordered by their lowest bus number."""
    edges = [edge for edge in _merge_edges(native, threshold) if zones[edge[1]] == zones[edge[2]]]
    # cimtopology wants unique equipment names; a 3-winding transformer gives two edges
    network = Network(sources=(), transformers=(), nodes=tuple(str(bus) for bus in sorted(zones)),
                      branches=tuple(Branch(f"{name}#{index}", str(first), str(second))
                                     for index, (name, first, second) in enumerate(edges)))
    members: dict[str, list[int]] = {}
    for bus, root in Topology(network).islands().items():
        members.setdefault(root, []).append(int(bus))
    groups = []
    for buses in members.values():
        inside = set(buses)
        merged_by = sorted({name for name, first, _ in edges if first in inside})
        groups.append(SubstationGroup(tuple(sorted(buses)), tuple(merged_by)))
    return sorted(groups, key=lambda group: group.buses[0])
