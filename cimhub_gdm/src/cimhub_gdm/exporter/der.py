"""PowerElectronicsConnection → DistributionSolar or DistributionBattery (``EXPORT_MAPPING.md#der``, X4, X7, X8).

Each PowerElectronicsUnit is one GDM DER, its class picking the GDM class: a PhotoVoltaicUnit gives a
DistributionSolar, a BatteryUnit a DistributionBattery; another unit raises. GDM holds one DC device per inverter, so
a connection of several units (a PV array and a battery behind one inverter) is chopped by ``get_inverter_units``, the
DSS exporter's rule: each unit's share is its maxP over the units' total, and it takes that share of the connection's
q and inverter rating, and its own p (else that share of the connection's p), in the generation sign. One unit is the
whole connection, and its DER is the connection's (name and uuid); several each take their unit's. The inverter is
the connection's InverterInfo, shared (X3) per share, else the DER's own. A battery's equipment is its unit's
BatteryInfo, shared, else its own. The equipment's rating is ``ratedU`` in the importer's ``system_voltage`` form,
inverted: line to line on three phases, else line to ground (a split-phase leg is half, any other phase ratedU / √3).
Inverter controllers are not in CIM, so ``controller`` is None (X8).

A PV's irradiance is ``PhotoVoltaicUnit.irradiance`` when set (B16b). When it is not, it is not neutral: ditto 0.1.8
writes no ``active_power``, and OpenDSS makes ``Pmpp × Irradiance``. So irradiance is then the output's share of the
panel's rating at standard test conditions (p / maxP × 1 kW/m²), and the PV makes CIM's p.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty
from cimhub_core.getters import describe
from cimhub_core.getters.der import (
    get_battery_unit,
    InverterUnitShare,
    get_der_output,
    get_inverter_rating,
    get_inverter_units,
    get_photovoltaic_unit,
)
from cimhub_core.getters.terminals import get_terminal_nodes
from gdm.quantities import ApparentPower, EnergyDC, Irradiance, ReactivePower
from gdm.systems.distribution.components import DistributionBattery, DistributionSolar
from gdm.systems.distribution.enums import VoltageTypes
from gdm.systems.distribution.equipment import BatteryEquipment, InverterEquipment, SolarEquipment
from infrasys.quantities import ActivePower, Voltage

from cimhub_gdm.exporter import fills
from cimhub_gdm.exporter.shared import (
    ExportContext,
    containers,
    gdm_phases,
    in_service,
    shared_equipment,
)
from cimhub_gdm.exporter.slots import UUID, Slot

CIM_CLASSES = (cim.PowerElectronicsConnection,)

#: The sign every DER value is read in: positive output, GDM's.
SIGN = "generation"
THREE_PHASE = {cim.SinglePhaseKind.A, cim.SinglePhaseKind.B, cim.SinglePhaseKind.C}
SPLIT_PHASES = {cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2}

_RATING = ("the connection's ratedU (get_inverter_rating), line to line on three phases, else line to ground: / 2 "
           "on a split-phase leg, / √3 otherwise (the importer's system_voltage inverted)")
_VOLTAGE_TYPE = "line-to-line on A, B and C, else line-to-ground"
_DER_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "Names (X2): the connection's for one unit, else the unit's"),
    "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
    "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
    "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
    "bus": Slot("written", "the bus of get_terminal_nodes"),
    "phases": Slot("written", "get_der_output.phases: the phase conductors, no neutral (balanced ABC on none, G3)"),
    "active_power": Slot("written", "get_inverter_units(sign='generation') p (kW): the unit's own, else its share "
                                    "of the connection's"),
    "reactive_power": Slot("written", "get_inverter_units(sign='generation') q (kVAr): its share of the "
                                      "connection's"),
    "controller": Slot("unset", "inverter controllers are not in CIM (PENDING on import, X8)"),
    "inverter": Slot("written", "the InverterEquipment of the connection's InverterInfo (shared, X3), else the "
                                "DER's own"),
}

SLOTS = {
    DistributionSolar: _DER_SLOTS | {
        "irradiance": Slot("rule", "PhotoVoltaicUnit.irradiance; unset, p / the panel's maxP × 1 kW/m² (standard "
                                   "test conditions): what OpenDSS makes of it (Pmpp × Irradiance) is CIM's p"),
        "equipment": Slot("written", "a SolarEquipment made for this DER"),
    },
    DistributionBattery: _DER_SLOTS | {
        "equipment": Slot("written", "the BatteryEquipment of the unit's BatteryInfo (shared, X3), else the DER's "
                                     "own"),
    },
    SolarEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the DER's name (X2)"),
        "rated_power": Slot("written", "get_photovoltaic_unit(sign='generation').max_p (kW); unset raises"),
        "power_temp_curve": Slot("unset", "untranscribed on import: until the Curve builder (B12)"),
        "resistance": Slot("fill", "fills.SOLAR_RESISTANCE, 0 % (§3.1)"),
        "reactance": Slot("fill", "fills.SOLAR_REACTANCE, 0 % (§3.1)"),
        "rated_voltage": Slot("rule", _RATING),
        "voltage_type": Slot("rule", _VOLTAGE_TYPE),
    },
    BatteryEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the BatteryInfo's name (X2); else the DER's"),
        "rated_energy": Slot("written", "get_battery_unit.rated_e (kWh); unset raises"),
        "rated_power": Slot("rule", "get_battery_unit(sign='generation').max_p (kW), with min_p unset or -max_p "
                                    "(GDM has one rating both ways); else raises"),
        "charging_efficiency": Slot("written", "get_battery_unit.charging_efficiency (%); unset raises"),
        "discharging_efficiency": Slot("written", "get_battery_unit.discharging_efficiency (%); unset raises"),
        "idling_efficiency": Slot("fill", "fills.BATTERY_IDLING_EFFICIENCY, 100 % (§3.1)"),
        "rated_voltage": Slot("rule", _RATING),
        "voltage_type": Slot("rule", _VOLTAGE_TYPE),
    },
    InverterEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the InverterInfo's name (X2), '' when it has none under name source 'name' (GDM's "
                                "default, which the importer reads as unnamed); else the DER's"),
        "rated_apparent_power": Slot("written", "get_inverter_rating.rated_s × the unit's share (kVA)"),
        "rise_limit": Slot("fill", "fills.INVERTER_RAMP_LIMIT, None (§3.1)"),
        "fall_limit": Slot("fill", "fills.INVERTER_RAMP_LIMIT, None (§3.1)"),
        "cutout_percent": Slot("fill", "fills.INVERTER_CUTOUT_PERCENT, 0 % (§3.1)"),
        "cutin_percent": Slot("fill", "fills.INVERTER_CUTIN_PERCENT, 0 % (§3.1)"),
        "dc_to_ac_efficiency": Slot("fill", "fills.INVERTER_EFFICIENCY, 100 % (§3.1)"),
        "eff_curve": Slot("unset", "untranscribed on import: until the Curve builder (B12)"),
    },
}


def export(connection: cim.PowerElectronicsConnection, context: ExportContext) -> tuple:
    """One GDM DER per unit of the connection."""
    units = get_inverter_units(connection, "kW", "kVAr", sign=SIGN)
    output = get_der_output(connection, "kW", "kVAr", sign=SIGN)
    rating = get_inverter_rating(connection, "kVA", "kVAr", sign=SIGN, voltage_unit="kV")
    voltage = equipment_voltage(rating.rated_u, output.phases)
    [node] = get_terminal_nodes(connection)
    common = {
        "bus": context.gdm(node),
        "phases": gdm_phases(output.phases, connection),
        "in_service": in_service(connection),
        **containers(connection.EquipmentContainer, context),
    }
    return tuple(der(connection, share, connection if len(units) == 1 else share.unit, rating, voltage, common,
                     context) for share in units)


def der(connection, share: InverterUnitShare, owner, rating, voltage: dict, common: dict, context: ExportContext):
    """The DER of one unit's ``share``, named and identified as ``owner`` (the connection, or the unit)."""
    unit = share.unit
    common = common | {
        **context.names.own(owner),
        "active_power": ActivePower(share.p, "kilowatt"),
        "reactive_power": ReactivePower(share.q, "kilovar"),
        "inverter": inverter(connection, owner, share.share * rating.rated_s, context),
    }
    if isinstance(unit, cim.PhotoVoltaicUnit):
        panel = solar_equipment(owner, unit, voltage, context)
        return DistributionSolar(irradiance=irradiance(share.p, panel, unit), equipment=panel, **common)
    if isinstance(unit, cim.BatteryUnit):
        return DistributionBattery(equipment=battery_equipment(owner, unit, voltage, context), **common)
    raise ValueError(f"no GDM export yet for a {type(unit).__name__}: {describe(connection)}")


def equipment_voltage(rated_u: float, phases) -> dict:
    """``rated_voltage`` (kV) and ``voltage_type`` from ratedU, line to line as CIM stores it (the importer's
    ``system_voltage`` inverted)."""
    conductors = set(phases)
    if THREE_PHASE <= conductors:
        return {"rated_voltage": Voltage(rated_u, "kilovolt"), "voltage_type": VoltageTypes.LINE_TO_LINE}
    leg = rated_u / 2 if SPLIT_PHASES & conductors else rated_u / math.sqrt(3)
    return {"rated_voltage": Voltage(leg, "kilovolt"), "voltage_type": VoltageTypes.LINE_TO_GROUND}


def inverter(connection, owner, rated_s: float, context: ExportContext) -> InverterEquipment:
    """The DER's inverter of ``rated_s`` kVA: its connection's InverterInfo's, shared, else ``owner``'s own."""
    equipment = InverterEquipment(
        name="",
        rated_apparent_power=ApparentPower(rated_s, "kilova"),
        rise_limit=context.fill("InverterEquipment.rise_limit", fills.INVERTER_RAMP_LIMIT),
        fall_limit=context.fill("InverterEquipment.fall_limit", fills.INVERTER_RAMP_LIMIT),
        cutin_percent=context.fill("InverterEquipment.cutin_percent", fills.INVERTER_CUTIN_PERCENT),
        cutout_percent=context.fill("InverterEquipment.cutout_percent", fills.INVERTER_CUTOUT_PERCENT),
        dc_to_ac_efficiency=context.fill("InverterEquipment.dc_to_ac_efficiency", fills.INVERTER_EFFICIENCY),
    )
    info = connection.AssetDatasheet
    if not isinstance(info, cim.InverterInfo):
        return equipment.model_copy(update=context.names.part(owner, InverterEquipment))
    return shared_equipment(context, info, equipment, unnamed="")  # GDM's default; the importer reads it as unnamed


def irradiance(output_kw: float, panel: SolarEquipment, unit: cim.PhotoVoltaicUnit) -> Irradiance:
    """The unit's irradiance; unset, the irradiance at which the panel makes ``output_kw``: its share of the rating,
    at 1 kW/m² for the rating."""
    stored = get_qty(unit, "irradiance", "kW/m^2")
    if stored is not None:
        return Irradiance(stored, "kilowatt / meter ** 2")
    rated_kw = panel.rated_power.to("kilowatt").magnitude
    if rated_kw <= 0:
        raise ValueError(f"{describe(unit)}: maxP is {rated_kw} kW; GDM's irradiance is the output's share of it")
    return Irradiance(output_kw / rated_kw, "kilowatt / meter ** 2")


def solar_equipment(owner, unit: cim.PhotoVoltaicUnit, voltage: dict, context: ExportContext) -> SolarEquipment:
    rated_power = get_photovoltaic_unit(unit, "kW", sign=SIGN).max_p
    if rated_power is None:
        raise ValueError(f"{describe(unit)}: maxP is unset; GDM needs the panel's rated_power")
    return SolarEquipment(
        **context.names.part(owner, SolarEquipment),
        rated_power=ActivePower(rated_power, "kilowatt"),
        resistance=context.fill("SolarEquipment.resistance", fills.SOLAR_RESISTANCE),
        reactance=context.fill("SolarEquipment.reactance", fills.SOLAR_REACTANCE),
        **voltage,
    )


def battery_equipment(owner, unit: cim.BatteryUnit, voltage: dict, context: ExportContext) -> BatteryEquipment:
    """The battery's equipment: its BatteryInfo's, shared, else ``owner``'s own."""
    battery = get_battery_unit(unit, "kW", "kWh", sign=SIGN)
    unset = [name for name in ("max_p", "rated_e", "charging_efficiency", "discharging_efficiency")
             if getattr(battery, name) is None]
    if unset:
        raise ValueError(f"{describe(unit)}: {', '.join(unset)} unset; GDM's BatteryEquipment requires them")
    if battery.min_p is not None and not math.isclose(battery.min_p, -battery.max_p):
        raise ValueError(f"{describe(unit)}: minP {battery.min_p} kW is not the negative of maxP {battery.max_p} kW; "
                         "GDM's BatteryEquipment has one rated_power both ways")
    equipment = BatteryEquipment(
        name="",
        rated_energy=EnergyDC(battery.rated_e, "kilowatthour"),
        rated_power=ActivePower(battery.max_p, "kilowatt"),
        charging_efficiency=battery.charging_efficiency,
        discharging_efficiency=battery.discharging_efficiency,
        idling_efficiency=context.fill("BatteryEquipment.idling_efficiency", fills.BATTERY_IDLING_EFFICIENCY),
        **voltage,
    )
    info = unit.AssetDatasheet
    if isinstance(info, cim.BatteryInfo):
        return shared_equipment(context, info, equipment)
    return equipment.model_copy(update=context.names.part(owner, BatteryEquipment))
