"""VoltageRegulator → DistributionRegulator with its RegulatorController (``EXPORT_MAPPING.md#regulators``, X3, X8).

One GDM regulator per CIM VoltageRegulator, the single-phase unit as wired. ditto 0.1.8 writes a GDM regulator as one
OpenDSS Transformer, whose RegControls then gang its phases, so a bank exported as one 3-phase regulator would lose
its units' own taps. The regulator's two AutoTransformerEnds are its windings (``get_transformer_model``, form AUTO).
The tap is the instance's, as a controller's state: the equipment keeps nominal taps, so the units of one bank share
it. The equipment is the tap changer's TapChangerInfo when it has one (shared, B17), else the regulator's own.

The controller is the importer's inverse: the PT-secondary settings are the primary targets / ptRatio, and line drop
R and X in volts are ohms × ctRating / ptRatio.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters import describe
from cimhub_core.getters.control import get_tap_changer_control
from cimhub_core.getters.tap_changer import get_tap_ratio, get_tap_steps
from cimhub_core.getters.transformer import get_transformer_model
from gdm.quantities import ApparentPower
from gdm.systems.distribution.common import SequencePair
from gdm.systems.distribution.components import DistributionRegulator
from gdm.systems.distribution.controllers import RegulatorController
from gdm.systems.distribution.enums import ConnectionType
from gdm.systems.distribution.equipment import DistributionTransformerEquipment, WindingEquipment
from infrasys.quantities import Current, Time, Voltage

from cimhub_gdm.exporter import fills
from cimhub_gdm.exporter.shared import ExportContext, containers, gdm_phases, in_service, shared_equipment
from cimhub_gdm.exporter.slots import UUID, Slot
from cimhub_gdm.exporter.transformer import (
    POWER_UNIT,
    VOLTAGE_UNIT,
    coil_voltage,
    end_node,
    tap_range,
    tap_ratio,
    winding_phases,
    winding_power,
)

CIM_CLASSES = (cim.VoltageRegulator,)

NEUTRAL = cim.SinglePhaseKind.N

SLOTS = {
    DistributionRegulator: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2): one per VoltageRegulator unit"),
        "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
        "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
        "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
        "buses": Slot("written", "each AutoTransformerEnd's ConnectivityNode, end 1 (S) first"),
        "winding_phases": Slot("rule", "each end's phase conductor, without the N its coil returns to (as a "
                                       "transformer's 1-phase wye coil)"),
        "tap_positions": Slot("rule", "get_tap_ratio(which='actual') on the tapped winding, 1.0 on the other"),
        "equipment": Slot("written", "the DistributionTransformerEquipment of the tap changer's TapChangerInfo "
                                     "(shared, X3), else the regulator's own"),
        "controllers": Slot("written", "one RegulatorController from get_tap_changer_control; GDM requires one per "
                                       "phase, so no control or a disabled one (enabled or controlEnabled false) "
                                       "raises"),
    },
    RegulatorController: {
        "uuid": UUID,
        "name": Slot("written", "the regulator's name (X2)"),
        "tapped_winding": Slot("written", "the endNumber of the end the RatioTapChanger is on"),
        "delay": Slot("written", "initialDelay (s); unset is None"),
        "v_setpoint": Slot("rule", "targetValue / pt_ratio (V)"),
        "min_v_limit": Slot("rule", "minLimitVoltage / pt_ratio (V); unset (GDM needs > 0) is v_setpoint × "
                                    "min_tap_pu, the tap range's reach, so it never acts first"),
        "max_v_limit": Slot("rule", "maxLimitVoltage / pt_ratio (V); unset is v_setpoint × max_tap_pu"),
        "pt_ratio": Slot("rule", "ptRatio (tap changer and control agreed); unset is 1, the targets as stored"),
        "use_ldc": Slot("rule", "lineDropCompensation; unset is False"),
        "is_reversible": Slot("rule", "reversible; unset is False"),
        "ldc_R": Slot("rule", "lineDropR × ctRating / pt_ratio (V); unset is 0 V (ditto 0.1.8 needs a value)"),
        "ldc_X": Slot("rule", "lineDropX × ctRating / pt_ratio (V); unset is 0 V (ditto 0.1.8 needs a value)"),
        "ct_primary": Slot("written", "ctRating (A); unset is None"),
        "max_step": Slot("fill", "highStep − lowStep: no limit per iteration (§3.1)"),
        "bandwidth": Slot("rule", "targetDeadband / pt_ratio (V); unset is 0"),
        "controlled_bus": Slot("written", "the bus of the monitored Terminal"),
        "controlled_phase": Slot("rule", "monitoredPhase; unset is the regulator's phase"),
    },
}


class Impedance(NamedTuple):
    r: float  # percent on winding 1's ratedS: both windings' together
    x: float


def export(regulator: cim.VoltageRegulator, context: ExportContext) -> DistributionRegulator:
    model = get_transformer_model(regulator, voltage_unit=VOLTAGE_UNIT, power_unit=POWER_UNIT)
    phases = [phase for phase in model.windings[0].phases if phase is not NEUTRAL]
    if len(model.windings) != 2 or len(phases) != 1:
        raise ValueError(f"no GDM export yet for a VoltageRegulator but a single-phase unit of two ends: "
                         f"{describe(regulator)} has {len(model.windings)} ends on {[p.value for p in phases]}")
    tapped = [winding for winding in model.windings if winding.end.RatioTapChanger is not None]
    if len(tapped) != 1:
        raise ValueError(f"{describe(regulator)}: {len(tapped)} RatioTapChangers; a regulator has one")
    tap = tapped[0].end.RatioTapChanger
    impedance = regulator_impedance(model, context)
    windings = [
        WindingEquipment(resistance=impedance.r / 2, is_grounded=bool(winding.grounded),
                         connection_type=ConnectionType.STAR,
                         rated_power=ApparentPower(winding_power(winding, False), "kilova"), num_phases=1,
                         tap_positions=[1.0], **coil_voltage(winding, ConnectionType.STAR), **tap_range(winding.end))
        for winding in model.windings
    ]
    equipment = DistributionTransformerEquipment(
        name=regulator.mRID, pct_no_load_loss=0.0, pct_full_load_loss=impedance.r, windings=windings,
        coupling_sequences=[SequencePair(from_index=0, to_index=1)], winding_reactances=[impedance.x],
        is_center_tapped=False)
    return DistributionRegulator(
        **context.names.own(regulator),
        buses=[context.gdm(end_node(winding.end)) for winding in model.windings],
        winding_phases=[winding_phases(winding, part) for winding, part in zip(model.windings, windings)],
        tap_positions=[[tap_ratio(winding.end)] for winding in model.windings],
        equipment=regulator_equipment(regulator, tap, equipment, context),
        controllers=[controller(regulator, tap, tapped[0].number, phases[0], context)],
        in_service=in_service(regulator),
        **containers(regulator.EquipmentContainer, context),
    )


def regulator_impedance(model, context: ExportContext) -> Impedance:
    """The mesh between the two ends (DSS-origin, the engine's stand-in impedance); without one, the fill."""
    mesh = model.mesh.get((1, 2))
    if mesh is None:
        return Impedance(context.fill("WindingEquipment.resistance (regulator)", fills.REGULATOR_RESISTANCE),
                         context.fill("DistributionTransformerEquipment.winding_reactances (regulator)",
                                      fills.REGULATOR_REACTANCE))
    return Impedance(0.0 if mesh.r is None else mesh.r, mesh.x)


def regulator_equipment(regulator, tap: cim.RatioTapChanger, equipment, context: ExportContext):
    """Shared through the tap changer's TapChangerInfo when it has one (B17), else the regulator's own."""
    info = tap.AssetDatasheet
    if isinstance(info, cim.TapChangerInfo):
        return shared_equipment(context, info, equipment)
    return equipment.model_copy(update=context.names.part(regulator, DistributionTransformerEquipment))


def controller(regulator, tap: cim.RatioTapChanger, tapped_winding: int, phase: cim.SinglePhaseKind,
               context: ExportContext) -> RegulatorController:
    """The regulator's one controller. GDM requires one per phase, so no control, or a disabled one, raises."""
    settings = get_tap_changer_control(tap, unit="V", time_unit="s", voltage_unit="V")
    control = settings.control
    if control is None or settings.control_enabled is False or control.enabled is False:
        raise ValueError(f"{describe(regulator)}: no enabled TapChangerControl; a GDM regulator needs a controller "
                         "per phase")
    if control.mode is not cim.RegulatingControlModeKind.voltage:
        raise ValueError(f"{describe(regulator)}: a {control.mode.value} tap changer control; GDM regulates voltage")
    pt_ratio = 1.0 if control.pt_ratio is None else control.pt_ratio  # unset: the targets as stored
    ct_rating = settings.ct_rating

    def secondary(volts: float | None) -> Voltage:
        return Voltage((volts or 0.0) / pt_ratio, "volt")

    def limit(volts: float | None, reach: str) -> Voltage:
        """A limit as set; unset, the setpoint moved by the whole tap range (GDM needs one above 0 V)."""
        if volts is not None:
            return secondary(volts)
        return secondary(control.target * get_tap_ratio(tap, which=reach))

    def line_drop(ohms: float | None) -> Voltage:
        if not ohms:
            return Voltage(0.0, "volt")
        if ct_rating is None:
            raise ValueError(f"{describe(tap)}: line drop compensation without a ctRating")
        return Voltage(ohms * ct_rating / pt_ratio, "volt")

    steps = get_tap_steps(tap)
    return RegulatorController(
        **context.names.part(regulator, RegulatorController),
        tapped_winding=tapped_winding,
        delay=None if settings.initial_delay is None else Time(settings.initial_delay, "second"),
        v_setpoint=secondary(control.target),
        bandwidth=secondary(control.deadband),
        min_v_limit=limit(settings.min_limit_u, "low"),
        max_v_limit=limit(settings.max_limit_u, "high"),
        pt_ratio=pt_ratio,
        use_ldc=bool(settings.line_drop_compensation),
        is_reversible=bool(settings.reversible),
        ldc_R=line_drop(settings.line_drop.r),
        ldc_X=line_drop(settings.line_drop.x),
        ct_primary=None if ct_rating is None else Current(ct_rating, "ampere"),
        max_step=context.fill("RegulatorController.max_step", steps.high - steps.low),
        controlled_bus=context.gdm(control.terminal.ConnectivityNode),
        controlled_phase=gdm_phases([controlled_phase(control, phase, regulator)], regulator)[0],
    )


def controlled_phase(control, phase: cim.SinglePhaseKind, regulator) -> cim.SinglePhaseKind:
    """``monitoredPhase``'s one phase conductor; unset, the regulator's phase."""
    if control.monitored_phases is None:
        return phase
    monitored = [p for p in control.monitored_phases if p is not NEUTRAL]
    if len(monitored) != 1:
        raise ValueError(f"{describe(regulator)}: its control monitors {[p.value for p in monitored]}; GDM's "
                         "controlled_phase is one phase")
    return monitored[0]
