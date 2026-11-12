"""(WireConfiguration, spacingYOffset) -> OpenDSS ``LineGeometry`` (``EXPORT_MAPPING.md#linegeometry-b2``).

DSS ``h=`` is a height above ground, and CIM puts a line's height in its ``spacingYOffset`` (G5), so one geometry is
written per (configuration, offset) among the lines, with its positions inline (B2): the writer emits them as
``cond=`` blocks, which can mix conductor kinds. A configuration no line uses is written at offset 0, its spacing's
positions as stored. Geometry stays geometry: no impedance is computed (skill ``conductor-geometry``).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.spacing import get_line_conductor_xy, get_spacing_xy
from cimhub_core.getters.wire import get_configuration_wires
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot
from cimhub_opendss.exporter.wire import wire_name
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.WireConfiguration,)
NATIVE_CLASS = schema.Linegeometry
NAMESPACE = "LineGeometry"
UNIT = "m"  # B1

_BLOCKS = "the writer folds wires/xs/hs into cond= blocks"
_NOT_IN_CIM = "not in CIM (untranscribed on import)"
SLOTS = {NATIVE_CLASS: {
    "name": Slot("written", "Names; <configuration> at offset 0, <configuration>_<offset>m otherwise ('.' as 'p')"),
    "nconds": Slot("written", "the spacing's positions"),
    "nphases": Slot("written", "WireConfiguration.numberOfPhases, required; position kinds phase then neutral"),
    "cond": Slot("not mapped", _BLOCKS), "wire": Slot("not mapped", _BLOCKS),
    "x": Slot("not mapped", _BLOCKS), "h": Slot("not mapped", _BLOCKS),
    "units": Slot("written", "m (B1)"),
    "normamps": Slot("unset", "no rating on a WireConfiguration (D9); the Line carries its own"),
    "emergamps": Slot("unset", "no rating on a WireConfiguration (D9); the Line carries its own"),
    "reduce": Slot("written", "y: the neutrals grounded at both ends, as the impedance getters assume (B4)"),
    "spacing": Slot("not mapped", "positions are written inline (B2)"),
    "wires": Slot("written", "get_configuration_wires, by sequence number; any of the three catalogs"),
    "cncable": Slot("not mapped", _BLOCKS), "tscable": Slot("not mapped", _BLOCKS),
    "cncables": Slot("not mapped", "wires carries every kind (the writer names each block's kind)"),
    "tscables": Slot("not mapped", "wires carries every kind (the writer names each block's kind)"),
    "xs": Slot("written", "get_line_conductor_xy x (m); an unused configuration: get_spacing_xy"),
    "hs": Slot("written", "get_line_conductor_xy y, above ground (m)"),
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
    suffix = "" if offset == 0 else f"_{offset!r}m".replace(".", "p")
    return names.name(configuration, NAMESPACE, suffix=suffix)


def export(context) -> list[schema.Linegeometry]:
    """One LineGeometry per (configuration, offset) over the lines, then one per unused configuration."""
    first_line = {}
    for line in context.objects(cim.ACLineSegment):
        if line.WireConfiguration is not None:
            first_line.setdefault((line.WireConfiguration, line_offset(line)), line)
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
    return records


def _geometry(configuration: cim.WireConfiguration, offset: float, positions, names: Names) -> schema.Linegeometry:
    wires = dict(get_configuration_wires(configuration))
    numbers = [position.sequence_number for position in positions]
    if sorted(wires) != numbers:
        raise ValueError(f"{describe(configuration)}: wires on sequence numbers {sorted(wires)}, positions on "
                         f"{numbers}")
    phases = configuration.numberOfPhases
    if phases is None:
        raise ValueError(f"{describe(configuration)}: numberOfPhases is unset")
    _check_kinds(configuration, positions, phases)
    return NATIVE_CLASS(
        name=geometry_name(configuration, offset, names),
        nconds=len(positions),
        nphases=phases,
        units=UNIT,
        reduce=True,  # B4
        wires=[wire_name(wires[number], names) for number in numbers],
        xs=[position.x for position in positions],
        hs=[position.y for position in positions],
    )


def _check_kinds(configuration: cim.WireConfiguration, positions, phases: int) -> None:
    """DSS's conductors 1..nphases are phases and the rest neutrals; a position's kind, where set, must agree."""
    for index, position in enumerate(positions, start=1):
        expected = cim.ConductorPositionKind.phase if index <= phases else cim.ConductorPositionKind.neutral
        if position.kind is not None and position.kind is not expected:
            raise ValueError(f"{describe(configuration)}: position {position.sequence_number} is "
                             f"{position.kind.value}; DSS takes conductors 1..{phases} as phases, the rest neutrals")
