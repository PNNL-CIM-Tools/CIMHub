"""What RegControl and CapControl write alike: the monitored phase's place and the control's enabled
(``EXPORT_MAPPING.md#regcontrol``, ``#capcontrol``)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe


def pt_phase(control, monitored: tuple[cim.SinglePhaseKind, ...] | None,
             conductors: list[cim.SinglePhaseKind]) -> int | None:
    """The 1-based place of the one ``monitored`` phase among the monitored ``conductors``; unset is None."""
    if monitored is None:
        return None
    if len(monitored) != 1 or monitored[0] not in conductors:
        raise ValueError(f"{describe(control)}: monitoredPhase {[p.value for p in monitored]} is not one of its "
                         f"monitored conductors {[p.value for p in conductors]}")
    return conductors.index(monitored[0]) + 1


def control_enabled(control, enabled: bool | None, equipment_enabled: bool | None) -> bool | None:
    """The control's ``enabled``; the regulated side's ``controlEnabled`` must agree, and stands in when it is
    unset."""
    if enabled is not None and equipment_enabled is not None and enabled != equipment_enabled:
        raise ValueError(f"{describe(control)}: enabled {enabled} and the regulated side's controlEnabled "
                         f"{equipment_enabled} differ")
    return equipment_enabled if enabled is None else enabled
