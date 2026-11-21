"""ACLineSegment -> ``overhead_line``, ``underground_line`` or ``triplex_line``, with the catalogs they name
(``EXPORT_MAPPING.md#x1-lines-and-switches``; skill ``conductor-geometry``).

A line with a ``WireConfiguration`` is geometry (its configuration names conductors and a spacing), whatever else it
has; otherwise its ``PerLengthImpedance`` is a matrix configuration; neither raises. A split-phase line (s1, s2) is a
``triplex_line``; a geometry line with a cable is an ``underground_line``; every other line an ``overhead_line``.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import get_current_limits
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimhub_gridlabd.exporter import line_catalog
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.line_catalog import LETTER, GeometryKey, MatrixKey
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

CIM_CLASSES = (cim.ACLineSegment,)
LINE_CLASSES = (schema.OverheadLine, schema.UndergroundLine, schema.TriplexLine)
#: a key's conductors in this order, so two lines on the same phases give one key
_ORDER = "ABCN12"

_LINE_SLOTS = {
    "name": Slot("written", "Names (X1)"),
    "phases": Slot("written", "the line's A, B, C, then N when it has a neutral conductor; a triplex line its "
                              "buses' service letter, then S"),
    "from_node": Slot("written", "terminal 1's bus"), "to": Slot("written", "terminal 2's bus"),
    "length": Slot("written", "ACLineSegment.length (ft); unset raises"),
    "configuration": Slot("written", "line_catalog: the configuration of the line's key"),
    **{f"continuous_rating_{letter}": Slot("written", "get_current_limits normal, on each of the line's phases")
       for letter in "ABC"},
    **{f"emergency_rating_{letter}": Slot("written", "get_current_limits emergency") for letter in "ABC"},
}
SLOTS = {
    **line_catalog.SLOTS,
    **{native_class: with_default(native_class, _LINE_SLOTS, Slot("unset", "not in CIM; GridLAB-D's default"))
       for native_class in LINE_CLASSES},
}


def export(context) -> list:
    """The catalogs the lines use, then the lines."""
    keyed = [(line, line_key(line)) for line in context.objects(*CIM_CLASSES)]
    keys, lines_by_key = [], {}
    for line, key in keyed:
        if key not in lines_by_key:
            keys.append(key)
            lines_by_key[key] = line
    catalog = line_catalog.build_catalog(keys, context.names, context.frequency, lines_by_key)
    return [*catalog.records, *(_line(line, key, catalog.names[key], context) for line, key in keyed)]


def line_key(line: cim.ACLineSegment) -> GeometryKey | MatrixKey:
    """How the line uses its template (``line_catalog``)."""
    phases = get_conductor_phases(line)
    triplex = any(phase in (cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2) for phase in phases)
    if line.WireConfiguration is not None:
        if isinstance(line.WireConfiguration.WireSpacing, cim.XYSpacing) and get_qty(line, "ySpacingOffset", "m"):
            raise ValueError(f"{describe(line)}: a ySpacingOffset on an XYSpacing is not exported yet (GLM's heights "
                             f"are on the shared line_spacing)")
        return GeometryKey(line.WireConfiguration, _conductors(line, phases), triplex)
    if line.PerLengthImpedance is not None:
        return MatrixKey(line.PerLengthImpedance, tuple(LETTER[phase] for phase in phases), triplex)
    raise ValueError(f"{describe(line)}: has neither a WireConfiguration nor a PerLengthImpedance")


def _conductors(line: cim.ACLineSegment, phases) -> tuple[tuple[str, int], ...]:
    """(GLM letter, sequence number) of each conductor: the ACLineSegmentPhases', else 1..n in conductor order."""
    if line.ACLineSegmentPhases:
        numbered = [(LETTER[phase.phase], phase.sequenceNumber) for phase in line.ACLineSegmentPhases]
    else:
        numbered = [(LETTER[phase], number) for number, phase in enumerate(phases, start=1)]
    return tuple(sorted(numbered, key=lambda item: _ORDER.index(item[0])))


def _line_class(key) -> type:
    if key.triplex:
        return schema.TriplexLine
    if isinstance(key, GeometryKey) and any(conductor_class is schema.UndergroundLineConductor
                                            for _, conductor_class in line_catalog.key_wires(key)):
        return schema.UndergroundLine
    return schema.OverheadLine


def _line(line: cim.ACLineSegment, key, configuration: str, context):
    native_class = _line_class(key)
    first, second = get_terminal_nodes(line)
    phases = get_conductor_phases(line)
    if key.triplex:
        glm_phases = context.buses[first].phases
    else:
        glm_phases = letters(phases) + ("N" if cim.SinglePhaseKind.N in phases else "")
    slots = {"name": context.names.name(line), "phases": glm_phases, "from_node": context.buses[first].name,
             "to": context.buses[second].name, "configuration": configuration,
             "length": required_qty(line, "length", glm_unit(native_class, "length"))}
    if not key.triplex:
        slots.update(ratings(line, letters(phases), native_class))
    return native_class(**slots)


def ratings(equipment, phase_letters: str, native_class: type) -> dict:
    """A link's ``continuous_rating_X``/``emergency_rating_X`` on each of its phases (``get_current_limits``)."""
    limits = get_current_limits(equipment, glm_unit(native_class, "continuous_rating_A"))
    slots = {}
    for letter in phase_letters:
        slots[f"continuous_rating_{letter}"] = limits.normal
        slots[f"emergency_rating_{letter}"] = limits.emergency
    return slots
