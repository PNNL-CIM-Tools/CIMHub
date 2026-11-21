"""PowerElectronicsConnection -> GLM ``inverter`` + its ``solar`` or ``battery``, parented to its bus
(``EXPORT_MAPPING.md#x4-der``; the importer's S4b inverted where CIM holds the value).

Each PowerElectronicsUnit is one GLM inverter (``get_inverter_units``: one unit is the whole connection, several each
take their maxP share of its ratedS and q), named as the connection, or ``<connection>_<n>`` when it has several.
The inverter is ``FOUR_QUADRANT``: a battery's in ``CONSTANT_PQ`` at CIM's dispatch (``P_Out``/``Q_Out`` in the
generation sign), so GridLAB-D holds that set point; a PV's in ``CONSTANT_PF`` at CIM's power factor (negative when
q is), GridLAB-D's own PV logic (the importer's S4b-1, so the export reads back): GridLAB-D computes the output from
its weather, which is CIM's p on a GLM-origin model and a listed difference otherwise. Its ``rated_power`` is per
phase (``ratedS`` over the phases; a split-phase inverter's whole). A battery child is GridLAB-D's internal model: ``battery_capacity`` ratedE,
``state_of_charge`` storedE / ratedE, ``round_trip_efficiency`` the product of the charging and discharging
efficiencies, ``battery_type`` from its BatteryInfo (lithiumIon or leadAcid; none: LI_ION, logged), and
``nominal_voltage`` unset (its DC voltage has no CIM home yet: the plan's DCConductingAssetInfo TODO, so GridLAB-D
takes its ``battery_type`` default). A solar child's ``rated_power`` is the unit's maxP; GridLAB-D's weather model
gives the DC power the PQ set point draws on. CIM's p already holds the PV losses (the importer folds GridLAB-D's
``derating``, ``soiling`` and ``inverter_efficiency`` into it, S4b-2), so the export writes them 1 (``LOSSLESS``):
GridLAB-D's 0.95, 0.95 and 0.9 defaults would take them off twice, and the set point could not be reached.
"""

from __future__ import annotations

import logging
import math

import cimprofiles.cim18.cim18v17 as cim
from cimtopology.core import System

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.der import (get_battery_unit, get_der_output, get_inverter_rating, get_inverter_units,
                                     get_photovoltaic_unit)
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

_log = logging.getLogger(__name__)

CIM_CLASSES = (cim.PowerElectronicsConnection, cim.PhotoVoltaicUnit, cim.BatteryUnit)
#: BatteryInfo.batteryType -> GLM battery_type (the importer's table inverted)
BATTERY_TYPES = {cim.BatteryTypeKind.lithiumIon: "LI_ION", cim.BatteryTypeKind.leadAcid: "LEAD_ACID"}
DEFAULT_BATTERY_TYPE = "LI_ION"
SIGN = "generation"
#: a PV's loss factors, already in CIM's p (module docstring)
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
        "max_charge_rate": Slot("written", "a battery's -minP"), "max_discharge_rate": Slot("written", "its maxP"),
        "inverter_efficiency": Slot("rule", "a PV's 1: its losses are in CIM's p (LOSSLESS)"),
    }, _UNSET),
    schema.Battery: with_default(schema.Battery, {
        "name": Slot("written", "Names (the BatteryUnit)"), "parent": Slot("written", "its inverter"),
        "use_internal_battery_model": Slot("written", "TRUE"),
        "battery_type": Slot("written", "BatteryInfo.batteryType; none: LI_ION, logged"),
        "battery_capacity": Slot("written", "ratedE (Wh)"),
        "state_of_charge": Slot("written", "storedE / ratedE"),
        "round_trip_efficiency": Slot("written", "chargingEfficiency x dischargingEfficiency"),
        "rated_power": Slot("written", "maxP (W)"),
        "nominal_voltage": Slot("unset", "the DC voltage: TODO through DCConductingAssetInfo (plan section 7)"),
    }, _UNSET),
    schema.Solar: with_default(schema.Solar, {
        "name": Slot("written", "Names (the PhotoVoltaicUnit)"), "parent": Slot("written", "its inverter"),
        "rated_power": Slot("written", "maxP (W)"),
        "derating": Slot("rule", "1: in CIM's p (LOSSLESS)"), "soiling": Slot("rule", "1: in CIM's p (LOSSLESS)"),
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
            slots.update(four_quadrant_control_mode="CONSTANT_PQ", P_Out=share.p, Q_Out=share.q)
        else:
            slots.update(four_quadrant_control_mode="CONSTANT_PF", power_factor=_power_factor(share.p, share.q))
        child = _child(share.unit, name, slots, context)
        records += [schema.Inverter(**slots), child]
    return records


def _child(unit, inverter: str, inverter_slots: dict, context):
    """The unit's GLM solar or battery; a battery also sets its inverter's charge rates."""
    watts = glm_unit(schema.Battery, "rated_power")
    if isinstance(unit, cim.BatteryUnit):
        battery = get_battery_unit(unit, watts, glm_unit(schema.Battery, "battery_capacity"), sign=SIGN)
        if battery.min_p is not None:
            inverter_slots["max_charge_rate"] = -battery.min_p
        inverter_slots["max_discharge_rate"] = battery.max_p
        efficiency = None
        if battery.charging_efficiency is not None and battery.discharging_efficiency is not None:
            efficiency = battery.charging_efficiency * battery.discharging_efficiency / 1e4
        state = None if not battery.rated_e or battery.stored_e is None else battery.stored_e / battery.rated_e
        return schema.Battery(name=context.names.name(unit), parent=inverter, use_internal_battery_model=True,
                              battery_type=_battery_type(unit), battery_capacity=battery.rated_e,
                              state_of_charge=state, round_trip_efficiency=efficiency, rated_power=battery.max_p)
    if isinstance(unit, cim.PhotoVoltaicUnit):
        inverter_slots["inverter_efficiency"] = LOSSLESS
        return schema.Solar(name=context.names.name(unit), parent=inverter, derating=LOSSLESS, soiling=LOSSLESS,
                            rated_power=get_photovoltaic_unit(unit, watts, sign=SIGN).max_p)
    raise ValueError(f"{type(unit).__name__} {unit.mRID!r}: GLM's inverter takes a solar or a battery")


def _power_factor(p: float, q: float) -> float:
    """p / |p + jq|, negative when q is (GridLAB-D's leading sign); 1 at no output."""
    apparent = math.hypot(p, q)
    if apparent == 0:
        return 1.0
    return -abs(p) / apparent if q < 0 else abs(p) / apparent


def _battery_type(unit: cim.BatteryUnit) -> str:
    """BatteryInfo.batteryType as GLM's battery_type; no datasheet: LI_ION, logged (the one default here)."""
    datasheet = unit.AssetDatasheet
    kind = datasheet.batteryType if isinstance(datasheet, cim.BatteryInfo) else None
    if kind is None:
        _log.warning("BatteryUnit %s: no BatteryInfo.batteryType; written as %s", unit.mRID, DEFAULT_BATTERY_TYPE)
        return DEFAULT_BATTERY_TYPE
    if kind not in BATTERY_TYPES:
        raise ValueError(f"BatteryUnit {unit.mRID!r}: batteryType {kind.value} has no GLM battery_type")
    return BATTERY_TYPES[kind]
