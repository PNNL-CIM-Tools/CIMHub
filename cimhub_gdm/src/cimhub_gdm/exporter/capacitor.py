"""LinearShuntCompensator → DistributionCapacitor, its RegulatingControl → a capacitor controller
(``EXPORT_MAPPING.md#capacitors``, decisions X7, X8).

Each phase gets an equal share of the rated Q (all sections in, on ``nomU``: ``get_shunt_reactive_power``). The
state is one entry, as ditto writes it: on when any section is in. The controller is the importer's inverse: on and
off = (target ∓ deadband / 2) / ratio. GDM names no monitored element, so a control on another terminal raises.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.cimtbl import lookup
from cimhub_core.getters import describe
from cimhub_core.getters.control import get_equipment_control
from cimhub_core.getters.shunt import get_shunt_reactive_power
from cimhub_core.getters.terminals import get_terminal_nodes
from gdm.quantities import ReactivePower
from gdm.systems.distribution.components import DistributionCapacitor
from gdm.systems.distribution.controllers import (
    ActivePowerCapacitorController,
    CurrentCapacitorController,
    ReactivePowerCapacitorController,
    VoltageCapacitorController,
)
from gdm.systems.distribution.enums import ConnectionType, VoltageTypes
from gdm.systems.distribution.equipment import CapacitorEquipment, PhaseCapacitorEquipment
from infrasys.quantities import ActivePower, Current, Time, Voltage

from cimhub_gdm.exporter.shared import ExportContext, connection_type, containers, gdm_phases, in_service
from cimhub_gdm.exporter.slots import UUID, Slot

CIM_CLASSES = (cim.LinearShuntCompensator,)

MODE = cim.RegulatingControlModeKind
#: Control mode → (controller class, on slot, off slot, quantity class, GDM unit of the mode's SI unit, ratio slot).
CONTROLLERS = {
    MODE.voltage: (VoltageCapacitorController, "on_voltage", "off_voltage", Voltage, "volt", "pt_ratio"),
    MODE.currentFlow: (CurrentCapacitorController, "on_current", "off_current", Current, "ampere", "ct_ratio"),
    MODE.activePower: (ActivePowerCapacitorController, "on_power", "off_power", ActivePower, "watt", None),
    MODE.reactivePower: (ReactivePowerCapacitorController, "on_power", "off_power", ReactivePower, "var", None),
}

BALANCED = (cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C)

_UNTRANSCRIBED = "untranscribed on import: no CIM home"
_CONTROLLER_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "the capacitor's name (X2)"),
    "delay_on": Slot("written", "get_equipment_control.delay (aVRDelay, s); unset is None"),
    "delay_off": Slot("unset", "untranscribed on import: CIM has one delay, aVRDelay"),
    "dead_time": Slot("unset", _UNTRANSCRIBED),
}
_ON = "(target − deadband / 2)"
_OFF = "(target + deadband / 2)"

SLOTS = {
    DistributionCapacitor: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
        "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
        "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
        "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
        "bus": Slot("written", "the bus of get_terminal_nodes"),
        "phases": Slot("written", "get_shunt_reactive_power.phases: the phase conductors, no neutral"),
        "controllers": Slot("rule", "one controller from get_equipment_control, by mode (CONTROLLERS); none when "
                                    "there is no control or it is disabled (enabled or controlEnabled false)"),
        "equipment": Slot("written", "a CapacitorEquipment made for this capacitor"),
        "state": Slot("rule", "one entry, as ditto writes it: sections (actual) > 0"),
    },
    CapacitorEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the capacitor's name (X2)"),
        "phase_capacitors": Slot("written", "one PhaseCapacitorEquipment per phase conductor"),
        "connection_type": Slot("written", "phaseConnection: Y and Yn → STAR, D → DELTA; others raise"),
        "rated_voltage": Slot("written", "get_shunt_reactive_power(voltage='nominal').voltage: nomU (kV)"),
        "voltage_type": Slot("rule", "line-to-line on balanced ABC and for delta (nomU across a branch), else "
                                     "line-to-ground: the importer's nominal_voltage inverse"),
    },
    PhaseCapacitorEquipment: {
        "uuid": UUID,
        "name": Slot("written", "<capacitor>_<phase> (X2)"),
        "resistance": Slot("unset", "untranscribed on import: no home on LinearShuntCompensator; GDM's default 0"),
        "reactance": Slot("unset", "untranscribed on import: no home on LinearShuntCompensator; GDM's default 0"),
        "rated_reactive_power": Slot("written", "get_shunt_reactive_power(sections='maximum', voltage='nominal')"
                                                ".per_phase (kVAr)"),
        "num_banks_on": Slot("written", "get_shunt_reactive_power(sections='actual').sections; a fraction raises"),
        "num_banks": Slot("written", "get_shunt_reactive_power(sections='maximum').sections"),
    },
    VoltageCapacitorController: _CONTROLLER_SLOTS | {
        "on_voltage": Slot("rule", f"{_ON} / pt_ratio (V)"),
        "off_voltage": Slot("rule", f"{_OFF} / pt_ratio (V)"),
        "pt_ratio": Slot("rule", "ptRatio; unset is 1, the targets as stored"),
    },
    CurrentCapacitorController: _CONTROLLER_SLOTS | {
        "on_current": Slot("rule", f"{_ON} / ct_ratio (A)"),
        "off_current": Slot("rule", f"{_OFF} / ct_ratio (A)"),
        "ct_ratio": Slot("rule", "ctRatio; unset is 1, the targets as stored"),
    },
    ActivePowerCapacitorController: _CONTROLLER_SLOTS | {
        "on_power": Slot("rule", f"{_ON} (W)"),
        "off_power": Slot("rule", f"{_OFF} (W)"),
    },
    ReactivePowerCapacitorController: _CONTROLLER_SLOTS | {
        "on_power": Slot("rule", f"{_ON} (VAr)"),
        "off_power": Slot("rule", f"{_OFF} (VAr)"),
    },
}


def export(shunt: cim.LinearShuntCompensator, context: ExportContext) -> DistributionCapacitor:
    rated = get_shunt_reactive_power(shunt, "kVAr", sections="maximum", voltage="nominal", voltage_unit="kV")
    actual = get_shunt_reactive_power(shunt, "kVAr", sections="actual", voltage="nominal", voltage_unit="kV")
    names = context.names
    phases = gdm_phases(rated.phases, shunt)
    banks_on = whole_sections(actual.sections, shunt)
    phase_capacitors = [
        PhaseCapacitorEquipment(**names.part(shunt, PhaseCapacitorEquipment, suffix=f"_{phase.value}"),
                                rated_reactive_power=ReactivePower(rated.per_phase[conductor], "kilovar"),
                                num_banks_on=banks_on, num_banks=whole_sections(rated.sections, shunt))
        for conductor, phase in zip(rated.phases, phases)
    ]
    connection = connection_type(rated.connection, shunt)
    equipment = CapacitorEquipment(**names.part(shunt, CapacitorEquipment), phase_capacitors=phase_capacitors,
                                   connection_type=connection, rated_voltage=Voltage(rated.voltage, "kilovolt"),
                                   voltage_type=voltage_type(rated.phases, connection))
    [node] = get_terminal_nodes(shunt)
    return DistributionCapacitor(
        **names.own(shunt),
        bus=context.gdm(node),
        phases=phases,
        equipment=equipment,
        state=[banks_on > 0],
        controllers=controllers(shunt, context),
        in_service=in_service(shunt),
        **containers(shunt.EquipmentContainer, context),
    )


def whole_sections(sections: float, shunt: cim.LinearShuntCompensator) -> int:
    """A section count as GDM's bank count; a fraction of a section raises."""
    if sections != int(sections):
        raise ValueError(f"{describe(shunt)}: {sections} sections; GDM counts whole banks")
    return int(sections)


def voltage_type(phases, connection: ConnectionType) -> VoltageTypes:
    """nomU's form: line to line on balanced ABC and across a delta branch, line to ground for a wye off ABC."""
    if tuple(phases) == BALANCED or connection is ConnectionType.DELTA:
        return VoltageTypes.LINE_TO_LINE
    return VoltageTypes.LINE_TO_GROUND


def controllers(shunt: cim.LinearShuntCompensator, context: ExportContext) -> list:
    """The capacitor's one controller, or none when it has no control or the control is disabled."""
    control = get_equipment_control(shunt, time_unit="s")
    if control is None or control.control_enabled is False or control.control.enabled is False:
        return []
    settings = control.control
    if settings.terminal not in shunt.Terminals:
        raise ValueError(f"{describe(shunt)}: its RegulatingControl monitors {describe(settings.terminal)}, not "
                         "its own terminal; a GDM capacitor controller names no monitored element")
    controller_class, on_slot, off_slot, quantity, unit, ratio_slot = lookup(
        CONTROLLERS, settings.mode, slot="mode", record_id=shunt.mRID)
    values = {}
    scale = 1.0
    if ratio_slot is not None:
        ratio = settings.pt_ratio if ratio_slot == "pt_ratio" else settings.ct_ratio
        scale = 1.0 if ratio is None else ratio  # unset: the targets as stored
        values[ratio_slot] = scale
    half_band = (settings.deadband or 0.0) / 2
    values[on_slot] = quantity((settings.target - half_band) / scale, unit)
    values[off_slot] = quantity((settings.target + half_band) / scale, unit)
    delay = None if control.delay is None else Time(control.delay, "second")
    return [controller_class(**context.names.part(shunt, controller_class), delay_on=delay, **values)]
