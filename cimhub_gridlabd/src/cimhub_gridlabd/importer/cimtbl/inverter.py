"""GLM ``inverter`` with its nested ``solar`` or ``battery`` -> ``inverter.cimtbl`` (S4b).

One ``PowerElectronicsConnection`` per inverter on its parent's root bus (GLM-4), with its one unit: a
``PhotoVoltaicUnit`` or a ``BatteryUnit``. The datasheets go on ``AssetDatasheet``: a ``GenerationInverterInfo`` or
``StorageInverterInfo`` on the connection, a ``SolarArrayInfo`` (with its ``SolarPanelInfo``) on a PV unit, and a
``BatteryInfo`` on a battery. GridLAB-D has no delta inverter. On A, B and C it is wye to neutral; split phase sits
across the legs at 240 V, which is ``s1s2`` D (S4b-4). ``ratedU`` is the bus's line-to-line nominal (S4b-5).

The dispatch is GridLAB-D's own (S4b-2, the user's call):
- **PV:** the static-weather output of a ``CONSTANT_PF`` inverter (``pv_output``). The written ``P_Out`` is an
  output GridLAB-D overwrites, so it only goes in the row comment.
- **Battery:** the ``CONSTANT_PQ`` set point ``P_Out`` (``battery_output``). A battery whose inverter says
  ``CONSTANT_PF`` is a Java export defect: GridLAB-D would never dispatch it. It is read as ``CONSTANT_PQ``, the mode
  the export meant, with a row comment.

Every other inverter type and mode raises (S4b-1). cim-tables cannot yet reference an ``Identity`` row, so the mode's
``InverterCapabilities`` flag (S4b-11) goes in the row comment until it can (plan section 7).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s4b-inverters-solar-and-batteries``.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from cimprofiles.units import units
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem, nominal_kv

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, field_names, fill_defaults, mrid, phases_cell, \
    untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import label
from cimhub_gridlabd.importer.cimtbl.link import provenance
from cimhub_gridlabd.schema import gridlabd as schema

NATIVE_CLASS = schema.Inverter
ANCHOR = "s4b-inverters-solar-and-batteries"
#: the connection's mRID prefix by its unit, as the DSS import's ``pv_``/``storage_`` (S4b-6)
PREFIXES = {schema.Solar: "pv_", schema.Battery: "storage_"}
_CONNECTION = "PowerElectronicsConnection"
_NOT_MAPPED = "raises when set: no deck sets it, so a mapping waits for one"

#: GridLAB-D's ``inverter::create()``/``init()`` values for the slots each unit's path reads (``inverter.cpp:433-600``,
#: ``:1342``, ``:1398``: an unset, 0 or negative ``inverter_efficiency`` is 0.9).
DEFAULTS = {"four_quadrant_control_mode": "CONSTANT_PF", "generator_status": "ONLINE"}
PATH_DEFAULTS = {schema.Solar: {**DEFAULTS, "inverter_efficiency": 0.9, "power_factor": 1.0},
                 schema.Battery: {**DEFAULTS, "P_Out": 0.0, "Q_Out": 0.0, "soc_reserve": 0.0}}
#: ``solar::create()`` values (``solar.cpp:160-205``); ``Rated_Insolation`` 92.902 W/sf is 1000 W/m^2.
SOLAR_DEFAULTS = {"panel_type": "SINGLE_CRYSTAL_SILICON", "NOCT": 118.4, "Rated_Insolation": 92.902,
                  "shading_factor": 1.0, "soiling": 0.95, "derating": 0.95, "tilt_angle": 45.0,
                  "orientation_azimuth": 180.0}
#: ``battery::init()``: an unset round-trip efficiency or nominal voltage (``battery.cpp:694-708``).
BATTERY_DEFAULTS = {"round_trip_efficiency": 0.8, "nominal_voltage": 115.0}
#: ``panel_type`` -> (efficiency, Pmax_temp_coeff per degF) when unset (``solar.cpp:559-598``).
PANELS = {"SINGLE_CRYSTAL_SILICON": (0.2, -0.00437 / 33.8), "MULTI_CRYSTAL_SILICON": (0.15, -0.00416 / 33.8),
          "AMORPHOUS_SILICON": (0.07, 0.1745 / 33.8), "THIN_FILM_GA_AS": (0.3, 0.0), "CONCENTRATOR": (0.15, 0.0)}
#: GridLAB-D's static weather with no climate object (``solar.cpp:321``) and its rating point, degF.
STATIC_AMBIENT_F = 59.0
RATED_MODULE_F = 77.0
#: ``four_quadrant_control_mode`` as read -> its ``InverterCapabilities`` flags (S4b-11).
CAPABILITIES = {"CONSTANT_PF": ("isModeCapableConstantPowerFactor",),
                "CONSTANT_PQ": ("isModeCapableActivePowerReactivePower",),
                "VOLT_VAR": ("isModeCapableVoltageReactivePower",),
                "VOLT_WATT": ("isModeCapableVoltageActivePower",),
                "VOLT_VAR_FREQ_PWR": ("isModeCapableVoltageReactivePower", "isModeCapableFrequencyActivePower")}
#: ``battery_type`` -> ``BatteryInfo.batteryType``
BATTERY_TYPES = {"LI_ION": "lithiumIon", "LEAD_ACID": "leadAcid"}
#: a Li-ion cell's voltage: GridLAB-D's ``n_series`` = floor(nominal_voltage / 4.1) (``battery.cpp:720``)
LI_ION_CELL_V = 4.1

_HEADER = ("groupid", "latitude", "longitude", "in_svc", "out_svc", "rank", "flags")


def _classify(native_cls: type, own: dict[str, Field], groups: tuple[tuple[str, tuple[str, ...]], ...]):
    """``FIELDS`` of one class: ``own``, then each untranscribed group (note, slots or ``prefix*``), in schema order.
    Raises on a slot nothing claims, so a new schema slot is never silently untranscribed."""
    fields = dict(own)
    for slot in field_names(native_cls):
        if slot in fields:
            continue
        note = next((note for note, names in groups
                     if slot in names or any(name.endswith("*") and slot.startswith(name[:-1]) for name in names)),
                    None)
        if note is None:
            raise ValueError(f"{native_cls.__name__}.{slot} is not classified (importer/cimtbl/inverter.py)")
        fields[slot] = Field("untranscribed", note=note)
    return {slot: fields[slot] for slot in field_names(native_cls)}


FIELDS = _classify(NATIVE_CLASS, {
    "name": Field("derived", note="PowerElectronicsConnection.name; mRID pv_/storage_ + name by its unit (S4b-6)"),
    "parent": Field("structural", note="node: the parent's root bus (GLM-4)"),
    "phases": Field("structural", note="A, B, C wye to neutral (3 phases: blank); S: s1s2 D across the legs at 240 V "
                                       "(S4b-4). GridLAB-D has no D keyword on an inverter"),
    "inverter_type": Field("structural", note="FOUR_QUADRANT; any other raises, unset is GridLAB-D's PWM "
                                              "(inverter.cpp:1350) (S4b-1)"),
    "four_quadrant_control_mode": Field("structural", note="CONSTANT_PF on a solar, CONSTANT_PQ on a battery, which "
                                                           "also reads CONSTANT_PF as the Java defect (S4b-2); others "
                                                           "raise; the capability flag goes in the row comment"),
    "generator_status": Field("derived", note="normallyInService: ONLINE (default) true; OFFLINE false, output 0 "
                                              "(inverter.cpp:2561)"),
    "rated_power": Field("derived", note="ratedS = rated_power x phases out (3, 2, 1; S is 1, inverter.cpp:1318); "
                                         "maxQ = -minQ = apparentPowerMaximum = ratedS; unset or 0 raises "
                                         "(GridLAB-D's silent 25 kVA, :1409)"),
    "inverter_efficiency": Field("derived", note="PV: AC = DC x inverter_efficiency (inverter.cpp:3290); unset, 0 "
                                                 "or negative is 0.9 (:1398); CIM has no inverter efficiency"),
    "P_Out": Field("derived", note="battery: the CONSTANT_PQ set point (S4b-2); PV: an output GridLAB-D overwrites "
                                   "(inverter.cpp:3879), listed in the row comment"),
    "Q_Out": Field("derived", note="CONSTANT_PQ: q = 0 when unset or 0; any other value raises (S4b-3)"),
    "power_factor": Field("derived", note="CONSTANT_PF: q = 0 when |pf| = 1; |pf| < 1 raises (S4b-3); not read by "
                                          "CONSTANT_PQ (a battery read as CONSTANT_PQ lists it in the row comment)"),
    "soc_reserve": Field("derived", note="BatteryUnit.minimumE = soc_reserve x battery_capacity; the battery does not "
                                         "discharge at or below it; default 0"),
    "max_charge_rate": Field("copied", (("StorageInverterInfo", "chargeRateActiveMax", "W"),),
                             "nameplate; GridLAB-D reads it only in load following"),
    "use_multipoint_efficiency": Field("structural", note="FALSE (default); TRUE raises (no deck)"),
    "pf_reg": Field("structural", note="EXCLUDED (default); power-factor regulation " + _NOT_MAPPED),
}, (
    ("object header", _HEADER),
    ("read only by the volt-var and volt-watt modes (inverter.cpp:318), which raise; ratedU is the bus's line-to-line "
     "voltage (S4b-5)", ("V_base",)),
    ("read only by load following and the group modes, which raise", (
        "sense_object", "max_discharge_rate", "charge_on_threshold", "charge_off_threshold", "discharge_on_threshold",
        "discharge_off_threshold", "charge_lockout_time", "discharge_lockout_time", "charge_threshold",
        "discharge_threshold", "group_max_charge_rate", "group_max_discharge_rate", "group_rated_power",
        "lf_dispatch_power", "load_follow_status", "lf_dispatch_change_allowed", "next_update_time",
        "excess_input_power")),
    ("read only by the non-four-quadrant types (inverter.cpp:1337), which raise", ("generator_mode",)),
    ("read only by power-factor regulation (pf_reg), which raises", ("pf_reg_*", "pf_target")),
    ("read only by the volt-var, volt-watt and frequency-power modes, which raise", (
        "V1", "V2", "V3", "V4", "Q1", "Q2", "Q3", "Q4", "VW_*", "volt_var_*", "disable_volt_var_if_no_input_power",
        "delay_time", "max_var_slew_rate", "max_pwr_slew_rate", "freq_pwr_sched", "m12", "b12", "m23", "b23", "m34",
        "b34", "allowed_vv_action", "last_vv_check", "pa_vw_limited", "pb_vw_limited", "pc_vw_limited")),
    ("read only by the multipoint efficiency model, which raises", (
        "inverter_manufacturer", "maximum_dc_power", "maximum_dc_voltage", "minimum_dc_power", "c_0", "c_1", "c_2",
        "c_3")),
    ("deltamode, VSI, droop and IEEE 1547 trip settings: dynamics, not the steady-state snapshot", (
        "inverter_convergence_criterion", "current_convergence", "e_source_*", "V_angle_*", "phaseA_I_Forming",
        "phaseB_I_Forming", "phaseC_I_Forming", "phaseA_I_Following", "phaseB_I_Following", "phaseC_I_Following",
        "pCircuit_V_Avg", "Pref", "Qref", "kpd", "kpq", "kid", "kiq", "kdd", "kdq", "epA", "epB", "epC", "eqA", "eqB",
        "eqC", "delta_*", "mdA", "mdB", "mdC", "mqA", "mqB", "mqC", "IdqA", "IdqB", "IdqC", "Tfreq_delay",
        "inverter_droop_*", "R_fp", "R_vq", "kppmax", "kipmax", "Pmax", "Pmin", "Pmax_Low_Limit", "Tvol_delay",
        "Tp_delay", "Tq_delay", "VSI_*", "ki_Vterminal", "kp_Vterminal", "V_set*", "enable_ramp_rates_*",
        "max_ramp_*", "dynamic_model_mode", "enable_1547_checks", "reconnect_time", "inverter_1547_status",
        "IEEE_1547_*", "over_freq_*", "under_freq_*", "over_voltage_*", "under_voltage_*",
        "out_of_violation_time_total", "deltamode_inclusive", "first_sync_delta_enabled", "first_iter_counter",
        "event_deltat", "nominal_frequency", "islanded_state")),
    ("solver state or output", (
        "V_In", "I_In", "P_In", "VA_Out", "Vdc", "phaseA_V_Out", "phaseB_V_Out", "phaseC_V_Out", "phaseA_I_Out",
        "phaseB_I_Out", "phaseC_I_Out", "power_A", "power_B", "power_C", "curr_VA_out_*", "prev_VA_out_*", "power_in",
        "rated_battery_power", "battery_soc", "number_of_phases_out", "efficiency_value", "WT_is_connected",
        "last_current_*", "last_power_*", "inverter_first_step", "first_iteration_current_injection", "prev_time",
        "prev_time_dbl", "start_time", "last_I_Out_*", "last_I_In", "first_run", "prev_value_IGenerated_*")),
))

SOLAR_FIELDS = _classify(schema.Solar, {
    "name": Field("derived", note="PhotoVoltaicUnit.name; mRID <connection>_unit"),
    "parent": Field("structural", note="its inverter; another parent raises"),
    "rated_power": Field("derived", note="maxP (W via pint), minP 0, and the DC output (S4b-2); unset raises "
                                         "(GridLAB-D derives it from area and insolation, solar.cpp:606)"),
    "Rated_Insolation": Field("derived", note="SolarPanelInfo.referenceIrradiation; the irradiance = Rated_Insolation "
                                              "x shading_factor (solar.cpp:1170); default 92.902 W/sf = 1000 W/m^2"),
    "shading_factor": Field("derived", note="SolarArrayInfo.shadingFactor (percent) and the irradiance; default 1"),
    "NOCT": Field("derived", note="the module temperature (S4b-2); default 118.4 degF"),
    "Pmax_temp_coeff": Field("derived", note="per degF, the DC output's temperature factor; default by panel_type"),
    "panel_type": Field("derived", note="the defaults of efficiency and Pmax_temp_coeff (solar.cpp:559); default "
                                        "SINGLE_CRYSTAL_SILICON"),
    "derating": Field("derived", note="a factor of the DC output; default 0.95; outside 0..1 raises"),
    "soiling": Field("derived", note="a factor of the DC output; default 0.95; outside 0..1 raises"),
    "efficiency": Field("copied", (("SolarPanelInfo", "efficiency", "percent"),), "default by panel_type"),
    "tilt_angle": Field("copied", (("SolarArrayInfo", "tiltAngle", "deg"),), "default 45"),
    "orientation_azimuth": Field("copied", (("SolarArrayInfo", "orientationAzimuth", "deg"),), "default 180"),
    "area": Field("structural", note=_NOT_MAPPED + " (with efficiency it can override rated_power, solar.cpp:624)"),
    "weather": Field("structural", note="unset, with no climate object in the model; a climate raises (S4b-2)"),
    "SOLAR_POWER_MODEL": Field("structural", note="DEFAULT (BASEEFFICIENT); others raise"),
    "orientation": Field("structural", note="DEFAULT; others raise (FIXED_AXIS needs a climate, solar.cpp:325)"),
}, (
    ("object header", _HEADER),
    ("read only with a climate object, which raises", ("SOLAR_TILT_MODEL", "latitude_angle_fix")),
    ("read only by the PV_CURVE and FLATPLATE models, which raise", (
        "pvc_*", "t_ref_cels", "S_ref_wpm2", "MAX_NR_ITERATIONS", "x0_root_rt", "DOA_NR_ITERATIONS", "a_coeff",
        "b_coeff", "dT_coeff", "T_coeff")),
    ("DC voltage and current: CIM has no DC array model", ("Voc_temp_coeff", "V_Max", "Voc_Max", "Voc",
                                                            "Rinternal")),
    ("with no climate GridLAB-D uses 59 degF and still air (solar.cpp:321)", ("ambient_temperature", "wind_speed")),
    ("solver state or output", (
        "Tmodule", "Tambient", "Insolation", "Tcell", "P_Out", "V_Out", "I_Out", "default_*", "prevTemp", "currTemp",
        "prevTime", "last_DC_current", "last_DC_power")),
))

BATTERY_FIELDS = _classify(schema.Battery, {
    "name": Field("derived", note="BatteryUnit.name; mRID <connection>_unit"),
    "parent": Field("structural", note="its inverter (GridLAB-D requires one, battery.cpp:657); another raises"),
    "use_internal_battery_model": Field("structural", note="true; false (the legacy model) raises"),
    "battery_capacity": Field("derived", note="ratedE and BatteryInfo.ratedCapacity (Wh via pint); unset raises"),
    "state_of_charge": Field("derived", note="storedE = state_of_charge x battery_capacity; unset raises"),
    "rated_power": Field("derived", note="maxP = rated_power, minP = -rated_power (the generation sign)"),
    "round_trip_efficiency": Field("derived", note="chargingEfficiency = dischargingEfficiency = sqrt of it, percent "
                                                   "(battery.cpp:2220); default 0.8"),
    "battery_type": Field("derived", note="BatteryInfo.batteryType: LI_ION lithiumIon, LEAD_ACID leadAcid; others "
                                          "blank"),
    "nominal_voltage": Field("derived", note="BatteryInfo.numberOfCells = floor(nominal_voltage / 4.1) on LI_ION "
                                             "(battery.cpp:720); default 115 V"),
    "rfb_size": Field("structural", note=_NOT_MAPPED + " (it overrides the battery's ratings, battery.cpp:661)"),
}, (
    ("object header", _HEADER),
    ("read only by the legacy battery model (use_internal_battery_model false), which raises", (
        "generator_mode", "additional_controls", "generator_status", "power_type", "battery_state",
        "number_battery_state_changes", "monitored_power", "power_set_*", "check_power_*", "voltage_set_*",
        "deadband", "sensitivity", "high_temperature", "midpoint_temperature", "low_temperature", "scheduled_power",
        "Rinternal", "V_Max", "I_Max", "E_Max", "P_Max", "power_factor", "Energy", "efficiency", "base_efficiency",
        "parasitic_power_draw")),
    ("set from the inverter's soc_reserve (battery.cpp:727)", ("reserve_state_of_charge",)),
    ("solver state or output", (
        "V_Out", "I_Out", "VA_Out", "I_In", "V_Internal", "I_Internal", "I_Prev", "power_transferred", "battery_load",
        "state_change_time_delta", "margin", "E_Next", "recalculate", "prev_time", "first_time_step", "prev_state",
        "internal_battery_load", "value_*", "parent_is_*", "climate_object_found")),
))

CLASSIFIED = {NATIVE_CLASS: FIELDS, schema.Solar: SOLAR_FIELDS, schema.Battery: BATTERY_FIELDS}


def _quantity(model: GlmModel, record, slot: str, unit: str) -> float:
    """``slot`` of ``record`` in ``unit``, from the unit it is written in."""
    return units.Quantity(float(getattr(record, slot)), registry_unit(model.unit(record, slot))).to(unit).magnitude


# -- GridLAB-D's output --------------------------------------------------------------------------------------------

class PvOutput(NamedTuple):
    irradiance: float  # W/m^2, the insolation the panel sees
    module_f: float  # degF
    dc: float  # W


def pv_output(model: GlmModel, solar) -> PvOutput:
    """GridLAB-D's static-weather DC output of a ``solar`` (defaults filled), BASEEFFICIENT with no climate object
    (``solar.cpp:1170``, ``:1218-1222``): insolation = Rated_Insolation x shading_factor, Tmodule = 59 degF + (NOCT -
    68) / 74.32 x insolation (W/sf), P = rated_power x insolation / Rated_Insolation x (1 + Pmax_temp_coeff x
    (Tmodule - 77)) x derating x soiling."""
    rated = _quantity(model, solar, "Rated_Insolation", "W/ft**2")
    insolation = rated * float(solar.shading_factor)
    module_f = STATIC_AMBIENT_F + (_quantity(model, solar, "NOCT", "degF") - 68.0) / 74.32 * insolation
    factor = 1.0 + float(solar.Pmax_temp_coeff) * (module_f - RATED_MODULE_F)
    dc = (_quantity(model, solar, "rated_power", "W") * insolation / rated * factor * float(solar.derating)
          * float(solar.soiling))
    return PvOutput(units.Quantity(insolation, "W/ft**2").to("W/m**2").magnitude, module_f, dc)


def static_dc_output(solar) -> float:
    """``pv_output``'s DC watts of a ``solar`` written in its schema's units, its unset slots at GridLAB-D's defaults
    (the exporter's derating, so GridLAB-D's output is CIM's p)."""
    filled, _ = fill_defaults(SOLAR_FIELDS, solar, _solar_defaults(solar))
    return pv_output(GlmModel(), filled).dc


def battery_output(set_point: float, soc: float, soc_reserve: float, rated_s: float) -> float:
    """GridLAB-D's CONSTANT_PQ output of a battery inverter, W, generation positive (``inverter.cpp:3485-3540``):
    the set point, 0 when charging a full battery or discharging at or below the reserve, capped at ratedS."""
    if (soc >= 1.0 and set_point < 0) or (soc <= soc_reserve and set_point > 0):
        return 0.0
    return math.copysign(min(abs(set_point), rated_s), set_point)


def battery_state(p_load: float) -> str:
    """``BatteryStateKind`` from the load-sign p (S4b-8)."""
    if p_load < 0:
        return "discharging"
    if p_load > 0:
        return "charging"
    return "waiting"


# -- one inverter ---------------------------------------------------------------------------------------------------

def unit_of(model: GlmModel, inverter):
    """The inverter's one solar or battery; none, several, or both raise (a hybrid, S4b-6)."""
    children = [record for cls in PREFIXES for record in model.list_by_class(cls)
                if str(record.parent) == str(inverter.name)]
    if len(children) != 1:
        raise ValueError(f"{label(inverter)}: has {len(children)} solar or battery children; one is mapped (S4b-6)")
    return children[0]


def phases_out(inverter) -> tuple[str, str, int]:
    """``(phases, phaseConnection, GridLAB-D's number_of_phases_out)`` (S4b-4; ``inverter.cpp:1318-1326``)."""
    written = str(inverter.phases or "")
    if set(written) - set("ABCNS"):
        raise ValueError(f"{label(inverter)}: phases {inverter.phases}; A, B, C, N and S are an inverter's")
    if "S" in written:
        return "s1s2", "D", 1
    letters = "".join(letter for letter in "ABC" if letter in written)
    if not letters:
        raise ValueError(f"{label(inverter)}: phases {inverter.phases or 'unset'}; no phase")
    return letters, "Y", len(letters)


def check(inverter) -> None:
    """The inverter types and modes not mapped (S4b-1)."""
    if str(inverter.inverter_type) != "FOUR_QUADRANT":
        raise ValueError(f"{label(inverter)}: inverter_type {inverter.inverter_type or 'unset (PWM)'}; FOUR_QUADRANT "
                         "is mapped (S4b-1)")
    if inverter.use_multipoint_efficiency:
        raise ValueError(f"{label(inverter)}: use_multipoint_efficiency TRUE; not mapped")
    if inverter.pf_reg is not None and str(inverter.pf_reg) != "EXCLUDED":
        raise ValueError(f"{label(inverter)}: pf_reg {inverter.pf_reg}; not mapped")


def check_solar(model: GlmModel, solar) -> None:
    for slot, allowed in (("SOLAR_POWER_MODEL", "DEFAULT"), ("orientation", "DEFAULT")):
        if getattr(solar, slot) is not None and str(getattr(solar, slot)) != allowed:
            raise ValueError(f"{label(solar)}: {slot} {getattr(solar, slot)}; {allowed} is mapped (S4b-2)")
    if solar.weather is not None or model.not_read.get("climate"):  # the schema has no climate class
        raise ValueError(f"{label(solar)}: a climate object; only GridLAB-D's static weather is mapped (S4b-2)")
    if solar.area is not None:
        raise ValueError(f"{label(solar)}: area {solar.area}; not mapped")
    if not solar.rated_power:
        raise ValueError(f"{label(solar)}: rated_power unset or 0; not mapped")
    for slot in ("derating", "soiling"):
        if not 0.0 <= float(getattr(solar, slot)) <= 1.0:
            raise ValueError(f"{label(solar)}: {slot} {getattr(solar, slot)} is outside 0..1 (solar.cpp:1023)")


def check_battery(battery) -> None:
    if not battery.use_internal_battery_model:
        raise ValueError(f"{label(battery)}: use_internal_battery_model false; the legacy model is not mapped")
    if battery.rfb_size is not None:
        raise ValueError(f"{label(battery)}: rfb_size {battery.rfb_size}; not mapped")
    for slot in ("battery_capacity", "state_of_charge", "rated_power"):
        if getattr(battery, slot) is None:
            raise ValueError(f"{label(battery)}: {slot} unset; not mapped")


def _solar_defaults(solar) -> dict[str, object]:
    efficiency, coefficient = PANELS.get(str(solar.panel_type or SOLAR_DEFAULTS["panel_type"]), (0.10, 0.0))
    return {**SOLAR_DEFAULTS, "efficiency": efficiency, "Pmax_temp_coeff": coefficient}


class _Rows:
    def __init__(self):
        self.generation_infos: list[Row] = []
        self.storage_infos: list[Row] = []
        self.arrays: list[Row] = []
        self.panels: list[Row] = []
        self.battery_infos: list[Row] = []
        self.connections: list[Row] = []
        self.pv_units: list[Row] = []
        self.battery_units: list[Row] = []


def _comment(*parts: str | None) -> str | None:
    return "\n".join(part for part in parts if part) or None


def _inverter(model: GlmModel, inverter, roots: dict[str, str], buses: dict[str, BusSystem], rows: _Rows) -> None:
    written_pf = inverter.power_factor
    unit = unit_of(model, inverter)
    inverter, defaulted = fill_defaults(FIELDS, inverter, PATH_DEFAULTS[type(unit)])
    check(inverter)
    if str(inverter.parent) not in roots:
        raise ValueError(f"{label(inverter)}: parent {inverter.parent or 'unset'} is not a bus object")
    node = roots[str(inverter.parent)]
    phases, connection, count = phases_out(inverter)
    if not inverter.rated_power:
        raise ValueError(f"{label(inverter)}: rated_power unset or 0; GridLAB-D would use 25 kVA per phase "
                         "(inverter.cpp:1409)")
    rated_s = _quantity(model, inverter, "rated_power", "VA") * count
    rated_u = units.Quantity(nominal_kv(buses[node].kv), "kV").to("V").magnitude
    online = str(inverter.generator_status) == "ONLINE"
    mode = str(inverter.four_quadrant_control_mode)
    connection_mrid = mrid(PREFIXES[type(unit)], inverter.name)
    notes = []
    if isinstance(unit, schema.Solar):
        if mode != "CONSTANT_PF":
            raise ValueError(f"{label(inverter)}: four_quadrant_control_mode {mode} on a solar; CONSTANT_PF is mapped "
                             "(S4b-1)")
        if abs(float(inverter.power_factor)) != 1.0:
            raise ValueError(f"{label(inverter)}: power_factor {inverter.power_factor}; |pf| < 1 is not mapped "
                             "(S4b-3)")
        unit, unit_defaulted = fill_defaults(SOLAR_FIELDS, unit, _solar_defaults(unit))
        check_solar(model, unit)
        output = pv_output(model, unit)
        efficiency = float(inverter.inverter_efficiency)
        if efficiency <= 0:
            efficiency = PATH_DEFAULTS[schema.Solar]["inverter_efficiency"]
            notes.append(f"inverter_efficiency {cell(inverter.inverter_efficiency)} is GridLAB-D's {cell(efficiency)} "
                         "(inverter.cpp:1398)")
        generation = min(output.dc * efficiency, rated_s) if online else 0.0
        written = "unset" if inverter.P_Out is None else f"{cell(inverter.P_Out)} {model.unit(inverter, 'P_Out')}"
        notes.append(f"P_Out as written (GridLAB-D recomputes it, S4b-2): {written}; GridLAB-D's: DC "
                     f"{cell(round(output.dc, 3))} W at Tmodule {cell(round(output.module_f, 3))} degF")
    else:
        unit, unit_defaulted = fill_defaults(BATTERY_FIELDS, unit, BATTERY_DEFAULTS)
        check_battery(unit)
        if mode == "CONSTANT_PF":
            notes.append("four_quadrant_control_mode CONSTANT_PF read as CONSTANT_PQ (a Java export defect: "
                         "GridLAB-D never dispatches a CONSTANT_PF battery, S4b-2)")
            if written_pf is not None:
                notes.append(f"CONSTANT_PQ: not read: power_factor={cell(written_pf)}")
            mode = "CONSTANT_PQ"
        if mode != "CONSTANT_PQ":
            raise ValueError(f"{label(inverter)}: four_quadrant_control_mode {mode} on a battery; CONSTANT_PQ is "
                             "mapped (S4b-1)")
        if inverter.Q_Out:
            raise ValueError(f"{label(inverter)}: Q_Out {inverter.Q_Out}; a non-zero CONSTANT_PQ Q is not mapped "
                             "(S4b-3)")
        set_point = _quantity(model, inverter, "P_Out", "W")
        generation = battery_output(set_point, float(unit.state_of_charge), float(inverter.soc_reserve),
                                    rated_s) if online else 0.0
        if online and generation != set_point:
            notes.append(f"P_Out {cell(set_point)} W limited to {cell(generation)} W by GridLAB-D's CONSTANT_PQ "
                         "(ratedS, a full battery or the reserve, inverter.cpp:3496-3540)")
    notes.append(f"capability: {', '.join(CAPABILITIES[mode])} (InverterCapabilities not written: cim-tables cannot "
                 "reference an Identity row yet)")
    p = 0.0 - generation  # the load sign
    info = f"{connection_mrid}_info"
    info_row = [info, str(inverter.name), cell(rated_s), cell(rated_s), cell(rated_s)]
    if isinstance(unit, schema.Solar):
        rows.generation_infos.append(Row(info_row))
    else:
        charge = None if inverter.max_charge_rate is None else _quantity(model, inverter, "max_charge_rate", "W")
        rows.storage_infos.append(Row([*info_row, cell(charge)]))
    rows.connections.append(Row(
        [connection_mrid, str(inverter.name), node, phases_cell(phases), connection, cell(rated_s), cell(rated_u),
         cell(p), cell(0.0), cell(rated_s), cell(-rated_s), cell(online), info, buses[node].base_voltage],
        comment=_comment(defaulted, *notes, untranscribed_values(FIELDS, inverter))))
    unit_mrid = f"{connection_mrid}_unit"
    unit_comment = _comment(unit_defaulted, untranscribed_values(CLASSIFIED[type(unit)], unit))
    if isinstance(unit, schema.Solar):
        array, panel = f"{connection_mrid}_array", f"{connection_mrid}_panel"
        rows.arrays.append(Row([array, str(unit.name), cell(float(unit.tilt_angle)),
                                cell(float(unit.orientation_azimuth)),
                                cell(units.Quantity(float(unit.shading_factor), "dimensionless").to("percent")
                                     .magnitude)]))
        rows.panels.append(Row([panel, str(unit.name),
                                cell(units.Quantity(float(unit.efficiency), "dimensionless").to("percent").magnitude),
                                cell(units.Quantity(_quantity(model, unit, "Rated_Insolation", "W/ft**2"), "W/ft**2")
                                     .to("W/m**2").magnitude), array]))
        rows.pv_units.append(Row([unit_mrid, str(unit.name), cell(_quantity(model, unit, "rated_power", "W")),
                                  cell(0.0), cell(output.irradiance), array, connection_mrid], comment=unit_comment))
        return
    capacity = _quantity(model, unit, "battery_capacity", "Wh")
    efficiency = units.Quantity(math.sqrt(float(unit.round_trip_efficiency)), "dimensionless").to("percent").magnitude
    rated_p = _quantity(model, unit, "rated_power", "W")
    battery_type = BATTERY_TYPES.get(str(unit.battery_type))
    cells = (math.floor(_quantity(model, unit, "nominal_voltage", "V") / LI_ION_CELL_V)
             if battery_type == "lithiumIon" else None)
    battery_info = f"{connection_mrid}_battery"
    rows.battery_infos.append(Row([battery_info, str(unit.name), battery_type, cell(capacity), cell(cells)]))
    rows.battery_units.append(Row(
        [unit_mrid, str(unit.name), cell(capacity), cell(float(unit.state_of_charge) * capacity),
         cell(float(inverter.soc_reserve) * capacity), cell(rated_p), cell(-rated_p), cell(efficiency),
         cell(efficiency), battery_state(p), battery_info, connection_mrid], comment=unit_comment))


# -- the document ---------------------------------------------------------------------------------------------------

def _check_children(model: GlmModel) -> None:
    """A solar or battery whose parent is not an inverter raises (``battery.cpp:657``)."""
    for cls in PREFIXES:
        for record in model.list_by_class(cls):
            if not isinstance(model.by_name(record.parent) if record.parent else None, NATIVE_CLASS):
                raise ValueError(f"{label(record)}: parent {record.parent or 'unset'} is not an inverter; not mapped")


def map_inverters(model: GlmModel, roots: dict[str, str], buses: dict[str, BusSystem], feeder: str) -> Document:
    """Every inverter as one document: the datasheets, the connections, then the units."""
    _check_children(model)
    inverters = model.list_by_class(NATIVE_CLASS)
    if not inverters:
        return Document(name=NATIVE_CLASS.class_name, statements=[], profile=CIM_PROFILE)
    rows = _Rows()
    for inverter in inverters:
        _inverter(model, inverter, roots, buses, rows)
    info_columns = [Column("mRID"), Column("name"), Column("apparentPowerMaximum", "VA"),
                    Column("reactivePowerInjectedMax", "VAr"), Column("reactivePowerAbsorbedMax", "VAr")]
    unit_tail = [Column("EquipmentContainer", default=feeder)]
    tables = [
        ("GenerationInverterInfo", info_columns, rows.generation_infos, "a PV inverter's nameplate: ratedS"),
        ("StorageInverterInfo", [*info_columns, Column("chargeRateActiveMax", "W")], rows.storage_infos,
         "a battery inverter's nameplate: ratedS; chargeRateActiveMax = max_charge_rate"),
        ("SolarArrayInfo", [Column("mRID"), Column("name"), Column("tiltAngle", "deg"),
                            Column("orientationAzimuth", "deg"), Column("shadingFactor", "percent")], rows.arrays,
         "the array as GridLAB-D orients it (read by its climate models only)"),
        ("SolarPanelInfo", [Column("mRID"), Column("name"), Column("efficiency", "percent"),
                            Column("referenceIrradiation", "W/m^2"), Column("referenceTemperature", "degC",
                                                                            default="25"),
                            Column("SolarArray")], rows.panels,
         "referenceIrradiation = Rated_Insolation; referenceTemperature: the 77 degF of GridLAB-D's temperature "
         "factor"),
        ("BatteryInfo", [Column("mRID"), Column("name"), Column("batteryType"), Column("ratedCapacity", "Wh"),
                         Column("numberOfCells")], rows.battery_infos,
         "numberOfCells = floor(nominal_voltage / 4.1) on LI_ION (battery.cpp:720)"),
        (_CONNECTION, [Column("mRID"), Column("name"), Column("node"), Column("phases"), Column("phaseConnection"),
                       Column("ratedS", "VA"), Column("ratedU", "V"), Column("p", "W"), Column("q", "VAr"),
                       Column("maxQ", "VAr"), Column("minQ", "VAr"), Column("normallyInService"),
                       Column("AssetDatasheet"), Column("BaseVoltage"), *unit_tail], rows.connections,
         "GridLAB-D's dispatch in the load sign (S4b-2): PV its static-weather output, a battery its CONSTANT_PQ set "
         "point; ratedU the bus's line-to-line voltage (S4b-5)"),
        ("PhotoVoltaicUnit", [Column("mRID"), Column("name"), Column("maxP", "W"), Column("minP", "W"),
                              Column("irradiance", "W/m^2"), Column("AssetDatasheet"),
                              Column("PowerElectronicsConnection"), *unit_tail], rows.pv_units,
         "irradiance: GridLAB-D's static weather, Rated_Insolation x shading_factor (solar.cpp:1170)"),
        ("BatteryUnit", [Column("mRID"), Column("name"), Column("ratedE", "Wh"), Column("storedE", "Wh"),
                         Column("minimumE", "Wh"), Column("maxP", "W"), Column("minP", "W"),
                         Column("chargingEfficiency", "percent"), Column("dischargingEfficiency", "percent"),
                         Column("batteryState"), Column("AssetDatasheet"), Column("PowerElectronicsConnection"),
                         *unit_tail], rows.battery_units,
         "storedE = state_of_charge x capacity, minimumE = soc_reserve x capacity; efficiencies sqrt(round trip)"),
    ]
    statements = [Table(cls, columns, table_rows, comment=comment)
                  for cls, columns, table_rows, comment in tables if table_rows]
    header = provenance(NATIVE_CLASS.class_name, "PowerElectronicsConnection + PhotoVoltaicUnit or BatteryUnit (with "
                        "its solar or battery and their datasheets)", len(inverters), ANCHOR)
    return Document(name=NATIVE_CLASS.class_name, statements=statements, profile=CIM_PROFILE, comment=header)
