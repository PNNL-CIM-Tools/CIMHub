"""BatteryUnit behind a PowerElectronicsConnection -> OpenDSS ``Storage`` (``EXPORT_MAPPING.md#storage``).

One Storage per battery unit (``inverter.inverter_pieces``). ``State`` is the unit's batteryState, and its
output is the setpoint as the engine keeps it, a percent of kWrated: ``%Discharge`` or ``%Charge`` = |p| /
kWrated x 100. ``kW`` is not written: the engine turns it into that percent at the kWrated of the moment, and the
writer puts kW before kWrated (probe: ``kW=-5`` then ``kWrated=5`` charges at 1 kW). A waiting battery draws its
idling loss, ``%IdlingkW``, which is then its p. The energies go before ``State`` in the writer's order, as the
engine checks them when the state is assigned. q must be 0, as on import.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.der import get_battery_unit
from cimhub_core.getters.phase_power import SUM_REL_TOL
from cimhub_opendss.exporter.inverter import inverter_pieces
from cimhub_opendss.exporter.slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.PowerElectronicsConnection,)
NATIVE_CLASS = schema.Storage
NAMESPACE = "Storage"
STATE = cim.BatteryStateKind
#: batteryState -> DSS State and the sign its output (generation sign) must have
STATES = {STATE.discharging: ("discharging", 1), STATE.charging: ("charging", -1), STATE.waiting: ("idling", 0)}

_INVERTER = "the connection's, by the unit's share (inverter_pieces)"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names: the connection's for one unit, the unit's for several, <name>_<phase> per phase"),
    "phases": Slot("written", "the phase conductors; a delta across two is 1"),
    "bus1": Slot("written", "bus_ref of the phase conductors; a wye inverter's neutral is node 0"),
    "kv": Slot("written", "ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted)"),
    "conn": Slot("written", "phaseConnection Y/Yn -> wye, D -> delta; others raise"),
    "kW": Slot("not mapped", "%Discharge/%Charge carry the output: the engine makes kW a percent of the kWrated "
                             "of the moment, and kWrated is written after kW"),
    "kvar": Slot("not mapped", "q must be 0 (it raises on import); another raises"),
    "pf": Slot("not mapped", "q is 0"),
    "kVA": Slot("written", f"ratedS, {_INVERTER}"),
    "kvarMax": Slot("written", f"maxQ, {_INVERTER}; unset -> not written"),
    "kvarMaxAbs": Slot("written", f"-minQ, {_INVERTER}; unset -> not written"),
    "kWrated": Slot("written", "the unit's maxP (kW), x 1/n for one of n phases; unset raises, a minP other than "
                               "-maxP raises"),
    "kWhrated": Slot("written", "ratedE (kWh), x 1/n for one of n phases; unset -> not written"),
    "kWhstored": Slot("written", "storedE (kWh), x 1/n for one of n phases; unset -> not written"),
    "pct_stored": Slot("not mapped", "kWhstored carries the energy"),
    "pct_reserve": Slot("written", "minimumE / ratedE x 100; either unset -> not written"),
    "State": Slot("written", "batteryState charging, discharging, waiting -> charging, discharging, idling; others "
                             "raise, and so does an output of the wrong sign"),
    "pct_Discharge": Slot("written", "discharging: the unit's output / kWrated x 100"),
    "pct_Charge": Slot("written", "charging: -(the unit's output) / kWrated x 100"),
    "pct_EffCharge": Slot("written", "chargingEfficiency (percent); unset -> not written"),
    "pct_EffDischarge": Slot("written", "dischargingEfficiency (percent); unset -> not written"),
    "pct_IdlingkW": Slot("written", "idlingP / kWrated x 100; waiting: its p (which idlingP, when set, must be)"),
    "Vminpu": Slot("written", "1 / maxIFault (the importer's rule inverted); unset -> not written"),
    "model": Slot("not mapped", "model 1, the engine's default; others raise on import"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "untranscribed or raising on import; not in CIM"))}


def export(context) -> list[schema.Storage]:
    """One Storage per BatteryUnit."""
    return [_storage(piece) for connection in context.objects(*CIM_CLASSES)
            for piece in inverter_pieces(connection, cim.BatteryUnit, NAMESPACE, context.names)]


def _storage(piece) -> schema.Storage:
    battery = get_battery_unit(piece.unit, "kW", "kWh", sign="generation")
    unit = describe(piece.unit)
    if battery.max_p is None or battery.max_p <= 0:
        raise ValueError(f"{unit}: maxP {battery.max_p}; a Storage's kWrated must be above 0")
    if battery.min_p is not None and not math.isclose(battery.min_p, -battery.max_p, rel_tol=SUM_REL_TOL):
        raise ValueError(f"{unit}: minP {battery.min_p} is not -maxP; a Storage has one kWrated both ways")
    if piece.q != 0:
        raise ValueError(f"{unit}: q {-piece.q} kVAr; a Storage's kvar is not mapped, as on import")
    if battery.state not in STATES:
        state = battery.state.value if battery.state is not None else None
        raise ValueError(f"{unit}: batteryState {state}; a Storage State is charging, discharging or waiting")
    state, sign = STATES[battery.state]
    if (sign > 0 and piece.p <= 0) or (sign < 0 and piece.p >= 0):
        raise ValueError(f"{unit}: {battery.state.value} with p {-piece.p} kW (the load sign)")
    _check_energy(unit, state, battery)
    idling = _scaled(battery.idling_p, piece.unit_share)
    if sign == 0:
        if idling is not None and not math.isclose(idling, -piece.p, rel_tol=SUM_REL_TOL):
            raise ValueError(f"{unit}: waiting with p {-piece.p} kW, not its idlingP {idling} kW")
        idling = -piece.p
    reserve = None
    if battery.minimum_e is not None and battery.rated_e:
        reserve = battery.minimum_e / battery.rated_e * 100
    kw_rated = battery.max_p * piece.unit_share
    return NATIVE_CLASS(
        name=piece.name, State=state, kWrated=kw_rated,
        pct_Discharge=_percent(piece.p, kw_rated) if sign > 0 else None,
        pct_Charge=_percent(-piece.p, kw_rated) if sign < 0 else None,
        kWhrated=_scaled(battery.rated_e, piece.unit_share), kWhstored=_scaled(battery.stored_e, piece.unit_share),
        pct_reserve=reserve, pct_EffCharge=battery.charging_efficiency,
        pct_EffDischarge=battery.discharging_efficiency,
        pct_IdlingkW=None if idling is None else _percent(idling, kw_rated), **piece.slots,
    )


def _scaled(value: float | None, share: float) -> float | None:
    return None if value is None else value * share


def _percent(kw: float, kw_rated: float) -> float:
    return kw / kw_rated * 100 + 0.0


def _check_energy(unit: str, state: str, battery) -> None:
    """The engine idles a battery told to charge when full or to discharge at or below its reserve (S4b); CIM's
    state would not run, so it raises, as on import."""
    stored, rated, minimum = battery.stored_e, battery.rated_e, battery.minimum_e
    if state == "charging" and stored is not None and rated is not None and stored >= rated:
        raise ValueError(f"{unit}: charging with {stored:g} of {rated:g} kWh stored; the engine idles a full battery")
    if state == "discharging" and stored is not None and minimum is not None and stored <= minimum:
        raise ValueError(f"{unit}: discharging with {stored:g} kWh stored, at or below its {minimum:g} kWh reserve; "
                         "the engine idles it")
