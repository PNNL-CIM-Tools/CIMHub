"""ACLineSegment -> OpenDSS ``Line`` (``EXPORT_MAPPING.md#line``).

A line names its catalog: a LineGeometry when it has a WireConfiguration (geometry wins, skill
``conductor-geometry``), else a LineCode. Lengths are in metres (B1). A line with only lumped values is written
inline per km with ``units=km`` (B6, the user's rule): the whole-line values divided by the length, or the values
themselves at ``length=1`` when the line has none. A neutral conductor is not on the bus: a geometry reduces it
(B4), and a line without geometry that has one raises.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import get_current_limits
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.line_impedance import get_line_sequence_impedance
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_opendss.exporter.linecode import linecode_name, sequence_slots
from cimhub_opendss.exporter.linegeometry import geometry_name, line_offset
from cimhub_opendss.exporter.slots import Slot
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.ACLineSegment,)
NATIVE_CLASS = schema.Line
NAMESPACE = "Line"
UNIT = "m"  # B1
LUMPED_UNIT = "km"  # B6

_LUMPED = "lumped only (B6): the whole-line value / length in km"
_NOT_IN_CIM = "not in CIM (untranscribed or raising on import)"
SLOTS = {NATIVE_CLASS: {
    "name": Slot("written", "Names"),
    "bus1": Slot("written", "bus_ref(get_terminal_nodes[0], the phase conductors of get_conductor_phases)"),
    "bus2": Slot("written", "bus_ref(get_terminal_nodes[1], the same phases)"),
    "linecode": Slot("written", "the PerLengthImpedance's LineCode name"),
    "length": Slot("written", "required_qty(length, m); lumped: km, unset -> 1"),
    "phases": Slot("written", "the phase conductors (a neutral is reduced, B4)"),
    "r1": Slot("written", f"{_LUMPED} (ohm/km)"), "x1": Slot("written", f"{_LUMPED} (ohm/km)"),
    "r0": Slot("written", f"{_LUMPED} (ohm/km); unset raises"),
    "x0": Slot("written", f"{_LUMPED} (ohm/km); unset raises"),
    "C1": Slot("rule", f"{_LUMPED}, c_from_b(bch) (nF/km); unset -> 0"),
    "C0": Slot("rule", f"{_LUMPED}, c_from_b(b0ch) (nF/km); unset -> 0"),
    "rmatrix": Slot("not mapped", "a phase matrix is always a LineCode"),
    "xmatrix": Slot("not mapped", "a phase matrix is always a LineCode"),
    "cmatrix": Slot("not mapped", "a phase matrix is always a LineCode"),
    "Switch": Slot("not mapped", "a Switch is exported by switch.py"),
    "Rg": Slot("unset", _NOT_IN_CIM), "Xg": Slot("unset", _NOT_IN_CIM), "rho": Slot("unset", _NOT_IN_CIM),
    "geometry": Slot("written", "the (WireConfiguration, spacingYOffset) LineGeometry name"),
    "units": Slot("written", "m (B1); lumped: km (B6)"),
    "spacing": Slot("not mapped", "a line with WireSpacing and no WireConfiguration raises (B2)"),
    "cncables": Slot("not mapped", "per-phase ACLineSegmentPhase.WireInfo raises (B2)"),
    "tscables": Slot("not mapped", "per-phase ACLineSegmentPhase.WireInfo raises (B2)"),
    "wires": Slot("not mapped", "per-phase ACLineSegmentPhase.WireInfo raises (B2)"),
    "EarthModel": Slot("unset", _NOT_IN_CIM),
    "B1": Slot("not mapped", "C1 carries the susceptance"), "B0": Slot("not mapped", "C0 carries the susceptance"),
    "Seasons": Slot("unset", _NOT_IN_CIM), "Ratings": Slot("unset", _NOT_IN_CIM),
    "LineType": Slot("unset", _NOT_IN_CIM), "EpsRmedium": Slot("unset", _NOT_IN_CIM),
    "HeightOffset": Slot("not mapped", "spacingYOffset goes into the geometry's heights"),
    "HeightUnit": Slot("not mapped", "spacingYOffset goes into the geometry's heights"),
    "conductors": Slot("unset", _NOT_IN_CIM),
    "normamps": Slot("rule", "get_current_limits normal (A); unset -> not written, the engine copies the catalog's"),
    "emergamps": Slot("rule", "get_current_limits emergency (A); unset -> not written, as normamps"),
    "faultrate": Slot("unset", _NOT_IN_CIM), "pct_perm": Slot("unset", _NOT_IN_CIM),
    "repair": Slot("unset", _NOT_IN_CIM),
    "basefreq": Slot("unset", "Options.defaultbasefreq is the deck's"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}}


def export(context) -> list[schema.Line]:
    """One Line per ACLineSegment."""
    return [_line(line, context) for line in context.objects(*CIM_CLASSES)]


def terminal_buses(equipment, phases, names) -> tuple[str, str]:
    """``(bus1, bus2)`` of a two-terminal equipment on ``phases``."""
    nodes = get_terminal_nodes(equipment)
    if len(nodes) != 2:
        raise ValueError(f"{describe(equipment)}: has {len(nodes)} terminals; a DSS line has two")
    return bus_ref(nodes[0], phases, names), bus_ref(nodes[1], phases, names)


def ratings(equipment) -> dict:
    """``normamps``/``emergamps`` from the equipment's normal and emergency limits (A); unset is not written."""
    limits = get_current_limits(equipment, "A")
    return dict(normamps=limits.normal, emergamps=limits.emergency)


def _line(line: cim.ACLineSegment, context) -> schema.Line:
    names = context.names
    phases = get_conductor_phases(line)
    conductors = tuple(phase for phase in phases if phase is not cim.SinglePhaseKind.N)
    has_neutral = len(conductors) < len(phases)
    if any(phase.WireInfo is not None for phase in line.ACLineSegmentPhases):
        raise ValueError(f"{describe(line)}: ACLineSegmentPhase.WireInfo is not exported; no producer writes it (B2)")
    bus1, bus2 = terminal_buses(line, conductors, names)
    slots = dict(name=names.name(line, NAMESPACE), bus1=bus1, bus2=bus2, phases=len(conductors), **ratings(line),
                 enabled=get_in_service(line, which="normal"))
    configuration, code = line.WireConfiguration, line.PerLengthImpedance
    if configuration is not None:
        if configuration.numberOfPhases != len(conductors):
            raise ValueError(f"{describe(line)}: {len(conductors)} phase conductors on {describe(configuration)} "
                             f"of {configuration.numberOfPhases} phases")
        slots.update(geometry=geometry_name(configuration, line_offset(line), names),
                     length=required_qty(line, "length", UNIT), units=UNIT)
    elif line.WireSpacing is not None:
        raise ValueError(f"{describe(line)}: a WireSpacing without a WireConfiguration is not exported; no producer "
                         f"writes one (B2)")
    elif has_neutral:
        raise ValueError(f"{describe(line)}: a neutral conductor without geometry needs LineCode Kron/neutral, which "
                         f"is not mapped (B4)")
    elif code is not None:
        _check_code_phases(line, code, len(conductors))
        slots.update(linecode=linecode_name(code, names), length=required_qty(line, "length", UNIT), units=UNIT)
    else:
        slots.update(_lumped(line, context.network.base_frequency.to("Hz")))
    return NATIVE_CLASS(**slots)


def _check_code_phases(line: cim.ACLineSegment, code: cim.PerLengthImpedance, count: int) -> None:
    """DSS builds the line from the code's own order (DSS-10): a phase code's conductorCount, a sequence code's 3."""
    expected = code.conductorCount if isinstance(code, cim.PerLengthPhaseImpedance) else 3
    if expected != count:
        raise ValueError(f"{describe(line)}: {count} phase conductors on {describe(code)} of {expected}")


def _lumped(line: cim.ACLineSegment, frequency: float) -> dict:
    """B6: the whole-line values per km of the line's length, or at length 1 km when it has none."""
    whole = get_line_sequence_impedance(line, "ohm")
    length = get_qty(line, "length", LUMPED_UNIT)
    length = 1.0 if length is None else length
    per_km = whole._replace(**{name: _per(getattr(whole, name), length) for name in ("r", "x", "r0", "x0")},
                            **{name: _per(_nano_siemens(getattr(whole, name)), length)
                               for name in ("b", "g", "b0", "g0")})
    return dict(length=length, units=LUMPED_UNIT, **sequence_slots(line, per_km, frequency))


def _per(value: float | None, length: float) -> float | None:
    return None if value is None else value / length


def _nano_siemens(value: float | None) -> float | None:
    """S -> nS (c_from_b takes nS) through the CIMUnit class."""
    return None if value is None else cim.Susceptance(value, "S").to("nS")
