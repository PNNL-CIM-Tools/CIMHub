"""Lines → ACLineSegment, and their catalogs (GDM_MAPPING.md §15).

- ``MatrixImpedanceBranchEquipment`` → PerLengthPhaseImpedance ``lc_`` + PhaseImpedanceData (lower triangle).
- ``SequenceImpedanceBranchEquipment`` → PerLengthSequenceImpedance ``lc_``.
- Both are named catalogs shared by lines, so both are templates (DSS-14): the impedance has ``isTemplate=true`` and
  is held by a WireConfiguration ``<lc>_wc`` (the catalog's name, no WireSpacing). Its lines name that
  WireConfiguration and set no ``ACLineSegment.PerLengthImpedance`` of their own.
- ``GeometryBranchEquipment`` → XYSpacing ``spc_`` + WireConfiguration ``wc_``, over the wire and cable catalogs
  (OverheadWireInfo ``wire_``, ConcentricNeutralCableInfo ``cn_``). Geometry is never replaced by an impedance matrix
  (CONDUCTOR_GEOMETRY_ANTI_PATTERNS.md).

A line keeps its phases, balanced ABC included: its ACLineSegmentPhases are the conductor order (the DSS wave's
S4b-9 rule). Ratings go on the line's own OperationalLimitSet, as the DSS wave writes them.
"""

from __future__ import annotations

import numpy as np
from cimbuilder.object_builder import (
    ACLineSegmentBuilder,
    ConcentricNeutralCableInfoBuilder,
    OperationalLimitSetBuilder,
    OverheadWireInfoBuilder,
    PerLengthPhaseImpedanceBuilder,
    PerLengthSequenceImpedanceBuilder,
    WireConfigurationBuilder,
    XYSpacingBuilder,
)
from cimhub_core.cimtbl import Field
from cimtables.units import Qty
from gdm.systems.distribution.equipment import BareConductorEquipment, GeometryBranchEquipment, MatrixImpedanceBranchEquipment

from cimhub_gdm.importer.shared import (
    FREQUENCY_HZ,
    UUID_FIELD,
    Naming,
    bus_base_voltage,
    bus_mrid,
    container_mrid,
    name_field,
    object_mrid,
    phases_text,
    qty,
    require_in_service,
    susceptance,
)

PREFIX = "ln_"
IMPEDANCE_PREFIX = "lc_"
WIRE_PREFIX = "wire_"
CABLE_PREFIX = "cn_"
SPACING_PREFIX = "spc_"
CONFIGURATION_PREFIX = "wc_"

#: The two OperationalLimitTypes every line limit names, created the first time a line needs them.
LIMIT_TYPES = {
    "olt_normal": {"name": "normal", "isInfiniteDuration": True, "direction": "absoluteValue"},
    "olt_emergency": {"name": "emergency", "isInfiniteDuration": False, "direction": "absoluteValue"},
}

_NO_CATALOG_HOME = "no home on PerLengthImpedance"

_LINE_FIELDS = {
    "uuid": UUID_FIELD,
    "name": name_field(PREFIX),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "buses": Field("structural", note="node1, node2; BaseVoltage from bus 1 (GDM requires equal bus voltages)"),
    "length": Field("copied", (("add_connectivity", "length", None),)),
    "phases": Field("structural", note="ACLineSegmentPhase per conductor, in conductor order, balanced ABC included"),
}
FIELDS_MatrixImpedanceBranch = _LINE_FIELDS | {
    "equipment": Field("structural", note="WireConfiguration <lc>_wc (the template); its ampacity → the line's "
                                          "normal CurrentLimit"),
}
FIELDS_SequenceImpedanceBranch = dict(FIELDS_MatrixImpedanceBranch)
FIELDS_GeometryBranch = _LINE_FIELDS | {
    "equipment": Field("structural", note="WireConfiguration; the first conductor's ampacity and "
                                          "emergency_ampacity → the line's CurrentLimits (the DSS engine's rule)"),
}

FIELDS_MatrixImpedanceBranchEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(IMPEDANCE_PREFIX),
    "construction": Field("untranscribed", note=_NO_CATALOG_HOME),
    "r_matrix": Field("structural", note="PhaseImpedanceData r, lower triangle (row ≥ column); asymmetric raises"),
    "x_matrix": Field("structural", note="PhaseImpedanceData x, lower triangle; asymmetric raises"),
    "c_matrix": Field("derived", note="PhaseImpedanceData b = 2πf·C (susceptance), lower triangle; asymmetric raises"),
    "ampacity": Field("structural", note="the normal CurrentLimit of every line using it"),
}
FIELDS_SequenceImpedanceBranchEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(IMPEDANCE_PREFIX),
    "pos_seq_resistance": Field("copied", (("add_electrical", "r", None),)),
    "zero_seq_resistance": Field("copied", (("add_short_circuit", "r0", None),)),
    "pos_seq_reactance": Field("copied", (("add_electrical", "x", None),)),
    "zero_seq_reactance": Field("copied", (("add_short_circuit", "x0", None),)),
    "pos_seq_capacitance": Field("derived", note="bch = 2πf·C1 (susceptance)"),
    "zero_seq_capacitance": Field("derived", note="b0ch = 2πf·C0 (susceptance)"),
    "ampacity": Field("structural", note="the normal CurrentLimit of every line using it"),
}
FIELDS_GeometryBranchEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(f"{SPACING_PREFIX} / {CONFIGURATION_PREFIX}"),
    "conductors": Field("structural", note="WireSequenceConfiguration <wc>_<n> → the wire or cable info, in order"),
    "horizontal_positions": Field("copied", (("add_wire_position_row", "xCoord", None),),
                                  note="XYConductorPosition <spc>_<n>"),
    "vertical_positions": Field("copied", (("add_wire_position_row", "yCoord", None),)),
    "insulation": Field("untranscribed", note="a permittivity; CIM has no permittivity, and no builder keyword sets "
                                              "an insulation material"),
}
FIELDS_BareConductorEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(WIRE_PREFIX),
    "conductor_diameter": Field("derived", note="radius = diameter / 2"),
    "conductor_gmr": Field("copied", (("add_asset_info", "gmr", None),)),
    "ampacity": Field("copied", (("add_asset_info", "ratedCurrent", None),),
                      note="also a geometry line's normal CurrentLimit"),
    "ac_resistance": Field("copied", (("add_asset_info", "rAC25", None),), note="no temperature given; rAC25 as DSS"),
    "emergency_ampacity": Field("structural", note="a geometry line's emergency CurrentLimit; the wire info's own "
                                                   "limit set has no builder (finding)"),
    "dc_resistance": Field("copied", (("add_asset_info", "rDC20", None),)),
}
FIELDS_ConcentricCableEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(CABLE_PREFIX),
    "strand_diameter": Field("derived", note="neutralStrandRadius = diameter / 2"),
    "conductor_diameter": Field("derived", note="radius = diameter / 2"),
    "cable_diameter": Field("copied", (("add_asset_info", "diameterOverJacket", None),)),
    "insulation_thickness": Field("copied", (("add_asset_info", "insulationThickness", None),)),
    "insulation_diameter": Field("copied", (("add_asset_info", "diameterOverInsulation", None),)),
    "ampacity": Field("copied", (("add_asset_info", "ratedCurrent", None),),
                      note="also a geometry line's normal CurrentLimit"),
    "conductor_gmr": Field("copied", (("add_asset_info", "gmr", None),)),
    "strand_gmr": Field("copied", (("add_asset_info", "neutralStrandGmr", None),)),
    "phase_ac_resistance": Field("copied", (("add_asset_info", "rAC25", None),), note="rAC25 as DSS"),
    "strand_ac_resistance": Field("copied", (("add_asset_info", "neutralStrandRDC20", None),),
                                  note="CIM's only strand resistance, as DSS"),
    "num_neutral_strands": Field("copied", (("add_asset_info", "neutralStrandCount", None),)),
    "rated_voltage": Field("copied", (("add_asset_info", "ratedVoltage", None),)),
    "insulation": Field("untranscribed", note="a permittivity; no builder keyword sets an insulation material"),
}


def radius(diameter):
    """Half a diameter, in its own unit."""
    return diameter / 2


def add_matrix_impedance(network, equipment, naming: Naming) -> None:
    """A PerLengthPhaseImpedance with one PhaseImpedanceData per lower-triangle element (row ≥ column, 1-based)."""
    size = _check_matrices(equipment)
    builder = PerLengthPhaseImpedanceBuilder(network, network.container)
    impedance = builder.create(mRID=impedance_mrid(equipment, naming), name=equipment.name)
    builder.add_electrical(impedance, conductorCount=size, isTemplate=True,
                           calculatedFrequency=Qty(FREQUENCY_HZ, "Hz"))
    for row in range(size):
        for column in range(row + 1):
            builder.add_phase_impedance_data_row(
                impedance, row=row + 1, column=column + 1,
                r=qty(equipment.r_matrix[row, column]),
                x=qty(equipment.x_matrix[row, column]),
                b=susceptance(equipment.c_matrix[row, column]),
            )
    add_template_configuration(network, equipment, naming)


def add_sequence_impedance(network, equipment, naming: Naming) -> None:
    """A PerLengthSequenceImpedance: r, x, r0, x0 as written; bch, b0ch from the capacitances."""
    builder = PerLengthSequenceImpedanceBuilder(network, network.container)
    impedance = builder.create(mRID=impedance_mrid(equipment, naming), name=equipment.name)
    builder.add_electrical(impedance, r=qty(equipment.pos_seq_resistance), x=qty(equipment.pos_seq_reactance),
                           bch=susceptance(equipment.pos_seq_capacitance), isTemplate=True,
                           calculatedFrequency=Qty(FREQUENCY_HZ, "Hz"))
    builder.add_short_circuit(impedance, r0=qty(equipment.zero_seq_resistance),
                              x0=qty(equipment.zero_seq_reactance), b0ch=susceptance(equipment.zero_seq_capacitance))
    add_template_configuration(network, equipment, naming)


def add_template_configuration(network, equipment, naming: Naming) -> None:
    """The WireConfiguration ``<lc>_wc`` a catalog's lines name: its PerLengthImpedance, no WireSpacing (DSS-14)."""
    builder = WireConfigurationBuilder(network, network.container)
    configuration = builder.create(mRID=template_mrid(equipment, naming), name=equipment.name)
    builder.add_electrical(configuration, PerLengthImpedance=impedance_mrid(equipment, naming))


def add_wire(network, conductor, naming: Naming) -> None:
    """An OverheadWireInfo."""
    builder = OverheadWireInfoBuilder(network, network.container)
    wire = builder.create(mRID=wire_info_mrid(conductor, naming), name=conductor.name)
    builder.add_asset_info(wire, gmr=qty(conductor.conductor_gmr), radius=qty(radius(conductor.conductor_diameter)),
                           rAC25=qty(conductor.ac_resistance), rDC20=qty(conductor.dc_resistance),
                           ratedCurrent=qty(conductor.ampacity))


def add_cable(network, cable, naming: Naming) -> None:
    """A ConcentricNeutralCableInfo."""
    builder = ConcentricNeutralCableInfoBuilder(network, network.container)
    info = builder.create(mRID=wire_info_mrid(cable, naming), name=cable.name)
    builder.add_asset_info(
        info,
        gmr=qty(cable.conductor_gmr),
        radius=qty(radius(cable.conductor_diameter)),
        rAC25=qty(cable.phase_ac_resistance),
        ratedCurrent=qty(cable.ampacity),
        ratedVoltage=qty(cable.rated_voltage),
        insulationThickness=qty(cable.insulation_thickness),
        diameterOverInsulation=qty(cable.insulation_diameter),
        diameterOverJacket=qty(cable.cable_diameter),
        neutralStrandCount=cable.num_neutral_strands,
        neutralStrandRadius=qty(radius(cable.strand_diameter)),
        neutralStrandGmr=qty(cable.strand_gmr),
        neutralStrandRDC20=qty(cable.strand_ac_resistance),
    )


def add_geometry(network, geometry, naming: Naming) -> None:
    """An XYSpacing template with a position per conductor, and a WireConfiguration naming each conductor's wire."""
    spacing_builder = XYSpacingBuilder(network, network.container)
    spacing = spacing_builder.create(mRID=object_mrid(SPACING_PREFIX, geometry, "XYSpacing", naming),
                                     name=geometry.name, isTemplate=True)
    for index in range(len(geometry.conductors)):
        spacing_builder.add_wire_position_row(spacing, sequenceNumber=index + 1,
                                              xCoord=qty(geometry.horizontal_positions[index]),
                                              yCoord=qty(geometry.vertical_positions[index]))
    configuration_builder = WireConfigurationBuilder(network, network.container)
    configuration = configuration_builder.create(mRID=configuration_mrid(geometry, naming), name=geometry.name,
                                                 WireSpacing=spacing.mRID)
    for index, conductor in enumerate(geometry.conductors):
        configuration_builder.add_wire_sequence_configuration(configuration, sequenceNumber=index + 1,
                                                              WireInfo=wire_info_mrid(conductor, naming))


def add_line(network, line, naming: Naming) -> None:
    """An ACLineSegment between the line's two buses, on its catalog, with its ratings."""
    require_in_service(line)
    if len(line.buses) != 2:
        raise ValueError(f"{type(line).__name__} {line.name!r}: {len(line.buses)} buses, expected 2")
    equipment = line.equipment
    # GDM checks a matrix catalog's size against the phases itself, but not a geometry's conductor count
    if isinstance(equipment, GeometryBranchEquipment) and len(equipment.conductors) != len(line.phases):
        raise ValueError(f"{type(line).__name__} {line.name!r}: {len(line.phases)} phases for "
                         f"{len(equipment.conductors)} conductors in {equipment.name!r}")
    bus1, bus2 = line.buses

    builder = ACLineSegmentBuilder(network, network.container)
    segment = builder.create(mRID=object_mrid(PREFIX, line, "ACLineSegment", naming), name=line.name)
    builder.add_connectivity(segment, node1=bus_mrid(bus1, naming), node2=bus_mrid(bus2, naming),
                             phases=phases_text(line.phases), length=qty(line.length),
                             EquipmentContainer=container_mrid(line, naming), BaseVoltage=bus_base_voltage(bus1))
    if isinstance(equipment, GeometryBranchEquipment):
        builder.add_wire_configuration(segment, WireConfiguration=configuration_mrid(equipment, naming))
        first = equipment.conductors[0]
        emergency = first.emergency_ampacity if isinstance(first, BareConductorEquipment) else None
        add_line_limits(network, segment.mRID, normal=first.ampacity, emergency=emergency)
    else:
        builder.add_wire_configuration(segment, WireConfiguration=template_mrid(equipment, naming))
        add_line_limits(network, segment.mRID, normal=equipment.ampacity, emergency=None)


def add_line_limits(network, segment: str, *, normal, emergency) -> None:
    """``<ln>_limits`` with a normal CurrentLimit ``<ln>_norm`` and, when given, an emergency one ``<ln>_emerg``."""
    builder = OperationalLimitSetBuilder(network, network.container)
    limit_set = builder.create(mRID=f"{segment}_limits")
    builder.add_equipment(limit_set, Equipment=segment)
    builder.add_current_limit(limit_set, mRID=f"{segment}_norm", normalValue=qty(normal),
                              OperationalLimitType=limit_type(network, "olt_normal"))
    if emergency is not None:
        builder.add_current_limit(limit_set, mRID=f"{segment}_emerg", normalValue=qty(emergency),
                                  OperationalLimitType=limit_type(network, "olt_emergency"))


def limit_type(network, type_mrid: str) -> str:
    """The OperationalLimitType ``type_mrid``, created the first time it is named."""
    if network.find_by_mRID(type_mrid) is None:
        OperationalLimitSetBuilder(network, network.container).add_limit_type(mRID=type_mrid,
                                                                              **LIMIT_TYPES[type_mrid])
    return type_mrid


def impedance_mrid(equipment, naming: Naming) -> str:
    cim_class = ("PerLengthPhaseImpedance" if isinstance(equipment, MatrixImpedanceBranchEquipment)
                 else "PerLengthSequenceImpedance")
    return object_mrid(IMPEDANCE_PREFIX, equipment, cim_class, naming)


def template_mrid(equipment, naming: Naming) -> str:
    return f"{impedance_mrid(equipment, naming)}_wc"


def configuration_mrid(geometry, naming: Naming) -> str:
    return object_mrid(CONFIGURATION_PREFIX, geometry, "WireConfiguration", naming)


def wire_info_mrid(conductor, naming: Naming) -> str:
    if isinstance(conductor, BareConductorEquipment):
        return object_mrid(WIRE_PREFIX, conductor, "OverheadWireInfo", naming)
    return object_mrid(CABLE_PREFIX, conductor, "ConcentricNeutralCableInfo", naming)


def _check_matrices(equipment) -> int:
    """The conductor count of a matrix catalog; raises unless r, x and c are square, the same size and symmetric."""
    size = None
    for slot in ("r_matrix", "x_matrix", "c_matrix"):
        matrix = np.asarray(getattr(equipment, slot).magnitude)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or (size is not None and matrix.shape[0] != size):
            raise ValueError(f"MatrixImpedanceBranchEquipment {equipment.name!r}: {slot} is {matrix.shape}, expected "
                             "square and the size of the other matrices")
        if not np.allclose(matrix, matrix.T, rtol=1e-9, atol=0.0):
            raise ValueError(f"MatrixImpedanceBranchEquipment {equipment.name!r}: {slot} is not symmetric; CIM "
                             "holds the lower triangle only")
        size = matrix.shape[0]
    return size

