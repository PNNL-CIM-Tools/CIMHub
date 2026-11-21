"""Switch classes -> GLM ``switch``, ``fuse``, ``recloser``, ``sectionalizer``
(``EXPORT_MAPPING.md#x1-lines-and-switches``).

A Fuse is a ``fuse``, a Recloser a ``recloser``, a Sectionaliser a ``sectionalizer``; every other Switch (a
LoadBreakSwitch, Breaker, Disconnector, Jumper, a plain Switch) is a ``switch``, as GLM has no breaker. ``status``
is the CIM state the caller picks (``switch_state``: ``open`` or ``normalOpen``). A tie between laterals on different
phases (``get_switch_sides``, S6-9) is written on side 1's phases, as the GLM deck it came from was.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.switch_state import get_switch_state
from cimhub_core.getters.terminals import get_switch_sides, get_terminal_nodes
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.line import ratings
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

#: every Switch class (``context.objects`` reads each class exactly, not its subclasses)
CIM_CLASSES = (cim.Switch, cim.LoadBreakSwitch, cim.Breaker, cim.Disconnector, cim.Jumper, cim.Fuse, cim.Recloser,
               cim.Sectionaliser)
#: CIM class -> GLM class; the first match in this order wins (a Recloser is a ProtectedSwitch is a Switch)
GLM_CLASS = ((cim.Fuse, schema.Fuse), (cim.Recloser, schema.Recloser), (cim.Sectionaliser, schema.Sectionalizer),
             (cim.Switch, schema.Switch))

_SLOTS = {
    "name": Slot("written", "Names (X1)"),
    "phases": Slot("written", "side 1's A, B, C"),
    "from_node": Slot("written", "terminal 1's bus"), "to": Slot("written", "terminal 2's bus"),
    "status": Slot("written", "get_switch_state(which=switch_state): OPEN or CLOSED"),
    **{f"continuous_rating_{letter}": Slot("written", "get_current_limits normal") for letter in "ABC"},
    **{f"emergency_rating_{letter}": Slot("written", "get_current_limits emergency") for letter in "ABC"},
}
_UNSET = Slot("unset", "not in CIM; GridLAB-D's default")
SLOTS = {
    schema.Switch: with_default(schema.Switch, _SLOTS, _UNSET),
    schema.Fuse: with_default(schema.Fuse, {**_SLOTS, "current_limit": Slot("written", "Fuse.ratedCurrent (A)")},
                              _UNSET),
    schema.Recloser: with_default(schema.Recloser, _SLOTS, _UNSET),
    schema.Sectionalizer: with_default(schema.Sectionalizer, _SLOTS, _UNSET),
}


def export(context) -> list:
    return [_switch(switch, context) for switch in context.objects(*CIM_CLASSES)]


def _switch(switch: cim.Switch, context):
    native_class = next(glm for cim_class, glm in GLM_CLASS if isinstance(switch, cim_class))
    first, second = get_terminal_nodes(switch)
    side_letters = letters(get_switch_sides(switch)[0])
    is_open = get_switch_state(switch, which=context.switch_state)
    slots = {"name": context.names.name(switch), "phases": side_letters, "from_node": context.buses[first].name,
             "to": context.buses[second].name, "status": "OPEN" if is_open else "CLOSED",
             **ratings(switch, side_letters, native_class)}
    if native_class is schema.Fuse:
        slots["current_limit"] = get_qty(switch, "ratedCurrent", glm_unit(schema.Fuse, "current_limit"))
    return native_class(**slots)
