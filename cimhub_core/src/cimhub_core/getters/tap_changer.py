"""A tap changer's steps, turns ratio and voltage (skill `export-getters`).

``TapChanger.step`` is a tap **position**, never a turns ratio (as are ``normalStep``, ``lowStep``, ``highStep`` and
``neutralStep``). The ratio at a position about the neutral is 1 + (position - neutralStep) × stepVoltageIncrement /
100, and the voltage there is neutralU + (position - neutralStep) × stepVoltageIncrement / 100 × the end's ratedU
(CIM's increment is in percent of the end's rated voltage, and neutralU need not be ratedU). There is no default
increment: an unset one raises, except on a fixed tap (lowStep = highStep), which has no step to increment: its
increment is None, its ratio at that one position 1 and its voltage its neutralU. A ``PhaseTapChangerLinear``'s
positions step by ``stepPhaseShiftIncrement``.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty

# which position -> the TapChanger attribute that holds it
POSITION_ATTRIBUTE = {"actual": "step", "normal": "normalStep", "low": "lowStep", "high": "highStep"}


class TapSteps(NamedTuple):
    low: int
    high: int
    neutral: int
    normal: int | None
    step: float | None  # the actual position
    increment: float | None  # percent per step; None on a fixed tap (lowStep = highStep)
    neutral_u: float | None  # voltage_unit


def get_tap_steps(tap: cim.RatioTapChanger, voltage_unit: str = "V") -> TapSteps:
    """The positions (low, high, neutral and the increment required) and the neutral voltage."""
    return TapSteps(
        low=_required(tap, "lowStep"),
        high=_required(tap, "highStep"),
        neutral=_required(tap, "neutralStep"),
        normal=tap.normalStep,
        step=tap.step,
        increment=_increment(tap),
        neutral_u=get_qty(tap, "neutralU", voltage_unit),
    )


class PhaseTapSteps(NamedTuple):
    low: int
    high: int
    neutral: int
    normal: int | None
    step: float | None  # the actual position
    increment: float  # angle_unit per step, in CIM's sign (from the terminal into the transformer)


def get_phase_tap_steps(tap: cim.PhaseTapChangerLinear, angle_unit: str = "deg") -> PhaseTapSteps:
    """The positions (low, high, neutral required) and the angle per step (required)."""
    return PhaseTapSteps(
        low=_required(tap, "lowStep"),
        high=_required(tap, "highStep"),
        neutral=_required(tap, "neutralStep"),
        normal=tap.normalStep,
        step=tap.step,
        increment=required_qty(tap, "stepPhaseShiftIncrement", angle_unit),
    )


def get_tap_voltage(tap: cim.RatioTapChanger, *, which: str, voltage_unit: str = "V") -> float:
    """The end's voltage at the ``which`` position (as ``get_tap_ratio``): neutralU + (position - neutralStep) ×
    stepVoltageIncrement / 100 × the end's ratedU; a fixed tap's is its neutralU. neutralU is required, and so is the
    end's ratedU on a tap that moves."""
    if which not in POSITION_ATTRIBUTE:
        raise ValueError(f"which must be one of {sorted(POSITION_ATTRIBUTE)}, not {which!r}")
    neutral_u = required_qty(tap, "neutralU", voltage_unit)
    increment = _increment(tap)
    if increment is None:
        return neutral_u
    if tap.TransformerEnd is None:
        raise ValueError(f"{describe(tap)}: has no TransformerEnd, whose ratedU its increment is a percent of")
    rated_u = required_qty(tap.TransformerEnd, "ratedU", voltage_unit)
    position = _required(tap, POSITION_ATTRIBUTE[which])
    return neutral_u + (position - _required(tap, "neutralStep")) * increment / 100.0 * rated_u


def get_tap_ratio(tap: cim.RatioTapChanger, *, which: str) -> float:
    """The turns ratio at the ``which`` position: ``'actual'`` (step), ``'normal'``, ``'low'`` or ``'high'``. There
    is no default, because the actual and normal positions differ in any model that is not as built."""
    if which not in POSITION_ATTRIBUTE:
        raise ValueError(f"which must be one of {sorted(POSITION_ATTRIBUTE)}, not {which!r}")
    position = _required(tap, POSITION_ATTRIBUTE[which])
    increment = _increment(tap)
    if increment is None:
        return 1.0
    return 1.0 + (position - _required(tap, "neutralStep")) * increment / 100.0


def _increment(tap: cim.RatioTapChanger) -> float | None:
    """Percent per step; None on a fixed tap (lowStep = highStep); unset on any other raises."""
    increment = get_qty(tap, "stepVoltageIncrement", "percent")
    if increment is None and _required(tap, "lowStep") != _required(tap, "highStep"):
        raise ValueError(f"{describe(tap)}: stepVoltageIncrement is unset")
    return increment


def _required(tap: cim.RatioTapChanger, attribute: str):
    value = getattr(tap, attribute)
    if value is None:
        raise ValueError(f"{describe(tap)}: {attribute} is unset")
    return value
