"""ACLineSegment → MatrixImpedanceBranch or SequenceImpedanceBranch, on shared catalogs (``EXPORT_MAPPING.md#lines``).

The line's PerLengthImpedance picks the GDM class: PerLengthPhaseImpedance → MatrixImpedanceBranchEquipment,
PerLengthSequenceImpedance → SequenceImpedanceBranchEquipment. GDM puts the line's ``ampacity`` on the catalog, so one
GDM equipment is made per (catalog, normal current limit): ``<catalog>`` for the first limit seen, ``<catalog>_2``
and on for others (X3). A line with a WireConfiguration is a GeometryBranch on its wires and positions (``geometry.py``, X4), never a
computed matrix (CONDUCTOR_GEOMETRY_ANTI_PATTERNS.md).

GDM holds capacitance, CIM susceptance: C = b / (2πf) at the importer's 60 Hz, the inverse of its ``susceptance``.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
import numpy as np
from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.current_limits import get_current_limits
from cimhub_core.getters.line_impedance import get_line_phase_impedance_matrix, get_line_sequence_impedance_per_length
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from gdm.quantities import CapacitancePULength, ReactancePULength, ResistancePULength
from gdm.systems.distribution.components import GeometryBranch, MatrixImpedanceBranch, SequenceImpedanceBranch
from gdm.systems.distribution.equipment import MatrixImpedanceBranchEquipment, SequenceImpedanceBranchEquipment
from infrasys.quantities import Current, Distance

from cimhub_gdm.exporter import geometry
from cimhub_gdm.exporter.shared import ExportContext, containers, gdm_phases, in_service, shared_equipment
from cimhub_gdm.exporter.slots import UUID, Slot
from cimhub_gdm.importer.shared import FREQUENCY_HZ

CIM_CLASSES = (cim.ACLineSegment,)

#: Per-length units the getters are asked for; GDM converts on use.
IMPEDANCE_UNIT, ADMITTANCE_UNIT = "ohm/km", "S/km"
GDM_IMPEDANCE_UNIT, GDM_CAPACITANCE_UNIT = "ohm / kilometer", "farad / kilometer"

_LINE_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "Names (X2)"),
    "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
    "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
    "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
    "buses": Slot("written", "get_terminal_nodes"),
    "length": Slot("written", "required_qty(length, 'm')"),
    "phases": Slot("written", "get_conductor_phases: ACLineSegmentPhase order, the matrix's row order"),
}
_AMPACITY = Slot("written", "get_current_limits(line).normal (A) of the lines on it; unset raises")

SLOTS = {
    MatrixImpedanceBranch: _LINE_SLOTS | {
        "equipment": Slot("written", "the MatrixImpedanceBranchEquipment for (PerLengthPhaseImpedance, ampacity)"),
    },
    SequenceImpedanceBranch: _LINE_SLOTS | {
        "equipment": Slot("written", "the SequenceImpedanceBranchEquipment for (PerLengthSequenceImpedance, "
                                     "ampacity)"),
    },
    GeometryBranch: _LINE_SLOTS | {
        "equipment": Slot("written", "the GeometryBranchEquipment for (WireConfiguration, the line's positions and "
                                     "ratings) (geometry.py)"),
    },
    MatrixImpedanceBranchEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the catalog's name; <catalog>_<n> for its n-th ampacity (X3)"),
        "construction": Slot("unset", "untranscribed on import: no home on PerLengthImpedance; GDM's default"),
        "r_matrix": Slot("written", "get_line_phase_impedance_matrix.r (ohm/km), the lower triangle mirrored"),
        "x_matrix": Slot("written", "get_line_phase_impedance_matrix.x (ohm/km)"),
        "c_matrix": Slot("rule", "get_line_phase_impedance_matrix.b (S/km) / 2πf; unset b is zero; a non-zero g "
                                 "raises: GDM has no shunt conductance"),
        "ampacity": _AMPACITY,
    },
    SequenceImpedanceBranchEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the catalog's name; <catalog>_<n> for its n-th ampacity (X3)"),
        "pos_seq_resistance": Slot("written", "get_line_sequence_impedance_per_length.r (ohm/km)"),
        "zero_seq_resistance": Slot("written", "get_line_sequence_impedance_per_length.r0; unset raises"),
        "pos_seq_reactance": Slot("written", "get_line_sequence_impedance_per_length.x"),
        "zero_seq_reactance": Slot("written", "get_line_sequence_impedance_per_length.x0; unset raises"),
        "pos_seq_capacitance": Slot("rule", "b (S/km) / 2πf; unset is zero; a non-zero g raises"),
        "zero_seq_capacitance": Slot("rule", "b0 (S/km) / 2πf; unset is zero; a non-zero g0 raises"),
        "ampacity": _AMPACITY,
    },
    **geometry.SLOTS,
}


def export(line: cim.ACLineSegment, context: ExportContext):
    code = line.PerLengthImpedance
    phases = get_conductor_phases(line)
    if line.WireConfiguration is not None:
        if code is not None:
            raise ValueError(f"{describe(line)}: has both a WireConfiguration and a PerLengthImpedance")
        component_class, equipment = GeometryBranch, geometry.geometry_equipment(line, len(phases), context)
    elif isinstance(code, cim.PerLengthPhaseImpedance):
        component_class, equipment = MatrixImpedanceBranch, catalog(line, code, context)
    elif isinstance(code, cim.PerLengthSequenceImpedance):
        component_class, equipment = SequenceImpedanceBranch, catalog(line, code, context)
    else:
        raise ValueError(f"{describe(line)}: has no PerLengthImpedance or WireConfiguration; GDM lines are per "
                         "length")
    node1, node2 = get_terminal_nodes(line)
    return component_class(
        name=context.names.name(line, component_class),
        buses=[context.gdm(node1), context.gdm(node2)],
        phases=gdm_phases(phases, line),
        length=Distance(required_qty(line, "length", "m"), "meter"),
        equipment=equipment,
        in_service=in_service(line),
        **containers(line.EquipmentContainer, context),
    )


def catalog(line: cim.ACLineSegment, code, context: ExportContext):
    """The shared GDM equipment for the line's catalog and normal current limit (shared_equipment)."""
    ampacity = get_current_limits(line, "A").normal
    if ampacity is None:
        raise ValueError(f"{describe(line)}: has no normal current limit; GDM needs the catalog's ampacity")
    if isinstance(code, cim.PerLengthPhaseImpedance):
        equipment_class, values = MatrixImpedanceBranchEquipment, matrix_values(line)
    else:
        equipment_class, values = SequenceImpedanceBranchEquipment, sequence_values(line)
    equipment = equipment_class(name=code.mRID, ampacity=Current(ampacity, "ampere"), **values)
    return shared_equipment(context, code, equipment)


def matrix_values(line: cim.ACLineSegment) -> dict:
    """r, x and c matrices of the line's PerLengthPhaseImpedance, square and symmetric."""
    matrix = get_line_phase_impedance_matrix(line, IMPEDANCE_UNIT, ADMITTANCE_UNIT)
    size = len(matrix.phases)
    if matrix.g is not None and any(matrix.g.values()):
        raise ValueError(f"{describe(line.PerLengthImpedance)}: a shunt conductance g has no GDM home")
    susceptance = square(matrix.b, size) if matrix.b is not None else np.zeros((size, size))
    return {"r_matrix": ResistancePULength(square(matrix.r, size), GDM_IMPEDANCE_UNIT),
            "x_matrix": ReactancePULength(square(matrix.x, size), GDM_IMPEDANCE_UNIT),
            "c_matrix": CapacitancePULength(capacitance(susceptance), GDM_CAPACITANCE_UNIT)}


def sequence_values(line: cim.ACLineSegment) -> dict:
    """Positive and zero sequence values of the line's PerLengthSequenceImpedance."""
    values = get_line_sequence_impedance_per_length(line, IMPEDANCE_UNIT, ADMITTANCE_UNIT)
    code = line.PerLengthImpedance
    unset = [name for name in ("r0", "x0") if getattr(values, name) is None]
    if unset:
        raise ValueError(f"{describe(code)}: {', '.join(unset)} unset; GDM needs the zero sequence")
    if values.g or values.g0:
        raise ValueError(f"{describe(code)}: a shunt conductance gch or g0ch has no GDM home")
    return {
        "pos_seq_resistance": ResistancePULength(values.r, GDM_IMPEDANCE_UNIT),
        "zero_seq_resistance": ResistancePULength(values.r0, GDM_IMPEDANCE_UNIT),
        "pos_seq_reactance": ReactancePULength(values.x, GDM_IMPEDANCE_UNIT),
        "zero_seq_reactance": ReactancePULength(values.x0, GDM_IMPEDANCE_UNIT),
        "pos_seq_capacitance": CapacitancePULength(capacitance(values.b or 0.0), GDM_CAPACITANCE_UNIT),
        "zero_seq_capacitance": CapacitancePULength(capacitance(values.b0 or 0.0), GDM_CAPACITANCE_UNIT),
    }


def square(triangle: dict[tuple[int, int], float], size: int) -> np.ndarray:
    """A lower triangle ``{(row, column): value}`` (1-based, row ≥ column) as the full symmetric matrix."""
    matrix = np.zeros((size, size))
    for (row, column), value in triangle.items():
        matrix[row - 1, column - 1] = matrix[column - 1, row - 1] = value
    return matrix


def capacitance(susceptance):
    """C = b / (2πf): per-length susceptance in S/km → capacitance in F/km (the importer's ``susceptance`` inverse)."""
    return susceptance / (2 * math.pi * FREQUENCY_HZ)
