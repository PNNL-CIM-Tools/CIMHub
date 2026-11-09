"""Switch -> OpenDSS ``Line`` with ``Switch=y``, plus its ``Fuse`` / ``Recloser`` / ``SwtControl`` and ``Open``
(``EXPORT_MAPPING.md#switches-e6``).

CIM gives a switch no impedance (DSS-8), so each is written with a small invented one (B3, the user's rule): 1 mOhm
resistive. Both of CIM's states go back (E6): ``normalOpen`` -> the control's ``Normal``, ``open`` -> ``State`` and
an ``Open Line.<name> 1`` command. A switch that is not a Fuse or Recloser gets a SwtControl only when it is open in
either state. The class is lossy on the way back: every class but Fuse and Recloser comes back a LoadBreakSwitch
(DSS-9).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.switch_state import get_switch_state
from cimhub_core.getters.terminals import get_conductor_phases
from cimhub_opendss.exporter.line import terminal_buses, ratings
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.exporter.slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.Switch, cim.AirBreakSwitch, cim.Breaker, cim.Cut, cim.DisconnectingCircuitBreaker, cim.Disconnector,
               cim.EarthingSwitch, cim.Elbow, cim.Fuse, cim.GroundDisconnector, cim.HookstickSwitch, cim.Jumper,
               cim.LoadBreakSwitch, cim.ProtectedSwitch, cim.Recloser, cim.Sectionaliser, cim.ServiceDisconnect)
LINE_NAMESPACE = "Line"
#: B3: 1 mOhm, resistive (the old exporter's zero-impedance floor; the IEEE decks write their switches resistive)
SWITCH_IMPEDANCE = dict(r1=1e-3, r0=1e-3, x1=0.0, x0=0.0, C1=0.0, C0=0.0, length=1.0, units="m")
STATE_WORD = {True: "open", False: "closed"}

_STATE = {
    "Normal": Slot("written", "get_switch_state(which='normal'); written only when open in either state"),
    "State": Slot("written", "get_switch_state(which='actual'); written only when open in either state"),
}
_FUSE_STATE = {name: Slot(slot.kind, slot.note + "; one value per phase (the engine sets a fuse per phase)")
               for name, slot in _STATE.items()}
_PROTECTION = "protection setting; untranscribed on import (DSS-11)"
_NO_HOME = "no home on a Switch (untranscribed on import)"


SLOTS = {
    schema.Line: with_default(schema.Line, {
        "name": Slot("written", "Names, the Line namespace (shared with ACLineSegments)"),
        "bus1": Slot("written", "bus_ref, as a Line"), "bus2": Slot("written", "bus_ref, as a Line"),
        "phases": Slot("written", "the phase conductors"),
        "Switch": Slot("written", "y"),
        **{name: Slot("rule", "SWITCH_IMPEDANCE: CIM has no switch impedance (B3, 1 mOhm)") for name in SWITCH_IMPEDANCE},
        "normamps": Slot("rule", "get_current_limits normal (A); unset -> not written"),
        "emergamps": Slot("rule", "get_current_limits emergency (A); unset -> not written"),
        "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
        "like": Slot("not mapped", "the writer never writes like="),
    }, Slot("unset", "a switch has no other line data (DSS-8)")),
    schema.Fuse: with_default(schema.Fuse, {
        "name": Slot("written", "Names, the switch's"),
        "MonitoredObj": Slot("written", "Line.<the switch's Line name>"),
        "SwitchedObj": Slot("not mapped", "the engine takes MonitoredObj"),
        "RatedCurrent": Slot("written", "Switch.ratedCurrent (A)"),
        "FuseCurve": Slot("unset", _PROTECTION),
        **_FUSE_STATE,
        "like": Slot("not mapped", "the writer never writes like="),
    }, Slot("unset", _NO_HOME)),
    schema.Recloser: with_default(schema.Recloser, {
        "name": Slot("written", "Names, the switch's"),
        "MonitoredObj": Slot("written", "Line.<the switch's Line name>"),
        "SwitchedObj": Slot("not mapped", "the engine takes MonitoredObj"),
        **_STATE,
        "like": Slot("not mapped", "the writer never writes like="),
    }, Slot("unset", _PROTECTION)),
    schema.Swtcontrol: with_default(schema.Swtcontrol, {
        "name": Slot("written", "Names, the switch's"),
        "SwitchedObj": Slot("written", "Line.<the switch's Line name>"),
        **_STATE,
        "like": Slot("not mapped", "the writer never writes like="),
    }, Slot("unset", _NO_HOME)),
}


def switch_name(switch: cim.Switch, names: Names) -> str:
    """The switch's Line name, as its record, its control and its Open command write it."""
    return names.name(switch, LINE_NAMESPACE)


def export(context) -> list:
    """Each switch's Line, then its control when it has one."""
    records = []
    for switch in context.objects(*CIM_CLASSES):
        records.append(_line(switch, context.names))
        control = _control(switch, context.names)
        if control is not None:
            records.append(control)
    return records


def open_terminals(context) -> list[str]:
    """``Line.<name> 1`` for every switch that is open now (E6); the deck's ``Open`` commands."""
    return [f"Line.{switch_name(switch, context.names)} 1" for switch in context.objects(*CIM_CLASSES)
            if get_switch_state(switch, which="actual")]


def _line(switch: cim.Switch, names: Names) -> schema.Line:
    phases = get_conductor_phases(switch)
    bus1, bus2 = terminal_buses(switch, phases, names)
    return schema.Line(name=switch_name(switch, names), bus1=bus1, bus2=bus2, phases=len(phases), Switch=True,
                       **SWITCH_IMPEDANCE, **ratings(switch), enabled=get_in_service(switch, which="normal"))


def _control(switch: cim.Switch, names: Names):
    """The switch's Fuse, Recloser or SwtControl, or None for a closed switch that is neither."""
    normal, actual = get_switch_state(switch, which="normal"), get_switch_state(switch, which="actual")
    state = dict(Normal=STATE_WORD[normal], State=STATE_WORD[actual]) if normal or actual else {}
    target = f"Line.{switch_name(switch, names)}"
    if isinstance(switch, cim.Fuse):
        # the engine sets a fuse's state phase by phase: one value per phase (State=open alone opens phase 1)
        phases = len(get_conductor_phases(switch))
        per_phase = {slot: [word] * phases for slot, word in state.items()}
        return schema.Fuse(name=names.name(switch, "Fuse"), MonitoredObj=target,
                           RatedCurrent=get_qty(switch, "ratedCurrent", "A"), **per_phase)
    if isinstance(switch, cim.Recloser):
        return schema.Recloser(name=names.name(switch, "Recloser"), MonitoredObj=target, **state)
    if not state:
        return None
    return schema.Swtcontrol(name=names.name(switch, "SwtControl"), SwitchedObj=target, **state)
