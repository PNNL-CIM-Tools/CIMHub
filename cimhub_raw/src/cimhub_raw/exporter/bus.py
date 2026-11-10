"""TopologicalNode (+ its BusbarSection and SvVoltage) -> Bus (``EXPORT_MAPPING.md#bus``)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.voltage import VoltageLimits, get_node_voltage, get_voltage_limits
from cimhub_raw.exporter.identity import raw_name
from cimhub_raw.importer.cimtbl.derived import per_unit_from_kv

NATIVE_CLASS = schema.BusRecord
CIM_CLASSES = (cim.BusbarSection,)
NAME_WIDTH = 12

_LIMIT = "on the bus's BusbarSection (get_voltage_limits), pu of BASKV"
SLOTS = {NATIVE_CLASS: {
    "bus_number": Slot("written", "I: busNumber"),
    "name": Slot("written", "NAME: name; blank when it is the bus number"),
    "base_voltage": Slot("written", "BASKV: get_base_voltage (kV, LL)"),
    "bus_type": Slot("rule", "IDE: 3 with a referencePriority machine, 2 with an enabled plant control, else 1"),
    "area": Slot("written", "AREA: the R5 trace; blank when untraced"),
    "zone": Slot("written", "ZONE: the number of its Substation's Region"),
    "owner": Slot("unset", "OWNER: ownership is an asset concept (CIM 18 gap)"),
    "voltage_magnitude": Slot("written", "VM: get_node_voltage v / BASKV"),
    "voltage_angle": Slot("written", "VA: get_node_voltage angle (deg)"),
    "normal_voltage_magnitude_high_limit": Slot("written", f"NVHI: normal high {_LIMIT}"),
    "normal_voltage_magnitude_low_limit": Slot("written", f"NVLO: normal low {_LIMIT}"),
    "emergency_voltage_magnitude_high_limit": Slot("written", f"EVHI: emergency high {_LIMIT}"),
    "emergency_voltage_magnitude_low_limit": Slot("written", f"EVLO: emergency low {_LIMIT}"),
}}

SWING, GENERATOR, LOAD = 3, 2, 1


def export(context) -> list[schema.BusRecord]:
    """One Bus per numbered TopologicalNode, by number."""
    limits = _bus_limits(context)
    types = _bus_types(context)
    records = []
    for node, number in sorted(context.bus_numbers.items(), key=lambda item: item[1]):
        base_kv = get_base_voltage(node, "kV", form="LL")
        voltage = get_node_voltage(node, "kV", "deg")
        bus_limits = limits.get(node, VoltageLimits(None, None, None, None))
        area = context.bus_areas.get(node)
        records.append(schema.BusRecord(
            bus_number=number, name=raw_name(node, str(number), NAME_WIDTH), base_voltage=base_kv,
            bus_type=types.get(node, LOAD), area=None if area is None else context.area_numbers[area],
            zone=_zone(node, context),
            voltage_magnitude=None if voltage is None else per_unit_from_kv(voltage.v, base_kv),
            voltage_angle=None if voltage is None else voltage.angle,
            normal_voltage_magnitude_high_limit=_per_unit(bus_limits.normal_high, base_kv),
            normal_voltage_magnitude_low_limit=_per_unit(bus_limits.normal_low, base_kv),
            emergency_voltage_magnitude_high_limit=_per_unit(bus_limits.emergency_high, base_kv),
            emergency_voltage_magnitude_low_limit=_per_unit(bus_limits.emergency_low, base_kv)))
    return records


def raw_bus(node: cim.TopologicalNode, context) -> cim.TopologicalNode:
    """The numbered node a device on ``node`` belongs to: ``node`` itself, or, for a node internal to a device (R3b's
    ``<machine>_int``, P2b's valve side), the one numbered node across the transformers on it."""
    if node in context.bus_numbers:
        return node
    across = {terminal.TopologicalNode
              for own in node.Terminal if isinstance(own.ConductingEquipment, cim.PowerTransformer)
              for terminal in own.ConductingEquipment.Terminals
              if terminal.TopologicalNode in context.bus_numbers}
    if len(across) != 1:
        raise ValueError(f"{describe(node)} has no busNumber, and its transformers reach {len(across)} numbered "
                         "nodes (one expected)")
    return across.pop()


def _bus_types(context) -> dict[cim.TopologicalNode, int]:
    """IDE of every bus with a plant: 3 with a referencePriority machine (import R3), else 2 when a machine's or
    connection's control is enabled (import R3: enabled = IDE 2/3)."""
    types: dict[cim.TopologicalNode, int] = {}
    for device in context.objects(cim.SynchronousMachine, cim.PowerElectronicsConnection):
        node = raw_bus(device.Terminals[0].TopologicalNode, context)
        if isinstance(device, cim.SynchronousMachine) and (device.referencePriority or 0) > 0:
            types[node] = SWING
        elif device.RegulatingControl is not None and device.RegulatingControl.enabled:
            types.setdefault(node, GENERATOR)
    return types


def _bus_limits(context) -> dict[cim.TopologicalNode, VoltageLimits]:
    """Each bus's voltage limits, from the one BusbarSection on it with limits; two with limits raise."""
    holder: dict[cim.TopologicalNode, cim.BusbarSection] = {}
    limits: dict[cim.TopologicalNode, VoltageLimits] = {}
    for busbar in context.objects(cim.BusbarSection):
        found = get_voltage_limits(busbar, "kV")
        if found == VoltageLimits(None, None, None, None):
            continue
        node = busbar.Terminals[0].TopologicalNode
        if node in holder:
            raise ValueError(f"{describe(holder[node])} and {describe(busbar)} both hold voltage limits of "
                             f"{describe(node)}")
        holder[node], limits[node] = busbar, found
    return limits


def _zone(node: cim.TopologicalNode, context) -> int | None:
    container = node.ConnectivityNodeContainer
    region = getattr(container, "Region", None)
    return None if region is None else context.zone_numbers[region]


def _per_unit(kv: float | None, base_kv: float) -> float | None:
    return None if kv is None else per_unit_from_kv(kv, base_kv)
