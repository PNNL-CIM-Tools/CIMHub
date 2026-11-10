"""A bus's AREA, traced over the bound CIM (``EXPORT_MAPPING.md#a-buss-area-area_tracepy-r5``).

CIM 18 has no node -> ControlArea association, so the importer records the area through what CIM already places in
one: generating units (R3) and tie flows (R5). Seeds: the node of every SynchronousMachine and
PowerElectronicsConnection, with its unit's ControlArea; a TieFlow pair's terminal, with the pair's
``positiveFlowIn = false`` area; the other terminals of that device, with the pair's ``true`` (home) area. The areas
spread across every device with two or more nodes and no TieFlow. The importer's ``untraced_area_buses`` runs the
same rule over the RAW records.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_raw.importer.topology import islands


def trace_areas(network) -> dict[cim.TopologicalNode, cim.ControlArea | None]:
    """Every TopologicalNode's ControlArea; ``None`` for a node in an island with no seed. Two areas meeting in one
    island raise."""
    nodes = list(network.graph.get(cim.TopologicalNode, {}).values())
    seeds: dict[cim.TopologicalNode, list[tuple[cim.ControlArea, object]]] = {}

    def seed(node, area, source) -> None:
        seeds.setdefault(node, []).append((area, source))

    for machine in _objects(network, cim.SynchronousMachine):
        for area in _unit_areas(machine.GeneratingUnit, "ControlAreaGeneratingUnit"):
            seed(_node(machine.Terminals[0]), area, machine)
    for connection in _objects(network, cim.PowerElectronicsConnection):
        for unit in connection.PowerElectronicsUnit:
            for area in _unit_areas(unit, "ControlAreaPowerElectronicsUnit"):
                seed(_node(connection.Terminals[0]), area, connection)
    edges = []
    for equipment in _conducting_equipment(network):
        terminals = list(equipment.Terminals)
        tied = [terminal for terminal in terminals if terminal.TieFlow]
        if tied:
            for terminal in tied:
                own, home = _pair_areas(terminal)
                seed(_node(terminal), own, terminal)
                for other in terminals:
                    if other is not terminal and not other.TieFlow:
                        seed(_node(other), home, terminal)
            continue
        ends = [_node(terminal) for terminal in terminals if terminal.TopologicalNode is not None]
        edges.extend((equipment.mRID, ends[0], end) for end in ends[1:] if end is not ends[0])
    areas: dict[cim.TopologicalNode, cim.ControlArea | None] = {}
    for group in islands(nodes, edges):
        found = [(area, source) for node in group for area, source in seeds.get(node, [])]
        distinct = {area for area, _ in found}
        if len(distinct) > 1:
            raise ValueError(f"buses joined inside one area are seeded with {sorted(a.mRID for a in distinct)} "
                             f"(by {sorted({describe(source) for _, source in found})[:4]})")
        area = distinct.pop() if distinct else None
        areas.update((node, area) for node in group)
    return areas


def _objects(network, cim_class) -> list:
    return list(network.graph.get(cim_class, {}).values())


def _conducting_equipment(network) -> list:
    return [obj for cls, objects in network.graph.items() if issubclass(cls, cim.ConductingEquipment)
            for obj in objects.values()]


def _node(terminal: cim.Terminal) -> cim.TopologicalNode:
    if terminal.TopologicalNode is None:
        raise ValueError(f"{describe(terminal)}: has no TopologicalNode (a bus-branch model, X3)")
    return terminal.TopologicalNode


def _unit_areas(unit, membership: str) -> list[cim.ControlArea]:
    return [] if unit is None else [member.ControlArea for member in getattr(unit, membership)]


def _pair_areas(terminal: cim.Terminal) -> tuple[cim.ControlArea, cim.ControlArea]:
    """A tie terminal's (own area, home area): its TieFlows with ``positiveFlowIn`` false and true (R5)."""
    by_flow = {}
    for tie_flow in terminal.TieFlow:
        if tie_flow.positiveFlowIn in by_flow:
            raise ValueError(f"{describe(terminal)}: two TieFlows with positiveFlowIn = {tie_flow.positiveFlowIn}")
        by_flow[tie_flow.positiveFlowIn] = tie_flow.ControlArea
    if set(by_flow) != {False, True}:
        raise ValueError(f"{describe(terminal)}: TieFlows are not a pair (positiveFlowIn {sorted(by_flow)})")
    return by_flow[False], by_flow[True]


def metered_terminal(device) -> int | None:
    """The ``sequenceNumber`` of the device's terminal holding its TieFlow pair (a tie's metered end, R5); None off
    a tie. Pairs on two terminals of a two-terminal device raise: MET names one end."""
    holding = [terminal.sequenceNumber for terminal in device.Terminals if terminal.TieFlow]
    if len(holding) > 1:
        raise ValueError(f"{describe(device)}: TieFlows on terminals {sorted(holding)}; MET names one metered end")
    return holding[0] if holding else None
