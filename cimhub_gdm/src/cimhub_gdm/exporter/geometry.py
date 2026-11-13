"""ACLineSegment on a WireConfiguration → GeometryBranch on a GeometryBranchEquipment (``EXPORT_MAPPING.md#lines``,
X3, X4).

Geometry stays geometry: the positions and the wires are written, never an impedance computed from them
(CONDUCTOR_GEOMETRY_ANTI_PATTERNS.md). The positions are the line's (``get_line_conductor_xy``: its spacing raised by
``spacingYOffset``), so one GDM equipment is made per (configuration, positions, conductors). Each conductor is its
WireInfo (``get_wire_info``): an OverheadWireInfo gives a BareConductorEquipment, a ConcentricNeutralCableInfo a
ConcentricCableEquipment, each shared per (wire, values). A tape-shield cable has no GDM class and raises.

GDM rates a geometry line by its conductors, and the importer puts the first conductor's ratings on the line (the
DSS engine's rule). So the first conductor carries the line's own normal and emergency limits where it has them, and
every other conductor its wire's. An unset emergency rating is 1.5 × the normal one, OpenDSS's ``emergamps``.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
import numpy as np
from cimhub_core.getters import describe
from cimhub_core.getters.base_voltage import get_base_voltage
from cimhub_core.getters.current_limits import CurrentLimits, get_current_limits
from cimhub_core.getters.spacing import get_line_conductor_xy
from cimhub_core.getters.wire import get_configuration_wires, get_wire_info
from cimtables.graph_write import get_qty
from gdm.quantities import ResistancePULength
from gdm.systems.distribution.equipment import (
    BareConductorEquipment,
    ConcentricCableEquipment,
    GeometryBranchEquipment,
)
from infrasys.quantities import Current, Distance, Voltage

from cimhub_gdm.exporter.shared import ExportContext, shared_equipment
from cimhub_gdm.exporter.slots import UUID, Slot

LENGTH_UNIT, RESISTANCE_UNIT = "m", "ohm/m"
GDM_RESISTANCE_UNIT = "ohm / meter"
#: OpenDSS's emergamps when only normamps is given.
EMERGENCY_PER_NORMAL = 1.5

_UNSET_RAISES = "; unset raises"
_NORMAL = Slot("rule", "the first conductor: the line's normal limit (get_current_limits), else its wire's; the "
                       "others: the wire's normal limit, else ratedCurrent (get_wire_info); none raises")

SLOTS = {
    GeometryBranchEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the WireConfiguration's name; <configuration>_<n> for its n-th values (X3)"),
        "conductors": Slot("written", "get_configuration_wires, by sequence number: one kind (bare or "
                                      "concentric), a tape-shield cable raises"),
        "horizontal_positions": Slot("written", "get_line_conductor_xy x (m)"),
        "vertical_positions": Slot("written", "get_line_conductor_xy y (m): the spacing raised by the line's "
                                              "spacingYOffset"),
        "insulation": Slot("unset", "untranscribed on import: CIM has no permittivity; GDM's default (air)"),
    },
    BareConductorEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the OverheadWireInfo's name; <wire>_<n> for its n-th values (X3)"),
        "conductor_diameter": Slot("written", f"2 × get_wire_info.radius (m){_UNSET_RAISES}"),
        "conductor_gmr": Slot("written", f"get_wire_info.gmr (m){_UNSET_RAISES}"),
        "ampacity": _NORMAL,
        "ac_resistance": Slot("written", f"get_wire_info.r_ac25 (ohm/m){_UNSET_RAISES}"),
        "emergency_ampacity": Slot("rule", "the first conductor: the line's emergency limit, else its wire's; the "
                                           "others: the wire's; unset is 1.5 × ampacity (OpenDSS's emergamps)"),
        "dc_resistance": Slot("written", f"get_wire_info.r_dc20 (ohm/m){_UNSET_RAISES}"),
    },
    ConcentricCableEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the ConcentricNeutralCableInfo's name; <cable>_<n> for its n-th values (X3)"),
        "strand_diameter": Slot("written", f"2 × neutral_strand_radius (m){_UNSET_RAISES}"),
        "conductor_diameter": Slot("written", f"2 × radius (m){_UNSET_RAISES}"),
        "cable_diameter": Slot("written", f"diameter_over_jacket (m){_UNSET_RAISES}"),
        "insulation_thickness": Slot("written", f"insulation_thickness (m){_UNSET_RAISES}"),
        "insulation_diameter": Slot("written", f"diameter_over_insulation (m){_UNSET_RAISES}"),
        "ampacity": _NORMAL,
        "conductor_gmr": Slot("written", f"gmr (m){_UNSET_RAISES}"),
        "strand_gmr": Slot("written", f"neutral_strand_gmr (m){_UNSET_RAISES}"),
        "phase_ac_resistance": Slot("written", f"r_ac25 (ohm/m){_UNSET_RAISES}"),
        "strand_ac_resistance": Slot("written", f"neutral_strand_r_dc20 (ohm/m), CIM's one strand resistance"
                                                f"{_UNSET_RAISES}"),
        "num_neutral_strands": Slot("written", f"neutral_strand_count{_UNSET_RAISES}"),
        "rated_voltage": Slot("rule", "the cable's ratedVoltage (kV; get_wire_info has none); unset is the line's "
                                      "BaseVoltage, line to line"),
        "insulation": Slot("unset", "untranscribed on import: CIM has no permittivity; GDM's default (PE)"),
    },
}


def geometry_equipment(line: cim.ACLineSegment, phase_count: int, context: ExportContext) -> GeometryBranchEquipment:
    """The line's shared GeometryBranchEquipment: its configuration's wires at the line's positions."""
    configuration = line.WireConfiguration
    wires = dict(get_configuration_wires(configuration))
    positions = get_line_conductor_xy(line, LENGTH_UNIT)
    numbers = [position.sequence_number for position in positions]
    if sorted(wires) != sorted(numbers):
        raise ValueError(f"{describe(configuration)}: wires on sequence numbers {sorted(wires)}, positions on "
                         f"{numbers}")
    if len(numbers) != phase_count:
        raise ValueError(f"{describe(line)}: {phase_count} phases for {len(numbers)} conductors in "
                         f"{describe(configuration)}")
    line_limits = get_current_limits(line, "A")
    conductors = [conductor(wires[number], line, line_limits if index == 0 else None, context)
                  for index, number in enumerate(numbers)]
    if len({type(item) for item in conductors}) > 1:
        raise ValueError(f"{describe(configuration)}: mixes bare wires and cables; GDM's conductors are one kind")
    equipment = GeometryBranchEquipment(
        name=configuration.mRID,
        conductors=conductors,
        horizontal_positions=Distance(np.array([position.x for position in positions]), "meter"),
        vertical_positions=Distance(np.array([position.y for position in positions]), "meter"),
    )
    return shared_equipment(context, configuration, equipment)


def conductor(wire: cim.WireInfo, line: cim.ACLineSegment, line_limits: CurrentLimits | None,
              context: ExportContext):
    """The wire as GDM equipment, rated by ``line_limits`` where given (the first conductor) and set."""
    values = get_wire_info(wire, LENGTH_UNIT, RESISTANCE_UNIT, "A")
    if values.kind is cim.TapeShieldCableInfo:
        raise ValueError(f"{describe(wire)}: GDM has no tape-shield cable")
    if values.kind is cim.CableInfo:
        raise ValueError(f"{describe(wire)}: GDM has no unshielded cable")
    normal, emergency = ratings(wire, values, line_limits)
    common = {"conductor_diameter": _distance(2 * _required(values.radius, "radius", wire)),
              "conductor_gmr": _distance(_required(values.gmr, "gmr", wire)),
              "ampacity": Current(normal, "ampere")}
    phase_resistance = _resistance(_required(values.r_ac25, "rAC25", wire))
    if values.kind is cim.OverheadWireInfo:
        equipment = BareConductorEquipment(name=wire.mRID, ac_resistance=phase_resistance,
                                           dc_resistance=_resistance(_required(values.r_dc20, "rDC20", wire)),
                                           emergency_ampacity=Current(emergency, "ampere"), **common)
    else:
        cable = values.cable
        equipment = ConcentricCableEquipment(
            name=wire.mRID,
            strand_diameter=_distance(2 * _required(cable.neutral_strand_radius, "neutralStrandRadius", wire)),
            cable_diameter=_distance(_required(cable.diameter_over_jacket, "diameterOverJacket", wire)),
            insulation_thickness=_distance(_required(cable.insulation_thickness, "insulationThickness", wire)),
            insulation_diameter=_distance(_required(cable.diameter_over_insulation, "diameterOverInsulation", wire)),
            strand_gmr=_distance(_required(cable.neutral_strand_gmr, "neutralStrandGmr", wire)),
            phase_ac_resistance=phase_resistance,
            strand_ac_resistance=_resistance(_required(cable.neutral_strand_r_dc20, "neutralStrandRDC20", wire)),
            num_neutral_strands=_required(cable.neutral_strand_count, "neutralStrandCount", wire),
            rated_voltage=Voltage(cable_voltage(wire, line), "kilovolt"),
            **common,
        )
    return shared_equipment(context, wire, equipment)


def ratings(wire: cim.WireInfo, values, line_limits: CurrentLimits | None) -> tuple[float, float]:
    """(normal, emergency) in A: the line's where given and set, else the wire's; an unset emergency is 1.5 × normal."""
    normal = values.limits.normal if values.limits.normal is not None else values.rated_current
    emergency = values.limits.emergency
    if line_limits is not None:
        normal = line_limits.normal if line_limits.normal is not None else normal
        emergency = line_limits.emergency if line_limits.emergency is not None else emergency
    if normal is None:
        raise ValueError(f"{describe(wire)}: has no rating (ratedCurrent or a normal limit), nor has its line; GDM "
                         "needs the conductor's ampacity")
    return normal, EMERGENCY_PER_NORMAL * normal if emergency is None else emergency


def cable_voltage(cable: cim.WireInfo, line: cim.ACLineSegment) -> float:
    """The cable's ratedVoltage in kV; unset, the line's BaseVoltage (line to line)."""
    rated = get_qty(cable, "ratedVoltage", "kV")
    return get_base_voltage(line, "kV", form="LL") if rated is None else rated


def _required(value, attribute: str, wire: cim.WireInfo):
    if value is None:
        raise ValueError(f"{describe(wire)}: {attribute} is unset; GDM requires it")
    return value


def _distance(meters: float) -> Distance:
    return Distance(meters, "meter")


def _resistance(ohms_per_meter: float) -> ResistancePULength:
    return ResistancePULength(ohms_per_meter, GDM_RESISTANCE_UNIT)

