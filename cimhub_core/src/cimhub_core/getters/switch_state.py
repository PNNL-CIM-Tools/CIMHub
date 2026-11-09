"""Whether a switch is open (skill `export-getters`, semantic rule 1)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe

# which state -> the Switch attribute that holds it
STATE_ATTRIBUTE = {"actual": "open", "normal": "normalOpen"}


def get_switch_state(switch: cim.Switch, *, which: str) -> bool:
    """True when the switch is open: ``which='actual'`` reads ``Switch.open``, ``'normal'`` reads
    ``Switch.normalOpen``. There is no default, because the two differ in any model that is not as built. Raises
    when the attribute is unset."""
    if which not in STATE_ATTRIBUTE:
        raise ValueError(f"which must be one of {sorted(STATE_ATTRIBUTE)}, not {which!r}")
    attribute = STATE_ATTRIBUTE[which]
    is_open = getattr(switch, attribute)
    if is_open is None:
        raise ValueError(f"{describe(switch)}: {attribute} is unset")
    return is_open
