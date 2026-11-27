"""Line geometries -> OpenDSS ``LineGeometry`` (``EXPORT_MAPPING.md#linegeometry-b2``).

DSS ``h=`` is a height above ground, and CIM puts a line's height in its ``ySpacingOffset`` (G5). Positions are
written inline (B2): the writer emits them as ``cond=`` blocks, which can mix conductor kinds. Geometry stays
geometry: no impedance is computed (skill ``conductor-geometry``). Two CIM shapes are written:

- A line with geometry, a WireConfiguration naming a WireSpacing (``get_line_geometry``): one geometry per
  (configuration, offset) among the lines. A configuration no line uses is written at offset 0 on the spacing's
  positions its own WireSequenceConfigurations name: a template spacing may hold several circuits, each its own
  configuration. A WireConfiguration with a PerLengthImpedance and no WireSpacing is a template LineCode,
  which ``linecode.py`` writes.
- A spacing line, with a direct ``WireSpacing`` and a WireInfo on each ACLineSegmentPhase (the EPRI line shape):
  one geometry per (spacing, offset, conductors), the conductors being each phase's sequence number, wire and
  whether it is the neutral. The spacing may hold several circuits; the line takes the positions of its own
  phases. The geometry is named after the first line that has it (``<line>_geometry``).
- The lines of one ``MultiCircuitGroup`` at its highest nominal voltage, when two or more are in the network (H1,
  H5, ``coupled_groups``), each a spacing line or a line with geometry: one geometry for the group (``<group>_geometry``), every line's phase conductors in circuit
  order and then the neutrals. A position on several lines is one conductor (H6), so a shared neutral is written
  once. ``line.py`` writes the group as one DSS line on it, so the circuits are coupled. Every other line of a group
  is an ordinary line on its own positions, and so is the rest of a coupled line beyond the group's length
  (H4).

DSS takes a WireData only above grade, so a plain CableInfo (a WireData, B7) below grade is written at the same
height above it.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.earth import get_earth_resistivity, get_network_earth
from cimhub_core.getters.line_impedance import get_line_geometry
from cimhub_core.getters.spacing import ConductorXY, get_line_conductor_xy, get_spacing_xy
from cimhub_core.getters.wire import get_configuration_wires, get_line_phase_wires
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot
from cimhub_opendss.exporter.wire import wire_name
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.WireConfiguration,)
NATIVE_CLASS = schema.Linegeometry
NAMESPACE = "LineGeometry"
UNIT = "m"  # B1
#: a name carries the offset to the mm (10p363m), so two offsets of one configuration must differ by more
NAME_DECIMALS = 3

LOGGER = logging.getLogger(__name__)


class CoupledGroup(NamedTuple):
    """A MultiCircuitGroup's lines written as one DSS line (H1): ``lines`` in circuit order, coupled over
    ``length`` (m, to the mm), the shortest line's. ``remainders`` is the rest of each longer line (m), written as
    that line's own section at its terminal-2 end (H4)."""

    lines: tuple[cim.ACLineSegment, ...]
    length: float
    remainders: dict[cim.ACLineSegment, float]
    rho: float | None  # ohm-m, line_rho of every line

_BLOCKS = "the writer folds wires/xs/hs into cond= blocks"
_NOT_IN_CIM = "not in CIM (untranscribed on import)"
SLOTS = {NATIVE_CLASS: {
    "name": Slot("written", "Names; <configuration> at offset 0, <configuration>_<offset>m otherwise, to the mm "
                            "('.' as 'p'); a spacing line's: <line>_geometry of the first line with its spacing, "
                            "offset and conductors; a coupled group's: <group>_geometry (H1)"),
    "nconds": Slot("written", "the configuration's positions; a spacing line's: its phases' positions; a coupled group's: "
                              "its lines' positions, a shared neutral once"),
    "nphases": Slot("written", "WireConfiguration.numberOfPhases, required; a spacing line's: its phases other "
                               "than N, a coupled group's: every line's; position kinds phase then neutral"),
    "cond": Slot("not mapped", _BLOCKS), "wire": Slot("not mapped", _BLOCKS),
    "x": Slot("not mapped", _BLOCKS), "h": Slot("not mapped", _BLOCKS),
    "units": Slot("written", "m (B1)"),
    "normamps": Slot("unset", "no rating on a WireConfiguration (D9); the Line carries its own"),
    "emergamps": Slot("unset", "no rating on a WireConfiguration (D9); the Line carries its own"),
    "reduce": Slot("written", "y: the neutrals grounded at both ends, as the impedance getters assume (B4)"),
    "spacing": Slot("not mapped", "positions are written inline (B2)"),
    "wires": Slot("written", "get_configuration_wires, or a spacing line's get_line_phase_wires (line_wires), "
                             "by sequence number; any of the three catalogs"),
    "cncable": Slot("not mapped", _BLOCKS), "tscable": Slot("not mapped", _BLOCKS),
    "cncables": Slot("not mapped", "wires carries every kind (the writer names each block's kind)"),
    "tscables": Slot("not mapped", "wires carries every kind (the writer names each block's kind)"),
    "xs": Slot("written", "get_line_conductor_xy x (m); an unused configuration: get_spacing_xy on its "
                          "WireSequenceConfigurations' sequence numbers"),
    "hs": Slot("written", "get_line_conductor_xy y, above ground (m); a plain CableInfo's abs(y) (B7)"),
    "Seasons": Slot("unset", _NOT_IN_CIM), "Ratings": Slot("unset", _NOT_IN_CIM),
    "LineType": Slot("unset", _NOT_IN_CIM),
    "conductors": Slot("not mapped", "wires carries the names"),
    "like": Slot("not mapped", "the writer never writes like="),
}}


def line_offset(line: cim.ACLineSegment) -> float:
    """The line's ySpacingOffset in m; unset is 0, the spacing's origin at ground."""
    offset = get_qty(line, "ySpacingOffset", UNIT)
    return 0.0 if offset is None else offset


def geometry_name(configuration: cim.WireConfiguration, offset: float, names: Names) -> str:
    """The DSS name of ``configuration`` at ``offset`` (m), as its record and every Line write it."""
    rounded = round(offset, NAME_DECIMALS) + 0.0
    suffix = "" if rounded == 0 else f"_{rounded!r}m".replace(".", "p")
    return names.name(configuration, NAMESPACE, suffix=suffix)


def is_spacing_line(line: cim.ACLineSegment) -> bool:
    """A line with a direct WireSpacing and no WireConfiguration: its wires are on its ACLineSegmentPhases."""
    return line.WireConfiguration is None and line.WireSpacing is not None


def line_wires(line: cim.ACLineSegment) -> dict[int, cim.WireInfo]:
    """Sequence number -> WireInfo: a line with geometry's from its WireConfiguration, a spacing line's from its
    ACLineSegmentPhases."""
    configuration = get_line_geometry(line)
    if configuration is not None:
        return dict(get_configuration_wires(configuration))
    return dict(get_line_phase_wires(line))


def line_rho(line: cim.ACLineSegment, network) -> float | None:
    """The earth resistivity (ohm-m) of a line with geometry: its WireConfiguration's EarthResistivity, None when it
    names none (DSS's default); a spacing line's the network's one (``get_network_earth``)."""
    configuration = get_line_geometry(line)
    if configuration is None:
        return get_network_earth(network).rho
    earth = get_earth_resistivity(configuration)
    return None if earth is None else earth.rho


def spacing_geometry_owners(context) -> dict[cim.ACLineSegment, cim.ACLineSegment]:
    """Each spacing line written on its own positions -> the first such line with its spacing, offset and
    conductors, which names their geometry. A coupled line is one only for its remainder (H4)."""
    whole = {line for group in context.coupled.values() for line in group.lines if line not in group.remainders}
    first, owners = {}, {}
    for line in context.objects(cim.ACLineSegment):
        if is_spacing_line(line) and line not in whole:
            owners[line] = first.setdefault(_spacing_key(line), line)
    return owners


def spacing_geometry_name(owner, names: Names) -> str:
    """The DSS name of the geometry ``owner`` names: ``<line>_geometry`` for a line from ``spacing_geometry_owners``
    (apart from a configuration the DSS importer names after its line), ``<group>_geometry`` for a coupled group."""
    return names.name(owner, NAMESPACE, suffix="_geometry")


def coupled_groups(network) -> dict[cim.MultiCircuitGroup, CoupledGroup]:
    """Each MultiCircuitGroup with two or more lines in the network at its highest nominal voltage -> those lines,
    coupled (H1). The group's lines at another voltage (an underbuilt secondary) stay on their own positions (H5).
    The coupled lines must be spacing lines or lines with geometry, either kind, on one spacing at one offset over
    one earth, each with a wire on each of its phases' positions. A position several of them name is one
    conductor and must be a neutral on each (H6); a phase position on several (series pieces of one circuit) leaves
    the group uncoupled, with a warning (H7). ``cim_to_dss`` calls it once, for ``ExportContext.coupled``."""
    members = {}
    for line in network.graph.get(cim.ACLineSegment, {}).values():
        if line.MultiCircuitGroup is not None:
            members.setdefault(line.MultiCircuitGroup, []).append(line)
    groups = {}
    for group, lines in members.items():
        voltages = {line: get_base_voltage(line, "kV", form="LL") for line in lines}
        top = max(voltages.values())
        lines = [line for line in lines if voltages[line] == top]
        if len(lines) < 2:
            continue
        for line in lines:
            if get_line_geometry(line) is None and not is_spacing_line(line):
                raise ValueError(f"{describe(line)}: one of {len(lines)} lines of {describe(group)}, but has no "
                                 f"geometry (a WireConfiguration naming a WireSpacing, or a direct WireSpacing); only "
                                 f"lines with geometry are coupled")
            wired = sorted(line_wires(line))
            phased = sorted(phase.sequenceNumber for phase in line.ACLineSegmentPhases
                            if phase.sequenceNumber is not None)
            if wired != phased or len(phased) != len(line.ACLineSegmentPhases):
                raise ValueError(f"{describe(line)} of {describe(group)}: wires on sequence numbers {wired}, "
                                 f"ACLineSegmentPhases on {phased} of {len(line.ACLineSegmentPhases)}; a coupled "
                                 f"line needs each phase on a sequence number with a wire")
        group_value(group, lines, "spacings",
                    lambda line: (line.WireSpacing or line.WireConfiguration.WireSpacing).mRID)
        group_value(group, lines, "ySpacingOffsets (m, to the mm)",
                    lambda line: round(line_offset(line), NAME_DECIMALS))
        rho = group_value(group, lines, "earth resistivities (ohm-m)", lambda line: line_rho(line, network))
        shared = _shared_phase_positions(lines)
        if shared:
            LOGGER.warning("%s: %s name phase positions %s of one another; written uncoupled, on their own positions "
                           "(H7)", describe(group), [line.mRID for line in lines], shared)
            continue
        lengths = {line: round(required_qty(line, "length", UNIT), NAME_DECIMALS) for line in lines}
        length = min(lengths.values())
        if length <= 0:
            raise ValueError(f"{describe(group)}: coupled line length {length} m must be positive")
        remainders = {line: round(lengths[line] - length, NAME_DECIMALS) for line in lines if lengths[line] > length}
        groups[group] = CoupledGroup(tuple(sorted(lines, key=_lowest_phase_number)), length, remainders, rho)
    return groups


def group_value(group: cim.MultiCircuitGroup, lines, what: str, value_of):
    """The one value of ``value_of`` over the group's lines. Lines that differ raise: one DSS line carries them."""
    values = {line.mRID: value_of(line) for line in lines}
    first = values[lines[0].mRID]
    if any(value != first for value in values.values()):
        raise ValueError(f"{describe(group)}: its lines' {what} differ {values}; one DSS line carries the group")
    return first


def export(context) -> list[schema.Linegeometry]:
    """One LineGeometry per (configuration, offset) over the lines, then one per unused configuration, then one per
    spacing-line owner."""
    whole = {line for group in context.coupled.values() for line in group.lines if line not in group.remainders}
    first_line = {}
    for line in context.objects(cim.ACLineSegment):
        if line in whole:
            continue
        configuration = get_line_geometry(line)
        if configuration is not None:
            first_line.setdefault((configuration, line_offset(line)), line)
    _check_names_differ(first_line)
    records = []
    for (configuration, offset), line in first_line.items():
        positions = get_line_conductor_xy(line, UNIT)
        records.append(_geometry(configuration, offset, positions, context.names))
    used = {configuration for configuration, _ in first_line}
    for configuration in context.objects(*CIM_CLASSES):
        if configuration not in used:
            if configuration.WireSpacing is None:
                if configuration.PerLengthImpedance is not None:
                    continue  # a template LineCode
                raise ValueError(f"{describe(configuration)}: has neither a WireSpacing nor a PerLengthImpedance")
            wires = dict(get_configuration_wires(configuration))
            positions = tuple(position for position in get_spacing_xy(configuration.WireSpacing, UNIT)
                              if position.sequence_number in wires)
            records.append(_geometry(configuration, 0.0, positions, context.names))
    for owner in dict.fromkeys(spacing_geometry_owners(context).values()):
        records.append(_spacing_geometry(owner, context.names))
    for group, coupled in context.coupled.items():
        records.append(_coupled_geometry(group, coupled.lines, context.names))
    return records


def _spacing_key(line: cim.ACLineSegment) -> tuple:
    if not get_line_phase_wires(line):
        raise ValueError(f"{describe(line)}: has a WireSpacing but no ACLineSegmentPhase.WireInfo; a spacing line "
                         f"needs a wire on each phase (B2)")
    conductors = tuple((phase.sequenceNumber, phase.WireInfo, phase.phase is cim.SinglePhaseKind.N)
                       for phase in sorted(line.ACLineSegmentPhases, key=lambda phase: phase.sequenceNumber))
    return line.WireSpacing, line_offset(line), conductors


def _check_names_differ(first_line: dict) -> None:
    """Two offsets of one configuration that round to one name raise, naming both lines."""
    named = {}
    for (configuration, offset), line in first_line.items():
        key = (configuration, round(offset, NAME_DECIMALS))
        if key in named:
            raise ValueError(f"{describe(named[key])} and {describe(line)}: {describe(configuration)} at "
                             f"ySpacingOffset {offset} m and one within a mm of it share one LineGeometry name")
        named[key] = line


def _geometry(configuration: cim.WireConfiguration, offset: float, positions: tuple[ConductorXY, ...],
              names: Names) -> schema.Linegeometry:
    wires = dict(get_configuration_wires(configuration))
    numbers = [position.sequence_number for position in positions]
    if sorted(wires) != sorted(numbers):
        raise ValueError(f"{describe(configuration)}: wires on sequence numbers {sorted(wires)}, positions on "
                         f"{numbers}")
    phases = configuration.numberOfPhases
    if phases is None:
        raise ValueError(f"{describe(configuration)}: numberOfPhases is unset")
    return _record(configuration, geometry_name(configuration, offset, names), positions,
                   [wires[number] for number in numbers], phases, names)


def _spacing_geometry(line: cim.ACLineSegment, names: Names) -> schema.Linegeometry:
    """The positions are those of the line's phases (``get_line_conductor_xy``), so each has the wire of its phase."""
    wires = dict(get_line_phase_wires(line))
    positions = get_line_conductor_xy(line, UNIT)
    phases = sum(1 for phase in line.ACLineSegmentPhases if phase.phase is not cim.SinglePhaseKind.N)
    return _record(line, spacing_geometry_name(line, names), positions,
                   [wires[position.sequence_number] for position in positions], phases, names)


def _coupled_geometry(group: cim.MultiCircuitGroup, lines: tuple[cim.ACLineSegment, ...],
                      names: Names) -> schema.Linegeometry:
    """Every line's phase conductors in circuit order, then the neutrals in sequence-number order. A neutral
    position on several lines is one conductor (H6), on one wire. SharedPhases is not needed; where a phase names a
    MultiCircuitGroup, it must be its line's."""
    conductors = {}  # sequence number -> (position, wire, is it a neutral)
    for line in lines:
        wires = line_wires(line)
        phases = {phase.sequenceNumber: phase for phase in line.ACLineSegmentPhases}
        for position in get_line_conductor_xy(line, UNIT):
            number, phase = position.sequence_number, phases[position.sequence_number]
            if phase.MultiCircuitGroup not in (None, group):
                raise ValueError(f"{describe(phase)} of {describe(line)} in {describe(group)}: is a shared phase of "
                                 f"{describe(phase.MultiCircuitGroup)}")
            _, wire, _ = conductors.setdefault(number, (position, wires[number], phase.phase is cim.SinglePhaseKind.N))
            if wire is not wires[number]:
                raise ValueError(f"{describe(group)}: sequence number {number} is {describe(wire)} on one line and "
                                 f"{describe(wires[number])} on {describe(line)}")
    neutrals = sorted(number for number, (_, _, neutral) in conductors.items() if neutral)
    order = [number for number in conductors if number not in neutrals] + neutrals
    return _record(group, spacing_geometry_name(group, names), tuple(conductors[number][0] for number in order),
                   [conductors[number][1] for number in order], len(conductors) - len(neutrals), names)


def _shared_phase_positions(lines: list[cim.ACLineSegment]) -> list[int]:
    """The sequence numbers several of the lines name, other than those every one names as a neutral."""
    on = {}
    for line in lines:
        for phase in line.ACLineSegmentPhases:
            on.setdefault(phase.sequenceNumber, []).append(phase.phase)
    return sorted(number for number, kinds in on.items()
                  if len(kinds) > 1 and any(kind is not cim.SinglePhaseKind.N for kind in kinds))


def _lowest_phase_number(line: cim.ACLineSegment) -> int:
    return min(phase.sequenceNumber for phase in line.ACLineSegmentPhases if phase.phase is not cim.SinglePhaseKind.N)


def _record(owner, name: str, positions: tuple[ConductorXY, ...], wires: list[cim.WireInfo], phases: int,
            names: Names) -> schema.Linegeometry:
    _check_kinds(owner, positions, phases)
    return NATIVE_CLASS(
        name=name,
        nconds=len(positions),
        nphases=phases,
        units=UNIT,
        reduce=True,  # B4
        wires=[wire_name(wire, names) for wire in wires],
        xs=[position.x for position in positions],
        hs=[_height(position, wire) for position, wire in zip(positions, wires, strict=True)],
    )


def _height(position: ConductorXY, wire: cim.WireInfo) -> float:
    """B7: a buried plain CableInfo is mirrored above grade, the one place DSS takes its WireData."""
    return abs(position.y) if type(wire) is cim.CableInfo else position.y


def _check_kinds(owner, positions: tuple[ConductorXY, ...], phases: int) -> None:
    """DSS's conductors 1..nphases are phases and the rest neutrals; a position's kind, where set, must agree."""
    for index, position in enumerate(positions, start=1):
        expected = cim.ConductorPositionKind.phase if index <= phases else cim.ConductorPositionKind.neutral
        if position.kind is not None and position.kind is not expected:
            raise ValueError(f"{describe(owner)}: position {position.sequence_number} is "
                             f"{position.kind.value}; DSS takes conductors 1..{phases} as phases, the rest neutrals")
