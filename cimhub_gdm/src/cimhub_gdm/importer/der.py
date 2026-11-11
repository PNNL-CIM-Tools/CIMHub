"""DistributionSolar / DistributionBattery → PowerElectronicsConnection + its unit (GDM_MAPPING.md §20).

Each DER is one PowerElectronicsConnection (``pv_<name>`` or ``storage_<name>``) on its bus, as the DSS wave's
PVSystem and Storage goldens write it: ``ratedS`` from the inverter, ``ratedU`` line-to-line from the equipment
rating, the snapshot ``p`` / ``q`` in the load sign (``injection``: generation and discharge are negative). Its
PhotoVoltaicUnit or BatteryUnit is ``<pec>_unit``. The inverter is an InverterInfo ``inv_<inverter>`` on the
connection's AssetDatasheet (GenerationInverterInfo for PV, StorageInverterInfo for a battery); a battery's
BatteryInfo ``batt_<equipment>`` is on the unit's. GDM names no connection kind for a DER, so ``phaseConnection`` is
not written; a DER on the neutral raises. Inverter controllers are ``PENDING`` (OPEN_DECISIONS 12).
"""

from __future__ import annotations

import logging

from cimbuilder.object_builder import (
    BatteryInfoBuilder,
    BatteryUnitBuilder,
    GenerationInverterInfoBuilder,
    PhotoVoltaicUnitBuilder,
    PowerElectronicsConnectionBuilder,
    StorageInverterInfoBuilder,
)
from cimhub_core.cimtbl import Field
from cimtables.units import Qty
from gdm.systems.distribution.enums import Phase

from cimhub_gdm.importer.shared import (
    POWER_UNIT_ENDINGS,
    UUID_FIELD,
    Naming,
    active_power_unit,
    builder_phases,
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

log = logging.getLogger(__name__)

PV_PREFIX = "pv_"
STORAGE_PREFIX = "storage_"
INVERTER_PREFIX = "inv_"
BATTERY_INFO_PREFIX = "batt_"


def _der_fields(prefix: str, unit: str) -> dict:
    """The FIELDS shared by DistributionSolar and DistributionBattery."""
    return {
        "uuid": UUID_FIELD,
        "name": name_field(prefix),
        "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
        "feeder": Field("structural", note="EquipmentContainer"),
        "in_service": Field("structural", note="False raises: no CIM home"),
        "bus": Field("structural", note="the Terminal's ConnectivityNode; BaseVoltage"),
        "phases": Field("structural", note="PowerElectronicsConnectionPhase children; none for ABC (G3); N raises"),
        "active_power": Field("derived", note="PowerElectronicsConnection p = -active_power (injection)"),
        "reactive_power": Field("derived", note="PowerElectronicsConnection q = -reactive_power (injection)"),
        "controller": Field("structural", note="an InverterController is PENDING (OPEN_DECISIONS 12)"),
        "inverter": Field("structural", note=f"ratedS; InverterInfo {INVERTER_PREFIX}<inverter> on the "
                                             "AssetDatasheet"),
        "equipment": Field("structural", note=f"ratedU; {unit} <pec>_unit"),
    }


FIELDS_DistributionSolar = {
    **_der_fields(PV_PREFIX, "PhotoVoltaicUnit"),
    "irradiance": Field("copied", (("add_ssh", "irradiance", None),),
                        note="PhotoVoltaicUnit.irradiance (B16b); an irradiance series stays dropped (T2)"),
}
FIELDS_DistributionBattery = {
    **_der_fields(STORAGE_PREFIX, "BatteryUnit"),
    "active_power": Field("derived", note="PowerElectronicsConnection p = -active_power (injection); "
                                          "BatteryUnit batteryState from its sign (battery_state)"),
}
FIELDS_SolarEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline; the unit is named after its DER"),
    "rated_power": Field("copied", (("add_electrical", "maxP", None),),
                         note="PhotoVoltaicUnit; a kVA unit (ditto) is taken as kW with a WARNING (panel_power)"),
    "power_temp_curve": Field("untranscribed", note="until the Curve builder (B12, OPEN_DECISIONS 16)"),
    "resistance": Field("untranscribed", note="no CIM home (no PowerElectronicsConnection impedance)"),
    "reactance": Field("untranscribed", note="no CIM home (no PowerElectronicsConnection impedance)"),
    "rated_voltage": Field("derived", note="PowerElectronicsConnection ratedU, line-to-line (system_voltage)"),
    "voltage_type": Field("structural", note="how rated_voltage becomes line-to-line"),
}
FIELDS_BatteryEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(BATTERY_INFO_PREFIX),
    "rated_energy": Field("copied", (("add_electrical", "ratedE", None), ("add_asset_info", "ratedCapacity", None)),
                          note=f"BatteryUnit ratedE; BatteryInfo {BATTERY_INFO_PREFIX}<equipment> ratedCapacity"),
    "rated_power": Field("derived", note="BatteryUnit maxP = rated_power, minP = -rated_power (one rating both ways)"),
    "charging_efficiency": Field("copied", (("add_electrical", "chargingEfficiency", "percent"),)),
    "discharging_efficiency": Field("copied", (("add_electrical", "dischargingEfficiency", "percent"),)),
    "idling_efficiency": Field("untranscribed", note="no CIM home: BatteryUnit idlingP is a power"),
    "rated_voltage": Field("derived", note="PowerElectronicsConnection ratedU, line-to-line (system_voltage)"),
    "voltage_type": Field("structural", note="how rated_voltage becomes line-to-line"),
}
FIELDS_InverterEquipment = {
    "uuid": UUID_FIELD,
    "name": name_field(INVERTER_PREFIX),
    "rated_apparent_power": Field("copied", (("add_electrical", "ratedS", None),
                                             ("add_asset_info", "apparentPowerMaximum", None)),
                                  note="PowerElectronicsConnection ratedS; InverterInfo apparentPowerMaximum"),
    "rise_limit": Field("untranscribed", note="no InverterInfo slot"),
    "fall_limit": Field("untranscribed", note="no InverterInfo slot"),
    "cutout_percent": Field("untranscribed", note="no InverterInfo slot"),
    "cutin_percent": Field("untranscribed", note="no InverterInfo slot"),
    "dc_to_ac_efficiency": Field("untranscribed", note="no InverterInfo slot"),
    "eff_curve": Field("untranscribed", note="until the Curve builder (B12, OPEN_DECISIONS 16)"),
}


def add_solar(network, solar, naming: Naming) -> None:
    """A PowerElectronicsConnection ``pv_<name>`` with its PhotoVoltaicUnit."""
    label = f"DistributionSolar {solar.name!r}"
    pec = add_connection(network, solar, PV_PREFIX, GenerationInverterInfoBuilder, naming, label)
    builder = PhotoVoltaicUnitBuilder(network, network.container)
    unit = builder.create(mRID=f"{pec}_unit", name=solar.name)
    builder.add_electrical(unit, maxP=panel_power(solar.equipment.rated_power, label),
                           PowerElectronicsConnection=pec)
    builder.add_ssh(unit, irradiance=qty(solar.irradiance))


def panel_power(rated_power, label: str) -> Qty:
    """The panel's rated_power (its Pmpp). ditto's PVSystem reader writes it as an ActivePower in kVA
    (GDM_MAPPING.md §14), so an apparent unit is taken as the same active one, with a WARNING (user, 2026-11-08)."""
    if not str(rated_power.units).endswith(POWER_UNIT_ENDINGS["apparent"]):
        return power_qty(rated_power, "active", label=label)
    apparent = power_qty(rated_power, "apparent", label=label)
    active = Qty(apparent.value, active_power_unit(apparent))
    log.warning("%s: SolarEquipment rated_power %s is in an apparent power unit (ditto's PVSystem reader); taken as "
                "%s %s", label, rated_power, active.value, active.unit)
    return active


def add_battery(network, battery, naming: Naming) -> None:
    """A PowerElectronicsConnection ``storage_<name>`` with its BatteryUnit and BatteryInfo."""
    label = f"DistributionBattery {battery.name!r}"
    equipment = battery.equipment
    pec = add_connection(network, battery, STORAGE_PREFIX, StorageInverterInfoBuilder, naming, label)
    rated_power = power_qty(equipment.rated_power, "active", label=label)
    builder = BatteryUnitBuilder(network, network.container)
    unit = builder.create(mRID=f"{pec}_unit", name=battery.name)
    builder.add_electrical(unit, maxP=rated_power, minP=negated(rated_power),
                           ratedE=qty(equipment.rated_energy),
                           chargingEfficiency=Qty(equipment.charging_efficiency, "percent"),
                           dischargingEfficiency=Qty(equipment.discharging_efficiency, "percent"),
                           PowerElectronicsConnection=pec)
    builder.add_ssh(unit, batteryState=battery_state(battery.active_power))
    builder.add_asset_datasheet(unit, AssetDatasheet=battery_info(network, equipment, naming))


def add_connection(network, der, prefix: str, info_builder, naming: Naming, label: str) -> str:
    """The DER's PowerElectronicsConnection on its bus, with its inverter's InverterInfo. Returns its mRID."""
    require_in_service(der)
    if Phase.N in der.phases:
        raise ValueError(f"{label}: phases {[p.value for p in der.phases]}: a DER on the neutral has no "
                         "PowerElectronicsConnectionPhase")
    equipment = der.equipment
    builder = PowerElectronicsConnectionBuilder(network, network.container)
    pec = builder.create(mRID=object_mrid(prefix, der, "PowerElectronicsConnection", naming), name=der.name)
    builder.add_connectivity(pec, node=bus_mrid(der.bus, naming), phases=builder_phases(der.phases),
                             EquipmentContainer=container_mrid(der, naming), BaseVoltage=bus_base_voltage(der.bus))
    builder.add_electrical(pec, ratedS=power_qty(der.inverter.rated_apparent_power, "apparent", label=label),
                           ratedU=qty(system_voltage(equipment.rated_voltage, equipment.voltage_type, der.phases)))
    builder.add_ssh(pec, p=injection(der.active_power, "active", label),
                    q=injection(der.reactive_power, "reactive", label))
    builder.add_asset_datasheet(pec, AssetDatasheet=inverter_info(network, der.inverter, info_builder, naming))
    return pec.mRID


def injection(power, kind: str, label: str) -> Qty:
    """A GDM output (positive = into the network) in the CIM load sign (positive = out of the node): negated."""
    return negated(power_qty(power, kind, label=label))


def negated(value: Qty) -> Qty:
    """``-value``, in its own unit (``0.0 - v``, so zero stays 0.0, not -0.0)."""
    return Qty(0.0 - value.value, value.unit)


def battery_state(active_power) -> str:
    """BatteryStateKind from the snapshot output: discharging above zero, charging below, waiting at zero."""
    magnitude = float(active_power.magnitude)
    if magnitude > 0:
        return "discharging"
    if magnitude < 0:
        return "charging"
    return "waiting"


def inverter_info(network, inverter, info_builder, naming: Naming) -> str:
    """The inverter's InverterInfo ``inv_<inverter>``, built the first time a DER names it. An inverter shared by a
    PV and a battery raises: it would be a GenerationInverterInfo and a StorageInverterInfo at once."""
    info_mrid = object_mrid(INVERTER_PREFIX, inverter, info_builder.cim_class_name, naming)
    existing = network.find_by_mRID(info_mrid)
    if existing is not None:
        if type(existing).__name__ != info_builder.cim_class_name:
            raise ValueError(f"InverterEquipment {inverter.name!r}: shared by a PV and a battery; it is one "
                             f"{type(existing).__name__} or one {info_builder.cim_class_name}")
        return info_mrid
    builder = info_builder(network, network.container)
    info = builder.create(mRID=info_mrid, name=inverter.name or None)  # GDM's default inverter name is ''
    builder.add_asset_info(info, apparentPowerMaximum=power_qty(inverter.rated_apparent_power, "apparent",
                                                                label=f"InverterEquipment {inverter.name!r}"))
    return info_mrid


def battery_info(network, equipment, naming: Naming) -> str:
    """The battery equipment's BatteryInfo ``batt_<equipment>``, built the first time a battery names it."""
    info_mrid = object_mrid(BATTERY_INFO_PREFIX, equipment, "BatteryInfo", naming)
    if network.find_by_mRID(info_mrid) is None:
        builder = BatteryInfoBuilder(network, network.container)
        info = builder.create(mRID=info_mrid, name=equipment.name)
        builder.add_asset_info(info, ratedCapacity=qty(equipment.rated_energy))
    return info_mrid
