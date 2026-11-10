"""Whether a switch is open (skill `export-getters`, semantic rule 1), and how a protected switch recloses."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

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


def get_reclose_delays(switch: cim.ProtectedSwitch, time_unit: str = "s") -> tuple[float, ...]:
    """The delay before each automatic reclosure, in ``recloseStep`` order: one per RecloseSequence, none for a
    switch that does not reclose. The steps must be 1..n, each with a delay."""
    steps = sorted(sequence.recloseStep for sequence in switch.RecloseSequences if sequence.recloseStep is not None)
    if steps != list(range(1, len(switch.RecloseSequences) + 1)):
        raise ValueError(f"{describe(switch)}: reclose steps {steps} of {len(switch.RecloseSequences)} sequences; "
                         f"they must be 1..n")
    delays = []
    for sequence in sorted(switch.RecloseSequences, key=lambda sequence: sequence.recloseStep):
        if sequence.recloseDelay is None:
            raise ValueError(f"{describe(sequence)} of {describe(switch)}: recloseDelay is unset")
        delays.append(get_qty(sequence, "recloseDelay", time_unit))
    return tuple(delays)
