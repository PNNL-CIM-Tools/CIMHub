"""DistributionBus → ConnectivityNode + BaseVoltage (GDM_MAPPING.md §7).

Buses are built before any equipment, so the builders' ``add_connectivity`` reuses each ConnectivityNode.
"""

from __future__ import annotations

from cimbuilder.object_builder import BaseVoltageBuilder, ConnectivityNodeBuilder
from cimhub_core.cimtbl import Field
from cimtables.units import Qty

from cimhub_gdm.importer.shared import (
    UUID_FIELD,
    Naming,
    base_voltage_mrid,
    bus_mrid,
    container_mrid,
    name_field,
    require_in_service,
    round_significant,
    system_voltage,
)

FIELDS_DistributionBus = {
    "uuid": UUID_FIELD,
    "name": name_field(""),
    "substation": Field("structural", note="ConnectivityNodeContainer when there is no feeder"),
    "feeder": Field("structural", note="ConnectivityNodeContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "voltage_type": Field("mapped", note="selects the system_voltage factor"),
    "phases": Field("structural", note="split-phase (S1/S2) selects ×2 in system_voltage"),
    "voltagelimits": Field("untranscribed", note="an OperationalLimitSet hangs on equipment, not a ConnectivityNode"),
    "rated_voltage": Field("derived", note="BaseVoltage: system_voltage, 4 significant figures (OPEN_DECISIONS 5)"),
    "coordinate": Field("untranscribed", note="ConnectivityNode is not a PowerSystemResource (B14)"),
}


def add_bus(network, bus, naming: Naming) -> None:
    """A ConnectivityNode named after the bus, on its BaseVoltage (created the first time it is seen)."""
    require_in_service(bus)
    voltage = system_voltage(bus.rated_voltage, bus.voltage_type, bus.phases)
    base_voltage = base_voltage_mrid(voltage)
    if network.find_by_mRID(base_voltage) is None:
        BaseVoltageBuilder(network, network.container).create(
            mRID=base_voltage, nominalVoltage=Qty(round_significant(float(voltage.magnitude)), str(voltage.units)))

    builder = ConnectivityNodeBuilder(network, network.container)
    node = builder.create(mRID=bus_mrid(bus, naming), name=bus.name)
    builder.add_connectivity(node, BaseVoltage=base_voltage,
                             ConnectivityNodeContainer=container_mrid(bus, naming))

