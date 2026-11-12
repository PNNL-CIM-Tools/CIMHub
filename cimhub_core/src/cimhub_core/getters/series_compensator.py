"""A series compensator's impedance and varistor (skill `export-getters`).

r and x are the positive-sequence values per phase, r0 and x0 the zero sequence; CIM marks r and x required, so an
unset one raises. In ohm, or in pu on the compensator's BaseVoltage and the system base power (RAW), as the line
getter reads a line.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty


IMPEDANCE_UNITS = ("ohm", "pu")


class SeriesCompensatorData(NamedTuple):
    r: float  # the caller's unit
    x: float
    r0: float | None
    x0: float | None
    compensator_type: cim.CompensatorKind | None
    varistor_present: bool | None
    varistor_rated_current: float | None  # A
    varistor_voltage_threshold: float | None  # V


def get_series_compensator(compensator: cim.SeriesCompensator, unit: str = "ohm", *,
                           base_power=None) -> SeriesCompensatorData:
    """r and x (required), r0 and x0 in ``unit``, and the compensator's kind and varistor. ``'pu'`` is on the
    compensator's BaseVoltage and ``base_power`` (``network.base_power``), through ``cimtables.impedance.z_base``."""
    if not isinstance(compensator, cim.SeriesCompensator):
        raise ValueError(f"{describe(compensator)}: is not a SeriesCompensator")
    if unit not in IMPEDANCE_UNITS:
        raise ValueError(f"unit must be one of {list(IMPEDANCE_UNITS)}, not {unit!r}")
    return SeriesCompensatorData(
        r=required_qty(compensator, "r", unit, system_base=base_power),
        x=required_qty(compensator, "x", unit, system_base=base_power),
        r0=get_qty(compensator, "r0", unit, system_base=base_power),
        x0=get_qty(compensator, "x0", unit, system_base=base_power),
        compensator_type=compensator.compensatorType,
        varistor_present=compensator.varistorPresent,
        varistor_rated_current=get_qty(compensator, "varistorRatedCurrent", "A"),
        varistor_voltage_threshold=get_qty(compensator, "varistorVoltageThreshold", "V"),
    )
