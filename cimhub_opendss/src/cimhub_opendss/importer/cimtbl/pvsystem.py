"""OpenDSS ``PVSystem`` -> ``pvsystem.cimtbl``: a ``PowerElectronicsConnection`` and its ``PhotoVoltaicUnit``.

p is the engine's snapshot dispatch at rated voltage: the panel's Pmpp x irradiance capped at Pmpp x %Pmpp, off
when the panel is below %Cutout of kVA, and cut to fit kVA with q kept (``pv_power``). irradiance is also copied, to
the gridappsd extension ``PhotoVoltaicUnit.irradiance``. q is kvar or comes from pf, whichever the deck assigned last (the
engine's rule; S4b-8). An inverter that is off still gives a set kvar unless ``VarFollowInverter`` (engine-checked).
The load sign: generation is negative p, q = -kvar (S4b-1).

A ``yearly`` LoadShape scales the irradiance (engine-checked): the PV's own ``EnergyConnectionSchedule``, its p and
q at each sample in the Parquet sidecar, each ``pv_power`` at irradiance x mult (``schedule_points``, S9). A sample
whose panel power falls between %Cutout and %Cutin raises: the engine keeps the inverter on or off as it was.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#pvsystem``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import loadshape
from cimhub_opendss.importer.cimtbl.injection import device_terminal, inverter_power, is_delta, reactive_power
from cimhub_opendss.importer.cimtbl.inverter import CONNECTION, connection_columns, connection_row, unit_id
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Pvsystem
PREFIX = "pv_"

_UNIT = "PhotoVoltaicUnit"
_NO_DECK = "no deck in the sweep sets it, so a mapping waits for one"
_NOT_MAPPED = "raises when set: " + _NO_DECK
_SHAPE = "a time-series curve; a snapshot does not use it (DSS-11)"
_DYNAMICS = "a dynamics setting; no home in the network profile parts"
_HARMONIC = "harmonics model; no home in the network profile parts"

FIELDS = {
    "name": Field("copied", ((CONNECTION, "name", None),), "mRID = pv_ + name, lowercased; the unit is <mRID>_unit"),
    "phases": Field("structural", note="the conductor count; default 3"),
    "bus1": Field("structural", note="node and phases, by the S4 shared phase rule"),
    "kv": Field("derived", note="ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); not checked against the "
                                "bus; default 12.47"),
    "irradiance": Field("copied", ((_UNIT, "irradiance", "kW/m2"),), "also p (pv_power); default 1"),
    "Pmpp": Field("copied", ((_UNIT, "maxP", "kW"),), "also p (pv_power); default 500"),
    "pct_Pmpp": Field("derived", note="p is capped at Pmpp x %Pmpp / 100 (pv_power); default 100"),
    "Temperature": Field("untranscribed", note="acts only through a P-TCurve, which raises"),
    "pf": Field("derived", note="q = -kW x tan(acos abs(pf)) x sign(pf), unless kvar was assigned after it "
                                "(the last of the two wins, S4b-8); default 1"),
    "conn": Field("mapped", ((CONNECTION, "phaseConnection", None),), "wye -> Y, delta -> D; default wye"),
    "kvar": Field("derived", note="q (kVAr) = -kvar (the load sign), unless pf was assigned after it"),
    "kVA": Field("copied", ((CONNECTION, "ratedS", "kVA"),), "also caps p (var priority); default 500"),
    "pct_Cutin": Field("structural", note="acts only after the inverter turns off; the snapshot state uses %Cutout; "
                                          "a yearly sample between %Cutout and %Cutin raises (S9); default 20"),
    "pct_Cutout": Field("derived", note="p = 0 when Pmpp x irradiance is below %Cutout of kVA, q too unless kvar is "
                                        "set (VarFollowInverter); default 20"),
    "EffCurve": Field("structural", note="raises: an efficiency curve changes the snapshot power"),
    "P_TCurve": Field("structural", note="raises: a temperature curve changes the snapshot power"),
    "pct_R": Field("untranscribed", note=_DYNAMICS),
    "pct_X": Field("untranscribed", note=_DYNAMICS),
    "model": Field("structural", note="1 (constant P, PF) only; any other raises (ieee9500's Mode=7 is model=7, "
                                      "which the engine rejects too); default 1"),
    "Vminpu": Field("derived", note="maxIFault = 1 / Vminpu (the engine's CIM export); default 0.9"),
    "Vmaxpu": Field("untranscribed", note="above it the engine models the PV as constant Z; a power-flow setting"),
    "Balanced": Field("structural", note="raises when yes: " + _NO_DECK),
    "LimitCurrent": Field("structural", note="raises when yes: " + _NO_DECK),
    "yearly": Field("mapped", ((loadshape.DEVICE_SCHEDULE, "name", None),),
                    "the PV's EnergyConnectionSchedule <mRID>_yearly: pv_power at irradiance x mult per sample (S9)"),
    "daily": Field("untranscribed", note=_SHAPE),
    "duty": Field("untranscribed", note=_SHAPE),
    "Tyearly": Field("untranscribed", note=_SHAPE),
    "Tdaily": Field("untranscribed", note=_SHAPE),
    "Tduty": Field("untranscribed", note=_SHAPE),
    "class_class": Field("untranscribed", note="a DSS report grouping"),
    "UserModel": Field("structural", note=_NOT_MAPPED),
    "UserData": Field("structural", note=_NOT_MAPPED),
    "debugtrace": Field("untranscribed", note="a DSS debugging switch"),
    "VarFollowInverter": Field("derived", note="yes: an inverter that is off gives no kvar either (pv_power, "
                                               "engine-checked); default no"),
    "DutyStart": Field("untranscribed", note=_SHAPE),
    "WattPriority": Field("structural", note="raises when yes: " + _NO_DECK + " (var priority is mapped)"),
    "PFPriority": Field("structural", note="raises when yes: " + _NO_DECK),
    "pct_PminNoVars": Field("structural", note="raises when nonzero: " + _NO_DECK),
    "pct_PminkvarMax": Field("structural", note="raises when nonzero: " + _NO_DECK),
    "kvarMax": Field("copied", ((CONNECTION, "maxQ", "kVAr"),), "default kVA"),
    "kvarMaxAbs": Field("derived", note="minQ (kVAr) = -kvarMaxAbs; default kVA"),
    "kVDC": Field("untranscribed", note=_DYNAMICS),
    "Kp": Field("untranscribed", note=_DYNAMICS),
    "PITol": Field("untranscribed", note=_DYNAMICS),
    "SafeVoltage": Field("untranscribed", note=_DYNAMICS),
    "SafeMode": Field("untranscribed", note=_DYNAMICS),
    "DynamicEq": Field("untranscribed", note=_DYNAMICS),
    "DynOut": Field("untranscribed", note=_DYNAMICS),
    "ControlMode": Field("structural", note="GFL only; GFM raises (" + _NO_DECK + ")"),
    "AmpLimit": Field("untranscribed", note=_DYNAMICS),
    "AmpLimitGain": Field("untranscribed", note=_DYNAMICS),
    "spectrum": Field("untranscribed", note=_HARMONIC),
    "basefreq": Field("untranscribed", note="no home on an inverter"),
    "enabled": Field("copied", ((CONNECTION, "normallyInService", None),), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = ("EffCurve", "P_TCurve", "UserModel", "UserData")
_YES_UNMAPPED = ("Balanced", "LimitCurrent", "WattPriority", "PFPriority")
_NONZERO_UNMAPPED = ("pct_PminNoVars", "pct_PminkvarMax")

_PROVENANCE = """OpenDSS PVSystem -> PowerElectronicsConnection + PhotoVoltaicUnit on its bus: the snapshot dispatch at
rated voltage, in the load sign (generation is negative p).
Source table: PVSystem (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#pvsystem"""


class PvPower(NamedTuple):
    kw: float
    kvar: float
    off: bool


def pv_power(label: str, *, pmpp: float, irradiance: float, pct_pmpp: float, kva: float, pct_cutout: float,
             pf: float, kvar: float | None, var_follow: bool = False) -> PvPower:
    """The engine's snapshot output of a PV (generator sign): off when the panel's power (Pmpp x irradiance) is
    below %Cutout of kVA, else that power capped at %Pmpp of Pmpp, with its kvar (``kvar``, or from ``pf`` when it
    is ``None``), cut to fit kVA (var priority). Off, it gives no kW, and a set ``kvar`` unless ``var_follow``
    (``VarFollowInverter``; engine-checked)."""
    panel = pmpp * irradiance
    if panel < pct_cutout / 100 * kva:
        return PvPower(0.0, float(kvar) if kvar is not None and not var_follow else 0.0, True)
    available = min(panel, pmpp * pct_pmpp / 100)
    q = float(kvar) if kvar is not None else reactive_power(label, available, pf)
    return PvPower(inverter_power(label, available, q, kva), q, False)


def _check(pv) -> None:
    """Raise on what the mapping does not cover (on the record as written, before defaults)."""
    unmapped = [slot for slot in _UNMAPPED if getattr(pv, slot) not in (None, [])]
    unmapped += [slot for slot in _YES_UNMAPPED if getattr(pv, slot)]
    unmapped += [slot for slot in _NONZERO_UNMAPPED if getattr(pv, slot) not in (None, 0)]
    if pv.ControlMode is not None and str(pv.ControlMode).upper() != "GFL":
        unmapped.append(f"ControlMode={pv.ControlMode}")
    if unmapped:
        raise ValueError(f"PVSystem {pv.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets "
                         "them)")
    if pv.model is not None and int(pv.model) != 1:
        raise ValueError(f"PVSystem {pv.name}: model={pv.model} is not mapped (model 1 is; the engine rejects "
                         "anything but 1, 2 and 3)")


def _output(native, original, pv, irradiance: float) -> PvPower:
    """``pv_power`` of a PV (defaults filled) at ``irradiance``; q by kvar or pf, whichever the deck assigned last."""
    return pv_power(f"PVSystem {pv.name}", pmpp=float(pv.Pmpp), irradiance=irradiance, pct_pmpp=float(pv.pct_Pmpp),
                    kva=float(pv.kVA), pct_cutout=float(pv.pct_Cutout), pf=float(pv.pf),
                    kvar=pv.kvar if native.last_of(original, "pf", "kvar") == "kvar" else None,
                    var_follow=bool(pv.VarFollowInverter))


def check_cutin_band(pv, shape: loadshape.Shape) -> None:
    """Raise on a sample of ``shape`` that puts the panel between %Cutout and %Cutin of kVA (``pv`` with defaults
    filled): the inverter stays as it was, which depends on the samples before (and on a snapshot solved first)."""
    cutout, cutin = (float(pv.pct_Cutout) / 100 * float(pv.kVA), float(pv.pct_Cutin) / 100 * float(pv.kVA))
    for number, value in enumerate(shape.mult, start=1):
        panel = float(pv.Pmpp) * (float(pv.irradiance) * value)
        if cutout <= panel < cutin:
            raise ValueError(f"PVSystem {pv.name}: sample {number} of yearly={pv.yearly} puts the panel at "
                             f"{panel:g} kW, between %Cutout ({cutout:g}) and %Cutin ({cutin:g}); the engine keeps "
                             "the inverter as it was, which is not mapped")


def schedule_points(native) -> dict[str, loadshape.DevicePoints]:
    """Each PV's yearly schedule (``<mRID>_yearly``): -``pv_power`` at irradiance x mult at each sample (the load
    sign; engine-checked). A sample between %Cutout and %Cutin raises (``check_cutin_band``)."""
    points, defaults = {}, dss_defaults(NATIVE_CLASS)
    for original in native.list_by_class(NATIVE_CLASS):
        shape = loadshape.device_shape(native, original, f"PVSystem {original.name}")
        if shape is None:
            continue
        pv, _ = fill_defaults(FIELDS, original, defaults)
        check_cutin_band(pv, shape)
        outputs = [_output(native, original, pv, float(pv.irradiance) * value) for value in shape.mult]
        points[mrid(PREFIX, pv.name, lowercase=True) + loadshape.DEVICE_SCHEDULE_SUFFIX] = loadshape.DevicePoints(
            loadshape.point_times(shape), [-output.kw + 0.0 for output in outputs],
            [-output.kvar + 0.0 for output in outputs])
    return points


def map_pvsystem(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``PVSystem`` of a DSS model as one ``pvsystem`` document; ``container`` is the Feeder mRID."""
    pvs = native.list_by_class(NATIVE_CLASS)
    if not pvs:
        return Document(name="pvsystem", statements=[], profile=CIM_PROFILE)
    defaults = dss_defaults(NATIVE_CLASS)
    connections, units, schedules = [], [], []
    for original in pvs:
        _check(original)
        pv, defaulted = fill_defaults(FIELDS, original, defaults)
        label = f"PVSystem {pv.name}"
        terminal = device_terminal(label, pv.bus1, int(pv.phases), is_delta(pv.conn), buses)
        power = _output(native, original, pv, float(pv.irradiance))
        notes = ["off: below %Cutout of kVA" if power.off else None, defaulted, untranscribed_values(FIELDS, pv)]
        connections.append(connection_row(PREFIX, pv, terminal, kva=float(pv.kVA), p=-power.kw, q=-power.kvar,
                                          comment="\n".join(note for note in notes if note) or None))
        units.append(Row([unit_id(PREFIX, pv), cell(float(pv.Pmpp)), cell(0.0), cell(float(pv.irradiance)),
                          connections[-1].cells[0]]))
        shape = loadshape.device_shape(native, original, label)
        if shape is not None:
            check_cutin_band(pv, shape)
            schedules.append(loadshape.device_schedule_row(connections[-1].cells[0], pv))
    statements = [
        Table(CONNECTION, connection_columns(container), connections,
              comment="derived: p = -(Pmpp x irradiance, capped at %Pmpp of Pmpp, cut to fit kVA), 0 when "
                      "Pmpp x irradiance is below %Cutout (pv_power); q = -kvar"),
        Table(_UNIT, [Column("mRID"), Column("maxP", "kW"), Column("minP", "kW"), Column("irradiance", "kW/m2"),
                      Column("PowerElectronicsConnection"), Column("EquipmentContainer", default=container)], units),
    ]
    if schedules:
        statements.append(loadshape.device_schedules(schedules))
    return Document(name="pvsystem", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(pvs)))
