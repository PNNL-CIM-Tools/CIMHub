"""OpenDSS ``Storage`` -> ``storage.cimtbl``: a ``PowerElectronicsConnection`` and its ``BatteryUnit``.

The state and p are the engine's snapshot dispatch, replayed from the deck's assignments in order
(``battery_dispatch``, S4b-8): a kW sets the discharge (> 0) or charge (< 0) setpoint and the state, 0 idles, and
``State`` picks which setpoint runs; capped at kVA. An idling battery
draws its idling losses. The load sign: discharge is negative p, charging positive (S4b-1). q is 0.

A ``yearly`` LoadShape with ``DispMode=follow`` is the battery's own ``EnergyConnectionSchedule`` (S9): at each
sample it discharges at mult x kWrated (mult > 0), charges at -mult x kWrated (< 0) or idles (0), capped at kVA
(engine-checked; %Charge, %Discharge and %kWrated have no effect), p in the Parquet sidecar (``schedule_points``).
That is the dispatch asked for: a battery full or at its reserve idles in the engine, which the schedule does not
model. Such a battery's snapshot idles, so a kW or State on it raises; a shape in another dispatch mode raises.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#storage``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import loadshape
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
    "kW": Field("derived", note="replayed in deck order (battery_dispatch, S4b-8): > 0 sets the discharge setpoint "
                                "and discharging, < 0 the charge setpoint and charging, 0 waiting; capped at kVA"),
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
    "kWhstored": Field("copied", ((_UNIT, "storedE", "kWh"),), "unless %stored was assigned after it (the last wins)"),
    "pct_stored": Field("derived", note="storedE (kWh) = %stored x kWhrated / 100 unless kWhstored was assigned after "
                                        "it; default 100"),
    "pct_reserve": Field("derived", note="minimumE (kWh) = %reserve x kWhrated / 100; default 20"),
    "State": Field("mapped", ((_UNIT, "batteryState", None),),
                   "charging, discharging, idling -> waiting (by the first letter, as the engine reads it: the decks' "
                   "charge); picks the setpoint that runs, replayed with kW (S4b-8); default idling"),
    "pct_Discharge": Field("derived", note="the discharge setpoint kWrated x %Discharge / 100 until a kW > 0 sets it; "
                                           "default 100"),
    "pct_Charge": Field("derived", note="the charge setpoint kWrated x %Charge / 100 until a kW < 0 sets it; default "
                                        "100"),
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
    "yearly": Field("mapped", ((loadshape.DEVICE_SCHEDULE, "name", None),),
                    "DispMode=follow: the battery's EnergyConnectionSchedule <mRID>_yearly, mult x kWrated per sample "
                    "(S9); with another DispMode raises"),
    "daily": Field("untranscribed", note=_SHAPE),
    "duty": Field("untranscribed", note=_SHAPE),
    "DispMode": Field("structural", note="default, or follow with a yearly shape (S9); another dispatch mode raises "
                                         "(" + _NOT_MAPPED + ")"),
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
_FOLLOW = "follow"
#: The slots that give the stored energy and its limits.
_ENERGY = ("kWhstored", "pct_stored", "kWhrated", "pct_reserve")

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


def battery_dispatch(name: str, assignments: Iterable[tuple[str, object]], *, kw_rated: float, kva: float,
                     pct_charge: float, pct_discharge: float, idling_kw: float, stored: float, minimum: float,
                     rated: float) -> Dispatch:
    """The engine's snapshot state and p (load sign) of a battery, from its ``(slot, value)`` assignments in deck
    order (S4b-8). The engine keeps a discharge and a charge setpoint: a kW > 0 sets the first and discharges, a
    kW < 0 the second and charges, 0 idles; ``State`` picks which runs; a ``%Discharge``/``%Charge`` puts its
    setpoint back to the rating's share. So ``state=charge kW=150`` discharges at 150 kW.

    The engine checks the stored energy against full and the reserve when the state is assigned, with the energy of
    that moment, so an energy assigned after the last State or kW raises (no deck in the sweep does it)."""
    state, discharge, charge, note, energy_after, state_set = "idling", None, None, None, None, False
    for slot, value in assignments:
        if slot in _ENERGY:
            energy_after = slot
        if slot in ("kW", "State"):
            energy_after = None
        if slot == "kW":
            kw = float(value)
            by_kw = "discharging" if kw > 0 else "charging" if kw < 0 else "idling"
            if kw > 0:
                discharge = kw
            elif kw < 0:
                charge = -kw
            if state_set and by_kw != state:
                note = f"kW={kw:g} after State={state}: {by_kw}"
            state = by_kw
        elif slot == "State":
            state, note, state_set = engine_state(value, name=name), None, True
        elif slot == "pct_Discharge":
            discharge = None
        elif slot == "pct_Charge":
            charge = None
    if energy_after and state != "idling":
        raise ValueError(f"Storage {name}: {energy_after} is assigned after its last State or kW; the engine checks "
                         "the stored energy when the state is assigned, which is not mapped")
    if state == "charging" and stored >= rated:
        raise ValueError(f"Storage {name}: charging with {stored:g} of {rated:g} kWh stored; the engine idles a "
                         "full battery, which is not mapped")
    if state == "discharging" and stored <= minimum:
        raise ValueError(f"Storage {name}: discharging with {stored:g} kWh stored, at or below its {minimum:g} kWh "
                         "reserve; the engine idles it, which is not mapped")
    if state == "idling":
        return Dispatch("waiting", idling_kw, note)
    if state == "charging":
        return Dispatch("charging", min(charge if charge is not None else kw_rated * pct_charge / 100, kva), note)
    return Dispatch("discharging", -min(discharge if discharge is not None else kw_rated * pct_discharge / 100, kva),
                    note)


def _check(storage) -> None:
    """Raise on what the mapping does not cover (on the record as written, before defaults)."""
    unmapped = [slot for slot in _UNMAPPED if getattr(storage, slot) not in (None, [])]
    unmapped += [slot for slot in _YES_UNMAPPED if getattr(storage, slot)]
    unmapped += [slot for slot in _NONZERO_UNMAPPED if getattr(storage, slot) not in (None, 0)]
    if storage.ControlMode is not None and str(storage.ControlMode).upper() != "GFL":
        unmapped.append(f"ControlMode={storage.ControlMode}")
    mode = str(storage.DispMode).lower() if storage.DispMode is not None else "default"
    if mode not in ("default", _FOLLOW):
        unmapped.append(f"DispMode={storage.DispMode}")
    if storage.pf is not None and float(storage.pf) != 1:
        unmapped.append(f"pf={storage.pf}")
    if unmapped:
        raise ValueError(f"Storage {storage.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets "
                         "them)")
    if storage.model is not None and int(storage.model) != 1:
        raise ValueError(f"Storage {storage.name}: model={storage.model} is not mapped (model 1 is)")
    if (mode == _FOLLOW) != (storage.yearly is not None):
        raise ValueError(f"Storage {storage.name}: DispMode={storage.DispMode} with yearly={storage.yearly}; only a "
                         "follow-mode battery's yearly shape is mapped (S9-6)")
    if mode == _FOLLOW and (storage.kW is not None or storage.State is not None):
        raise ValueError(f"Storage {storage.name}: DispMode=follow with a kW or State; the engine's snapshot of such a "
                         "battery is not mapped (one with neither idles)")


def follow_power(value: float, *, kw_rated: float, kva: float, idling_kw: float) -> float:
    """A follow-mode battery's p (kW, the load sign) at a shape sample: discharge at mult x kWrated, charge at
    -mult x kWrated, idle at 0, capped at kVA (engine-checked)."""
    if value == 0:
        return idling_kw
    return -min(value * kw_rated, kva) if value > 0 else min(-value * kw_rated, kva)


def schedule_points(native) -> dict[str, loadshape.DevicePoints]:
    """Each follow-mode battery's yearly schedule (``<mRID>_yearly``): ``follow_power`` at each sample, p only."""
    points, defaults = {}, dss_defaults(NATIVE_CLASS)
    for original in native.list_by_class(NATIVE_CLASS):
        shape = loadshape.device_shape(native, original, f"Storage {original.name}")
        if shape is None:
            continue
        battery, _ = fill_defaults(FIELDS, original, defaults)
        kw_rated = float(battery.kWrated)
        kva = float(battery.kVA) if battery.kVA is not None else kw_rated
        idling_kw = float(battery.pct_IdlingkW) * kw_rated / 100
        points[mrid(PREFIX, battery.name, lowercase=True) + loadshape.DEVICE_SCHEDULE_SUFFIX] = loadshape.DevicePoints(
            loadshape.point_times(shape),
            [follow_power(value, kw_rated=kw_rated, kva=kva, idling_kw=idling_kw) + 0.0 for value in shape.mult], None)
    return points


def map_storage(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Storage`` of a DSS model as one ``storage`` document; ``container`` is the Feeder mRID."""
    batteries = native.list_by_class(NATIVE_CLASS)
    if not batteries:
        return Document(name="storage", statements=[], profile=CIM_PROFILE)
    defaults = dss_defaults(NATIVE_CLASS)
    connections, units, schedules = [], [], []
    for original in batteries:
        _check(original)
        by_energy = native.last_of(original, "kWhstored", "pct_stored") == "kWhstored"
        unused = {"pct_stored"} if by_energy else set()
        battery, defaulted = fill_defaults(FIELDS, original, {k: v for k, v in defaults.items() if k not in unused})
        terminal = device_terminal(f"Storage {battery.name}", battery.bus1, int(battery.phases),
                                   is_delta(battery.conn), buses)
        kw_rated, rated = float(battery.kWrated), float(battery.kWhrated)
        kva = float(battery.kVA) if battery.kVA is not None else kw_rated
        stored = float(battery.kWhstored) if by_energy else float(battery.pct_stored) * rated / 100
        minimum = float(battery.pct_reserve) * rated / 100
        idling_kw = float(battery.pct_IdlingkW) * kw_rated / 100
        dispatch = battery_dispatch(battery.name, native.assignments(original), kw_rated=kw_rated, kva=kva,
                                    pct_charge=float(battery.pct_Charge), pct_discharge=float(battery.pct_Discharge),
                                    idling_kw=idling_kw, stored=stored, minimum=minimum, rated=rated)
        notes = [dispatch.note, "kVA defaulted to kWrated" if battery.kVA is None else None, defaulted,
                 untranscribed_values(FIELDS, battery)]
        row = connection_row(PREFIX, battery, terminal, kva=kva, p=dispatch.kw, q=0.0,
                             comment="\n".join(note for note in notes if note) or None)
        connections.append(row)
        units.append(Row([unit_id(PREFIX, battery), cell(rated), cell(stored), cell(minimum), cell(kw_rated),
                          cell(-kw_rated + 0.0), cell(float(battery.pct_EffCharge)), cell(float(battery.pct_EffDischarge)),
                          cell(idling_kw), dispatch.state, row.cells[0]]))
        if loadshape.device_shape(native, original, f"Storage {battery.name}") is not None:
            schedules.append(loadshape.device_schedule_row(row.cells[0], battery))
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
    if schedules:
        statements.append(loadshape.device_schedules(schedules))
    return Document(name="storage", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(batteries)))
