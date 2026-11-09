"""DistributionVoltageSource → EnergySource (GDM_MAPPING.md §6).

EnergySourcePhase has only ``phase``, so every per-phase value must be equal; the phase angles must be 120° apart.
"""

from __future__ import annotations

from cimbuilder.object_builder import EnergySourceBuilder
from cimhub_core.cimtbl import Field, mrid

from cimhub_gdm.importer.shared import (builder_phases, bus_base_voltage, bus_mrid, container_mrid, qty,
                                        require_in_service, system_voltage)

PREFIX = "src_"

FIELDS_DistributionVoltageSource = {
    "uuid": Field("structural", note="never the mRID; only rehashed for an empty or clashing name (B18)"),
    "name": Field("copied", (("create", "mRID", None), ("create", "name", None)), note="mRID = src_ + name"),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "bus": Field("structural", note="node; BaseVoltage; nominalVoltage = the bus's system voltage"),
    "phases": Field("structural", note="builder_phases: None for balanced ABC"),
    "equipment": Field("structural", note="inline VoltageSourceEquipment"),
}

FIELDS_VoltageSourceEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline: no CIM object of its own"),
    "sources": Field("structural", note="one per phase; all equal (EnergySourcePhase has only phase)"),
}

FIELDS_PhaseVoltageSourceEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline: no CIM object of its own"),
    "r0": Field("copied", (("add_short_circuit", "r0", None),)),
    "r1": Field("copied", (("add_electrical", "r", None),)),
    "x0": Field("copied", (("add_short_circuit", "x0", None),)),
    "x1": Field("copied", (("add_electrical", "x", None),)),
    "voltage": Field("derived", note="voltageMagnitude = system_voltage(voltage, voltage_type, phases)"),
    "voltage_type": Field("mapped", note="selects the system_voltage factor"),
    "angle": Field("copied", (("add_ssh", "voltageAngle", None),),
                   note="the first phase's angle; the others must be 120° apart (either direction, G2)"),
}

_EQUAL_FIELDS = ("r0", "r1", "x0", "x1", "voltage", "voltage_type")


def add_source(network, source, system_name: str) -> None:
    """An EnergySource on the source's bus, from its (equal) per-phase values."""
    require_in_service(source)
    phase_sources = source.equipment.sources
    if len(phase_sources) != len(source.phases):
        raise ValueError(f"DistributionVoltageSource {source.name!r}: {len(phase_sources)} phase sources for "
                         f"{len(source.phases)} phases")
    for field in _EQUAL_FIELDS:
        values = [getattr(s, field) for s in phase_sources]
        if any(value != values[0] for value in values):
            raise ValueError(f"DistributionVoltageSource {source.name!r}: {field} differs by phase ({values}); "
                             "EnergySourcePhase has only phase")
    check_phase_angles(source.name, [s.angle for s in phase_sources])
    first = phase_sources[0]
    bus = source.bus

    builder = EnergySourceBuilder(network, network.container)
    energy_source = builder.create(mRID=mrid(PREFIX, source.name), name=source.name)
    builder.add_connectivity(
        energy_source,
        node=bus_mrid(bus),
        nominalVoltage=qty(system_voltage(bus.rated_voltage, bus.voltage_type, bus.phases)),
        phases=builder_phases(source.phases),
        EquipmentContainer=container_mrid(source, system_name),
        BaseVoltage=bus_base_voltage(bus),
    )
    builder.add_electrical(energy_source, r=qty(first.r1), x=qty(first.x1))
    builder.add_short_circuit(energy_source, r0=qty(first.r0), x0=qty(first.x0))
    builder.add_ssh(energy_source,
                    voltageMagnitude=qty(system_voltage(first.voltage, first.voltage_type, source.phases)),
                    voltageAngle=qty(first.angle))


def check_phase_angles(name: str, angles) -> None:
    """Raise unless consecutive phase angles step by the same ±120° (G2: ditto writes +120°, OpenDSS −120°)."""
    steps = {round(float((later - earlier).to("degree").magnitude) % 360, 3)
             for earlier, later in zip(angles, angles[1:])}
    if len(steps) > 1 or not steps <= {120.0, 240.0}:
        raise ValueError(f"DistributionVoltageSource {name!r}: phase angles {[str(a) for a in angles]} are not "
                         "120° apart")
