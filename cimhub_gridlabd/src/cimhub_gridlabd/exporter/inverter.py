"""PowerElectronicsConnection -> GLM ``inverter`` + its ``solar`` or ``battery``, parented to its bus
(``EXPORT_MAPPING.md#x4-der``; the importer's S4b inverted where CIM holds the value).

Each PowerElectronicsUnit is one GLM inverter (``get_inverter_units``: one unit is the whole connection, several each
take their maxP share of its ratedS, q and charge rate), named as the connection, or ``<connection>_<n>`` when it has
several. The inverter is ``FOUR_QUADRANT``, its ``rated_power`` per phase (``ratedS`` over the phases; a split-phase
inverter's whole).

A battery's is ``CONSTANT_PQ`` at CIM's dispatch (``P_Out``/``Q_Out`` in the generation sign), so GridLAB-D holds
that set point, with ``soc_reserve`` minimumE / ratedE and ``max_charge_rate`` its StorageInverterInfo's
chargeRateActiveMax (``max_discharge_rate`` has no CIM home; both are read by LOAD_FOLLOWING only,
``inverter.cpp:1788``). Its battery child is GridLAB-D's internal model: ``battery_capacity`` ratedE,
``state_of_charge`` storedE / ratedE, ``round_trip_efficiency`` the product of the charging and discharging
efficiencies, ``battery_type`` from its BatteryInfo (unset without one: GridLAB-D's UNKNOWN, as the deck it came
from), and ``nominal_voltage`` unset (its DC voltage has no CIM home yet: the plan's DCConductingAssetInfo TODO, so
GridLAB-D takes its default).

A PV's is ``CONSTANT_PF`` at CIM's power factor (negative when q is), GridLAB-D's own PV logic (the importer's
S4b-1), so GridLAB-D computes the output from its static weather: rated_power x shading_factor x the temperature
factor x derating x soiling x inverter_efficiency (``solar.cpp:1233``, the importer's ``pv_output``). The solar child
carries its datasheets (``tilt_angle``, ``orientation_azimuth``, ``shading_factor`` from the SolarArrayInfo,
``efficiency`` and ``Rated_Insolation`` from its SolarPanelInfo) and ``rated_power`` the unit's maxP. CIM's p already
holds the losses and the module temperature (the importer folds them in, S4b-2) and keeps neither, nor the panel type
and NOCT, which GridLAB-D's temperature factor reads (a 0 ``Pmax_temp_coeff`` is its panel's default,
``solar.cpp:571``). So those stay unset, ``soiling`` and ``inverter_efficiency`` are 1, and ``derating`` carries the
whole loss: p over GridLAB-D's lossless output at its defaults (the importer's ``static_dc_output``), so GridLAB-D's
output, and the re-import's p, is CIM's p. A p above that has no GLM form (GridLAB-D's factors are at most 1,
``solar.cpp:1039``, ``inverter.cpp:1210``) and raises.
"""

from __future__ import annotations

import dataclasses
import math

import cimprofiles.cim18.cim18v17 as cim
from cimtopology.core import System

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.der import (get_battery_unit, get_der_output, get_inverter_datasheet, get_inverter_rating,
                                     get_inverter_units, get_photovoltaic_datasheet, get_photovoltaic_unit)
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.units import from_percent, glm_unit
from cimhub_gridlabd.importer.cimtbl.inverter import static_dc_output  # GridLAB-D's PV formula, once
from cimhub_gridlabd.schema import gridlabd as schema


CIM_CLASSES = (cim.PowerElectronicsConnection, cim.PhotoVoltaicUnit, cim.BatteryUnit)
#: BatteryInfo.batteryType -> GLM battery_type (the importer's table inverted)
BATTERY_TYPES = {cim.BatteryTypeKind.lithiumIon: "LI_ION", cim.BatteryTypeKind.leadAcid: "LEAD_ACID"}
SIGN = "generation"
#: a PV's soiling and inverter efficiency: CIM's p holds them (module docstring)
LOSSLESS = 1.0

_UNSET = Slot("unset", "not in CIM; GridLAB-D's default")
SLOTS = {
    schema.Inverter: with_default(schema.Inverter, {
        "name": Slot("written", "Names; <connection>_<n> for each of several units"),
        "parent": Slot("written", "its bus"),
        "phases": Slot("written", "its letters then N; a split-phase bus's letter then S"),
        "generator_status": Slot("written", "OFFLINE when normallyInService is false, else ONLINE"),
        "inverter_type": Slot("written", "FOUR_QUADRANT"),
        "four_quadrant_control_mode": Slot("written", "a battery's CONSTANT_PQ (CIM's set point), a PV's CONSTANT_PF "
                                                      "(GridLAB-D's PV logic, S4b-1)"),
        "P_Out": Slot("written", "a battery's get_inverter_units p, generation sign"),
        "Q_Out": Slot("written", "a battery's get_inverter_units q, generation sign"),
        "power_factor": Slot("written", "a PV's p / |p + jq|, negative when q is"),
        "rated_power": Slot("written", "ratedS x share / phases (GLM's is per phase)"),
        "soc_reserve": Slot("written", "a battery's minimumE / ratedE"),
        "max_charge_rate": Slot("written", "a battery's StorageInverterInfo.chargeRateActiveMax x share"),
        "inverter_efficiency": Slot("rule", "a PV's 1: its losses are in CIM's p (module docstring)"),
    }, _UNSET),
    schema.Battery: with_default(schema.Battery, {
        "name": Slot("written", "Names (the BatteryUnit)"), "parent": Slot("written", "its inverter"),
        "use_internal_battery_model": Slot("written", "TRUE"),
        "battery_type": Slot("written", "BatteryInfo.batteryType; none: unset (GridLAB-D's UNKNOWN)"),
        "battery_capacity": Slot("written", "ratedE (Wh)"),
        "state_of_charge": Slot("written", "storedE / ratedE"),
        "round_trip_efficiency": Slot("written", "chargingEfficiency x dischargingEfficiency"),
        "rated_power": Slot("written", "maxP (W)"),
        "nominal_voltage": Slot("unset", "the DC voltage: TODO through DCConductingAssetInfo (plan section 7)"),
    }, _UNSET),
    schema.Solar: with_default(schema.Solar, {
        "name": Slot("written", "Names (the PhotoVoltaicUnit)"), "parent": Slot("written", "its inverter"),
        "rated_power": Slot("written", "maxP (W); unset raises"),
        "tilt_angle": Slot("written", "SolarArrayInfo.tiltAngle"),
        "orientation_azimuth": Slot("written", "SolarArrayInfo.orientationAzimuth"),
        "shading_factor": Slot("written", "SolarArrayInfo.shadingFactor"),
        "efficiency": Slot("written", "SolarPanelInfo.efficiency"),
        "Rated_Insolation": Slot("written", "SolarPanelInfo.referenceIrradiation"),
        "derating": Slot("rule", "p / GridLAB-D's lossless output: the whole loss (module docstring)"),
        "soiling": Slot("rule", "1: in CIM's p (module docstring)"),
    }, _UNSET),
}


def export(context) -> list:
    records = []
    for connection in context.objects(cim.PowerElectronicsConnection):
        records += _inverters(connection, context)
    return records


def _inverters(connection: cim.PowerElectronicsConnection, context) -> list:
    [node] = get_terminal_nodes(connection)
    bus = context.buses[node]
    power_unit = glm_unit(schema.Inverter, "P_Out")
    rating = get_inverter_rating(connection, power_unit, sign=SIGN)
    datasheet = get_inverter_datasheet(connection, active_unit=glm_unit(schema.Inverter, "max_charge_rate"))
    charge_rate = None if datasheet is None else datasheet.charge_rate_max
    output = get_der_output(connection, sign=SIGN)
    units = get_inverter_units(connection, glm_unit(schema.Battery, "rated_power"),
                               glm_unit(schema.Inverter, "Q_Out"), sign=SIGN)
    split = bus.system is System.SPLIT_PHASE
    phases = bus.phases if split else letters(output.phases) + "N"
    phase_count = 1 if split else len(letters(output.phases))
    in_service = get_in_service(connection, which="normal")
    records = []
    for number, share in enumerate(units, start=1):
        name = context.names.name(connection, suffix="" if len(units) == 1 else f"_{number}")
        slots = {"name": name, "parent": bus.name, "phases": phases,
                 "generator_status": "OFFLINE" if in_service is False else "ONLINE",
                 "inverter_type": "FOUR_QUADRANT", "rated_power": rating.rated_s * share.share / phase_count}
        if isinstance(share.unit, cim.BatteryUnit):
            slots.update(four_quadrant_control_mode="CONSTANT_PQ", P_Out=share.p, Q_Out=share.q,
                         max_charge_rate=None if charge_rate is None else charge_rate * share.share)
            child = _battery(share.unit, name, slots, context)
        elif isinstance(share.unit, cim.PhotoVoltaicUnit):
            slots.update(four_quadrant_control_mode="CONSTANT_PF", power_factor=_power_factor(share.p, share.q),
                         inverter_efficiency=LOSSLESS)
            child = _solar(share.unit, share.p, name, context)
        else:
            raise ValueError(f"{type(share.unit).__name__} {share.unit.mRID!r}: GLM's inverter takes a solar or a "
                             f"battery")
        records += [schema.Inverter(**slots), child]
    return records


def _battery(unit: cim.BatteryUnit, inverter: str, inverter_slots: dict, context) -> schema.Battery:
    """The unit's GLM battery; its reserve goes on the inverter."""
    battery = get_battery_unit(unit, glm_unit(schema.Battery, "rated_power"),
                               glm_unit(schema.Battery, "battery_capacity"), sign=SIGN)
    if battery.minimum_e is not None and battery.rated_e:
        inverter_slots["soc_reserve"] = battery.minimum_e / battery.rated_e
    efficiency = None
    if battery.charging_efficiency is not None and battery.discharging_efficiency is not None:
        efficiency = (from_percent(battery.charging_efficiency, schema.Battery, "round_trip_efficiency")
                      * from_percent(battery.discharging_efficiency, schema.Battery, "round_trip_efficiency"))
    state = None if not battery.rated_e or battery.stored_e is None else battery.stored_e / battery.rated_e
    return schema.Battery(name=context.names.name(unit), parent=inverter, use_internal_battery_model=True,
                          battery_type=_battery_type(unit), battery_capacity=battery.rated_e,
                          state_of_charge=state, round_trip_efficiency=efficiency, rated_power=battery.max_p)


def _solar(unit: cim.PhotoVoltaicUnit, p: float, inverter: str, context) -> schema.Solar:
    """The unit's GLM solar, its loss in ``derating`` so GridLAB-D's output is CIM's ``p`` (module docstring)."""
    max_p = get_photovoltaic_unit(unit, glm_unit(schema.Solar, "rated_power"), sign=SIGN).max_p
    if max_p is None:
        raise ValueError(f"PhotoVoltaicUnit {unit.mRID!r}: maxP unset; GLM's solar needs its rated_power")
    sheet = get_photovoltaic_datasheet(unit, glm_unit(schema.Solar, "tilt_angle"),
                                       glm_unit(schema.Solar, "Rated_Insolation"))
    slots = {}
    if sheet is not None:
        slots = {"tilt_angle": sheet.tilt, "orientation_azimuth": sheet.azimuth,
                 "shading_factor": from_percent(sheet.shading, schema.Solar, "shading_factor"),
                 "efficiency": from_percent(sheet.panel_efficiency, schema.Solar, "efficiency"),
                 "Rated_Insolation": sheet.reference_irradiance}
    solar = schema.Solar(name=context.names.name(unit), parent=inverter, rated_power=max_p, derating=LOSSLESS,
                         soiling=LOSSLESS, **slots)
    lossless = static_dc_output(solar)
    derating = LOSSLESS if lossless == 0 else p / lossless
    if not 0.0 <= derating <= 1.0:
        raise ValueError(f"PhotoVoltaicUnit {unit.mRID!r}: p {p} W is outside 0..{lossless} W, GridLAB-D's lossless "
                         f"output; its derating is 0..1 (solar.cpp:1039)")
    return dataclasses.replace(solar, derating=derating)


def _power_factor(p: float, q: float) -> float:
    """p / |p + jq|, negative when q is (GridLAB-D's leading sign); 1 at no output."""
    apparent = math.hypot(p, q)
    if apparent == 0:
        return 1.0
    return -abs(p) / apparent if q < 0 else abs(p) / apparent


def _battery_type(unit: cim.BatteryUnit) -> str | None:
    """BatteryInfo.batteryType as GLM's battery_type; None without one (GridLAB-D's UNKNOWN)."""
    datasheet = unit.AssetDatasheet
    kind = datasheet.batteryType if isinstance(datasheet, cim.BatteryInfo) else None
    if kind is None:
        return None
    if kind not in BATTERY_TYPES:
        raise ValueError(f"BatteryUnit {unit.mRID!r}: batteryType {kind.value} has no GLM battery_type")
    return BATTERY_TYPES[kind]
