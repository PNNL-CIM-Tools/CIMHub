"""An impedance tap changer table's points (skill `export-getters`).

An ``ImpedanceTapChangerTable`` lists, per point, the tap position, ratio or angle it applies at, and the deviation of
each end's r and x from their nominal values, in percent (``rEnd1`` .. ``xEnd3``). A point's ``ratio`` is in pu of
the end's ratedU and its ``angle`` in degrees in CIM's sign; which of step, ratio and angle a consumer looks it up by
is the consumer's, so each is returned as stored.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe


class ImpedanceTablePoint(NamedTuple):
    step: int | None
    ratio: float | None  # pu of the end's ratedU
    angle: float | None  # angle_unit
    r: tuple[float | None, float | None, float | None]  # rEnd1..3, percent of the nominal r
    x: tuple[float | None, float | None, float | None]  # xEnd1..3, percent of the nominal x


def get_impedance_table(table: cim.ImpedanceTapChangerTable, angle_unit: str = "deg") -> tuple[ImpedanceTablePoint, ...]:
    """The table's points, in its list order. A table without points raises."""
    points = table.ImpedanceTapChangerTablePoint
    if not points:
        raise ValueError(f"{describe(table)}: has no ImpedanceTapChangerTablePoint")
    return tuple(ImpedanceTablePoint(
        step=point.step,
        ratio=point.ratio,
        angle=get_qty(point, "angle", angle_unit),
        r=tuple(get_qty(point, f"rEnd{end}", "percent") for end in (1, 2, 3)),
        x=tuple(get_qty(point, f"xEnd{end}", "percent") for end in (1, 2, 3)),
    ) for point in points)
