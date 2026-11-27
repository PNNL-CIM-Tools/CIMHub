"""RegulatingControl of a LinearShuntCompensator -> OpenDSS ``CapControl`` (``EXPORT_MAPPING.md#capcontrol``).

The importer's band inverted: ON and OFF = targetValue -+ targetDeadband / 2 (``on_off_from_band``), ON below OFF
for voltage and time and above it for current and kvar, then on the relay's side: voltage / PTratio, current /
CTratio, kvar in kvar, time in hours. A TapChangerControl is RegControl's and a SynchronousMachine's control its
Generator's (model 3); every other RegulatingControl must regulate one LinearShuntCompensator.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.derived.control_band import on_off_from_band
from cimhub_core.getters import describe
from cimhub_core.getters.control import get_equipment_control
from cimhub_core.getters.terminals import get_conductor_phases
from cimhub_opendss.exporter import line, switch
from cimhub_opendss.exporter.capacitor import capacitor_name
from cimhub_opendss.exporter.controls import control_enabled, pt_phase
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.RegulatingControl,)
NATIVE_CLASS = schema.Capcontrol
NAMESPACE = "CapControl"
MODE = cim.RegulatingControlModeKind
#: mode -> (DSS type, the unit its targets are read in; None: as stored, hours for time)
TYPE = {MODE.voltage: ("voltage", "V"), MODE.currentFlow: ("current", "A"), MODE.reactivePower: ("kvar", "kVAr"),
        MODE.timeScheduled: ("time", None)}
#: modes whose ON setting is the upper one
ON_ABOVE = (MODE.currentFlow, MODE.reactivePower)

_SETTING = "targetValue {sign} targetDeadband / 2 (on_off_from_band), voltage / PTratio, current / CTratio"
_NO_HOME = "untranscribed on import (S4-5); the engine's default"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the CapControl namespace"),
    "element": Slot("written", "the monitored Terminal's equipment: Line.<line or switch> (a coupled line's: the "
                               "jumper or remainder at that end, line_element), Capacitor.<shunt>; others raise"),
    "terminal": Slot("written", "the monitored Terminal's sequenceNumber"),
    "capacitor": Slot("written", "the one LinearShuntCompensator the control regulates"),
    "type": Slot("written", "mode voltage, currentFlow, reactivePower, timeScheduled -> voltage, current, kvar, "
                            "time; others raise"),
    "PTratio": Slot("written", "ptRatio; unset -> not written, and a voltage control raises, as does one <= 0"),
    "CTratio": Slot("written", "ctRatio; unset -> not written, and a current control raises, as does one <= 0"),
    "ONsetting": Slot("written", _SETTING.format(sign="-+") + "; ON below OFF for voltage and time"),
    "OFFsetting": Slot("written", _SETTING.format(sign="+-") + "; an unset target or deadband raises"),
    "Delay": Slot("written", "the shunt's aVRDelay (s); unset -> not written"),
    "PTPhase": Slot("written", "1-based place of monitoredPhase among the monitored equipment's phase conductors"),
    "enabled": Slot("written", "the control's enabled; the shunt's controlEnabled must agree"),
    **{slot: Slot("unset", _NO_HOME) for slot in ("VoltOverride", "Vmax", "Vmin", "DelayOFF", "DeadTime")},
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "untranscribed or raising on import; not in CIM"))}


def export(context) -> list[schema.Capcontrol]:
    """One CapControl per RegulatingControl (a TapChangerControl is another class, RegControl's), except a
    machine's own, which its Generator carries (model 3)."""
    return [_capcontrol(control, context) for control in context.objects(*CIM_CLASSES)
            if not _machines_own(control)]


def _machines_own(control: cim.RegulatingControl) -> bool:
    regulated = control.RegulatingCondEq
    return len(regulated) == 1 and isinstance(regulated[0], cim.SynchronousMachine)


def _capcontrol(control: cim.RegulatingControl, context) -> schema.Capcontrol:
    names = context.names
    if control.mode not in TYPE:
        mode = control.mode.value if control.mode is not None else None
        raise ValueError(f"{describe(control)}: mode {mode}; a CapControl is voltage, current, kvar or time")
    dss_type, unit = TYPE[control.mode]
    shunt = _shunt(control)
    equipment = get_equipment_control(shunt, unit=unit, time_unit="s")
    settings = equipment.control
    unmapped = [name for name, value in (("minAllowedTargetValue", settings.min_allowed),
                                         ("maxAllowedTargetValue", settings.max_allowed),
                                         ("reverseTargetValue", settings.reverse_target),
                                         ("reverseTargetDeadband", settings.reverse_deadband)) if value is not None]
    if unmapped:
        raise ValueError(f"{describe(control)}: {unmapped} have no CapControl slot")
    for attribute, value in (("targetValue", settings.target), ("targetDeadband", settings.deadband)):
        if value is None:
            raise ValueError(f"{describe(control)}: {attribute} is unset; a CapControl needs ON and OFF")
    on, off = on_off_from_band(settings.target, settings.deadband, on_above=control.mode in ON_ABOVE)
    ratio = _relay_ratio(control, settings)
    element, terminal, conductors = _monitored(settings.terminal, context)
    return NATIVE_CLASS(
        name=names.name(control, NAMESPACE),
        element=element,
        terminal=terminal,
        capacitor=capacitor_name(shunt, names),
        type=dss_type,
        PTratio=settings.pt_ratio,
        CTratio=settings.ct_ratio,
        ONsetting=on / ratio,
        OFFsetting=off / ratio,
        Delay=equipment.delay,
        PTPhase=pt_phase(control, settings.monitored_phases, conductors),
        enabled=control_enabled(control, settings.enabled, equipment.control_enabled),
    )


def _shunt(control: cim.RegulatingControl) -> cim.LinearShuntCompensator:
    regulated = control.RegulatingCondEq
    if len(regulated) != 1 or not isinstance(regulated[0], cim.LinearShuntCompensator):
        raise ValueError(f"{describe(control)}: regulates {[describe(eq) for eq in regulated]}; a CapControl has one "
                         f"LinearShuntCompensator (other regulated equipment is not exported yet)")
    return regulated[0]


def _relay_ratio(control: cim.RegulatingControl, settings) -> float:
    """What a primary setting is divided by on the relay's side: PTratio (voltage), CTratio (current), else 1."""
    needed = {MODE.voltage: ("ptRatio", settings.pt_ratio), MODE.currentFlow: ("ctRatio", settings.ct_ratio)}
    if control.mode not in needed:
        return 1.0
    attribute, ratio = needed[control.mode]
    if ratio is None:
        raise ValueError(f"{describe(control)}: {attribute} is unset; a {control.mode.value} CapControl setting is on "
                         f"the relay's side")
    if ratio <= 0:
        raise ValueError(f"{describe(control)}: {attribute} {ratio}; a CapControl's relay ratio is positive (a "
                         f"negative one switches the bank the wrong way)")
    return ratio


def _monitored(terminal: cim.Terminal, context) -> tuple[str, int, list[cim.SinglePhaseKind]]:
    """``(element, terminal, phase conductors)`` of the monitored Terminal, as the element's record writes them (a
    coupled line's: the jumper or remainder at that end, ``line.line_element``)."""
    names = context.names
    equipment = terminal.ConductingEquipment
    if terminal.sequenceNumber is None:
        raise ValueError(f"{describe(terminal)}: has no sequenceNumber")
    if isinstance(equipment, cim.ACLineSegment):
        element = line.line_element(equipment, terminal.sequenceNumber, context)
    elif isinstance(equipment, switch.CIM_CLASSES):
        element = f"Line.{switch.switch_name(equipment, names)}"
    elif isinstance(equipment, cim.LinearShuntCompensator):
        element = f"Capacitor.{capacitor_name(equipment, names)}"
    else:
        raise ValueError(f"{describe(terminal)}: on {describe(equipment)}; a CapControl monitors a line, a switch or "
                         f"a capacitor")
    conductors = [phase for phase in get_conductor_phases(equipment) if phase is not cim.SinglePhaseKind.N]
    return element, terminal.sequenceNumber, conductors
