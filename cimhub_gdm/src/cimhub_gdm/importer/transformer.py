"""DistributionTransformer → PowerTransformer on a TransformerTankConfiguration template (GDM_MAPPING.md §18).

The catalog (``DistributionTransformerEquipment``, ``PowerTransformerEquipment``) becomes a TransformerTankConfiguration
``xc_``, as the DSS wave's XfmrCode goldens write it:

- **by tank end** (every catalog but a center tap): a TransformerTankEnd ``<xc>_end_<n>`` and a TransformerWinding
  ``<xc>_wdg_<n>`` per winding, no phases on the template; instance end n is template end n.
- **by lug** (a center tap, DSS-2): TransformerLugs H1 H2 X1 X3 X2, whose ``sequenceNumber`` is the instance conductor
  each lands on, and windings H1→H2, X1→X2 (s1→N), X2→X3 (N→s2), so the polarity is in the coils.

Either way a TransformerMeshImpedance ``<xc>_mesh_<i><j>`` per coupled pair carries x, in percent on the From
winding's base, and each winding carries its own r. The instance is a PowerTransformer ``xf_`` with a
PowerTransformerEnd per bus (a center tap's two halves share one low-side end and Terminal, ``s1s2N``), a
TransformerTank on the template, and for a center tap a TransformerPhaseEnd per conductor on its lug's number.

A wye end's two facts come from GDM as written: the neutral is brought out (``Yn``) when the winding's phases list N,
and the end is ``grounded`` when the catalog winding ``is_grounded``. A single-phase wye coil written with one phase
(``A``) returns to the neutral, so its end is ``AN`` (GDM treats N as optional there). ditto's OpenDSS reader writes
``is_grounded=False`` as a placeholder and lists N only for an explicit ``.0`` node, so DSS-derived wyes import as
written: ungrounded, and ``Y`` unless the deck spelled out the neutral (GDM_MAPPING.md §14).
"""

from __future__ import annotations

import math

from cimbuilder.object_builder import (
    CoolingInfoBuilder,
    RatioTapChangerBuilder,
    TransformerBankFromConfigurationBuilder,
    TransformerTankConfigurationBuilder,
)
from cimhub_core.cimtbl import Field, lookup
from cimtables.units import Qty
from gdm.systems.distribution.enums import ConnectionType, Phase, VoltageTypes
from gdm.systems.distribution.equipment import PowerTransformerEquipment

from cimhub_gdm.importer.shared import (
    PHASE,
    UUID_FIELD,
    active_power_unit,
    Naming,
    bus_base_voltage,
    bus_mrid,
    container_mrid,
    name_field,
    object_mrid,
    power_qty,
    qty,
    require_in_service,
    system_voltage,
)

PREFIX = "xf_"
CONFIGURATION_PREFIX = "xc_"
COOLING_PREFIX = "cool_"

#: A winding's connection on the template's TransformerTankEnd. OPEN_DELTA, OPEN_STAR and ZIG_ZAG raise.
TANK_END_CONNECTION = {ConnectionType.STAR: "Y", ConnectionType.DELTA: "D"}

#: A center tap's low-side end, both halves on one Terminal (DSS-2); grounded as its halves are.
SPLIT_END_CONNECTION = "I"

#: A center tap's lugs (IEEE C57.12.70, additive polarity) in conductor order: end 1 (phase, N), end 2 (s1, s2, N).
CENTER_TAP_LUGS = (("H1", 1), ("H2", 2), ("X1", 3), ("X3", 4), ("X2", 5))
#: Each winding's (From lug, To lug): H1→H2, X1→X2 (s1→N), X2→X3 (N→s2).
CENTER_TAP_COILS = (("H1", "H2"), ("X1", "X2"), ("X2", "X3"))
SPLIT_END_PHASES = (Phase.S1, Phase.S2, Phase.N)

_NO_HOME = "no CIM home"

FIELDS_DistributionTransformer = {
    "uuid": UUID_FIELD,
    "name": name_field(PREFIX),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "buses": Field("structural", note="a PowerTransformerEnd per bus, node and BaseVoltage; a center tap's halves "
                                      "share end 2"),
    "winding_phases": Field("structural", note="the end's Terminal phases as written (a 3-phase wye listing N is "
                                               "Yn); a 1-phase wye coil gets its N; a center tap's halves must be "
                                               "S1 N and N S2 → s1s2N"),
    "tap_positions": Field("structural", note="a RatioTapChanger <end>_tap when off nominal (G4); else the catalog "
                                              "winding's"),
    "equipment": Field("structural", note="TransformerTank <xf>_tank on TankConfiguration xc_<equipment>"),
}
FIELDS_DistributionTransformerEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(CONFIGURATION_PREFIX),
    "mounting": Field("untranscribed", note=_NO_HOME),
    "pct_no_load_loss": Field("derived", note="noLoadLoss = pct × winding 1 rated_power / 100, in W"),
    "pct_full_load_loss": Field("derived", note="loadLoss = pct × winding 1 rated_power / 100, in W"),
    "windings": Field("structural", note="a TankEnd and a TransformerWinding each; by lug for a center tap"),
    "coupling_sequences": Field("structural", note="the mesh pairs, 0- or 1-based (coupling_pairs)"),
    "winding_reactances": Field("copied", (("add_mesh_impedance", "x", "percent"),),
                                note="on the From winding's base, which must be winding 1's kVA"),
    "is_center_tapped": Field("structural", note="selects the lug template (DSS-2)"),
    "magnetizing_current_pct": Field("copied", (("add_electrical", "percentMagnetizingCurrent", "percent"),)),
}
FIELDS_PowerTransformerEquipment = FIELDS_DistributionTransformerEquipment | {
    "vector_group": Field("structural", note="connections and phasing checked against the windings (vector_group), "
                                             "neutral marks not; a mismatch raises"),
    "cooling_class": Field("copied", (("add_asset_info", "typeOfCooling", None),),
                           note=f"CoolingInfo {COOLING_PREFIX}<equipment>, each tank's AssetDatasheet"),
    "fluid_type": Field("untranscribed", note="no Specification/Medium builder"),
}
FIELDS_WindingEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline; the winding is <xc>_wdg_<n>"),
    "resistance": Field("copied", (("add_transformer_winding", "r", "percent"),), note="on the winding's own base"),
    "is_grounded": Field("copied", (("add_power_transformer_end", "grounded", None),),
                         note="each instance end of this winding; a grounded delta raises. Regulators: no "
                              "AutoTransformerEnd keyword (B27), untranscribed"),
    "rated_voltage": Field("derived", note="ratedU line-to-line (system_voltage); baseU the coil (coil_voltage)"),
    "voltage_type": Field("structural", note="selects the system_voltage and coil_voltage factors"),
    "rated_power": Field("copied", (("add_transformer_winding", "ratedS", None),),
                         note="baseS = rated_power / num_phases; a center tap half: ratedS = rated_power / 2, "
                              "baseS = rated_power"),
    "num_phases": Field("structural", note="1 or 3; selects the end connection and baseS"),
    "connection_type": Field("mapped", note="TANK_END_CONNECTION, end_connection; open and zig-zag raise"),
    "tap_positions": Field("structural", note="the instance's tap when the instance's are nominal (G4)"),
    "total_taps": Field("structural", note="tap_step: highStep, lowStep, stepVoltageIncrement"),
    "min_tap_pu": Field("structural", note="tap_step"),
    "max_tap_pu": Field("structural", note="tap_step"),
}


def add_tank_configuration(network, equipment, naming: Naming) -> None:
    """A TransformerTankConfiguration with its windings and mesh, by tank end or (center tap) by lug."""
    label = f"{type(equipment).__name__} {equipment.name!r}"
    windings = equipment.windings
    first = windings[0]
    builder = TransformerTankConfigurationBuilder(network, network.container)
    config = builder.create(mRID=configuration_mrid(equipment, naming), name=equipment.name)
    builder.add_electrical(config, noLoadLoss=loss(equipment.pct_no_load_loss, first.rated_power, label),
                           loadLoss=loss(equipment.pct_full_load_loss, first.rated_power, label),
                           percentMagnetizingCurrent=equipment.magnetizing_current_pct)
    if equipment.is_center_tapped:
        check_center_tap(equipment, label)
        for designation, sequence in CENTER_TAP_LUGS:
            builder.add_transformer_lug(config, designation=designation, sequenceNumber=sequence)
    else:
        for number, winding in enumerate(windings, start=1):
            connection = lookup(TANK_END_CONNECTION, ConnectionType(winding.connection_type),
                                slot="connection_type", record_id=equipment.name)
            builder.add_transformer_tank_end(config, endNumber=number, connectionKind=connection)

    for number, winding in enumerate(windings, start=1):
        rated_s, base_s = winding_powers(winding, half=equipment.is_center_tapped and number > 1)
        placement = {"FromTransformerEnd": f"{config.mRID}_end_{number}"}
        if equipment.is_center_tapped:
            from_lug, to_lug = CENTER_TAP_COILS[number - 1]
            placement = {"FromTransformerLug": f"{config.mRID}_lug_{from_lug.lower()}",
                         "ToTransformerLug": f"{config.mRID}_lug_{to_lug.lower()}"}
        builder.add_transformer_winding(
            config, TransformerWinding=f"{config.mRID}_wdg_{number}", **placement,
            ratedU=qty(rated_voltage(winding, split=equipment.is_center_tapped and number > 1)),
            baseU=qty(coil_voltage(winding)),
            ratedS=power_qty(rated_s, "apparent", label=label), baseS=power_qty(base_s, "apparent", label=label),
            r=Qty(winding.resistance, "percent"),
        )

    for (i, j), reactance in zip(coupling_pairs(equipment), equipment.winding_reactances):
        if windings[i].rated_power != first.rated_power:
            raise ValueError(f"{label}: winding {i + 1} is rated {windings[i].rated_power}, not winding 1's "
                             f"{first.rated_power}; the coupling reactances are on winding 1's base")
        builder.add_mesh_impedance(config, FromWinding=f"{config.mRID}_wdg_{i + 1}",
                                   ToWinding=f"{config.mRID}_wdg_{j + 1}", x=Qty(reactance, "percent"))

    if isinstance(equipment, PowerTransformerEquipment):
        check_vector_group(equipment, label)
        if equipment.cooling_class:
            cooling_builder = CoolingInfoBuilder(network, network.container)
            cooling = cooling_builder.create(mRID=cooling_mrid(equipment, naming), name=equipment.name)
            cooling_builder.add_asset_info(cooling, typeOfCooling=equipment.cooling_class)


def add_transformer(network, component, naming: Naming) -> None:
    """A PowerTransformer with an end per bus, a tank on its template and, off nominal, its taps."""
    require_in_service(component)
    label = f"DistributionTransformer {component.name!r}"
    equipment = component.equipment
    builder = TransformerBankFromConfigurationBuilder(network, network.container)
    xfmr = builder.create(mRID=object_mrid(PREFIX, component, "PowerTransformer", naming), name=component.name)
    builder.add_connectivity(xfmr, EquipmentContainer=container_mrid(component, naming))

    end_phases = transformer_end_phases(component, label)
    ends = []
    for number, phases in enumerate(end_phases, start=1):
        winding = equipment.windings[number - 1]
        bus = component.buses[number - 1]
        if equipment.is_center_tapped and number == 2:
            connection, grounded = SPLIT_END_CONNECTION, split_grounded(equipment, label)
        else:
            connection, grounded = end_connection(winding, phases, label)
        _, _, end = builder.add_power_transformer_end(
            xfmr, node=bus_mrid(bus, naming), endNumber=number,
            phases="".join(PHASE[phase] for phase in phases),
            connectionKind=connection, grounded=grounded, BaseVoltage=bus_base_voltage(bus))
        ends.append(end)

    _, tank = builder.add_transformer_tank(xfmr, TankConfiguration=configuration_mrid(equipment, naming))
    if equipment.is_center_tapped:
        sequence = 0
        for number, phases in enumerate(end_phases, start=1):
            for phase in phases:
                sequence += 1
                builder.add_transformer_phase_end(xfmr, endNumber=number, sequenceNumber=sequence,
                                                  phase=PHASE[phase])
    if isinstance(equipment, PowerTransformerEquipment) and equipment.cooling_class:
        builder.add_asset_datasheet(tank, AssetDatasheet=cooling_mrid(equipment, naming))

    for number, end in enumerate(ends, start=1):
        add_tap(network, end, component, number - 1, label)


def add_tap(network, end, component, index: int, label: str) -> None:
    """A RatioTapChanger ``<end>_tap`` with no control when winding ``index`` is off nominal (G4)."""
    winding = component.equipment.windings[index]
    tap = winding_tap(component, index, label)
    if tap == 1.0:
        return
    high, low, increment, step = tap_step(tap, winding.total_taps, winding.min_tap_pu, winding.max_tap_pu, label)
    builder = RatioTapChangerBuilder(network, network.container)
    tap_changer = builder.create(mRID=f"{end.mRID}_tap")
    builder.add_connectivity(tap_changer, TransformerEnd=end.mRID)
    builder.add_electrical(tap_changer, highStep=high, lowStep=low, normalStep=step, stepVoltageIncrement=increment)
    builder.add_regulating_control(tap_changer, neutralStep=0, neutralU=qty(coil_voltage(winding)))
    builder.add_ssh(tap_changer, step=step)


def winding_tap(component, index: int, label: str) -> float:
    """The tap of winding ``index``: the instance's when it is set and off nominal, else the catalog winding's
    (ditto writes a DSS tap on the catalog; user, 2026-11-08). Raises when the two are off nominal and differ, or
    when the phases of one winding differ."""
    instance = instance_taps(component, index)
    catalog = component.equipment.windings[index].tap_positions
    taps = instance if instance and any(tap != 1.0 for tap in instance) else catalog
    if len(set(taps)) > 1:
        raise ValueError(f"{label}: winding {index + 1} taps differ by phase ({taps}); one RatioTapChanger per end")
    if instance and set(instance) != {1.0} and set(catalog) != {1.0} and set(instance) != set(catalog):
        raise ValueError(f"{label}: winding {index + 1} instance taps {instance} and catalog taps {catalog} differ")
    if component.equipment.is_center_tapped and index > 0 and taps[0] != 1.0:
        raise ValueError(f"{label}: a center tap half is off nominal ({taps}); the halves share one end")
    return float(taps[0])


def instance_taps(component, index: int) -> list[float] | None:
    """The instance's taps on winding ``index`` for its phase conductors: GDM keeps one per listed phase, N included,
    and the neutral has no tap."""
    if not component.tap_positions:
        return None
    phases = component.winding_phases[index]
    return [tap for tap, phase in zip(component.tap_positions[index], phases) if Phase(phase) is not Phase.N]


def tap_step(tap: float, total_taps: int, min_pu: float, max_pu: float, label: str) -> tuple[int, int, float, int]:
    """(highStep, lowStep, stepVoltageIncrement %, step) of a tap in per unit (GDM_MAPPING.md §5). The taps split
    evenly across boost and buck; the step must be a whole tap position."""
    if total_taps % 2 or not math.isclose(max_pu - 1, 1 - min_pu, abs_tol=1e-9):
        raise ValueError(f"{label}: taps {min_pu}-{max_pu} pu in {total_taps} steps are not symmetric about 1.0")
    increment = (max_pu - min_pu) / total_taps * 100
    position = (tap - 1) * 100 / increment
    if not math.isclose(position, round(position), abs_tol=1e-6):
        raise ValueError(f"{label}: tap {tap} pu is not a whole step of {increment} %")
    return total_taps // 2, -(total_taps // 2), increment, round(position)


def transformer_end_phases(component, label: str) -> list[list[Phase]]:
    """Each end's conductors, as written, but a single-phase wye coil written with one phase gets the N it returns to;
    a center tap's two halves (S1 N, N S2) are one end, s1 s2 N."""
    equipment = component.equipment
    phases = [[Phase(p) for p in winding_phases] for winding_phases in component.winding_phases]
    ends = []
    for winding, winding_phases in zip(equipment.windings, phases):
        single_wye = ConnectionType(winding.connection_type) is ConnectionType.STAR and winding.num_phases == 1
        if single_wye and Phase.N not in winding_phases:
            winding_phases = winding_phases + [Phase.N]
        ends.append(winding_phases)
    if not equipment.is_center_tapped:
        return ends
    if {*phases[1]} != {Phase.S1, Phase.N} or {*phases[2]} != {Phase.N, Phase.S2}:
        raise ValueError(f"{label}: center tap halves on {phases[1:]}; expected S1 N and N S2")
    return [ends[0], list(SPLIT_END_PHASES)]


def end_connection(winding, phases, label: str) -> tuple[str, bool]:
    """An instance end's (connectionKind, grounded), from GDM as written: a 3-phase wye is ``Yn`` when its phases list
    N (the neutral brought out), else ``Y``; a single-phase wye is ``Y``; a delta ``D``. ``grounded`` is the winding's
    ``is_grounded``; a grounded delta has no mapping and raises."""
    connection = ConnectionType(winding.connection_type)
    if connection is ConnectionType.DELTA:
        if winding.is_grounded:
            raise ValueError(f"{label}: a grounded delta winding has no mapping")
        return "D", False
    if connection is not ConnectionType.STAR:
        raise ValueError(f"{label}: a {connection.value} winding has no mapping yet")
    if winding.num_phases == 3 and Phase.N in phases:
        return "Yn", winding.is_grounded
    return "Y", winding.is_grounded


def split_grounded(equipment, label: str) -> bool:
    """A center tap's low-side ``grounded``: its two halves' ``is_grounded``, which must agree."""
    halves = {equipment.windings[1].is_grounded, equipment.windings[2].is_grounded}
    if len(halves) > 1:
        raise ValueError(f"{label}: one center tap half is grounded and the other is not")
    return halves.pop()


def check_center_tap(equipment, label: str) -> None:
    """A center tap is three single-phase wye windings: the primary and two halves (DSS-2)."""
    shapes = [(w.num_phases, ConnectionType(w.connection_type)) for w in equipment.windings]
    if shapes != [(1, ConnectionType.STAR)] * 3:
        raise ValueError(f"{label}: a center tap needs three single-phase wye windings, got {shapes}")


def coupling_pairs(equipment) -> list[tuple[int, int]]:
    """GDM ``coupling_sequences`` as 0-based winding pairs: 0-based if any index is 0 (ditto), else 1-based (the GDM
    repo's p5r). GDM requires every pair exactly once, so a complete set is never ambiguous; an index out of range
    raises."""
    pairs = [(pair.from_index, pair.to_index) for pair in equipment.coupling_sequences]
    if all(0 not in pair for pair in pairs):
        pairs = [(i - 1, j - 1) for i, j in pairs]
    count = len(equipment.windings)
    if any(not 0 <= index < count for pair in pairs for index in pair):
        raise ValueError(f"{type(equipment).__name__} {equipment.name!r}: coupling indices "
                         f"{[(c.from_index, c.to_index) for c in equipment.coupling_sequences]} out of range for "
                         f"{count} windings")
    return pairs


def rated_voltage(winding, *, split: bool):
    """ratedU, the line-to-line nameplate voltage: system_voltage of the rating (a center tap half's is 2×)."""
    phases = [Phase.S1, Phase.S2] if split else [Phase.A, Phase.B, Phase.C]
    return system_voltage(winding.rated_voltage, winding.voltage_type, phases)


def coil_voltage(winding):
    """baseU, the voltage across one coil: line-to-ground on a wye, line-to-line on a delta."""
    line_to_line = VoltageTypes(winding.voltage_type) is VoltageTypes.LINE_TO_LINE
    if ConnectionType(winding.connection_type) is ConnectionType.DELTA:
        return winding.rated_voltage if line_to_line else winding.rated_voltage * math.sqrt(3)
    return winding.rated_voltage / math.sqrt(3) if line_to_line else winding.rated_voltage


def winding_powers(winding, *, half: bool):
    """(ratedS, baseS): the rating and the per-coil base. A 3-phase winding's base is a third of its rating; a center
    tap half is rated half the kVA on the full kVA base (DSS-2)."""
    if half:
        return winding.rated_power / 2, winding.rated_power
    return winding.rated_power, winding.rated_power / winding.num_phases


def loss(pct: float, rated_power, label: str) -> Qty:
    """pct % of an apparent power, as active power in the same prefix (1.74408 % of 75 kVA → 1.30806 kW)."""
    return Qty(pct / 100 * float(rated_power.magnitude),
               active_power_unit(power_qty(rated_power, "apparent", label=label)))


def vector_group(equipment) -> str:
    """The IEC vector group the windings' connections make, without neutral marks, ANSI phasing (the low side lags 30°
    across a wye-delta, OpenDSS's default), the first winding upper case: ``Dy1``, ``Yy0``, ``Yd1``, ``Yy0d1``."""
    first = ConnectionType(equipment.windings[0].connection_type)
    text = "D" if first is ConnectionType.DELTA else "Y"
    for winding in equipment.windings[1:]:
        connection = ConnectionType(winding.connection_type)
        text += ("d" if connection is ConnectionType.DELTA else "y") + ("0" if connection is first else "1")
    return text


def check_vector_group(equipment, label: str) -> None:
    """``vector_group`` must match the connections and phasing. Its neutral marks (``n``, ``N``) are not checked: a
    neutral brought out is the instance's N, not the catalog's (and is not ``is_grounded``)."""
    if not equipment.vector_group:
        return
    written = equipment.vector_group.replace(" ", "").replace("N", "").replace("n", "")
    if written != vector_group(equipment):
        raise ValueError(f"{label}: vector_group {equipment.vector_group!r}, but the windings make "
                         f"{vector_group(equipment)!r}")


def configuration_mrid(equipment, naming: Naming) -> str:
    return object_mrid(CONFIGURATION_PREFIX, equipment, "TransformerTankConfiguration", naming)


def cooling_mrid(equipment, naming: Naming) -> str:
    return object_mrid(COOLING_PREFIX, equipment, "CoolingInfo", naming)
