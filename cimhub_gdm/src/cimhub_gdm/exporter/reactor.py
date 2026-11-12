"""SeriesCompensator → DistributionReactor between its buses (``EXPORT_MAPPING.md#reactors``, X4).

The importer's §21, inverted. ``get_series_compensator`` gives r and x per phase, lumped, which go on an inline
ReactorEquipment (the importer builds no SeriesReactorInfo). GDM's reactor has no zero sequence, so r0 or x0 other
than r or x raises (no mutual coupling, as the DSS goldens write it), and no varistor, so one present raises.
``length`` has no CIM home and is a fill (X4): the impedance is lumped, and ditto writes no length for a reactor.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters import describe
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from gdm.quantities import Reactance
from gdm.systems.distribution.components import DistributionReactor
from gdm.systems.distribution.equipment import ReactorEquipment
from infrasys.quantities import Resistance

from cimhub_gdm.exporter import fills
from cimhub_gdm.exporter.shared import ExportContext, containers, gdm_phases, in_service
from cimhub_gdm.exporter.slots import UUID, Slot

CIM_CLASSES = (cim.SeriesCompensator,)

SLOTS = {
    DistributionReactor: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
        "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
        "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
        "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
        "buses": Slot("written", "the buses of get_terminal_nodes: Terminal 1, Terminal 2"),
        "length": Slot("fill", "fills.REACTOR_LENGTH, 1 m: the impedance is lumped; ditto writes no length"),
        "phases": Slot("written", "get_conductor_phases (balanced ABC on none, G3)"),
        "equipment": Slot("written", "a ReactorEquipment made for this reactor"),
    },
    ReactorEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the reactor's name (X2)"),
        "resistance": Slot("written", "get_series_compensator.r (ohm); r0 other than r raises"),
        "reactance": Slot("written", "get_series_compensator.x (ohm); x0 other than x raises"),
    },
}


def export(compensator: cim.SeriesCompensator, context: ExportContext) -> DistributionReactor:
    data = get_series_compensator(compensator)
    coupled = [f"{zero_name} {zero} ohm" for zero_name, zero, positive in (("r0", data.r0, data.r), ("x0", data.x0, data.x))
               if zero is not None and not math.isclose(zero, positive)]
    if coupled:
        raise ValueError(f"{describe(compensator)}: {', '.join(coupled)} differ from r {data.r}, x {data.x} ohm; GDM's "
                         "ReactorEquipment has no zero sequence")
    if data.varistor_present:
        raise ValueError(f"{describe(compensator)}: has a varistor; GDM's reactor has none")
    node1, node2 = get_terminal_nodes(compensator)
    names = context.names
    return DistributionReactor(
        **names.own(compensator),
        buses=[context.gdm(node1), context.gdm(node2)],
        phases=gdm_phases(get_conductor_phases(compensator), compensator),
        length=context.fill("DistributionReactor.length", fills.REACTOR_LENGTH),
        equipment=ReactorEquipment(**names.part(compensator, ReactorEquipment),
                                   resistance=Resistance(data.r, "ohm"), reactance=Reactance(data.x, "ohm")),
        in_service=in_service(compensator),
        **containers(compensator.EquipmentContainer, context),
    )
