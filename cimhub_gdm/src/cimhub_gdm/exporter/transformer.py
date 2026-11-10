"""PowerTransformer → DistributionTransformer on a DistributionTransformerEquipment (``EXPORT_MAPPING.md#transformers``,
decision X3).

``get_transformer_model`` reads the transformer's one unit (its tank, or the transformer itself by ends) in any CIM
form, and each winding becomes a WindingEquipment on the bus its end lands on. A tank on a TransformerTankConfiguration
shares one GDM equipment per (configuration, values), named after the configuration; any other transformer gets its
own, named after it.

The taps go on the equipment: ditto 0.1.8 writes no instance tap (its OpenDSS Transformer has no ``Tap_wdg``), so a
winding's ratio from its end's RatioTapChanger is the catalog winding's, and instances on other taps split the
catalog. A center tap is three windings, the last two on one end (DSS-2).
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.cimtbl import lookup
from cimhub_core.getters import describe
from cimhub_core.getters.tap_changer import get_tap_ratio, get_tap_steps
from cimhub_core.getters.transformer import get_transformer_model, get_transformer_units
from cimtables.graph_write import get_qty
from gdm.quantities import ApparentPower
from gdm.systems.distribution.common import SequencePair
from gdm.systems.distribution.components import DistributionTransformer
from gdm.systems.distribution.enums import ConnectionType, Phase, VoltageTypes
from gdm.systems.distribution.equipment import (
    DistributionTransformerEquipment,
    PowerTransformerEquipment,
    WindingEquipment,
)
from infrasys.quantities import Voltage

from cimhub_gdm.exporter.shared import ExportContext, containers, gdm_phases, in_service, shared_equipment
from cimhub_gdm.exporter.slots import UUID, Slot
from cimhub_gdm.importer.transformer import vector_group

CIM_CLASSES = (cim.PowerTransformer,)

#: The units the transformer getter is asked for.
VOLTAGE_UNIT, POWER_UNIT = "kV", "kVA"

#: CIM winding connection → GDM. I is a center tap's split end (DSS-2), whose halves are wye coils. Others raise.
WINDING_CONNECTION = {
    cim.WindingConnection.Y: ConnectionType.STAR, cim.WindingConnection.Yn: ConnectionType.STAR,
    cim.WindingConnection.I: ConnectionType.STAR, cim.WindingConnection.D: ConnectionType.DELTA,
}
THREE_PHASE = {cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C}
SPLIT_PHASES = {Phase.S1, Phase.S2}

_COMPONENT_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "Names (X2)"),
    "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
    "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
    "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
    "buses": Slot("written", "each winding's end's ConnectivityNode, in winding order (a center tap's halves share "
                             "one)"),
    "winding_phases": Slot("rule", "each winding's phases from get_transformer_model (its end's terminal, or a "
                                   "coil's two phase ends), a 1-phase wye coil without its N (ditto 0.1.8 counts "
                                   "the list as Phases)"),
}
_EQUIPMENT_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "the TankConfiguration's name, <configuration>_<n> for its n-th values (X3); else the "
                            "transformer's"),
    "mounting": Slot("unset", "untranscribed on import: no CIM home; GDM's default"),
    "pct_no_load_loss": Slot("rule", "get_transformer_model core g (% on winding 1's ratedS); unset is 0"),
    "pct_full_load_loss": Slot("rule", "loadLoss on the tank or its configuration, % of winding 1's ratedS; unset is "
                                       "windings 1 and 2's r summed (OpenDSS's %loadloss)"),
    "windings": Slot("written", "one WindingEquipment per get_transformer_model winding"),
    "coupling_sequences": Slot("written", "the mesh pairs, 0-based (as ditto writes them)"),
    "winding_reactances": Slot("written", "the mesh x, % on winding 1's ratedS"),
    "is_center_tapped": Slot("rule", "three windings, the last two on one end (DSS-2)"),
    "magnetizing_current_pct": Slot("written", "get_transformer_model core b (% on winding 1's ratedS); unset is "
                                               "None"),
}
_TAP_RANGE = "from the end's RatioTapChanger (get_tap_steps, get_tap_ratio); none: GDM's default"

SLOTS = {
    DistributionTransformer: _COMPONENT_SLOTS | {
        "tap_positions": Slot("unset", "the taps are the equipment's (ditto 0.1.8 writes no instance tap)"),
        "equipment": Slot("written", "the DistributionTransformerEquipment (or PowerTransformerEquipment) made for it"),
    },
    DistributionTransformerEquipment: _EQUIPMENT_SLOTS,
    PowerTransformerEquipment: _EQUIPMENT_SLOTS | {
        "vector_group": Slot("rule", "made from the windings' connections, ANSI phasing, no neutral marks (the "
                                     "importer's vector_group)"),
        "cooling_class": Slot("written", "typeOfCooling of the unit's CoolingInfo AssetDatasheet; one is what makes "
                                         "it a PowerTransformerEquipment"),
        "fluid_type": Slot("unset", "untranscribed on import: no Specification builder"),
    },
    WindingEquipment: {
        "uuid": UUID,
        "name": Slot("unset", "untranscribed on import: inline, no CIM object of its own"),
        "resistance": Slot("written", "the winding's r, moved to its own rated_power; unset raises (a regulator: "
                                      "half the mesh r)"),
        "is_grounded": Slot("rule", "grounded; unset is False on a delta and raises on a wye (a regulator: unset is "
                                    "False, B27)"),
        "rated_voltage": Slot("rule", "the coil: baseU, else ratedU (/ √3 on a wye)"),
        "voltage_type": Slot("rule", "line-to-line on a delta, line-to-ground on a wye"),
        "rated_power": Slot("rule", "ratedS (kVA); a center tap half 2 × ratedS (its baseS)"),
        "num_phases": Slot("rule", "3 when the winding's phases hold A, B and C, else 1"),
        "connection_type": Slot("written", "connectionKind: Y, Yn and I (a center tap's split end) → STAR, D → "
                                           "DELTA; others raise (a regulator: STAR)"),
        "tap_positions": Slot("rule", "get_tap_ratio(which='actual') of the end's RatioTapChanger, one per phase; "
                                      "none is 1.0 (a regulator's are 1.0: its tap is the instance's)"),
        "total_taps": Slot("rule", f"highStep − lowStep {_TAP_RANGE}"),
        "min_tap_pu": Slot("rule", f"get_tap_ratio(which='low') {_TAP_RANGE}"),
        "max_tap_pu": Slot("rule", f"get_tap_ratio(which='high') {_TAP_RANGE}"),
    },
}


def export(transformer: cim.PowerTransformer, context: ExportContext) -> DistributionTransformer:
    unit = one_unit(transformer)
    model = get_transformer_model(unit, voltage_unit=VOLTAGE_UNIT, power_unit=POWER_UNIT)
    for winding in model.windings:
        tap = winding.end.RatioTapChanger
        if tap is not None and tap.TapChangerControl is not None:
            raise ValueError(f"no GDM export yet for a PowerTransformer under tap control (an LTC): "
                             f"{describe(transformer)}")
    center_tap = is_center_tap(model)
    windings = [winding_equipment(winding, model, center_tap, transformer) for winding in model.windings]
    return DistributionTransformer(
        **context.names.own(transformer),
        buses=[context.gdm(end_node(winding.end)) for winding in model.windings],
        winding_phases=[winding_phases(winding, part) for winding, part in zip(model.windings, windings)],
        equipment=transformer_equipment(transformer, unit, model, windings, center_tap, context),
        in_service=in_service(transformer),
        **containers(transformer.EquipmentContainer, context),
    )


def one_unit(transformer: cim.PowerTransformer):
    """The transformer's one unit: GDM holds one equipment per transformer, so a bank of tanks raises."""
    units = get_transformer_units(transformer)
    if len(units) > 1:
        raise ValueError(f"no GDM export yet for a bank of {len(units)} tanks: {describe(transformer)}")
    return units[0]


def is_center_tap(model) -> bool:
    """Three windings, the last two on one end: a center tap's halves (DSS-2)."""
    windings = model.windings
    return len(windings) == 3 and windings[1].end is windings[2].end


def winding_equipment(winding, model, center_tap: bool, owner) -> WindingEquipment:
    """One winding as GDM holds it: its coil voltage and rating, its own-base r, its taps."""
    connection = lookup(WINDING_CONNECTION, winding.connection, slot="connectionKind", record_id=winding.end.mRID)
    rated_power = winding_power(winding, center_tap)
    if winding.r is None:
        raise ValueError(f"{describe(winding.end)}: winding {winding.number} has no r")
    num_phases = phase_count(winding.phases)
    return WindingEquipment(
        resistance=winding.r * rated_power / winding_power(model.windings[0], center_tap),
        is_grounded=is_grounded(winding, connection),
        connection_type=connection,
        rated_power=ApparentPower(rated_power, "kilova"),
        num_phases=num_phases,
        tap_positions=[tap_ratio(winding.end)] * num_phases,
        **coil_voltage(winding, connection),
        **tap_range(winding.end),
    )


def winding_phases(winding, equipment: WindingEquipment) -> list:
    """The winding's phases as GDM lists them: a 1-phase wye coil on A, B or C without the N it returns to (the
    importer adds it back; a center tap's halves keep theirs). ditto 0.1.8 writes a transformer's ``Phases`` as the length of winding 1's list, so ``[B, N]`` would be a
    2-phase unit."""
    phases = gdm_phases(winding.phases, winding.end)
    single_wye = equipment.num_phases == 1 and equipment.connection_type is ConnectionType.STAR
    if single_wye and len(phases) == 2 and Phase.N in phases and not SPLIT_PHASES & set(phases):
        phases.remove(Phase.N)
    return phases


def winding_power(winding, center_tap: bool) -> float:
    """rated_power in kVA: ratedS, but a center tap half is rated half its baseS (DSS-2), so 2 × ratedS."""
    if winding.rated_s is None:
        raise ValueError(f"{describe(winding.end)}: winding {winding.number} has no ratedS")
    half = center_tap and winding.number > 1
    return 2 * winding.rated_s if half else winding.rated_s


def phase_count(phases) -> int:
    """GDM's num_phases: 3 for a winding on A, B and C, else 1 (a 1-phase delta spans two conductors)."""
    return 3 if THREE_PHASE <= set(phases) else 1


def is_grounded(winding, connection: ConnectionType) -> bool:
    """``grounded`` as written; unset is False on a delta, which has no neutral, and raises on a wye."""
    if winding.grounded is not None:
        return winding.grounded
    if connection is ConnectionType.DELTA:
        return False
    raise ValueError(f"{describe(winding.end)}: grounded is unset on a wye winding")


def coil_voltage(winding, connection: ConnectionType) -> dict:
    """``rated_voltage`` and ``voltage_type`` of the coil: baseU, else ratedU (line to line) over √3 on a wye. A delta
    coil is line to line, a wye coil line to ground (as ditto's DSS reader writes them)."""
    delta = connection is ConnectionType.DELTA
    if winding.base_u is not None:
        kv = winding.base_u
    elif winding.rated_u is not None:
        kv = winding.rated_u if delta else winding.rated_u / math.sqrt(3)
    else:
        raise ValueError(f"{describe(winding.end)}: winding {winding.number} has neither baseU nor ratedU")
    voltage_type = VoltageTypes.LINE_TO_LINE if delta else VoltageTypes.LINE_TO_GROUND
    return {"rated_voltage": Voltage(kv, "kilovolt"), "voltage_type": voltage_type}


def tap_ratio(end) -> float:
    """The actual turns ratio of the end's RatioTapChanger; 1.0 when it has none."""
    tap = end.RatioTapChanger
    return 1.0 if tap is None else get_tap_ratio(tap, which="actual")


def tap_range(end) -> dict:
    """``total_taps``, ``min_tap_pu`` and ``max_tap_pu`` of the end's RatioTapChanger; none leaves GDM's defaults."""
    tap = end.RatioTapChanger
    if tap is None:
        return {}
    steps = get_tap_steps(tap)
    return {"total_taps": steps.high - steps.low, "min_tap_pu": get_tap_ratio(tap, which="low"),
            "max_tap_pu": get_tap_ratio(tap, which="high")}


def transformer_equipment(transformer, unit, model, windings: list, center_tap: bool, context: ExportContext):
    """The unit's GDM equipment: shared through its TankConfiguration, else its own."""
    values = {
        "windings": windings,
        "pct_no_load_loss": model.core.g or 0.0,
        "pct_full_load_loss": full_load_loss(unit, model),
        "magnetizing_current_pct": model.core.b,
        "coupling_sequences": [SequencePair(from_index=i - 1, to_index=j - 1) for i, j in model.mesh],
        "winding_reactances": [mesh.x for mesh in model.mesh.values()],
        "is_center_tapped": center_tap,
    }
    cooling = unit.AssetDatasheet if isinstance(unit.AssetDatasheet, cim.CoolingInfo) else None
    if cooling is None:
        equipment = DistributionTransformerEquipment(name=transformer.mRID, **values)
    else:
        equipment = PowerTransformerEquipment(name=transformer.mRID, cooling_class=cooling.typeOfCooling, **values)
        equipment = equipment.model_copy(update={"vector_group": vector_group(equipment)})
    config = getattr(unit, "TankConfiguration", None)
    if config is not None:
        return shared_equipment(context, config, equipment)
    return equipment.model_copy(update=context.names.part(transformer, type(equipment)))


def full_load_loss(unit, model) -> float:
    """``loadLoss`` on the tank or its configuration as % of winding 1's ratedS; unset, windings 1 and 2's r summed
    (OpenDSS's %loadloss, which a by-ends transformer from DSS holds as r)."""
    holders = [unit, unit.TankConfiguration] if isinstance(unit, cim.TransformerTank) else []
    losses = [(holder, loss) for holder in holders if holder is not None
              and (loss := get_qty(holder, "loadLoss", "kW")) is not None]
    if len(losses) > 1:
        raise ValueError(f"{describe(unit)}: both it and its TankConfiguration set loadLoss")
    if losses:
        return losses[0][1] / model.windings[0].rated_s * 100
    return sum(winding.r for winding in model.windings[:2])


def end_node(end) -> cim.ConnectivityNode:
    if end.Terminal is None or end.Terminal.ConnectivityNode is None:
        raise ValueError(f"{describe(end)}: its Terminal is on no ConnectivityNode")
    return end.Terminal.ConnectivityNode
