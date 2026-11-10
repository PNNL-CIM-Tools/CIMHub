"""A series compensator's impedance and varistor (skill `export-getters`).

r and x are the positive-sequence values per phase, r0 and x0 the zero sequence; CIM marks r and x required, so an
unset one raises. All in ohm: no spoke needs per unit yet.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty


class SeriesCompensatorData(NamedTuple):
    r: float  # ohm
    x: float
    r0: float | None
    x0: float | None
    compensator_type: cim.CompensatorKind | None
    varistor_present: bool | None
    varistor_rated_current: float | None  # A
    varistor_voltage_threshold: float | None  # V


def get_series_compensator(compensator: cim.SeriesCompensator) -> SeriesCompensatorData:
    """r and x (required), r0 and x0 in ohm, and the compensator's kind and varistor."""
    if not isinstance(compensator, cim.SeriesCompensator):
        raise ValueError(f"{describe(compensator)}: is not a SeriesCompensator")
    return SeriesCompensatorData(
        r=required_qty(compensator, "r", "ohm"),
        x=required_qty(compensator, "x", "ohm"),
        r0=get_qty(compensator, "r0", "ohm"),
        x0=get_qty(compensator, "x0", "ohm"),
        compensator_type=compensator.compensatorType,
        varistor_present=compensator.varistorPresent,
        varistor_rated_current=get_qty(compensator, "varistorRatedCurrent", "A"),
        varistor_voltage_threshold=get_qty(compensator, "varistorVoltageThreshold", "V"),
    )
