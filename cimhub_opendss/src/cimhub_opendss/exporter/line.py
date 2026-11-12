"""ACLineSegment -> OpenDSS ``Line`` (``EXPORT_MAPPING.md#line``).

A line names its catalog: a LineGeometry when it has a WireConfiguration or a direct WireSpacing+ACLineSegmentPhase
WireInfo (geometry wins, skill ``conductor-geometry``), else a LineCode. Lengths are in metres (B1). A line with
only lumped values is written inline per km with ``units=km`` (B6, the user's rule): the whole-line values divided
by the length, or the values themselves at ``length=1`` when the line has none. A neutral conductor is not on the
bus: a geometry reduces it (B4), and a line without geometry that has one raises.

Two shapes produce a LineGeometry (B2):
- Old shape (B2a): ``ACLineSegment.WireConfiguration`` -> ``XYSpacing`` (wire catalog in ``WireSequenceConfiguration``).
- New shape (B2b, EPRI 2026-09-29): ``ACLineSegment.WireSpacing`` direct + ``ACLineSegmentPhase.WireInfo`` per
  phase. The spacing may describe multiple circuits; the line takes the positions of its phases' sequence numbers
  (``get_line_conductor_xy``).
  The geometry name is ``<spacing>_c<circuit>`` at offset 0, ``<spacing>_c<circuit>_<offset>m`` otherwise.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import get_current_limits
from cimhub_core.getters.earth import get_earth_resistivity
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.line_impedance import get_line_sequence_impedance
from cimhub_core.getters.spacing import get_line_conductor_xy
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_opendss.exporter.buses import bus_ref
from cimhub_opendss.exporter.linecode import linecode_name, sequence_slots
from cimhub_opendss.exporter.linegeometry import geometry_name, line_offset
from cimhub_opendss.exporter.slots import Slot
from cimhub_opendss.exporter.wire import wire_name
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
    "Rg": Slot("unset", _NOT_IN_CIM), "Xg": Slot("unset", _NOT_IN_CIM),
    "rho": Slot("written", "a geometry line's WireConfiguration EarthResistivity.rho (ohm-m); unset -> not written"),
    "geometry": Slot("written", "the (WireConfiguration, spacingYOffset) LineGeometry name"),
    "units": Slot("written", "m (B1); lumped: km (B6)"),
    "spacing": Slot("not mapped", "positions are written inline in the LineGeometry (B2)"),
    "cncables": Slot("not mapped", "per-phase WireInfo written inline in the LineGeometry cond= blocks (B2b)"),
    "tscables": Slot("not mapped", "per-phase WireInfo written inline in the LineGeometry cond= blocks (B2b)"),
    "wires": Slot("written", "per-phase ACLineSegmentPhase.WireInfo ordered by sequenceNumber (B2b), "
                             "or get_configuration_wires on the WireConfiguration (B2a)"),
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
    bus1, bus2 = terminal_buses(line, conductors, names)
    slots = dict(name=names.name(line, NAMESPACE), bus1=bus1, bus2=bus2, phases=len(conductors), **ratings(line),
                 enabled=get_in_service(line, which="normal"))
    configuration, code = line.WireConfiguration, line.PerLengthImpedance
    phase_wire_infos = _phase_wire_infos(line)
    if configuration is not None:
        if configuration.numberOfPhases != len(conductors):
            raise ValueError(f"{describe(line)}: {len(conductors)} phase conductors on {describe(configuration)} "
                             f"of {configuration.numberOfPhases} phases")
        earth = get_earth_resistivity(configuration)
        slots.update(geometry=geometry_name(configuration, line_offset(line), names),
                     length=required_qty(line, "length", UNIT), units=UNIT,
                     rho=earth.rho if earth is not None else None)
    elif line.WireSpacing is not None and phase_wire_infos is not None:
        # B2b: direct WireSpacing + ACLineSegmentPhase.WireInfo
        geo_name = _direct_geometry_name(line, names)
        slots.update(geometry=geo_name, length=required_qty(line, "length", UNIT), units=UNIT)
    elif line.WireSpacing is not None:
        raise ValueError(f"{describe(line)}: has a WireSpacing but no ACLineSegmentPhase.WireInfo; "
                         f"cannot build a LineGeometry without per-phase wire catalog entries (B2b)")
    elif has_neutral:
        raise ValueError(f"{describe(line)}: a neutral conductor without geometry needs LineCode Kron/neutral, which "
                         f"is not mapped (B4)")
    elif code is not None:
        _check_code_phases(line, code, len(conductors))
        slots.update(linecode=linecode_name(code, names), length=required_qty(line, "length", UNIT), units=UNIT)
    else:
        slots.update(_lumped(line, context.network.base_frequency.to("Hz")))
    return NATIVE_CLASS(**slots)


_GEOMETRY_DECIMALS = 3  # match linegeometry.py NAME_DECIMALS


def _phase_wire_infos(line: cim.ACLineSegment) -> dict[int, cim.WireInfo] | None:
    """``{sequenceNumber: WireInfo}`` from ``ACLineSegmentPhases``, or ``None`` when no phase has a ``WireInfo``."""
    result = {}
    for phase in line.ACLineSegmentPhases:
        if phase.WireInfo is not None:
            if phase.sequenceNumber is None:
                raise ValueError(f"{describe(line)}: {describe(phase)} has WireInfo but no sequenceNumber; "
                                 f"sequenceNumber links the phase to its WirePosition in the spacing (B2b)")
            result[phase.sequenceNumber] = phase.WireInfo
    return result or None


def _direct_geometry_name(line: cim.ACLineSegment, names) -> str:
    """Name for the B2b LineGeometry: ``<spacing>_c<circuit>`` at offset 0, ``<spacing>_c<circuit>_<offset>m``
    otherwise. ``circuitNumber`` is omitted when None (single-circuit spacing)."""
    spacing = line.WireSpacing
    offset = line_offset(line)
    base = names.name(spacing, "LineGeometry")
    circuit = line.circuitNumber
    suffix = f"_c{circuit}" if circuit is not None else ""
    if offset != 0:
        suffix += f"_{round(offset, _GEOMETRY_DECIMALS)!r}m".replace(".", "p")
    return base + suffix


def export_direct_geometries(context) -> list[schema.Linegeometry]:
    """LineGeometry records for lines using the B2b shape (direct WireSpacing + ACLineSegmentPhase.WireInfo).

    One record per (spacing, circuitNumber, offset) combination; the combination is the geometry name key so that
    lines with different offsets on the same spacing get separate geometries, as in ``linegeometry.py``."""
    first_line: dict[tuple, cim.ACLineSegment] = {}
    for line in context.objects(*CIM_CLASSES):
        if line.WireSpacing is not None and line.WireConfiguration is None:
            wire_infos = _phase_wire_infos(line)
            if wire_infos is None:
                continue
            key = (line.WireSpacing, line.circuitNumber, line_offset(line))
            first_line.setdefault(key, line)

    records = []
    for (spacing, circuit_number, offset), line in first_line.items():
        wire_infos = _phase_wire_infos(line)
        positions = get_line_conductor_xy(line, UNIT)
        seq_numbers = [p.sequence_number for p in positions]
        missing = [seq for seq in seq_numbers if seq not in wire_infos]
        if missing:
            raise ValueError(f"{describe(line)}: sequenceNumbers {missing} have no ACLineSegmentPhase.WireInfo; "
                             f"every position in the circuit needs a wire catalog entry (B2b)")
        phases = get_conductor_phases(line)
        n_phases = sum(1 for p in phases if p is not cim.SinglePhaseKind.N)
        _check_position_kinds(line, positions, n_phases)
        name = _direct_geometry_name(line, context.names)
        records.append(schema.Linegeometry(
            name=name,
            nconds=len(positions),
            nphases=n_phases,
            units=UNIT,
            reduce=True,  # B4: grounded neutral is reduced
            wires=[wire_name(wire_infos[seq], context.names) for seq in seq_numbers],
            xs=[p.x for p in positions],
            hs=[p.y for p in positions],
        ))
    return records


def _check_position_kinds(line: cim.ACLineSegment, positions, n_phases: int) -> None:
    """Positions 1..n_phases must be phase kind (or unset); the rest neutral (or unset)."""
    for index, position in enumerate(positions, start=1):
        expected = cim.ConductorPositionKind.phase if index <= n_phases else cim.ConductorPositionKind.neutral
        if position.kind is not None and position.kind is not expected:
            raise ValueError(f"{describe(line)}: position {position.sequence_number} is {position.kind.value}; "
                             f"DSS takes conductors 1..{n_phases} as phases, the rest neutrals")


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
