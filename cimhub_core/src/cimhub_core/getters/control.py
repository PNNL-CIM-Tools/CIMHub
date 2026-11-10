"""Control settings: a RegulatingControl's target and band, and what a tap changer or a regulated device adds (skill
`export-getters`).

A ``RegulatingControl`` target is a plain float in primary units of its mode (V, A, W, VAr), times
``targetValueUnitMultiplier`` when set. ``get_regulating_control`` returns the target, deadband, limits and reverse
settings in the caller's unit (default the mode's SI unit). A mode with no quantity here (powerFactor, timeScheduled,
admittance, temperature) is returned as stored, and naming a unit or a multiplier for it raises.

Settings that CIM allows on either side must agree when both are set: ``ptRatio`` and ``ctRatio`` on a
``TapChanger`` and its ``TapChangerControl``. The regulated side adds its own: ``TapChanger`` delays and CT rating,
``RegulatingCondEq.controlEnabled``, ``ShuntCompensator.aVRDelay``. A control must monitor a Terminal.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.terminals import phase_code_tokens

MODE = cim.RegulatingControlModeKind
# mode -> (CIMUnit class, SI unit) of its targetValue
MODE_QUANTITY = {
    MODE.voltage: (cim.Voltage, "V"),
    MODE.currentFlow: (cim.CurrentFlow, "A"),
    MODE.activePower: (cim.ActivePower, "W"),
    MODE.reactivePower: (cim.ReactivePower, "VAr"),
}
# UnitMultiplier -> the pint prefix
PREFIX = {cim.UnitMultiplier.none: "", cim.UnitMultiplier.micro: "u"}
TARGET_ATTRIBUTES = ("targetValue", "targetDeadband", "minAllowedTargetValue", "maxAllowedTargetValue",
                     "reverseTargetValue", "reverseTargetDeadband")


class RegulatingSettings(NamedTuple):
    mode: cim.RegulatingControlModeKind
    unit: str | None  # what the targets are in; None for a mode returned as stored
    target: float
    deadband: float | None
    min_allowed: float | None
    max_allowed: float | None
    reverse_target: float | None
    reverse_deadband: float | None
    terminal: cim.Terminal  # the monitored terminal
    monitored_phases: tuple[cim.SinglePhaseKind, ...] | None
    enabled: bool | None
    discrete: bool | None
    pt_ratio: float | None
    ct_ratio: float | None


class LineDrop(NamedTuple):
    """Line drop compensation in primary ohms."""

    r: float | None
    x: float | None


class TapChangerSettings(NamedTuple):
    control: RegulatingSettings | None  # its TapChangerControl's; pt_ratio and ct_ratio agreed with the tap's
    control_enabled: bool | None
    ltc: bool | None
    ct_rating: float | None  # A
    initial_delay: float | None  # time_unit
    subsequent_delay: float | None  # time_unit
    line_drop_compensation: bool | None
    line_drop: LineDrop
    reverse_line_drop: LineDrop
    reversible: bool | None
    reverse_to_neutral: bool | None
    reversing_delay: float | None  # time_unit
    reversing_power_threshold: float | None  # power_unit
    min_limit_u: float | None  # voltage_unit
    max_limit_u: float | None  # voltage_unit


class EquipmentControl(NamedTuple):
    control: RegulatingSettings
    control_enabled: bool | None  # RegulatingCondEq.controlEnabled
    delay: float | None  # time_unit; ShuntCompensator.aVRDelay, None on other equipment


def get_regulating_control(control: cim.RegulatingControl, unit: str | None = None) -> RegulatingSettings:
    """The control's mode, targets in ``unit`` (default its mode's SI unit), monitored terminal and phases."""
    if control.mode is None:
        raise ValueError(f"{describe(control)}: mode is unset")
    if control.Terminal is None:
        raise ValueError(f"{describe(control)}: monitors no Terminal")
    if control.targetValue is None:
        raise ValueError(f"{describe(control)}: targetValue is unset")
    target_unit, convert = _target_conversion(control, unit)
    targets = []
    for name in TARGET_ATTRIBUTES:
        value = getattr(control, name)
        targets.append(None if value is None else convert(value))
    phases = None if control.monitoredPhase is None else phase_code_tokens(control.monitoredPhase, control)
    return RegulatingSettings(control.mode, target_unit, *targets, control.Terminal, phases, control.enabled,
                              control.discrete, control.ptRatio, control.ctRatio)


def get_tap_changer_control(tap: cim.TapChanger, *, unit: str | None = None, time_unit: str = "s",
                            voltage_unit: str = "V", power_unit: str = "W") -> TapChangerSettings:
    """The tap changer's control settings; ``control`` is None when it has no TapChangerControl. ``unit`` is the
    targets' (``get_regulating_control``)."""
    tap_control = tap.TapChangerControl
    control = None
    if tap_control is not None:
        control = get_regulating_control(tap_control, unit)._replace(
            pt_ratio=_agreed(tap, tap_control, "ptRatio"), ct_ratio=_agreed(tap, tap_control, "ctRatio"))

    def control_qty(attribute: str, quantity_unit: str) -> float | None:
        return None if tap_control is None else get_qty(tap_control, attribute, quantity_unit)

    def control_value(attribute: str):
        return None if tap_control is None else getattr(tap_control, attribute)

    return TapChangerSettings(
        control=control,
        control_enabled=tap.controlEnabled,
        ltc=tap.ltcFlag,
        ct_rating=tap.ctRating,
        initial_delay=get_qty(tap, "initialDelay", time_unit),
        subsequent_delay=get_qty(tap, "subsequentDelay", time_unit),
        line_drop_compensation=control_value("lineDropCompensation"),
        line_drop=LineDrop(control_qty("lineDropR", "ohm"), control_qty("lineDropX", "ohm")),
        reverse_line_drop=LineDrop(control_qty("reverseLineDropR", "ohm"), control_qty("reverseLineDropX", "ohm")),
        reversible=control_value("reversible"),
        reverse_to_neutral=control_value("reverseToNeutral"),
        reversing_delay=control_qty("reversingDelay", time_unit),
        reversing_power_threshold=control_qty("reversingPowerThreshold", power_unit),
        min_limit_u=control_qty("minLimitVoltage", voltage_unit),
        max_limit_u=control_qty("maxLimitVoltage", voltage_unit),
    )


def get_equipment_control(equipment: cim.RegulatingCondEq, *, unit: str | None = None,
                          time_unit: str = "s") -> EquipmentControl | None:
    """The control of a regulated device (a shunt, a machine, an inverter), or None when it has none."""
    if equipment.RegulatingControl is None:
        return None
    delay = get_qty(equipment, "aVRDelay", time_unit) if isinstance(equipment, cim.ShuntCompensator) else None
    return EquipmentControl(get_regulating_control(equipment.RegulatingControl, unit), equipment.controlEnabled, delay)


def _target_conversion(control: cim.RegulatingControl, unit: str | None):
    """``(unit, convert)``: the targets' unit and the function from a stored target to it."""
    multiplier = control.targetValueUnitMultiplier
    if control.mode not in MODE_QUANTITY:
        if unit is not None or multiplier not in (None, cim.UnitMultiplier.none):
            raise ValueError(f"{describe(control)}: a {control.mode.value} target is read as stored, without a unit "
                             f"or a multiplier")
        return None, float
    quantity, si_unit = MODE_QUANTITY[control.mode]
    stored_unit = si_unit if multiplier is None else PREFIX.get(multiplier, multiplier.value) + si_unit
    target_unit = unit or si_unit
    return target_unit, lambda value: quantity(value, stored_unit).to(target_unit)


def _agreed(tap: cim.TapChanger, control: cim.TapChangerControl, attribute: str) -> float | None:
    """The value set on the tap changer, its control, or both alike."""
    on_tap, on_control = getattr(tap, attribute), getattr(control, attribute)
    if on_tap is not None and on_control is not None and not math.isclose(on_tap, on_control):
        raise ValueError(f"{describe(tap)} and {describe(control)}: {attribute} {on_tap} and {on_control} differ")
    return on_control if on_tap is None else on_tap
