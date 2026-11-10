"""A node's or equipment's base voltage (skill `export-getters`).

One rule, CIM's (cim18v17 ``ConnectivityNode.BaseVoltage`` and ``ConductingEquipment.BaseVoltage``): a
ConnectivityNode or ConductingEquipment contained in a VoltageLevel takes ``VoltageLevel.BaseVoltage`` and its own
association is disregarded; one in any other container (a Feeder, a Substation) takes its own. A TopologicalNode and
a TransformerEnd always take their own. No walk to a neighbouring node or a connected equipment. A PowerTransformer
has no BaseVoltage (CIM: "not used for transformers"); read each end. ``nominalVoltage`` is line to line.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_phases

FORMS = ("LL", "LN")
SPLIT_PHASE = (cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2)


def get_base_voltage(obj, unit: str, *, form: str) -> float:
    """The object's base voltage (its VoltageLevel's where CIM says so) in ``unit``: ``form='LL'`` as stored, ``form='LN'`` the three-phase line
    to neutral value LL / sqrt(3). Equipment or a transformer end on a split-phase secondary (s1/s2) raises for
    'LN', whose 120 V leg is not LL / sqrt(3); a node carries no phases, so its 'LN' is always LL / sqrt(3).
    Raises when the object (or its VoltageLevel) has no BaseVoltage, or the BaseVoltage no nominalVoltage."""
    if form not in FORMS:
        raise ValueError(f"form must be one of {FORMS}, not {form!r}")
    base_voltage = _base_voltage(obj)
    line_to_line = get_qty(base_voltage, "nominalVoltage", unit)
    if line_to_line is None:
        raise ValueError(f"{describe(base_voltage)}: has no nominalVoltage")
    if form == "LL":
        return line_to_line
    if any(phase in SPLIT_PHASE for phase in _phases(obj)):
        raise ValueError(f"{describe(obj)}: a split-phase leg voltage is not LL / sqrt(3); read form='LL'")
    return line_to_line / math.sqrt(3)


def _base_voltage(obj) -> cim.BaseVoltage:
    """The VoltageLevel's BaseVoltage for a node or equipment inside one, else the object's own."""
    if isinstance(obj, cim.ConnectivityNode):
        container = obj.ConnectivityNodeContainer
    elif isinstance(obj, cim.ConductingEquipment):
        container = obj.EquipmentContainer
    else:
        container = None
    holder = container if isinstance(container, cim.VoltageLevel) else obj
    if holder.BaseVoltage is None:
        raise ValueError(f"{describe(holder)}: has no BaseVoltage")
    return holder.BaseVoltage


def _phases(obj) -> tuple[cim.SinglePhaseKind, ...]:
    """Equipment's or a transformer end's conductors; a node has none."""
    if isinstance(obj, cim.ConductingEquipment):
        return get_conductor_phases(obj)
    if isinstance(obj, cim.TransformerEnd):
        if obj.Terminal is None:
            raise ValueError(f"{describe(obj)}: has no Terminal for its phases")
        return get_terminal_phases(obj.Terminal)
    return ()
