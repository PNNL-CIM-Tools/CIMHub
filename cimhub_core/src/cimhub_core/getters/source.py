"""An energy source's voltage and Thevenin impedance (skill `export-getters`).

The voltage is ``voltageMagnitude`` (required) on ``nominalVoltage`` (required), and the angle is in the caller's
unit. The impedance is ``r``/``x`` (positive), ``r0``/``x0`` and ``r2``/``x2`` in ohm, or in pu on the source's
BaseVoltage and ``base_power`` (``get_qty``); an unset one is None and the spoke decides (semantic rule 8).
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.terminals import get_conductor_phases

IMPEDANCE_UNITS = ("ohm", "pu")
IMPEDANCE_ATTRIBUTES = ("r", "x", "r0", "x0", "r2", "x2")


class SourceImpedance(NamedTuple):
    r: float | None
    x: float | None
    r0: float | None
    x0: float | None
    r2: float | None
    x2: float | None


class Source(NamedTuple):
    phases: tuple[cim.SinglePhaseKind, ...]
    nominal_u: float  # voltage_unit
    magnitude: float  # voltage_unit
    magnitude_pu: float  # on nominal_u
    angle: float | None  # angle_unit
    impedance: SourceImpedance


def get_source(source: cim.EnergySource, *, angle_unit: str, voltage_unit: str = "V", impedance_unit: str = "ohm",
               base_power=None) -> Source:
    """The source's voltage and impedance; ``angle_unit`` (``'deg'`` or ``'rad'``) has no default."""
    if impedance_unit not in IMPEDANCE_UNITS:
        raise ValueError(f"impedance_unit must be one of {list(IMPEDANCE_UNITS)}, not {impedance_unit!r}")
    nominal = _required(source, "nominalVoltage", voltage_unit)
    magnitude = _required(source, "voltageMagnitude", voltage_unit)
    impedance = SourceImpedance(*(get_qty(source, name, impedance_unit, system_base=base_power)
                                  for name in IMPEDANCE_ATTRIBUTES))
    return Source(get_conductor_phases(source), nominal, magnitude, magnitude / nominal,
                  get_qty(source, "voltageAngle", angle_unit), impedance)


def _required(source: cim.EnergySource, attribute: str, unit: str) -> float:
    value = get_qty(source, attribute, unit)
    if value is None:
        raise ValueError(f"{describe(source)}: {attribute} is unset")
    return value
