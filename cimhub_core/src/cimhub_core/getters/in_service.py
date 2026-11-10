"""Whether equipment is in service (skill `export-getters`, semantic rule 1's pattern)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

# which state -> the Equipment attribute that holds it
SERVICE_ATTRIBUTE = {"actual": "inService", "normal": "normallyInService"}


def get_in_service(equipment: cim.Equipment, *, which: str) -> bool | None:
    """``which='actual'`` reads ``Equipment.inService``, ``'normal'`` reads ``normallyInService``; there is no
    default, as for a switch's state. Unset is None and the spoke decides (semantic rule 8)."""
    if which not in SERVICE_ATTRIBUTE:
        raise ValueError(f"which must be one of {sorted(SERVICE_ATTRIBUTE)}, not {which!r}")
    return getattr(equipment, SERVICE_ATTRIBUTE[which])
