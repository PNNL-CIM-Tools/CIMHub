"""OpenDSS ``Generator`` -> ``generator.cimtbl``: one ``SynchronousMachine`` per generator (shape
``synchronous_machine``).

p = -kW and q = -kvar, the load sign (S4b-1). kvar is the engine's: it keeps kvar as a power factor, so the
mapper replays the deck's kW, pf and kvar assignments in order (``dispatched_kvar``, S4b-8). A model 3 (PV
bus) machine regulates its own terminal: a ``RegulatingControl`` ``gen_<name>_ctrl`` after the machine, then an
``Update`` giving the machine its control (S4a's own-terminal form). SynchronousMachine has no phaseConnection, so
delta is ``earthing=false`` (S4b-5). The ``phases`` column gives one RotatingMachinePhase per phase.

A ``yearly`` LoadShape scales kW and kvar by mult (engine-checked): the machine's own ``EnergyConnectionSchedule``,
p and q at each sample in the Parquet sidecar (``schedule_points``, S9); a model 3 machine's q is its control's, so
its schedule carries p only.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#generator``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, phases_cell, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import loadshape
from cimhub_opendss.importer.cimtbl.injection import device_terminal, is_delta, line_kv, reactive_power
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Generator
PREFIX = "gen_"

_MACHINE = "SynchronousMachine"
_CONTROL = "RegulatingControl"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_SHAPE = "a time-series curve; a snapshot does not use it (DSS-11)"
_DYNAMICS = "a dynamics setting; no home in the network profile parts"
_DISPATCH = "a dispatch setting of time-series solutions; a snapshot does not use it"
_FUEL = "a fuel-limited dispatch setting; a snapshot does not use it"
#: The engine's default kVA is this times kW, and its default Maxkvar this times kvar.
KVA_PER_KW = 1.2
MAXKVAR_PER_KVAR = 2.0
_PV_BUS = "ConstantPV"
_MAPPED_MODELS = {"ConstantPQ": "constant kW and kvar", "CurrentLimited": "as model 1; below Vminpu the engine "
                  "limits its current, a power-flow behaviour", _PV_BUS: "a PV bus: a voltage RegulatingControl"}

FIELDS = {
    "name": Field("copied", ((_MACHINE, "name", None),), "mRID = gen_ + name, lowercased"),
    "phases": Field("structural", note="the conductor count; default 3"),
    "bus1": Field("structural", note="node and phases, by the S4 shared phase rule"),
    "kv": Field("derived", note="ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); default 12.47"),
    "kW": Field("derived", note="p (kW) = -kW (the load sign); default 1000"),
    "pf": Field("derived", note="q (kVAr) = -kvar, kvar replayed from the kW, pf and kvar assignments in deck order "
                                "(dispatched_kvar, S4b-8): each kW or pf recomputes kvar = kW x tan(acos abs(pf)); "
                                "default 0.88"),
    "kvar": Field("derived", note="sets the pf, kW / kVA with kvar's sign, at the kW of that moment; a pf of 0 (kvar "
                                  "at kW 0) leaves kvar as set (dispatched_kvar, S4b-8)"),
    "model": Field("structural", note="1 and 7 dispatch kW/kvar; 3 adds a voltage RegulatingControl; 2, 4, 5, 6 "
                                      "raise; default 1"),
    "Vminpu": Field("untranscribed", note="below it the engine models the machine as constant Z; a power-flow "
                                          "setting"),
    "Vmaxpu": Field("untranscribed", note="above it the engine models the machine as constant Z; a power-flow "
                                          "setting"),
    "yearly": Field("mapped", ((loadshape.DEVICE_SCHEDULE, "name", None),),
                    "the machine's EnergyConnectionSchedule <mRID>_yearly: -kW x mult, -kvar x mult per sample (S9)"),
    "daily": Field("untranscribed", note=_SHAPE),
    "duty": Field("untranscribed", note=_SHAPE),
    "dispmode": Field("untranscribed", note=_DISPATCH + "; with a yearly shape, another than Default raises"),
    "dispvalue": Field("untranscribed", note=_DISPATCH + "; with a yearly shape, above 0 raises"),
    "conn": Field("mapped", ((_MACHINE, "earthing", None),),
                  "wye -> earthing true, delta -> false (no phaseConnection on a machine, S4b-5); default wye"),
    "status": Field("untranscribed", note="Fixed/Variable: whether load multipliers scale it; " + _DISPATCH
                    + "; with a yearly shape, Fixed raises"),
    "gen_class": Field("untranscribed", note="a DSS report grouping"),
    "Vpu": Field("derived", note="model 3: the control's targetValue = Vpu x ratedU in kV "
                                 "(targetValueUnitMultiplier k); default 1"),
    "maxkvar": Field("copied", ((_MACHINE, "maxQ", "kVAr"),), "model 3 only (another model raises); default 2 x "
                                                              "kvar (reactive_limits)"),
    "minkvar": Field("copied", ((_MACHINE, "minQ", "kVAr"),), "model 3 only (another model raises); default -2 x "
                                                              "kvar (reactive_limits)"),
    "pvfactor": Field("untranscribed", note="a convergence aid of the engine's model 3"),
    "forceon": Field("untranscribed", note=_DISPATCH),
    "kVA": Field("copied", ((_MACHINE, "ratedS", "kVA"),), "default 1.2 x kW"),
    "MVA": Field("structural", note=_NOT_MAPPED + " (kVA is)"),
    "Xd": Field("untranscribed", note=_DYNAMICS),
    "Xdp": Field("untranscribed", note=_DYNAMICS),
    "Xdpp": Field("untranscribed", note=_DYNAMICS),
    "H": Field("untranscribed", note=_DYNAMICS),
    "D": Field("untranscribed", note=_DYNAMICS),
    "UserModel": Field("structural", note=_NOT_MAPPED),
    "UserData": Field("structural", note=_NOT_MAPPED),
    "ShaftModel": Field("structural", note=_NOT_MAPPED),
    "ShaftData": Field("structural", note=_NOT_MAPPED),
    "DutyStart": Field("untranscribed", note=_SHAPE),
    "debugtrace": Field("untranscribed", note="a DSS debugging switch"),
    "Balanced": Field("untranscribed", note="a power-flow setting of the engine's model"),
    "XRdp": Field("untranscribed", note=_DYNAMICS),
    "UseFuel": Field("untranscribed", note=_FUEL),
    "FuelkWh": Field("untranscribed", note=_FUEL),
    "pct_Fuel": Field("untranscribed", note=_FUEL),
    "pct_Reserve": Field("untranscribed", note=_FUEL),
    "Refuel": Field("untranscribed", note=_FUEL),
    "DynamicEq": Field("untranscribed", note=_DYNAMICS),
    "DynOut": Field("untranscribed", note=_DYNAMICS),
    "spectrum": Field("untranscribed", note="harmonics model; no home in the network profile parts"),
    "basefreq": Field("untranscribed", note="no home on a machine"),
    "enabled": Field("copied", ((_MACHINE, "normallyInService", None),), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = ("MVA", "UserModel", "UserData", "ShaftModel", "ShaftData")

_PROVENANCE = """OpenDSS Generator -> SynchronousMachine on its bus, in the load sign (generation is negative p); a model 3
machine regulates its own terminal (RegulatingControl, then an Update).
Source table: Generator (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#generator"""


#: The engine's kW, pf and kvar of a bare ``New Generator`` (its readback): where a replay starts.
ENGINE_START = (1000.0, 0.88, 60.0)


def dispatched_kvar(assignments: Iterable[tuple[str, object]]) -> float:
    """The kvar the engine dispatches a Generator at, from its ``(slot, value)`` assignments in deck order (S4b-8).

    The engine keeps kvar as a power factor: assigning kvar sets pf = kW / sqrt(kW^2 + kvar^2), with kvar's sign, at
    the kW of that moment; assigning kW or pf recomputes kvar = kW x tan(acos abs(pf)). A pf of 0 (kvar assigned at
    kW 0) leaves kvar as assigned. So ``kW=620 kvar=30`` then ``kW=0`` is 0 kvar, and ``kvar=30 kW=100`` is 3.
    """
    kw, pf, kvar = ENGINE_START
    for slot, value in assignments:
        if slot == "kvar":
            kvar = float(value)
            apparent = math.hypot(kw, kvar)
            if apparent:
                pf = math.copysign(kw / apparent, kvar)
        elif slot in ("kW", "pf"):
            if slot == "kW":
                kw = float(value)
            else:
                pf = float(value)
            if pf != 0:
                kvar = reactive_power(kw, pf)
    return kvar


def reactive_limits(assignments: Iterable[tuple[str, object]], kvar: float) -> tuple[float, float]:
    """``(Maxkvar, Minkvar)`` of a model 3 Generator as the engine holds them (engine-checked): each kW, pf or kvar
    assignment resets both to +-2 x kvar, so a Maxkvar or Minkvar stays only when assigned after the last of
    those. ``kvar`` is the dispatched kvar (``dispatched_kvar``)."""
    max_q = min_q = None
    for slot, value in assignments:
        if slot in ("kW", "pf", "kvar"):
            max_q = min_q = None
        elif slot == "maxkvar":
            max_q = float(value)
        elif slot == "minkvar":
            min_q = float(value)
    default = MAXKVAR_PER_KVAR * abs(kvar)
    return (default + 0.0 if max_q is None else max_q), (-default + 0.0 if min_q is None else min_q)


def model_name(model) -> str:
    return str(getattr(model, "text", model))


def _check(generator) -> None:
    """Raise on what the mapping does not cover (on the record as written, before defaults)."""
    unmapped = [slot for slot in _UNMAPPED if getattr(generator, slot) is not None]
    if unmapped:
        raise ValueError(f"Generator {generator.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep "
                         "sets them)")
    model = model_name(generator.model) if generator.model is not None else "ConstantPQ"
    if model not in _MAPPED_MODELS:
        raise ValueError(f"Generator {generator.name}: model {model} is not mapped (models 1, 3 and 7 are)")
    if model != _PV_BUS and (generator.maxkvar is not None or generator.minkvar is not None):
        raise ValueError(f"Generator {generator.name}: Maxkvar/Minkvar on model {model}; only model 3 uses them")
    if generator.yearly is None:
        return
    follows = (("dispmode", generator.dispmode, model_name(generator.dispmode).lower() == "default"),
               ("dispvalue", generator.dispvalue, not float(generator.dispvalue or 0) > 0),
               ("status", generator.status, model_name(generator.status).lower() == "variable"))
    dispatch = [f"{slot}={value}" for slot, value, followed in follows if value is not None and not followed]
    if dispatch:
        raise ValueError(f"Generator {generator.name}: yearly={generator.yearly} with {', '.join(dispatch)}; only a "
                         "generator that follows its shape is mapped (S9)")


def schedule_points(native) -> dict[str, loadshape.DevicePoints]:
    """Each machine's yearly schedule (``<mRID>_yearly``): -kW x mult and -kvar x mult at each sample (the load
    sign; engine-checked), p only for model 3 (its q is the control's)."""
    points, defaults = {}, dss_defaults(NATIVE_CLASS)
    for original in native.list_by_class(NATIVE_CLASS):
        shape = loadshape.device_shape(native, original, f"Generator {original.name}")
        if shape is None:
            continue
        generator, _ = fill_defaults(FIELDS, original, defaults)
        kw, kvar = float(generator.kW), dispatched_kvar(native.assignments(original))
        regulated = model_name(generator.model) == _PV_BUS
        key = mrid(PREFIX, generator.name, lowercase=True) + loadshape.DEVICE_SCHEDULE_SUFFIX
        points[key] = loadshape.DevicePoints(loadshape.point_times(shape), [-kw * value + 0.0 for value in shape.mult],
                                             None if regulated else [-kvar * value + 0.0 for value in shape.mult])
    return points


def map_generator(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Generator`` of a DSS model as one ``generator`` document; ``container`` is the Feeder mRID."""
    generators = native.list_by_class(NATIVE_CLASS)
    if not generators:
        return Document(name="generator", statements=[], profile=CIM_PROFILE)
    defaults = dss_defaults(NATIVE_CLASS)
    machines, controls, updates, schedules = [], [], [], []
    for original in generators:
        _check(original)
        generator, defaulted = fill_defaults(FIELDS, original, defaults)
        label = f"Generator {generator.name}"
        delta = is_delta(generator.conn)
        terminal = device_terminal(label, generator.bus1, int(generator.phases), delta, buses)
        kw = float(generator.kW)
        kvar = dispatched_kvar(native.assignments(original))
        kva = float(generator.kVA) if generator.kVA is not None else KVA_PER_KW * abs(kw)
        rated_kv = line_kv(float(generator.kv), terminal)
        machine = mrid(PREFIX, generator.name, lowercase=True)
        model = model_name(generator.model)
        max_q = min_q = None
        if model == _PV_BUS:
            max_q, min_q = reactive_limits(native.assignments(original), kvar)
            control = f"{machine}_ctrl"
            target_kv = float(generator.Vpu) * rated_kv
            controls.append(Row([control, cell(target_kv), f"{machine}_T1"],
                                comment=f"derived: targetValue (kV) = Vpu={cell(float(generator.Vpu))} x ratedU"))
            updates.append(Row([machine, control]))
        notes = [f"model {model}: {_MAPPED_MODELS[model]}" if model != "ConstantPQ" else None,
                 "kVA defaulted to 1.2 x kW" if generator.kVA is None else None, defaulted,
                 untranscribed_values(FIELDS, generator)]
        machines.append(Row([
            machine, str(generator.name), terminal.bus, phases_cell(terminal.phases), cell(kva), cell(rated_kv), cell(-kw + 0.0),
            cell(-kvar + 0.0), cell(max_q), cell(min_q), cell(not delta), cell(generator.enabled),
            terminal.system.base_voltage,
        ], comment="\n".join(note for note in notes if note) or None))
        if loadshape.device_shape(native, original, label) is not None:
            schedules.append(loadshape.device_schedule_row(machine, generator))
    columns = [Column("mRID"), Column("name"), Column("node"), Column("phases"), Column("ratedS", "kVA"),
               Column("ratedU", "kV"), Column("p", "kW"), Column("q", "kVAr"), Column("maxQ", "kVAr"),
               Column("minQ", "kVAr"), Column("earthing"), Column("normallyInService"), Column("BaseVoltage"),
               Column("type", default="generator"), Column("operatingMode", default="generator"),
               Column("EquipmentContainer", default=container)]
    statements = [Table(_MACHINE, columns, machines, comment="p = -kW, q = -kvar (the load sign)")]
    if controls:
        statements.append(Table(_CONTROL, [Column("mRID"), Column("targetValue"), Column("Terminal"),
                                           Column("targetValueUnitMultiplier", default="k"),
                                           Column("mode", default="voltage"), Column("discrete", default="false"),
                                           Column("enabled", default="true"), Column("targetDeadband", default="0")],
                                controls, comment="model 3 (PV bus): the machine regulates its own terminal"))
        statements.append(Table(_MACHINE, [Column("mRID"), Column("RegulatingControl"),
                                           Column("controlEnabled", default="true")], updates, update=True))
    if schedules:
        statements.append(loadshape.device_schedules(schedules))
    return Document(name="generator", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(generators)))
