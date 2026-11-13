"""Line geometries -> OpenDSS ``LineGeometry`` (``EXPORT_MAPPING.md#linegeometry-b2``).

DSS ``h=`` is a height above ground, and CIM puts a line's height in its ``spacingYOffset`` (G5). Positions are
written inline (B2): the writer emits them as ``cond=`` blocks, which can mix conductor kinds. Geometry stays
geometry: no impedance is computed (skill ``conductor-geometry``). Two CIM shapes are written:

- A line with a WireConfiguration: one geometry per (configuration, offset) among the lines. A configuration no
  line uses is written at offset 0, its spacing's positions as stored.
- A spacing line, with a direct ``WireSpacing`` and a WireInfo on each ACLineSegmentPhase (the EPRI line shape):
  one geometry per (spacing, offset, conductors), the conductors being each phase's sequence number, wire and
  whether it is the neutral. The spacing may hold several circuits; the line takes the positions of its own
  phases. The geometry is named after the first line that has it (``<line>_geometry``).

DSS takes a WireData only above grade, so a plain CableInfo (a WireData, B7) below grade is written at the same
height above it.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
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

_BLOCKS = "the writer folds wires/xs/hs into cond= blocks"
_NOT_IN_CIM = "not in CIM (untranscribed on import)"
SLOTS = {NATIVE_CLASS: {
    "name": Slot("written", "Names; <configuration> at offset 0, <configuration>_<offset>m otherwise, to the mm "
                            "('.' as 'p'); a spacing line's: <line>_geometry of the first line with its spacing, "
                            "offset and conductors"),
    "nconds": Slot("written", "the spacing's positions; a spacing line's: its phases' positions"),
    "nphases": Slot("written", "WireConfiguration.numberOfPhases, required; a spacing line's: its phases other "
                               "than N; position kinds phase then neutral"),
    "cond": Slot("not mapped", _BLOCKS), "wire": Slot("not mapped", _BLOCKS),
    "x": Slot("not mapped", _BLOCKS), "h": Slot("not mapped", _BLOCKS),
    "units": Slot("written", "m (B1)"),
    "normamps": Slot("unset", "no rating on a WireConfiguration (D9); the Line carries its own"),
    "emergamps": Slot("unset", "no rating on a WireConfiguration (D9); the Line carries its own"),
    "reduce": Slot("written", "y: the neutrals grounded at both ends, as the impedance getters assume (B4)"),
    "spacing": Slot("not mapped", "positions are written inline (B2)"),
    "wires": Slot("written", "get_configuration_wires, or a spacing line's get_line_phase_wires, by sequence "
                             "number; any of the three catalogs"),
    "cncable": Slot("not mapped", _BLOCKS), "tscable": Slot("not mapped", _BLOCKS),
    "cncables": Slot("not mapped", "wires carries every kind (the writer names each block's kind)"),
    "tscables": Slot("not mapped", "wires carries every kind (the writer names each block's kind)"),
    "xs": Slot("written", "get_line_conductor_xy x (m); an unused configuration: get_spacing_xy"),
    "hs": Slot("written", "get_line_conductor_xy y, above ground (m); a plain CableInfo's abs(y) (B7)"),
    "Seasons": Slot("unset", _NOT_IN_CIM), "Ratings": Slot("unset", _NOT_IN_CIM),
    "LineType": Slot("unset", _NOT_IN_CIM),
    "conductors": Slot("not mapped", "wires carries the names"),
    "like": Slot("not mapped", "the writer never writes like="),
}}


def line_offset(line: cim.ACLineSegment) -> float:
    """The line's spacingYOffset in m; unset is 0, the spacing's origin at ground."""
    offset = get_qty(line, "spacingYOffset", UNIT)
    return 0.0 if offset is None else offset


def geometry_name(configuration: cim.WireConfiguration, offset: float, names: Names) -> str:
    """The DSS name of ``configuration`` at ``offset`` (m), as its record and every Line write it."""
    suffix = "" if offset == 0 else f"_{round(offset, NAME_DECIMALS)!r}m".replace(".", "p")
    return names.name(configuration, NAMESPACE, suffix=suffix)


def is_spacing_line(line: cim.ACLineSegment) -> bool:
    """A line with a direct WireSpacing and no WireConfiguration: its wires are on its ACLineSegmentPhases."""
    return line.WireConfiguration is None and line.WireSpacing is not None


def spacing_geometry_owners(context) -> dict[cim.ACLineSegment, cim.ACLineSegment]:
    """Each spacing line -> the first spacing line with its spacing, offset and conductors, which names their
    geometry."""
    first, owners = {}, {}
    for line in context.objects(cim.ACLineSegment):
        if is_spacing_line(line):
            owners[line] = first.setdefault(_spacing_key(line), line)
    return owners


def spacing_geometry_name(owner: cim.ACLineSegment, names: Names) -> str:
    """The DSS name of the geometry ``owner`` (from ``spacing_geometry_owners``) names: ``<line>_geometry``, apart
    from a configuration the DSS importer names after its line."""
    return names.name(owner, NAMESPACE, suffix="_geometry")


def export(context) -> list[schema.Linegeometry]:
    """One LineGeometry per (configuration, offset) over the lines, then one per unused configuration, then one per
    spacing-line owner."""
    first_line = {}
    for line in context.objects(cim.ACLineSegment):
        if line.WireConfiguration is not None:
            first_line.setdefault((line.WireConfiguration, line_offset(line)), line)
    _check_names_differ(first_line)
    records = []
    for (configuration, offset), line in first_line.items():
        positions = get_line_conductor_xy(line, UNIT)
        records.append(_geometry(configuration, offset, positions, context.names))
    used = {configuration for configuration, _ in first_line}
    for configuration in context.objects(*CIM_CLASSES):
        if configuration not in used:
            if configuration.WireSpacing is None:
                raise ValueError(f"{describe(configuration)}: has no WireSpacing")
            positions = get_spacing_xy(configuration.WireSpacing, UNIT)
            records.append(_geometry(configuration, 0.0, positions, context.names))
    for owner in dict.fromkeys(spacing_geometry_owners(context).values()):
        records.append(_spacing_geometry(owner, context.names))
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
                             f"spacingYOffset {offset} m and one within a mm of it share one LineGeometry name")
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
