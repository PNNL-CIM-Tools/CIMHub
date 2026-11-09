"""DistributionReactor → SeriesCompensator between its buses (GDM_MAPPING.md §21, OPEN_DECISIONS 17b).

As the DSS wave's series Reactor golden writes it: ``rx_<name>`` with the ReactorEquipment's lumped r, x per phase,
and r0 = r, x0 = x (no mutual coupling). SeriesCompensator has no per-phase class, so a reactor of fewer than three
phases puts its phases on its Terminals. ReactorEquipment has no SeriesReactorInfo slot (r, x are not nameplate
fields there), so no AssetInfo is built.
"""

from __future__ import annotations

from cimbuilder.object_builder import SeriesCompensatorBuilder
from cimhub_core.cimtbl import Field

from cimhub_gdm.importer.shared import (
    UUID_FIELD,
    Naming,
    builder_phases,
    bus_base_voltage,
    bus_mrid,
    container_mrid,
    name_field,
    object_mrid,
    qty,
    require_in_service,
)

PREFIX = "rx_"

FIELDS_DistributionReactor = {
    "uuid": UUID_FIELD,
    "name": name_field(PREFIX),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "buses": Field("structural", note="Terminal 1 on bus 1, Terminal 2 on bus 2; bus 1's BaseVoltage (GDM requires "
                                      "both at one voltage)"),
    "length": Field("untranscribed", note="no CIM home: a reactor's r, x are lumped"),
    "phases": Field("structural", note="Terminal phases as written; none for ABC (G3)"),
    "equipment": Field("structural", note="r, x"),
}
FIELDS_ReactorEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline; no SeriesReactorInfo slot for r, x, so no AssetInfo"),
    "resistance": Field("copied", (("add_electrical", "r", None), ("add_short_circuit", "r0", None)),
                        note="r0 = r: no mutual coupling"),
    "reactance": Field("copied", (("add_electrical", "x", None), ("add_short_circuit", "x0", None)),
                       note="x0 = x: no mutual coupling"),
}


def add_reactor(network, reactor, naming: Naming) -> None:
    """A SeriesCompensator ``rx_<name>`` with the reactor's r, x."""
    require_in_service(reactor)
    equipment = reactor.equipment
    builder = SeriesCompensatorBuilder(network, network.container)
    compensator = builder.create(mRID=object_mrid(PREFIX, reactor, "SeriesCompensator", naming), name=reactor.name)
    first, second = reactor.buses
    builder.add_connectivity(compensator, node1=bus_mrid(first, naming), node2=bus_mrid(second, naming),
                             phases=builder_phases(reactor.phases), EquipmentContainer=container_mrid(reactor, naming),
                             BaseVoltage=bus_base_voltage(first))
    builder.add_electrical(compensator, r=qty(equipment.resistance), x=qty(equipment.reactance))
    builder.add_short_circuit(compensator, r0=qty(equipment.resistance), x0=qty(equipment.reactance))
