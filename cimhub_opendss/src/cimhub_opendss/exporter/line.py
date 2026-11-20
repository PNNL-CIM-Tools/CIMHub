"""ACLineSegment -> OpenDSS ``Line`` (``EXPORT_MAPPING.md#line``).

A line names its catalog: a LineGeometry when it has a WireConfiguration, or a direct WireSpacing with a WireInfo on
each ACLineSegmentPhase (a spacing line; geometry wins, skill ``conductor-geometry``), else a LineCode. Lengths are
in metres (B1). A line with only lumped values is written inline per km with ``units=km`` (B6, the user's rule): the
whole-line values divided by the length, or the values themselves at ``length=1`` when the line has none. A neutral
conductor is not on the bus: a geometry reduces it (B4), and a line without geometry that has one raises.

The lines of a coupled MultiCircuitGroup (H1, ``ExportContext.coupled``) are one DSS line on the group's geometry,
from bus ``<group>_1`` to ``<group>_2`` over the group's length (the shortest line's), each circuit's phase
conductors on the next nodes in circuit order (1.2.3, then 4.5.6). A DSS terminal is on one bus and the circuits
end on different nodes, so each circuit has a jumper ``<line>_jumper1`` from its node 1 onto its nodes, with the
switches' invented 1 mOhm (B3). At the other end, a line no longer than the group has ``<line>_jumper2``; a longer
one goes on as ``<line>``, its own section on its own positions for the rest of its length (H4). Terminal 1 of
every line of a group is taken to be at the same end of the structure.
"""

from __future__ import annotations

from dataclasses import replace

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import get_current_limits
from cimhub_core.getters.earth import get_earth_resistivity, get_network_earth
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.line_impedance import get_line_sequence_impedance
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_opendss.exporter.linecode import linecode_name, sequence_slots
from cimhub_opendss.exporter.linegeometry import (CoupledGroup, geometry_name, group_value, is_spacing_line,
                                                  line_offset, spacing_geometry_name, spacing_geometry_owners)
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.ACLineSegment,)
NATIVE_CLASS = schema.Line
NAMESPACE = "Line"
UNIT = "m"  # B1
LUMPED_UNIT = "km"  # B6
#: B3: 1 mOhm, resistive (the old exporter's zero-impedance floor; the IEEE decks write their switches resistive).
#: A switch carries it, and so does a coupled group's jumper (H1)
SWITCH_IMPEDANCE = dict(r1=1e-3, r0=1e-3, x1=0.0, x0=0.0, C1=0.0, C0=0.0, length=1.0, units="m")

_LUMPED = "lumped only (B6): the whole-line value / length in km"
_JUMPER = "; a jumper's: SWITCH_IMPEDANCE (B3, H1)"
_NOT_IN_CIM = "not in CIM (untranscribed or raising on import)"
SLOTS = {NATIVE_CLASS: {
    "name": Slot("written", "Names; a coupled group's: the group's, <line>_jumper1 for each circuit, and "
                            "<line>_jumper2 or a longer line's remainder <line> (H1, H4)"),
    "bus1": Slot("written", "bus_ref(get_terminal_nodes[0], the phase conductors of get_conductor_phases); a coupled "
                            "group's: <group>_1 on nodes 1..n, its jumpers from each circuit's own bus, a remainder "
                            "from <group>_2 on its circuit's nodes (H1, H4)"),
    "bus2": Slot("written", "bus_ref(get_terminal_nodes[1], the same phases); a coupled group's: <group>_2 (H1)"),
    "linecode": Slot("written", "the PerLengthImpedance's LineCode name"),
    "length": Slot("written", "required_qty(length, m); lumped: km, unset -> 1; a coupled group's: its shortest "
                              "line's, a remainder the rest of its line, a jumper 1 m (H4)"),
    "phases": Slot("written", "the phase conductors (a neutral is reduced, B4); a coupled group's: every line's"),
    "r1": Slot("written", f"{_LUMPED} (ohm/km){_JUMPER}"), "x1": Slot("written", f"{_LUMPED} (ohm/km){_JUMPER}"),
    "r0": Slot("written", f"{_LUMPED} (ohm/km); unset raises{_JUMPER}"),
    "x0": Slot("written", f"{_LUMPED} (ohm/km); unset raises{_JUMPER}"),
    "C1": Slot("rule", f"{_LUMPED}, c_from_b(bch) (nF/km); unset -> 0{_JUMPER}"),
    "C0": Slot("rule", f"{_LUMPED}, c_from_b(b0ch) (nF/km); unset -> 0{_JUMPER}"),
    "rmatrix": Slot("not mapped", "a phase matrix is always a LineCode"),
    "xmatrix": Slot("not mapped", "a phase matrix is always a LineCode"),
    "cmatrix": Slot("not mapped", "a phase matrix is always a LineCode"),
    "Switch": Slot("not mapped", "a Switch is exported by switch.py"),
    "Rg": Slot("unset", _NOT_IN_CIM), "Xg": Slot("unset", _NOT_IN_CIM),
    "rho": Slot("written", "a geometry line's WireConfiguration EarthResistivity.rho (ohm-m), unset -> not written; "
                           "a spacing line's: get_network_earth"),
    "geometry": Slot("written", "the (WireConfiguration, spacingYOffset) LineGeometry name; a spacing line's: "
                                "spacing_geometry_name of its owner; a coupled group's: <group>_geometry (H1)"),
    "units": Slot("written", "m (B1); lumped: km (B6)"),
    "spacing": Slot("not mapped", "positions are written inline in the LineGeometry (B2)"),
    "cncables": Slot("not mapped", "the LineGeometry carries the conductors (B2)"),
    "tscables": Slot("not mapped", "the LineGeometry carries the conductors (B2)"),
    "wires": Slot("not mapped", "the LineGeometry carries the conductors (B2)"),
    "EarthModel": Slot("not mapped", "the deck's Set earthmodel carries it (options.py: one model per deck)"),
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
    """One Line per ACLineSegment outside the coupled groups, then each group's Line and jumpers."""
    owners = spacing_geometry_owners(context)
    coupled = {line for group in context.coupled.values() for line in group.lines}
    records = [_line(line, context, owners) for line in context.objects(*CIM_CLASSES) if line not in coupled]
    for group, lines in context.coupled.items():
        records.extend(_coupled_lines(group, lines, context, owners))
    return records


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


def _line(line: cim.ACLineSegment, context, owners: dict[cim.ACLineSegment, cim.ACLineSegment]) -> schema.Line:
    names = context.names
    phases = get_conductor_phases(line)
    conductors = tuple(phase for phase in phases if phase is not cim.SinglePhaseKind.N)
    has_neutral = len(conductors) < len(phases)
    bus1, bus2 = terminal_buses(line, conductors, names)
    slots = dict(name=names.name(line, NAMESPACE), bus1=bus1, bus2=bus2, phases=len(conductors), **ratings(line),
                 enabled=get_in_service(line, which="normal"))
    configuration, code = line.WireConfiguration, line.PerLengthImpedance
    if configuration is not None:
        if any(phase.WireInfo is not None for phase in line.ACLineSegmentPhases):
            raise ValueError(f"{describe(line)}: has both a WireConfiguration and ACLineSegmentPhase.WireInfo; a "
                             f"line's wires come from one of them")
        if configuration.numberOfPhases != len(conductors):
            raise ValueError(f"{describe(line)}: {len(conductors)} phase conductors on {describe(configuration)} "
                             f"of {configuration.numberOfPhases} phases")
        earth = get_earth_resistivity(configuration)
        slots.update(geometry=geometry_name(configuration, line_offset(line), names),
                     length=required_qty(line, "length", UNIT), units=UNIT,
                     rho=earth.rho if earth is not None else None)
    elif is_spacing_line(line):
        slots.update(geometry=spacing_geometry_name(owners[line], names), length=required_qty(line, "length", UNIT),
                     units=UNIT, rho=get_network_earth(context.network).rho)
    elif has_neutral:
        raise ValueError(f"{describe(line)}: a neutral conductor without geometry needs LineCode Kron/neutral, which "
                         f"is not mapped (B4)")
    elif code is not None:
        _check_code_phases(line, code, len(conductors))
        slots.update(linecode=linecode_name(code, names), length=required_qty(line, "length", UNIT), units=UNIT)
    else:
        slots.update(_lumped(line, context.network.base_frequency.to("Hz")))
    return NATIVE_CLASS(**slots)


def _coupled_lines(group: cim.MultiCircuitGroup, coupled: CoupledGroup, context,
                   owners: dict[cim.ACLineSegment, cim.ACLineSegment]) -> list[schema.Line]:
    """The group's Line on its geometry over the group's length, then each circuit's jumpers, or its remainder
    (H4) in place of the jumper at terminal 2. The lines must agree on ratings and in-service state, which the one
    Line carries."""
    names, lines = context.names, coupled.lines
    limits = group_value(group, lines, "ratings", ratings)
    enabled = group_value(group, lines, "in-service states", lambda line: get_in_service(line, which="normal"))
    start, end = names.bus(group, suffix="_1"), names.bus(group, suffix="_2")
    records, count = [], 0
    for line in lines:
        phases = tuple(phase for phase in get_conductor_phases(line) if phase is not cim.SinglePhaseKind.N)
        nodes = "".join(f".{node}" for node in range(count + 1, count + len(phases) + 1))
        count += len(phases)
        bus1, bus2 = terminal_buses(line, phases, names)
        jumper = dict(phases=len(phases), **SWITCH_IMPEDANCE, **limits, enabled=enabled)
        records.append(NATIVE_CLASS(name=names.name(line, NAMESPACE, suffix="_jumper1"), bus1=bus1,
                                    bus2=start + nodes, **jumper))
        if line in coupled.remainders:
            records.append(replace(_line(line, context, owners), bus1=end + nodes, length=coupled.remainders[line]))
        else:
            records.append(NATIVE_CLASS(name=names.name(line, NAMESPACE, suffix="_jumper2"), bus1=end + nodes,
                                        bus2=bus2, **jumper))
    nodes = "".join(f".{node}" for node in range(1, count + 1))
    line = NATIVE_CLASS(name=names.name(group, NAMESPACE), bus1=start + nodes, bus2=end + nodes, phases=count,
                        geometry=spacing_geometry_name(group, names), length=coupled.length, units=UNIT,
                        rho=get_network_earth(context.network).rho, **limits, enabled=enabled)
    return [line, *records]


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
