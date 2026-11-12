"""A node's solved voltage and an equipment's voltage limits (skill `export-getters`).

**Solved voltage:** a balanced node's ``SvVoltage`` is the one with no ``phase``; ``v`` is its line-to-line
magnitude and ``angle`` its angle. Per-phase SvVoltages (an unbalanced solution) are not read here.

**Voltage limits** are found as ``get_current_limits`` finds current limits: every ``OperationalLimitSet`` on the
equipment and its terminals. Each ``VoltageLimit`` is classified by its ``OperationalLimitType``: ``durationKind``
normal or emergency, ``direction`` high or low (``shapes/common.cimtbl`` writes such types). A seasonal type, another
duration or direction raises, until a consumer needs one. Limits of one kind must agree.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import agreed_limit, equipment_limit_sets

# (LimitDurationKind, OperationalLimitDirectionKind) -> VoltageLimits field
KIND_FIELD = {
    (cim.LimitDurationKind.normal, cim.OperationalLimitDirectionKind.high): "normal_high",
    (cim.LimitDurationKind.normal, cim.OperationalLimitDirectionKind.low): "normal_low",
    (cim.LimitDurationKind.emergency, cim.OperationalLimitDirectionKind.high): "emergency_high",
    (cim.LimitDurationKind.emergency, cim.OperationalLimitDirectionKind.low): "emergency_low",
}


class NodeVoltage(NamedTuple):
    v: float  # line-to-line magnitude, in the caller's unit
    angle: float | None  # None when the SvVoltage has none


class VoltageLimits(NamedTuple):
    """Voltage limits by duration and direction; ``None`` when the equipment has no limit of that kind."""

    normal_high: float | None
    normal_low: float | None
    emergency_high: float | None
    emergency_low: float | None


def get_node_voltage(node: cim.TopologicalNode, voltage_unit: str = "V", angle_unit: str = "deg") -> NodeVoltage | None:
    """The node's balanced solved voltage, or ``None`` without one. Two balanced SvVoltages, or one with no ``v``,
    raise."""
    balanced = [voltage for voltage in node.SvVoltage if voltage.phase is None]
    if not balanced:
        return None
    if len(balanced) > 1:
        raise ValueError(f"{describe(node)}: {len(balanced)} balanced SvVoltages "
                         f"({sorted(str(voltage.uri()) for voltage in balanced)})")
    voltage = balanced[0]
    return NodeVoltage(required_qty(voltage, "v", voltage_unit), get_qty(voltage, "angle", angle_unit))


def get_voltage_limits(equipment: cim.ConductingEquipment, unit: str = "V") -> VoltageLimits:
    """The equipment's voltage limits in ``unit``, by kind (module docstring)."""
    found = {field: [] for field in VoltageLimits._fields}
    for limit_set in equipment_limit_sets(equipment):
        for limit in limit_set.OperationalLimitValue:
            if isinstance(limit, cim.VoltageLimit):
                found[_kind_field(limit)].append((limit, required_qty(limit, "normalValue", unit)))
    return VoltageLimits(**{field: agreed_limit(equipment, f"{field} voltage", values)
                            for field, values in found.items()})


def _kind_field(limit: cim.VoltageLimit) -> str:
    limit_type = limit.OperationalLimitType
    if limit_type is None:
        raise ValueError(f"{describe(limit)}: has no OperationalLimitType")
    if limit_type.season is not None:
        raise ValueError(f"{describe(limit_type)}: a seasonal voltage limit (season {limit_type.season}) is not read")
    kind = (limit_type.durationKind, limit_type.direction)
    if kind not in KIND_FIELD:
        raise ValueError(f"{describe(limit_type)}: durationKind {limit_type.durationKind}, direction "
                         f"{limit_type.direction} is not a normal or emergency high or low limit")
    return KIND_FIELD[kind]
