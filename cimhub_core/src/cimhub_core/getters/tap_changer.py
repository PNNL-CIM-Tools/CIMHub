"""A ratio tap changer's steps and turns ratio (skill `export-getters`).

``TapChanger.step`` is a tap **position**, never a turns ratio (as are ``normalStep``, ``lowStep``, ``highStep`` and
``neutralStep``). The ratio at a position is 1 + (position - neutralStep) × stepVoltageIncrement / 100. There is no
default increment: an unset one raises.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe

# which position -> the TapChanger attribute that holds it
POSITION_ATTRIBUTE = {"actual": "step", "normal": "normalStep", "low": "lowStep", "high": "highStep"}


class TapSteps(NamedTuple):
    low: int
    high: int
    neutral: int
    normal: int | None
    step: float | None  # the actual position
    increment: float  # percent per step
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


def get_tap_ratio(tap: cim.RatioTapChanger, *, which: str) -> float:
    """The turns ratio at the ``which`` position: ``'actual'`` (step), ``'normal'``, ``'low'`` or ``'high'``. There
    is no default, because the actual and normal positions differ in any model that is not as built."""
    if which not in POSITION_ATTRIBUTE:
        raise ValueError(f"which must be one of {sorted(POSITION_ATTRIBUTE)}, not {which!r}")
    position = _required(tap, POSITION_ATTRIBUTE[which])
    return 1.0 + (position - _required(tap, "neutralStep")) * _increment(tap) / 100.0


def _increment(tap: cim.RatioTapChanger) -> float:
    increment = get_qty(tap, "stepVoltageIncrement", "percent")
    if increment is None:
        raise ValueError(f"{describe(tap)}: stepVoltageIncrement is unset")
    return increment


def _required(tap: cim.RatioTapChanger, attribute: str):
    value = getattr(tap, attribute)
    if value is None:
        raise ValueError(f"{describe(tap)}: {attribute} is unset")
    return value
