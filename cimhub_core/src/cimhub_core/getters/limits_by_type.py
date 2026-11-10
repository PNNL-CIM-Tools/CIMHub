"""An equipment's limits of one class, by ``OperationalLimitType`` (skill `export-getters`).

Bus-branch formats number their ratings by set (RAW's RATE1..RATE12), so they read a limit by its type rather than
by duration. The sets are found as ``get_current_limits`` finds them: on the equipment and on its terminals. Each
type has one value; two limits of one type that disagree raise.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import agreed_limit, equipment_limit_sets


def get_limits_by_type(equipment: cim.ConductingEquipment, limit_class: type,
                       unit: str) -> dict[cim.OperationalLimitType, float]:
    """Each ``limit_class`` limit's ``normalValue`` in ``unit`` (required), keyed by its type. A limit with no
    OperationalLimitType raises."""
    found: dict[cim.OperationalLimitType, list] = {}
    for limit_set in equipment_limit_sets(equipment):
        for limit in limit_set.OperationalLimitValue:
            if not isinstance(limit, limit_class):
                continue
            if limit.OperationalLimitType is None:
                raise ValueError(f"{describe(limit)}: has no OperationalLimitType")
            found.setdefault(limit.OperationalLimitType, []).append(
                (limit, required_qty(limit, "normalValue", unit)))
    return {limit_type: agreed_limit(equipment, f"{limit_type.mRID} {limit_class.__name__}", values)
            for limit_type, values in found.items()}
