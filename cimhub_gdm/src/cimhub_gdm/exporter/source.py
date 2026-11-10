"""EnergySource → DistributionVoltageSource (``EXPORT_MAPPING.md#source``).

GDM holds a source per phase; CIM holds one voltage, angle and impedance for all of them. Every phase gets the same
values, and the angles step by -120 degrees from the source's angle (positive sequence).
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters import describe
from cimhub_core.getters.source import get_source
from cimhub_core.getters.terminals import get_terminal_nodes
from gdm.quantities import Angle, Reactance, Resistance, Voltage
from gdm.systems.distribution.components import DistributionVoltageSource
from gdm.systems.distribution.enums import VoltageTypes
from gdm.systems.distribution.equipment import PhaseVoltageSourceEquipment, VoltageSourceEquipment

from cimhub_gdm.exporter.shared import ExportContext, containers, gdm_phases, in_service
from cimhub_gdm.exporter.slots import UUID, Slot

CIM_CLASSES = (cim.EnergySource,)

_INLINE_NAME = Slot("written", "the source's name (X2)")

SLOTS = {
    DistributionVoltageSource: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
        "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
        "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
        "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
        "bus": Slot("written", "the bus of get_terminal_nodes"),
        "phases": Slot("written", "get_source.phases"),
        "equipment": Slot("written", "a VoltageSourceEquipment made for this source"),
    },
    VoltageSourceEquipment: {
        "uuid": UUID,
        "name": _INLINE_NAME,
        "sources": Slot("written", "one PhaseVoltageSourceEquipment per phase, all with the source's values"),
    },
    PhaseVoltageSourceEquipment: {
        "uuid": UUID,
        "name": Slot("written", "<source>_<phase> (X2)"),
        "r0": Slot("written", "get_source.impedance.r0 (ohm); unset raises"),
        "r1": Slot("written", "get_source.impedance.r (ohm); unset raises"),
        "x0": Slot("written", "get_source.impedance.x0 (ohm); unset raises"),
        "x1": Slot("written", "get_source.impedance.x (ohm); unset raises"),
        "voltage": Slot("written", "get_source.magnitude (kV, line to line)"),
        "voltage_type": Slot("rule", "always line-to-line: voltageMagnitude is line to line (X6)"),
        "angle": Slot("rule", "get_source.angle - 120 deg x the phase's position, wrapped to [-180, 180); an unset "
                              "angle is 0, the reference"),
    },
}

_REL_TOL = 1e-6


def export(source: cim.EnergySource, context: ExportContext) -> DistributionVoltageSource:
    values = get_source(source, angle_unit="deg", voltage_unit="kV", impedance_unit="ohm")
    impedance = values.impedance
    unset = [name for name in ("r", "x", "r0", "x0") if getattr(impedance, name) is None]
    if unset:
        raise ValueError(f"{describe(source)}: {', '.join(unset)} unset; GDM needs r1 x1 r0 x0 on every phase")
    for negative, positive in (("r2", "r"), ("x2", "x")):
        value = getattr(impedance, negative)
        if value is not None and not math.isclose(value, getattr(impedance, positive), rel_tol=_REL_TOL):
            raise ValueError(f"{describe(source)}: {negative} differs from {positive}; GDM has no negative sequence")
    [node] = get_terminal_nodes(source)
    names = context.names
    phases = gdm_phases(values.phases, source)
    angle = 0.0 if values.angle is None else values.angle  # unset: the reference angle
    phase_sources = [
        PhaseVoltageSourceEquipment(
            **names.part(source, PhaseVoltageSourceEquipment, suffix=f"_{phase.value}"),
            r0=Resistance(impedance.r0, "ohm"), r1=Resistance(impedance.r, "ohm"),
            x0=Reactance(impedance.x0, "ohm"), x1=Reactance(impedance.x, "ohm"),
            voltage=Voltage(values.magnitude, "kilovolt"), voltage_type=VoltageTypes.LINE_TO_LINE,
            angle=Angle(phase_angle(angle, position), "degree"))
        for position, phase in enumerate(phases)
    ]
    return DistributionVoltageSource(
        **names.own(source),
        bus=context.gdm(node),
        phases=phases,
        equipment=VoltageSourceEquipment(**names.part(source, VoltageSourceEquipment), sources=phase_sources),
        in_service=in_service(source),
        **containers(source.EquipmentContainer, context),
    )


def phase_angle(angle: float, position: int) -> float:
    """The angle of the phase at ``position`` (0 for the first): -120 degrees per position, in [-180, 180)."""
    return (angle - 120.0 * position + 180.0) % 360.0 - 180.0
