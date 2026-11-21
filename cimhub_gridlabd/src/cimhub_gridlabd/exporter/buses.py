"""ConnectivityNode -> ``node`` / ``triplex_node``, EnergySource -> ``substation`` (the swing)
(``EXPORT_MAPPING.md#x0-framework-writer-nodes-and-the-swing``, decisions X1, X6).

GLM gives a bus its phase letters and a ``nominal_voltage`` that depends on its system, which CIM does not store:
line to neutral on a three-phase system, the coil voltage on a single-phase one, one leg (s1 to N) on a split-phase
one, each from the node's BaseVoltage (line to line). The system is read per voltage zone (buses joined without a
transformer: ``cimtopology.core.Topology.voltage_zones``) from what lands in it, in this order:

1. a terminal on s1 or s2: split phase, a ``triplex_node`` whose phase letter is the service's (the A, B or C of the
   primary of the centre-tap transformers in the zone, which must agree);
2. the EnergySource, a transformer end on two or three of A, B, C, or one-phase ends on different phases (a bank,
   as ``cimtopology``'s walk reads it): three phase;
3. one-phase transformer ends, all on one phase: single phase.

A zone none of these reach raises. A bus's letters are the A, B, C of every terminal on it, then ``N``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtopology.core import Branch, Network, System, Topology

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.source import get_source
from cimhub_core.getters.terminals import get_terminal_phases
from cimhub_gridlabd.schema import gridlabd as schema

CIM_CLASSES = (cim.EnergySource,)
PHASE_LETTERS = "ABC"
SPLIT = (cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2)
#: equipment that joins two buses and keeps the voltage, with its subclasses (a regulator is an AutoTransformer,
#: ideal in GLM)
BRANCH_CLASSES = (cim.ACLineSegment, cim.Switch, cim.SeriesCompensator, cim.AutoTransformer)

_NOT_IN_CIM = "not in CIM; GridLAB-D's default"
NODE_SLOTS = {
    "name": Slot("written", "Names (X1)"),
    "phases": Slot("written", "the A, B, C of every terminal on the node, then N"),
    "nominal_voltage": Slot("written", "the BaseVoltage, LL / sqrt 3 on a three-phase system, LL on a single-phase "
                                       "one (module docstring)"),
    "bustype": Slot("written", "SWING on the substation only"),
}
TRIPLEX_SLOTS = {
    "name": NODE_SLOTS["name"],
    "phases": Slot("written", "the service's letter, then S"),
    "nominal_voltage": Slot("written", "the BaseVoltage (s1 to s2) / 2: one leg"),
}
SUBSTATION_SLOTS = {
    **NODE_SLOTS,
    "positive_sequence_voltage": Slot("written", "get_source: voltageMagnitude / sqrt 3 at voltageAngle"),
}
SLOTS = {
    schema.Node: with_default(schema.Node, NODE_SLOTS, Slot("unset", _NOT_IN_CIM)),
    schema.TriplexNode: with_default(schema.TriplexNode, TRIPLEX_SLOTS, Slot("unset", _NOT_IN_CIM)),
    schema.Substation: with_default(schema.Substation, SUBSTATION_SLOTS,
                                    Slot("unset", f"{_NOT_IN_CIM}; GLM's swing is ideal: the source impedance is "
                                                  f"not written (X6)")),
}


class Bus(NamedTuple):
    name: str
    system: System
    letters: str  # A, B, C in order; a split-phase bus's is its service's one letter
    nominal_voltage: float  # V, GLM's (module docstring)

    @property
    def phases(self) -> str:
        """GLM's phases: ``ABCN``, ``CN``; a split-phase bus ``BS``."""
        return self.letters + ("S" if self.system is System.SPLIT_PHASE else "N")


def letters(phases) -> str:
    """The A, B, C among ``phases`` (SinglePhaseKinds), in ABC order."""
    found = {phase.value for phase in phases}
    return "".join(letter for letter in PHASE_LETTERS if letter in found)


def bus_table(network, names) -> dict[cim.ConnectivityNode, Bus]:
    """Every ConnectivityNode's GLM bus."""
    nodes = list(network.graph.get(cim.ConnectivityNode, {}).values())
    terminals = defaultdict(list)
    for terminal in network.graph.get(cim.Terminal, {}).values():
        if terminal.ConnectivityNode is not None:
            terminals[terminal.ConnectivityNode.mRID].append(terminal)
    zone_of = _zones(network, nodes)
    systems = _zone_systems(network, zone_of, terminals)
    buses = {}
    for node in nodes:
        system, service = systems[zone_of[node.mRID]]
        on_node = letters(phase for terminal in terminals[node.mRID] for phase in get_terminal_phases(terminal))
        buses[node] = Bus(names.name(node), system, service if system is System.SPLIT_PHASE else on_node,
                          _nominal_voltage(node, system))
    return buses


def export(context) -> list:
    """A node per bus, the swing's a substation."""
    swings = {}
    for source in context.objects(cim.EnergySource):
        node = _single_terminal(source).ConnectivityNode
        if node in swings:
            raise ValueError(f"EnergySources {swings[node].mRID!r} and {source.mRID!r} share a node")
        swings[node] = source
    if len(swings) > 1:
        raise ValueError(f"{len(swings)} EnergySources; GridLAB-D's NR solver takes one swing")
    records = []
    for node, bus in context.buses.items():
        if node in swings:
            records.append(_substation(bus, swings[node]))
        elif bus.system is System.SPLIT_PHASE:
            records.append(schema.TriplexNode(name=bus.name, phases=bus.phases, nominal_voltage=bus.nominal_voltage))
        else:
            records.append(schema.Node(name=bus.name, phases=bus.phases, nominal_voltage=bus.nominal_voltage))
    return records


def _substation(bus: Bus, source: cim.EnergySource) -> schema.Substation:
    values = get_source(source, angle_unit="rad")
    magnitude = values.magnitude / math.sqrt(3)
    angle = values.angle or 0.0  # an unset angle is CIM's reference angle, 0
    voltage = schema.Complex(real=magnitude * math.cos(angle), imag=magnitude * math.sin(angle))
    return schema.Substation(name=bus.name, phases=bus.phases, nominal_voltage=bus.nominal_voltage, bustype="SWING",
                             positive_sequence_voltage=voltage)


def _single_terminal(equipment) -> cim.Terminal:
    if len(equipment.Terminals) != 1:
        raise ValueError(f"{type(equipment).__name__} {equipment.mRID!r}: has {len(equipment.Terminals)} terminals")
    return equipment.Terminals[0]


def _zones(network, nodes) -> dict[str, str]:
    """ConnectivityNode mRID -> its voltage zone."""
    branches = []
    for cim_class, objects in network.graph.items():
        if not issubclass(cim_class, BRANCH_CLASSES):
            continue
        for equipment in objects.values():
            ends = sorted(equipment.Terminals, key=lambda terminal: terminal.sequenceNumber)
            if len(ends) != 2 or None in (ends[0].ConnectivityNode, ends[1].ConnectivityNode):
                raise ValueError(f"{type(equipment).__name__} {equipment.mRID!r}: needs two connected terminals")
            branches.append(Branch(equipment.mRID, ends[0].ConnectivityNode.mRID, ends[1].ConnectivityNode.mRID))
    topology = Topology(Network(sources=(), branches=tuple(branches), transformers=(),
                                nodes=tuple(node.mRID for node in nodes)))
    return topology.voltage_zones()


def _zone_systems(network, zone_of: dict[str, str], terminals) -> dict[str, tuple[System, str]]:
    """zone -> (system, the split-phase service's letter or "")."""
    split, three = set(), set()
    single = defaultdict(set)  # zone -> the letters its one-phase ends are on
    services = defaultdict(set)
    for node_mrid, on_node in terminals.items():
        if any(phase in SPLIT for terminal in on_node for phase in get_terminal_phases(terminal)):
            split.add(zone_of[node_mrid])
    for source in network.graph.get(cim.EnergySource, {}).values():
        three.add(zone_of[_single_terminal(source).ConnectivityNode.mRID])
    for transformer in network.graph.get(cim.PowerTransformer, {}).values():
        ends = [(end, get_terminal_phases(end.Terminal)) for end in transformer.PowerTransformerEnd]
        primary_letters = letters(phase for end, phases in ends if not set(phases) & set(SPLIT) for phase in phases)
        for end, phases in ends:
            zone = zone_of[end.Terminal.ConnectivityNode.mRID]
            if set(phases) & set(SPLIT):
                services[zone].add(primary_letters)
            elif len(letters(phases)) >= 2:
                three.add(zone)
            else:
                single[zone].add(letters(phases))
    three |= {zone for zone, phase_letters in single.items() if len(phase_letters) > 1}
    systems = {}
    for zone in set(zone_of.values()):
        if zone in split:
            if len(services[zone]) != 1 or len(next(iter(services[zone]))) != 1:
                raise ValueError(f"split-phase zone of bus {zone!r}: its centre taps' primaries are on "
                                 f"{sorted(services[zone]) or 'no phase'}, not one phase")
            systems[zone] = (System.SPLIT_PHASE, next(iter(services[zone])))
        elif zone in three:
            systems[zone] = (System.THREE_PHASE, "")
        elif zone in single:
            systems[zone] = (System.SINGLE_PHASE, "")
        else:
            raise ValueError(f"the zone of bus {zone!r} has no source and no transformer end: its system is unknown")
    return systems


def _nominal_voltage(node: cim.ConnectivityNode, system: System) -> float:
    line_to_line = get_base_voltage(node, "V", form="LL")
    if system is System.THREE_PHASE:
        return line_to_line / math.sqrt(3)
    if system is System.SPLIT_PHASE:
        return line_to_line / 2
    return line_to_line
