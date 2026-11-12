"""DistributionCapacitor → LinearShuntCompensator, its controller → RegulatingControl (GDM_MAPPING.md §6, §17).

The compensator holds the totals: nomQ summed over phases, nomU across one unit (line-to-line for balanced ABC, the
rating as written otherwise, as the DSS wave writes it), bPerSection = nomQ / (nomU² · maximumSections) by the
builder. Per-phase values that differ raise. A controller monitors the capacitor's own Terminal: GDM names no
monitored element.
"""

from __future__ import annotations

from cimbuilder.object_builder import LinearShuntCompensatorBuilder, RegulatingControlBuilder
from cimhub_core.cimtbl import Field, lookup
from gdm.systems.distribution.controllers import (
    ActivePowerCapacitorController,
    CurrentCapacitorController,
    ReactivePowerCapacitorController,
    VoltageCapacitorController,
)
from gdm.systems.distribution.enums import ConnectionType, Phase, VoltageTypes

from cimhub_gdm.importer.shared import (
    PHASE,
    SHUNT_CONNECTION,
    UUID_FIELD,
    Naming,
    builder_phases,
    bus_base_voltage,
    bus_mrid,
    container_mrid,
    name_field,
    object_mrid,
    power_qty,
    qty,
    require_in_service,
    system_voltage,
)

PREFIX = "cap_"
CONTROL_PREFIX = "cc_"

#: Controller class → (mode, on slot, off slot, SI unit of targetValue, ratio slot, RegulatingControl ratio keyword).
#: targetValue and targetDeadband are unitless floats in CIM, in the mode's SI unit on the primary side.
CONTROLLER_SETTINGS = {
    VoltageCapacitorController: ("voltage", "on_voltage", "off_voltage", "volt", "pt_ratio", "ptRatio"),
    CurrentCapacitorController: ("currentFlow", "on_current", "off_current", "ampere", "ct_ratio", "ctRatio"),
    ActivePowerCapacitorController: ("activePower", "on_power", "off_power", "watt", None, None),
    ReactivePowerCapacitorController: ("reactivePower", "on_power", "off_power", "var", None, None),
}

_INLINE = "inline: no CIM object of its own"

FIELDS_DistributionCapacitor = {
    "uuid": UUID_FIELD,
    "name": name_field(PREFIX),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "bus": Field("structural", note="node; BaseVoltage"),
    "phases": Field("structural", note="None for balanced ABC, else a LinearShuntCompensatorPhase each; N raises"),
    "controllers": Field("structural", note=f"one RegulatingControl {CONTROL_PREFIX}<name>; one controller, or one "
                                            "per phase, all equal"),
    "equipment": Field("structural", note="inline"),
    "state": Field("structural", note="one entry or one per phase, all equal (G6): sections = num_banks_on when on, "
                                      "else 0"),
}
FIELDS_CapacitorEquipment = {
    "uuid": Field("untranscribed", note=_INLINE),
    "name": Field("untranscribed", note=_INLINE),
    "phase_capacitors": Field("structural", note="one per phase, equal; nomQ is their sum"),
    "connection_type": Field("mapped", note="SHUNT_CONNECTION → phaseConnection, grounded"),
    "rated_voltage": Field("derived", note="nomU: line-to-line for balanced ABC (system_voltage), else as written"),
    "voltage_type": Field("structural", note="selects the system_voltage factor; must match the connection off ABC"),
}
FIELDS_PhaseCapacitorEquipment = {
    "uuid": Field("untranscribed", note=_INLINE),
    "name": Field("untranscribed", note=_INLINE),
    "resistance": Field("untranscribed", note="no home on LinearShuntCompensator"),
    "reactance": Field("untranscribed", note="no home on LinearShuntCompensator"),
    "rated_reactive_power": Field("copied", (("add_electrical", "nomQ", None),), note="summed over phases"),
    "num_banks_on": Field("copied", (("add_electrical", "normalSections", None), ("add_ssh", "sections", None)),
                          note="0 when state is off"),
    "num_banks": Field("copied", (("add_electrical", "maximumSections", None),)),
}
_CONTROLLER_FIELDS = {
    "uuid": Field("untranscribed", note=_INLINE),
    "name": Field("untranscribed", note="inline; the control is named after its capacitor"),
    "delay_on": Field("copied", (("add_regulating_control", "aVRDelay", None),)),
    "delay_off": Field("untranscribed", note="CIM has one delay, aVRDelay"),
    "dead_time": Field("untranscribed", note="no CIM home"),
}
FIELDS_VoltageCapacitorController = _CONTROLLER_FIELDS | {
    "on_voltage": Field("derived", note="targetValue = (on + off) / 2 × pt_ratio, in V"),
    "off_voltage": Field("derived", note="targetDeadband = |off − on| × pt_ratio, in V"),
    "pt_ratio": Field("copied", (("add_regulating_control", "ptRatio", None),), note="also scales the targets"),
}
FIELDS_CurrentCapacitorController = _CONTROLLER_FIELDS | {
    "on_current": Field("derived", note="targetValue = (on + off) / 2 × ct_ratio, in A"),
    "off_current": Field("derived", note="targetDeadband = |off − on| × ct_ratio, in A"),
    "ct_ratio": Field("copied", (("add_regulating_control", "ctRatio", None),), note="also scales the targets"),
}
FIELDS_ActivePowerCapacitorController = _CONTROLLER_FIELDS | {
    "on_power": Field("derived", note="targetValue = (on + off) / 2, in W"),
    "off_power": Field("derived", note="targetDeadband = |off − on|, in W"),
}
FIELDS_ReactivePowerCapacitorController = _CONTROLLER_FIELDS | {
    "on_power": Field("derived", note="targetValue = (on + off) / 2, in VAr"),
    "off_power": Field("derived", note="targetDeadband = |off − on|, in VAr"),
}


def add_capacitor(network, capacitor, naming: Naming) -> None:
    """A LinearShuntCompensator with the capacitor's totals, sections and control."""
    require_in_service(capacitor)
    label = f"DistributionCapacitor {capacitor.name!r}"
    equipment = capacitor.equipment
    phase_capacitors = equipment.phase_capacitors
    if len(phase_capacitors) != len(capacitor.phases):
        raise ValueError(f"{label}: {len(phase_capacitors)} phase capacitors for {len(capacitor.phases)} phases")
    if Phase.N in capacitor.phases:
        raise ValueError(f"{label}: a capacitor on the neutral has no LinearShuntCompensatorPhase")
    first = phase_capacitors[0]
    for slot in ("rated_reactive_power", "num_banks", "num_banks_on"):
        values = [getattr(c, slot) for c in phase_capacitors]
        if any(value != values[0] for value in values):
            raise ValueError(f"{label}: {slot} differs by phase ({values}); per-phase capacitors are not mapped")
    connection = ConnectionType(equipment.connection_type)
    phase_connection, grounded = lookup(SHUNT_CONNECTION, connection, slot="connection_type",
                                        record_id=capacitor.name)
    sections = switched_sections(capacitor.state, capacitor.phases, first.num_banks_on, label)
    total = sum((c.rated_reactive_power for c in phase_capacitors[1:]), first.rated_reactive_power)

    builder = LinearShuntCompensatorBuilder(network, network.container)
    compensator = builder.create(mRID=object_mrid(PREFIX, capacitor, "LinearShuntCompensator", naming),
                                 name=capacitor.name)
    _, terminal, _ = builder.add_connectivity(
        compensator,
        node=bus_mrid(capacitor.bus, naming),
        compensatorType="capacitor",
        phaseConnection=phase_connection,
        phases=builder_phases(capacitor.phases),
        grounded=grounded,
        EquipmentContainer=container_mrid(capacitor, naming),
        BaseVoltage=bus_base_voltage(capacitor.bus),
    )
    builder.add_electrical(compensator, nomU=qty(nominal_voltage(equipment, capacitor.phases, label)),
                           nomQ=power_qty(total, "reactive", label=label), normalSections=sections,
                           maximumSections=first.num_banks)
    builder.add_ssh(compensator, sections=sections)
    add_control(network, builder, compensator, terminal.mRID, capacitor, naming, label)


def nominal_voltage(equipment, phases, label: str):
    """nomU, the voltage across one unit: line-to-line for balanced ABC; otherwise the rating as written, which must
    be line-to-ground for a wye and line-to-line for a delta capacitor."""
    if builder_phases(phases) is None:
        return system_voltage(equipment.rated_voltage, equipment.voltage_type, phases)
    across = VoltageTypes.LINE_TO_GROUND if ConnectionType(equipment.connection_type) is ConnectionType.STAR \
        else VoltageTypes.LINE_TO_LINE
    if VoltageTypes(equipment.voltage_type) is not across:
        raise ValueError(f"{label}: a {equipment.connection_type} capacitor on {len(phases)} phases rated "
                         f"{equipment.voltage_type}; expected {across.value}")
    return equipment.rated_voltage


def switched_sections(state, phases, num_banks_on: int, label: str) -> int:
    """The sections switched in: ``num_banks_on`` when ``state`` is on, else 0 (G6). ``state`` is one entry (ditto) or
    one per phase (GDM's own examples), and must be the same on every phase."""
    if len(state) not in (1, len(phases)) or len(set(state)) > 1:
        raise ValueError(f"{label}: state {state} must be one entry or one per phase, all equal")
    return num_banks_on if state[0] else 0


def capacitor_targets(controller) -> tuple[float, float, dict]:
    """(targetValue, targetDeadband, ratio keywords): the band centre and width on the primary side, in the mode's SI
    unit. CIM's targets have no unit, so this is the one place the spoke converts a unit (I2 exception)."""
    _, on_slot, off_slot, unit, ratio_slot, ratio_keyword = CONTROLLER_SETTINGS[type(controller)]
    scale = getattr(controller, ratio_slot) if ratio_slot else 1.0
    on = float(getattr(controller, on_slot).to(unit).magnitude) * scale
    off = float(getattr(controller, off_slot).to(unit).magnitude) * scale
    ratios = {ratio_keyword: getattr(controller, ratio_slot)} if ratio_slot else {}
    return (on + off) / 2, abs(off - on), ratios


def add_control(network, builder, compensator, terminal: str, capacitor, naming: Naming, label: str) -> None:
    """A RegulatingControl on the capacitor's own Terminal, switching the compensator."""
    controllers = capacitor.controllers
    if not controllers:
        return
    if len(controllers) not in (1, len(capacitor.phases)):
        raise ValueError(f"{label}: {len(controllers)} controllers for {len(capacitor.phases)} phases")
    first = controllers[0]
    if any(_settings(c) != _settings(first) for c in controllers):
        raise ValueError(f"{label}: the controllers differ by phase; CIM has one RegulatingControl per compensator")
    mode = lookup({cls: row[0] for cls, row in CONTROLLER_SETTINGS.items()}, type(first), slot="controllers",
                  record_id=capacitor.name)
    target, deadband, ratios = capacitor_targets(first)

    control_builder = RegulatingControlBuilder(network, network.container)
    control = control_builder.create(mRID=object_mrid(CONTROL_PREFIX, capacitor, "RegulatingControl", naming),
                                     name=capacitor.name)
    control_builder.add_regulating_control(control, Terminal=terminal, mode=mode, targetValue=target,
                                           targetDeadband=deadband, monitoredPhase=PHASE[Phase(capacitor.phases[0])],
                                           discrete=True, enabled=True, **ratios)
    builder.add_regulating_control(compensator, RegulatingControl=control.mRID, controlEnabled=True,
                                   aVRDelay=None if first.delay_on is None else qty(first.delay_on))


def _settings(controller) -> tuple:
    """A controller's class and every value but its identity, for the equal-across-phases check."""
    return (type(controller),) + tuple(getattr(controller, slot) for slot in type(controller).model_fields
                                       if slot not in ("uuid", "name"))
