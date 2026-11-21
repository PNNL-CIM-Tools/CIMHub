"""Switch -> OpenDSS ``Line`` with ``Switch=y``, plus its ``Fuse`` / ``Recloser`` / ``SwtControl`` and ``Open``
(``EXPORT_MAPPING.md#switches-e6``).

CIM gives a switch no impedance (DSS-8), so each is written with a small invented one (B3, the user's rule): 1 mOhm
resistive. Both of CIM's states go back (E6): ``normalOpen`` -> the control's ``Normal``, ``open`` -> ``State`` and
an ``Open Line.<name> 1`` command; ``switch_state='normal'`` writes ``normalOpen`` to both. A switch that is not a
Fuse or Recloser gets a SwtControl only when it is open in either state. The class is lossy on the way back: every
class but Fuse and Recloser comes back a LoadBreakSwitch (DSS-9).

A Fuse or Recloser control is written disabled (V7, the user's rule until U15): cim18v17 has no home for its trip
settings or curve, so the engine's defaults (a ~1 A recloser pickup, the default fuse curve) would trip it on the first
snapshot and black out what is behind it. Disabled, it leaves its switch as CIM says, and the importer reads it back
as the same Fuse or Recloser (a control's ``enabled`` is untranscribed).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters import describe
from cimhub_core.getters.switch_state import get_reclose_delays, get_switch_state
from cimhub_core.getters.terminals import get_switch_sides
from cimhub_opendss.exporter.line import SWITCH_IMPEDANCE, ratings, terminal_buses
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.Switch, cim.AirBreakSwitch, cim.Breaker, cim.Cut, cim.DisconnectingCircuitBreaker, cim.Disconnector,
               cim.EarthingSwitch, cim.ElbowSwitch, cim.Fuse, cim.GroundDisconnector, cim.HookstickSwitch, cim.Jumper,
               cim.LoadBreakSwitch, cim.ProtectedSwitch, cim.Recloser, cim.Sectionaliser, cim.ServiceDisconnect)
LINE_NAMESPACE = "Line"
STATE_WORD = {True: "open", False: "closed"}

_STATE = {
    "Normal": Slot("written", "get_switch_state(which='normal'); written only when open in either state"),
    "State": Slot("written", "get_switch_state(which=switch_state), 'actual' unless the caller asks 'normal'; "
                             "written only when open in either state"),
}
_FUSE_STATE = {name: Slot(slot.kind, slot.note + "; one value per phase (the engine sets a fuse per phase)")
               for name, slot in _STATE.items()}
_PROTECTION = "protection setting; no home in cim18v17's protection function blocks (DSS-11): the engine's default"
#: V7: a protective control is disabled until U15 gives its trip settings and curve a home
PROTECTION_ENABLED = False
_DISABLED = Slot("rule", "no: no trip settings or curve in CIM yet (U15), so the engine's defaults would trip it (V7)")
_NO_HOME = "no home on a Switch (untranscribed on import)"


SLOTS = {
    schema.Line: with_default(schema.Line, {
        "name": Slot("written", "Names, the Line namespace (shared with ACLineSegments)"),
        "bus1": Slot("written", "bus_ref of side 1's conductors (get_switch_sides)"),
        "bus2": Slot("written", "bus_ref of side 2's conductors: an open tie across phases (SwitchPhase.phaseSide2) "
                                "lands on other nodes, e.g. .2 to .3"),
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
        "enabled": _DISABLED,
        "like": Slot("not mapped", "the writer never writes like="),
    }, Slot("unset", _NO_HOME)),
    schema.Recloser: with_default(schema.Recloser, {
        "name": Slot("written", "Names, the switch's"),
        "MonitoredObj": Slot("written", "Line.<the switch's Line name>"),
        "SwitchedObj": Slot("not mapped", "the engine takes MonitoredObj"),
        "Shots": Slot("written", "the RecloseSequences + 1 (get_reclose_delays); none -> 1, no reclosure"),
        "RecloseIntervals": Slot("written", "each RecloseSequence's recloseDelay (s), in recloseStep order; none -> "
                                            "not written"),
        **_STATE,
        "enabled": _DISABLED,
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
        records.append(_line(switch, context.names, context.switch_state))
        control = _control(switch, context.names, context.switch_state)
        if control is not None:
            records.append(control)
    return records


def open_terminals(context) -> list[str]:
    """``Line.<name> 1`` for every switch open in ``context.switch_state`` (E6); the deck's ``Open`` commands."""
    return [f"Line.{switch_name(switch, context.names)} 1" for switch in context.objects(*CIM_CLASSES)
            if get_switch_state(switch, which=context.switch_state)]


def _line(switch: cim.Switch, names: Names, switch_state: str) -> schema.Line:
    """The switch's Line, side by side. A tie across phases must be open in both states: closed, it would join two
    phases."""
    side1, side2 = get_switch_sides(switch)
    if side1 != side2 and not (get_switch_state(switch, which="normal")
                               and get_switch_state(switch, which=switch_state)):
        raise ValueError(f"{describe(switch)}: a tie from {[p.value for p in side1]} to {[p.value for p in side2]} "
                         f"that is closed (normal or {switch_state}); only an open one is mapped")
    bus1, bus2 = terminal_buses(switch, side1, names, side2)
    return schema.Line(name=switch_name(switch, names), bus1=bus1, bus2=bus2, phases=len(side1), Switch=True,
                       **SWITCH_IMPEDANCE, **ratings(switch), enabled=get_in_service(switch, which="normal"))


def _control(switch: cim.Switch, names: Names, switch_state: str):
    """The switch's Fuse, Recloser or SwtControl, or None for a closed switch that is neither. ``State`` is the
    switch's ``switch_state`` ('actual' or 'normal')."""
    normal, actual = get_switch_state(switch, which="normal"), get_switch_state(switch, which=switch_state)
    state = dict(Normal=STATE_WORD[normal], State=STATE_WORD[actual]) if normal or actual else {}
    target = f"Line.{switch_name(switch, names)}"
    if isinstance(switch, cim.Fuse):
        # the engine sets a fuse's state phase by phase: one value per phase (State=open alone opens phase 1)
        phases = len(get_switch_sides(switch)[0])
        per_phase = {slot: [word] * phases for slot, word in state.items()}
        return schema.Fuse(name=names.name(switch, "Fuse"), MonitoredObj=target,
                           RatedCurrent=get_qty(switch, "ratedCurrent", "A"), enabled=PROTECTION_ENABLED, **per_phase)
    if isinstance(switch, cim.Recloser):
        delays = get_reclose_delays(switch)
        return schema.Recloser(name=names.name(switch, "Recloser"), MonitoredObj=target, Shots=len(delays) + 1,
                               RecloseIntervals=list(delays) or None, enabled=PROTECTION_ENABLED, **state)
    if isinstance(switch, cim.ProtectedSwitch) and switch.RecloseSequences:
        raise ValueError(f"{describe(switch)}: RecloseSequences on a {type(switch).__name__}; only a DSS Recloser "
                         f"recloses here (a Relay's reclosing is not mapped, DSS-11)")
    if not state:
        return None
    return schema.Swtcontrol(name=names.name(switch, "SwtControl"), SwitchedObj=target, **state)
