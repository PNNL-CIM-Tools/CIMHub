"""DistributionRegulator → VoltageRegulator per phase, with its tap changer and control (GDM_MAPPING.md §19).

Each regulated phase is one single-phase step-voltage regulator, as CIMTBL-Models ``regulator_example.cimtbl`` writes
it (OPEN_DECISIONS 7, DSS-13): a VoltageRegulator ``vr_<name>[_<phase>]``, named ``<name>[_<phase>]``, with two
AutoTransformerEnds (end 1 the S side on bus 1, end 2 the L side on bus 2), lugs S, L, SL and one series winding S→SL
tapped at L. The RatioTapChanger ``<vr>_tap`` sits on the AutoTransformerEnd of the controller's ``tapped_winding``;
its TapChangerControl ``<vr>_ctrl`` (GDM has one controller per phase) regulates the end on the controlled bus. A
regulator coil is single-phase, so its ends are ``<phase>N``; the builder's AutoTransformerEnd has no ``grounded``
keyword, so a winding's ``is_grounded`` is untranscribed for regulators (B27). The regulator's catalog data is a
TapChangerInfo ``tci_<equipment>`` (B17), each tap changer's AssetDatasheet. cim18v17 has no AutoTransformer
configuration, so the two-winding stand-in impedance (winding r, coupling x) has no home.
"""

from __future__ import annotations

from cimbuilder.object_builder import (
    RatioTapChangerBuilder,
    TapChangerControlBuilder,
    TapChangerInfoBuilder,
    VoltageRegulatorBuilder,
)
from cimhub_core.cimtbl import Field
from cimtables.units import Qty
from gdm.systems.distribution.enums import ConnectionType, Phase

from cimhub_gdm.importer.shared import (
    PHASE,
    UUID_FIELD,
    Naming,
    bus_base_voltage,
    bus_mrid,
    container_mrid,
    name_field,
    object_mrid,
    qty,
    require_in_service,
)
from cimhub_gdm.importer.transformer import coil_voltage, instance_taps, tap_step

PREFIX = "vr_"
INFO_PREFIX = "tci_"

#: ANSI C57.15 lugs: (designation, sequenceNumber, the end it lands on or None).
LUGS = (("S", 1, 1), ("L", 2, 2), ("SL", 3, None))

FIELDS_DistributionRegulator = {
    "uuid": UUID_FIELD,
    "name": name_field(PREFIX),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "buses": Field("structural", note="end 1 (S) on bus 1, end 2 (L) on bus 2"),
    "winding_phases": Field("structural", note="one VoltageRegulator per phase, ends <phase>N; the same on both "
                                               "windings"),
    "tap_positions": Field("structural", note="RatioTapChanger step on the tapped winding (tap_step); the catalog "
                                              "winding's when nominal"),
    "equipment": Field("structural", note=f"TapChangerInfo {INFO_PREFIX}<equipment>; two wye windings"),
    "controllers": Field("structural", note="a TapChangerControl each, matched to its phase by controlled_phase"),
}
FIELDS_RegulatorController = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline; the control is named after its regulator"),
    "tapped_winding": Field("structural", note="1-based; the end the RatioTapChanger sits on (default 2, the L side)"),
    "delay": Field("copied", (("add_regulating_control", "initialDelay", None),)),
    "v_setpoint": Field("derived", note="targetValue = v_setpoint × pt_ratio, in V"),
    "min_v_limit": Field("derived", note="minLimitVoltage = min_v_limit × pt_ratio; above max raises"),
    "max_v_limit": Field("derived", note="maxLimitVoltage = max_v_limit × pt_ratio"),
    "pt_ratio": Field("copied", (("add_regulating_control", "ptRatio", None),), note="also scales the voltages"),
    "use_ldc": Field("copied", (("add_regulating_control", "lineDropCompensation", None),)),
    "is_reversible": Field("copied", (("add_regulating_control", "reversible", None),)),
    "ldc_R": Field("derived", note="lineDropR = ldc_R × pt_ratio / ct_primary, in ohm"),
    "ldc_X": Field("derived", note="lineDropX = ldc_X × pt_ratio / ct_primary, in ohm"),
    "ct_primary": Field("copied", (("add_regulating_control", "ctRating", "A"),),
                        note="a plain float in A (I2 exception); also the LDC ohm base"),
    "max_step": Field("untranscribed", note="no CIM home"),
    "bandwidth": Field("derived", note="targetDeadband = bandwidth × pt_ratio, in V"),
    "controlled_bus": Field("structural", note="the Terminal of the end on it; not a regulator bus raises"),
    "controlled_phase": Field("copied", (("add_regulating_control", "monitoredPhase", None),),
                              note="also picks the regulator a per-phase controller controls"),
}


def add_regulator(network, component, naming: Naming) -> None:
    """A VoltageRegulator per phase, each with its tap changer and control."""
    require_in_service(component)
    label = f"DistributionRegulator {component.name!r}"
    check_regulator(component, label)
    phases = regulated_phases(component)
    base = object_mrid(PREFIX, component, "VoltageRegulator", naming)
    units = {phase: (base if len(phases) == 1 else f"{base}_{PHASE[phase].lower()}") for phase in phases}

    terminals = {}
    for phase, unit in units.items():
        terminals[phase] = add_unit(network, component, unit, phase, naming)
    controls = add_controls(network, component, units, terminals, label)
    info = tap_changer_info(network, component.equipment, naming)
    for index, (phase, unit) in enumerate(units.items()):
        add_tap_changer(network, component, unit, index, controls[phase], info, label)


def add_unit(network, component, unit: str, phase: Phase, naming: Naming) -> list:
    """One single-phase regulator: two AutoTransformerEnds, three lugs, the series winding. Returns its Terminals."""
    equipment = component.equipment
    winding = equipment.windings[0]
    builder = VoltageRegulatorBuilder(network, network.container)
    regulator = builder.create(mRID=unit, name=unit_name(component, phase))
    builder.add_connectivity(regulator, EquipmentContainer=container_mrid(component, naming))
    terminals, ends = [], []
    for number, bus in enumerate(component.buses, start=1):
        _, terminal, end = builder.add_auto_transformer_end(regulator, node=bus_mrid(bus, naming), endNumber=number,
                                                            phase=f"{PHASE[phase]}N", BaseVoltage=bus_base_voltage(bus))
        builder.add_electrical(end, baseU=qty(coil_voltage(winding)),
                               ratedS=qty(winding.rated_power / winding.num_phases))
        terminals.append(terminal)
        ends.append(end)
    for designation, sequence, end_number in LUGS:
        builder.add_transformer_lug(regulator, designation=designation, sequenceNumber=sequence,
                                    TransformerEnd=None if end_number is None else ends[end_number - 1].mRID)
    builder.add_transformer_winding(regulator, FromTransformerEnd=ends[0].mRID, ToTransformerEnd=ends[1].mRID,
                                    FromTransformerLug=f"{unit}_lug_s", ToTransformerLug=f"{unit}_lug_sl",
                                    AutoTransformerLug=f"{unit}_lug_l", baseU=qty(coil_voltage(winding)),
                                    ratedS=qty(buck_boost_rating(winding)))
    return terminals


def add_controls(network, component, units: dict, terminals: dict, label: str) -> dict:
    """A TapChangerControl per phase, from the controller on that phase (GDM requires one controller per phase)."""
    by_phase = {Phase(c.controlled_phase): c for c in component.controllers}
    if set(by_phase) != set(units):
        raise ValueError(f"{label}: controllers on {sorted(p.value for p in by_phase)} for regulated phases "
                         f"{sorted(p.value for p in units)}; one per phase")
    return {phase: add_control(network, by_phase[phase], unit, component, terminals, label)
            for phase, unit in units.items()}


def add_control(network, controller, owner: str, component, terminals: dict, label: str) -> str:
    """A TapChangerControl ``<owner>_ctrl`` from a RegulatorController (GDM_MAPPING.md §5)."""
    if controller.min_v_limit > controller.max_v_limit:
        raise ValueError(f"{label}: min_v_limit {controller.min_v_limit} is above max_v_limit "
                         f"{controller.max_v_limit}")
    bus_names = [bus.name for bus in component.buses]
    if controller.controlled_bus.name not in bus_names:
        raise ValueError(f"{label}: controlled_bus {controller.controlled_bus.name!r} is not one of its buses "
                         f"{bus_names}")
    phase = Phase(controller.controlled_phase)
    if phase not in terminals:
        raise ValueError(f"{label}: controlled_phase {phase.value} is not a regulated phase")
    terminal = terminals[phase][bus_names.index(controller.controlled_bus.name)]
    target, deadband, low, high = regulator_targets(controller)
    builder = TapChangerControlBuilder(network, network.container)
    control = builder.create(mRID=f"{owner}_ctrl", name=unit_name(component, phase))
    builder.add_regulating_control(
        control, Terminal=terminal.mRID, mode="voltage", targetValue=target, targetDeadband=deadband,
        monitoredPhase=PHASE[phase], discrete=True, enabled=True,
        lineDropCompensation=controller.use_ldc, reversible=controller.is_reversible,
        lineDropR=line_drop_ohm(controller.ldc_R, controller), lineDropX=line_drop_ohm(controller.ldc_X, controller),
        minLimitVoltage=Qty(low, "V"), maxLimitVoltage=Qty(high, "V"),
    )
    return control.mRID


def add_tap_changer(network, component, unit: str, index: int, control: str, info: str, label: str) -> None:
    """A RatioTapChanger ``<unit>_tap`` on the tapped winding's AutoTransformerEnd, on the regulator's tap."""
    controller = _controller_for(component, index)
    tapped = controller.tapped_winding or 2
    if tapped not in (1, 2):
        raise ValueError(f"{label}: tapped_winding {tapped}; a regulator has windings 1 and 2")
    winding = component.equipment.windings[tapped - 1]
    tap = regulator_tap(component, tapped - 1, index)
    high, low, increment, step = tap_step(tap, winding.total_taps, winding.min_tap_pu, winding.max_tap_pu, label)
    builder = RatioTapChangerBuilder(network, network.container)
    tap_changer = builder.create(mRID=f"{unit}_tap", name=unit_name(component, regulated_phases(component)[index]))
    builder.add_connectivity(tap_changer, TransformerEnd=f"{unit}_end{tapped}")
    builder.add_electrical(tap_changer, highStep=high, lowStep=low, normalStep=0, stepVoltageIncrement=increment)
    builder.add_regulating_control(
        tap_changer, neutralStep=0, neutralU=qty(coil_voltage(winding)), TapChangerControl=control, ltcFlag=True,
        controlEnabled=True, ptRatio=controller.pt_ratio,
        ctRating=None if controller.ct_primary is None else float(controller.ct_primary.to("ampere").magnitude),
        initialDelay=None if controller.delay is None else qty(controller.delay),
    )
    builder.add_ssh(tap_changer, step=step)
    builder.add_asset_datasheet(tap_changer, AssetDatasheet=info)


def _controller_for(component, index: int):
    """The controller on the regulator's ``index``-th phase."""
    phase = regulated_phases(component)[index]
    return next(c for c in component.controllers if Phase(c.controlled_phase) is phase)


def regulated_phases(component) -> list[Phase]:
    """The regulator's phase conductors, one unit each."""
    return [Phase(p) for p in component.winding_phases[0] if Phase(p) is not Phase.N]


def unit_name(component, phase: Phase) -> str:
    """A unit's name: the regulator's, with the phase for a unit of a bank (``rb_a``), so that each unit, which
    exports as its own GDM regulator, has a name of its own."""
    if len(regulated_phases(component)) == 1:
        return component.name
    return f"{component.name}_{PHASE[phase].lower()}"


def regulator_tap(component, winding: int, phase_index: int) -> float:
    """The phase's tap on ``winding``: the instance's when off nominal, else the catalog winding's (as G4)."""
    instance = instance_taps(component, winding)
    if instance and any(tap != 1.0 for tap in instance):
        return float(instance[phase_index])
    return float(component.equipment.windings[winding].tap_positions[phase_index])


def tap_changer_info(network, equipment, naming: Naming) -> str:
    """The regulator catalog's TapChangerInfo ``tci_<equipment>``, built the first time a regulator names it (B17)."""
    info_mrid = object_mrid(INFO_PREFIX, equipment, "TapChangerInfo", naming)
    if network.find_by_mRID(info_mrid) is not None:
        return info_mrid
    winding = equipment.windings[0]
    label = f"{type(equipment).__name__} {equipment.name!r}"
    high, low, increment, _ = tap_step(1.0, winding.total_taps, winding.min_tap_pu, winding.max_tap_pu, label)
    builder = TapChangerInfoBuilder(network, network.container)
    info = builder.create(mRID=info_mrid, name=equipment.name)
    builder.add_asset_info(info, ratedApparentPower=qty(winding.rated_power / winding.num_phases),
                           neutralU=qty(coil_voltage(winding)), highStep=high, lowStep=low, neutralStep=0,
                           stepVoltageIncrement=increment)
    return info_mrid


def check_regulator(component, label: str) -> None:
    """Two single-phase-per-unit wye windings with the same phases on both sides: the only regulator the
    VoltageRegulator template holds (a phase-to-phase regulator is not mapped yet)."""
    windings = component.equipment.windings
    if len(windings) != 2 or any(ConnectionType(w.connection_type) is not ConnectionType.STAR for w in windings):
        raise ValueError(f"{label}: a regulator needs two wye windings, got "
                         f"{[str(w.connection_type) for w in windings]}")
    sides = [[Phase(p) for p in phases if Phase(p) is not Phase.N] for phases in component.winding_phases]
    if sides[0] != sides[1]:
        raise ValueError(f"{label}: winding phases {sides} differ by side")


def regulator_targets(controller) -> tuple[float, float, float, float]:
    """(targetValue, targetDeadband, minLimitVoltage, maxLimitVoltage) in V on the primary side: the PT-secondary
    settings × pt_ratio. CIM's targets have no unit, so this converts to V (the I2 exception, as
    capacitor_targets)."""
    ratio = controller.pt_ratio
    return tuple(float(getattr(controller, slot).to("V").magnitude) * ratio
                 for slot in ("v_setpoint", "bandwidth", "min_v_limit", "max_v_limit"))


def line_drop_ohm(setting, controller) -> Qty | None:
    """A line drop compensator setting in volts as ohms: R or X = setting × pt_ratio / ct_primary."""
    if setting is None or not controller.use_ldc:
        return None
    return Qty(float((setting * controller.pt_ratio / controller.ct_primary).to("ohm").magnitude), "ohm")


def buck_boost_rating(winding):
    """The series winding's rating: the through rating per phase × the regulation range (10 % of 762 kVA)."""
    return winding.rated_power / winding.num_phases * (winding.max_tap_pu - 1)
