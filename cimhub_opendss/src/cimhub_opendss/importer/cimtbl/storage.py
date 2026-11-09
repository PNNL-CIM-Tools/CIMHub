"""OpenDSS ``Storage`` -> ``storage.cimtbl``: a ``PowerElectronicsConnection`` and its ``BatteryUnit``.

The state and p are the engine's snapshot dispatch (``battery_dispatch``, S4b-3): ``kW`` decides when set (every
deck gives it after ``state=``, and the engine keeps the last), else ``State``; capped at kVA. An idling battery
draws its idling losses. The load sign: discharge is negative p, charging positive (S4b-1). q is 0.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#storage``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl.injection import device_terminal, is_delta
from cimhub_opendss.importer.cimtbl.inverter import CONNECTION, connection_columns, connection_row, unit_id
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Storage
PREFIX = "storage_"

_UNIT = "BatteryUnit"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_SHAPE = "a time-series curve; a snapshot does not use it (DSS-11)"
_DYNAMICS = "a dynamics setting; no home in the network profile parts"

FIELDS = {
    "name": Field("copied", ((CONNECTION, "name", None),),
                  "mRID = storage_ + name, lowercased; the unit is <mRID>_unit"),
    "phases": Field("structural", note="the conductor count; default 3"),
    "bus1": Field("structural", note="node and phases, by the S4 shared phase rule"),
    "kv": Field("derived", note="ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); default 12.47"),
    "conn": Field("mapped", ((CONNECTION, "phaseConnection", None),), "wye -> Y, delta -> D; default wye"),
    "kW": Field("derived", note="decides the state when set (S4b-3): > 0 discharging, < 0 charging, 0 waiting; "
                                "p = -kW, capped at kVA (battery_dispatch)"),
    "kvar": Field("structural", note="raises when nonzero: " + _NOT_MAPPED + " (q = 0)"),
    "pf": Field("structural", note="1 only; another raises (the engine caps q by a kvarMax left from the default "
                                   "kVA); default 1"),
    "kVA": Field("copied", ((CONNECTION, "ratedS", "kVA"),), "also caps p; default kWrated"),
    "pct_Cutin": Field("untranscribed", note="an inverter cut-in; 0 by default for storage"),
    "pct_Cutout": Field("untranscribed", note="an inverter cut-out; 0 by default for storage"),
    "EffCurve": Field("structural", note="raises: an efficiency curve changes the snapshot power"),
    "VarFollowInverter": Field("untranscribed", note="acts only with an InvControl"),
    "kvarMax": Field("copied", ((CONNECTION, "maxQ", "kVAr"),), "default kVA"),
    "kvarMaxAbs": Field("derived", note="minQ (kVAr) = -kvarMaxAbs; default kVA"),
    "WattPriority": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "PFPriority": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "pct_PminNoVars": Field("structural", note="raises when nonzero: " + _NOT_MAPPED),
    "pct_PminkvarMax": Field("structural", note="raises when nonzero: " + _NOT_MAPPED),
    "kWrated": Field("copied", ((_UNIT, "maxP", "kW"),), "minP = -kWrated; also p by State; default 25"),
    "pct_kWrated": Field("untranscribed", note="the kW limit of the dispatch modes, which raise"),
    "kWhrated": Field("copied", ((_UNIT, "ratedE", "kWh"),), "default 50"),
    "kWhstored": Field("copied", ((_UNIT, "storedE", "kWh"),), "with %stored raises (the engine keeps the last)"),
    "pct_stored": Field("derived", note="storedE (kWh) = %stored x kWhrated / 100 when kWhstored is unset; "
                                        "default 100"),
    "pct_reserve": Field("derived", note="minimumE (kWh) = %reserve x kWhrated / 100; default 20"),
    "State": Field("mapped", ((_UNIT, "batteryState", None),),
                   "charging, discharging, idling -> waiting (by the first letter, as the engine reads it: the decks' "
                   "charge); kW decides when set "
                   "(S4b-3); default idling"),
    "pct_Discharge": Field("derived", note="p = -kWrated x %Discharge / 100 when discharging by State; default "
                                           "100"),
    "pct_Charge": Field("derived", note="p = kWrated x %Charge / 100 when charging by State; default 100"),
    "pct_EffCharge": Field("copied", ((_UNIT, "chargingEfficiency", "percent"),), "default 90"),
    "pct_EffDischarge": Field("copied", ((_UNIT, "dischargingEfficiency", "percent"),), "default 90"),
    "pct_IdlingkW": Field("derived", note="idlingP (kW) = %IdlingkW x kWrated / 100, also p when waiting; default 1"),
    "pct_Idlingkvar": Field("untranscribed", note="deprecated in the engine"),
    "pct_R": Field("untranscribed", note=_DYNAMICS),
    "pct_X": Field("untranscribed", note=_DYNAMICS),
    "model": Field("structural", note="1 (constant P, PF) only; any other raises; default 1"),
    "Vminpu": Field("derived", note="maxIFault = 1 / Vminpu (the engine's CIM export); default 0.9"),
    "Vmaxpu": Field("untranscribed", note="above it the engine models the battery as constant Z; a power-flow "
                                          "setting"),
    "Balanced": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "LimitCurrent": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "yearly": Field("untranscribed", note=_SHAPE),
    "daily": Field("untranscribed", note=_SHAPE),
    "duty": Field("untranscribed", note=_SHAPE),
    "DispMode": Field("structural", note="default only; another dispatch mode raises (" + _NOT_MAPPED + ")"),
    "DischargeTrigger": Field("untranscribed", note="acts only in a dispatch mode, which raises"),
    "ChargeTrigger": Field("untranscribed", note="acts only in a dispatch mode, which raises"),
    "TimeChargeTrig": Field("untranscribed", note="acts only in a dispatch mode, which raises"),
    "class_class": Field("untranscribed", note="a DSS report grouping"),
    "DynaDLL": Field("structural", note=_NOT_MAPPED),
    "DynaData": Field("structural", note=_NOT_MAPPED),
    "UserModel": Field("structural", note=_NOT_MAPPED),
    "UserData": Field("structural", note=_NOT_MAPPED),
    "debugtrace": Field("untranscribed", note="a DSS debugging switch"),
    "kVDC": Field("untranscribed", note=_DYNAMICS),
    "Kp": Field("untranscribed", note=_DYNAMICS),
    "PITol": Field("untranscribed", note=_DYNAMICS),
    "SafeVoltage": Field("untranscribed", note=_DYNAMICS),
    "SafeMode": Field("untranscribed", note=_DYNAMICS),
    "DynamicEq": Field("untranscribed", note=_DYNAMICS),
    "DynOut": Field("untranscribed", note=_DYNAMICS),
    "ControlMode": Field("structural", note="GFL only; GFM raises (" + _NOT_MAPPED + ")"),
    "AmpLimit": Field("untranscribed", note=_DYNAMICS),
    "AmpLimitGain": Field("untranscribed", note=_DYNAMICS),
    "spectrum": Field("untranscribed", note="harmonics model; no home in the network profile parts"),
    "basefreq": Field("untranscribed", note="no home on an inverter"),
    "enabled": Field("copied", ((CONNECTION, "normallyInService", None),), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = ("EffCurve", "DynaDLL", "DynaData", "UserModel", "UserData")
_YES_UNMAPPED = ("Balanced", "LimitCurrent", "WattPriority", "PFPriority")
_NONZERO_UNMAPPED = ("pct_PminNoVars", "pct_PminkvarMax", "kvar")
_STATES = {"charging": "charging", "discharging": "discharging", "idling": "waiting"}

_PROVENANCE = """OpenDSS Storage -> PowerElectronicsConnection + BatteryUnit on its bus: the snapshot dispatch (kW when set,
else State), in the load sign (discharge is negative p).
Source table: Storage (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#storage"""


class Dispatch(NamedTuple):
    state: str
    """The CIM ``BatteryStateKind``."""
    kw: float
    """p in kW, the load sign."""
    note: str | None


def engine_state(text, *, name: str) -> str:
    """The engine state a ``State`` value names. The engine reads only the first letter, so the decks' ``charge``
    is charging."""
    word = str(text).lower()
    for state in _STATES:
        if word and state[0] == word[0]:
            return state
    raise ValueError(f"Storage {name}: State={text} names none of {', '.join(_STATES)}")


def battery_dispatch(name: str, *, kw, state: str, kw_rated: float, kva: float, pct_charge: float,
                     pct_discharge: float, idling_kw: float, stored: float, minimum: float, rated: float) -> Dispatch:
    """The engine's snapshot state and p (load sign) of a battery (S4b-3). ``kw`` is the deck's, or ``None``."""
    note = None
    if kw is not None:
        kw = float(kw)
        by_kw = "discharging" if kw > 0 else "charging" if kw < 0 else "idling"
        if by_kw != state:
            note = f"kW={kw:g} after State={state}: {by_kw}"
        state = by_kw
    if state == "charging" and stored >= rated:
        raise ValueError(f"Storage {name}: charging with {stored:g} of {rated:g} kWh stored; the engine idles a "
                         "full battery, which is not mapped")
    if state == "discharging" and stored <= minimum:
        raise ValueError(f"Storage {name}: discharging with {stored:g} kWh stored, at or below its {minimum:g} kWh "
                         "reserve; the engine idles it, which is not mapped")
    if state == "idling":
        return Dispatch("waiting", idling_kw, note)
    if state == "charging":
        return Dispatch("charging", min(-kw if kw is not None else kw_rated * pct_charge / 100, kva), note)
    return Dispatch("discharging", -min(kw if kw is not None else kw_rated * pct_discharge / 100, kva), note)


def _check(storage) -> None:
    """Raise on what the mapping does not cover (on the record as written, before defaults)."""
    unmapped = [slot for slot in _UNMAPPED if getattr(storage, slot) not in (None, [])]
    unmapped += [slot for slot in _YES_UNMAPPED if getattr(storage, slot)]
    unmapped += [slot for slot in _NONZERO_UNMAPPED if getattr(storage, slot) not in (None, 0)]
    if storage.ControlMode is not None and str(storage.ControlMode).upper() != "GFL":
        unmapped.append(f"ControlMode={storage.ControlMode}")
    if storage.DispMode is not None and str(storage.DispMode).lower() != "default":
        unmapped.append(f"DispMode={storage.DispMode}")
    if storage.pf is not None and float(storage.pf) != 1:
        unmapped.append(f"pf={storage.pf}")
    if unmapped:
        raise ValueError(f"Storage {storage.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets "
                         "them)")
    if storage.model is not None and int(storage.model) != 1:
        raise ValueError(f"Storage {storage.name}: model={storage.model} is not mapped (model 1 is)")
    if storage.kWhstored is not None and storage.pct_stored is not None:
        raise ValueError(f"Storage {storage.name}: kWhstored with %stored; the engine keeps whichever comes last, "
                         "and the record keeps no order")


def map_storage(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Storage`` of a DSS model as one ``storage`` document; ``container`` is the Feeder mRID."""
    batteries = native.list_by_class(NATIVE_CLASS)
    if not batteries:
        return Document(name="storage", statements=[], profile=CIM_PROFILE)
    defaults = dss_defaults(NATIVE_CLASS)
    connections, units = [], []
    for original in batteries:
        _check(original)
        unused = {"pct_stored"} if original.kWhstored is not None else set()
        battery, defaulted = fill_defaults(FIELDS, original, {k: v for k, v in defaults.items() if k not in unused})
        terminal = device_terminal(f"Storage {battery.name}", battery.bus1, int(battery.phases),
                                   is_delta(battery.conn), buses)
        kw_rated, rated = float(battery.kWrated), float(battery.kWhrated)
        kva = float(battery.kVA) if battery.kVA is not None else kw_rated
        stored = float(battery.kWhstored) if battery.kWhstored is not None else float(battery.pct_stored) * rated / 100
        minimum = float(battery.pct_reserve) * rated / 100
        idling_kw = float(battery.pct_IdlingkW) * kw_rated / 100
        dispatch = battery_dispatch(battery.name, kw=original.kW, state=engine_state(battery.State, name=battery.name),
                                    kw_rated=kw_rated, kva=kva, pct_charge=float(battery.pct_Charge),
                                    pct_discharge=float(battery.pct_Discharge), idling_kw=idling_kw, stored=stored,
                                    minimum=minimum, rated=rated)
        notes = [dispatch.note, "kVA defaulted to kWrated" if battery.kVA is None else None, defaulted,
                 untranscribed_values(FIELDS, battery)]
        row = connection_row(PREFIX, battery, terminal, kva=kva, p=dispatch.kw, q=0.0,
                             comment="\n".join(note for note in notes if note) or None)
        connections.append(row)
        units.append(Row([unit_id(PREFIX, battery), cell(rated), cell(stored), cell(minimum), cell(kw_rated),
                          cell(-kw_rated), cell(float(battery.pct_EffCharge)), cell(float(battery.pct_EffDischarge)),
                          cell(idling_kw), dispatch.state, row.cells[0]]))
    statements = [
        Table(CONNECTION, connection_columns(container), connections,
              comment="derived: p by the state (battery_dispatch): -kW or -kWrated x %Discharge discharging, "
                      "kWrated x %Charge charging, idlingP waiting; capped at kVA"),
        Table(_UNIT, [Column("mRID"), Column("ratedE", "kWh"), Column("storedE", "kWh"), Column("minimumE", "kWh"),
                      Column("maxP", "kW"), Column("minP", "kW"), Column("chargingEfficiency", "percent"),
                      Column("dischargingEfficiency", "percent"), Column("idlingP", "kW"), Column("batteryState"),
                      Column("PowerElectronicsConnection"), Column("EquipmentContainer", default=container)], units,
              comment="derived: storedE = kWhstored or %stored x kWhrated; minimumE = %reserve x kWhrated; "
                      "idlingP = %IdlingkW x kWrated"),
    ]
    return Document(name="storage", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(batteries)))
