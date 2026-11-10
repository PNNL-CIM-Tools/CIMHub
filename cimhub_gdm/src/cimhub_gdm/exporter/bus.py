"""ConnectivityNode → DistributionBus (``EXPORT_MAPPING.md#buses``, decision X6).

Buses are rated line to ground, as ditto's DSS reader writes them: ditto's capacitor and solar writers read a bus
rating as line to ground whatever its ``voltage_type``, so a line-to-line bus would put a 3-phase capacitor at √3 times
its voltage.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.terminals import get_terminal_phases
from gdm.quantities import Voltage
from gdm.systems.distribution.components import DistributionBus
from gdm.systems.distribution.enums import Phase, VoltageTypes

from cimhub_gdm.exporter.shared import BUS_PHASE_ORDER, ExportContext, containers, gdm_phases
from cimhub_gdm.exporter.slots import UUID, Slot

CIM_CLASSES = (cim.ConnectivityNode,)

SPLIT_PHASES = {Phase.S1, Phase.S2}

SLOTS = {
    DistributionBus: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
        "substation": Slot("written", "the ConnectivityNodeContainer when it is a Substation or VoltageLevel "
                                      "(containers)"),
        "feeder": Slot("written", "the ConnectivityNodeContainer when it is a Feeder (containers)"),
        "in_service": Slot("unset", "a ConnectivityNode has no service state; GDM's default, True"),
        "voltage_type": Slot("rule", "always line-to-ground, as ditto writes buses: its capacitor and solar writers "
                                     "read every bus rating as line to ground (X6)"),
        "phases": Slot("rule", "the union of the conductors on the node's terminals, in A B C S1 S2 N order; [] when "
                               "no terminal is on it (X6)"),
        "voltagelimits": Slot("unset", "untranscribed on import: no OperationalLimitSet on a ConnectivityNode"),
        "rated_voltage": Slot("rule", "get_base_voltage(form='LN') (kV); on a split-phase bus (S1 or S2) the 120 V "
                                      "leg, get_base_voltage(form='LL') / 2 (the importer's system_voltage inverse)"),
        "coordinate": Slot("unset", "untranscribed on import: a ConnectivityNode is not a PowerSystemResource (X10)"),
    },
}


def export(node: cim.ConnectivityNode, context: ExportContext) -> DistributionBus:
    phases = bus_phases(node)
    return DistributionBus(
        **context.names.own(node),
        rated_voltage=Voltage(line_to_ground(node, phases), "kilovolt"),
        voltage_type=VoltageTypes.LINE_TO_GROUND,
        phases=phases,
        **containers(node.ConnectivityNodeContainer, context),
    )


def line_to_ground(node: cim.ConnectivityNode, phases: list) -> float:
    """The bus's line-to-ground rating in kV: half the line-to-line voltage on a split-phase bus (240 V → 120 V),
    else line to line / sqrt(3) (4.16 kV → 2.4018 kV)."""
    if SPLIT_PHASES & set(phases):
        return get_base_voltage(node, "kV", form="LL") / 2
    return get_base_voltage(node, "kV", form="LN")


def bus_phases(node: cim.ConnectivityNode) -> list:
    """Every conductor on the node's terminals, once, in ``BUS_PHASE_ORDER``."""
    found = set()
    for terminal in node.Terminals:
        found.update(gdm_phases(get_terminal_phases(terminal), terminal))
    return [phase for phase in BUS_PHASE_ORDER if phase in found]
