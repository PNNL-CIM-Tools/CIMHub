"""OpenDSS ``PVSystem`` -> ``pvsystem.cimtbl``: a ``PowerElectronicsConnection`` and its ``PhotoVoltaicUnit``.

p is the engine's snapshot dispatch at rated voltage: Pmpp x irradiance x %Pmpp, off below %Cutout of kVA, and
cut to fit kVA with q kept (``pv_power``). q is kvar or comes from pf, whichever the deck assigned last (the
engine's rule; S4b-8). The load sign:
generation is negative p, q = -kvar (S4b-1).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#pvsystem``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl.injection import device_terminal, inverter_power, is_delta, reactive_power
from cimhub_opendss.importer.cimtbl.inverter import CONNECTION, connection_columns, connection_row, unit_id
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Pvsystem
PREFIX = "pv_"

_UNIT = "PhotoVoltaicUnit"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_SHAPE = "a time-series curve; a snapshot does not use it (DSS-11)"
_DYNAMICS = "a dynamics setting; no home in the network profile parts"
_HARMONIC = "harmonics model; no home in the network profile parts"

FIELDS = {
    "name": Field("copied", ((CONNECTION, "name", None),), "mRID = pv_ + name, lowercased; the unit is <mRID>_unit"),
    "phases": Field("structural", note="the conductor count; default 3"),
    "bus1": Field("structural", note="node and phases, by the S4 shared phase rule"),
    "kv": Field("derived", note="ratedU (kV, LL) = kv, x sqrt 3 for 1-phase wye (S4b-4); not checked against the "
                                "bus; default 12.47"),
    "irradiance": Field("derived", note="p: Pmpp x irradiance x %Pmpp / 100 (pv_power); default 1"),
    "Pmpp": Field("copied", ((_UNIT, "maxP", "kW"),), "also p (pv_power); default 500"),
    "pct_Pmpp": Field("derived", note="p (pv_power); default 100"),
    "Temperature": Field("untranscribed", note="acts only through a P-TCurve, which raises"),
    "pf": Field("derived", note="q = -kW x tan(acos abs(pf)) with the sign of pf, unless kvar was assigned after it "
                                "(the last of the two wins, S4b-8); default 1"),
    "conn": Field("mapped", ((CONNECTION, "phaseConnection", None),), "wye -> Y, delta -> D; default wye"),
    "kvar": Field("derived", note="q (kVAr) = -kvar (the load sign), unless pf was assigned after it"),
    "kVA": Field("copied", ((CONNECTION, "ratedS", "kVA"),), "also caps p (var priority); default 500"),
    "pct_Cutin": Field("untranscribed", note="acts only after the inverter turns off; the snapshot state uses "
                                             "%Cutout"),
    "pct_Cutout": Field("derived", note="p = q = 0 when Pmpp x irradiance x %Pmpp is below %Cutout of kVA; "
                                        "default 20"),
    "EffCurve": Field("structural", note="raises: an efficiency curve changes the snapshot power"),
    "P_TCurve": Field("structural", note="raises: a temperature curve changes the snapshot power"),
    "pct_R": Field("untranscribed", note=_DYNAMICS),
    "pct_X": Field("untranscribed", note=_DYNAMICS),
    "model": Field("structural", note="1 (constant P, PF) only; any other raises (ieee9500's Mode=7 is model=7, "
                                      "which the engine rejects too); default 1"),
    "Vminpu": Field("derived", note="maxIFault = 1 / Vminpu (the engine's CIM export); default 0.9"),
    "Vmaxpu": Field("untranscribed", note="above it the engine models the PV as constant Z; a power-flow setting"),
    "Balanced": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "LimitCurrent": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "yearly": Field("untranscribed", note=_SHAPE),
    "daily": Field("untranscribed", note=_SHAPE),
    "duty": Field("untranscribed", note=_SHAPE),
    "Tyearly": Field("untranscribed", note=_SHAPE),
    "Tdaily": Field("untranscribed", note=_SHAPE),
    "Tduty": Field("untranscribed", note=_SHAPE),
    "class_class": Field("untranscribed", note="a DSS report grouping"),
    "UserModel": Field("structural", note=_NOT_MAPPED),
    "UserData": Field("structural", note=_NOT_MAPPED),
    "debugtrace": Field("untranscribed", note="a DSS debugging switch"),
    "VarFollowInverter": Field("untranscribed", note="acts only with an InvControl"),
    "DutyStart": Field("untranscribed", note=_SHAPE),
    "WattPriority": Field("structural", note="raises when yes: " + _NOT_MAPPED + " (var priority is mapped)"),
    "PFPriority": Field("structural", note="raises when yes: " + _NOT_MAPPED),
    "pct_PminNoVars": Field("structural", note="raises when nonzero: " + _NOT_MAPPED),
    "pct_PminkvarMax": Field("structural", note="raises when nonzero: " + _NOT_MAPPED),
    "kvarMax": Field("copied", ((CONNECTION, "maxQ", "kVAr"),), "default kVA"),
    "kvarMaxAbs": Field("derived", note="minQ (kVAr) = -kvarMaxAbs; default kVA"),
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
             pf: float, kvar: float | None) -> PvPower:
    """The engine's snapshot output of a PV (generator sign): off below %Cutout of kVA, else the available
    power with its kvar (``kvar``, or from ``pf`` when it is ``None``), cut to fit kVA (var priority)."""
    available = pmpp * irradiance * pct_pmpp / 100
    if available < pct_cutout / 100 * kva:
        return PvPower(0.0, 0.0, True)
    q = float(kvar) if kvar is not None else reactive_power(available, pf)
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


def map_pvsystem(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``PVSystem`` of a DSS model as one ``pvsystem`` document; ``container`` is the Feeder mRID."""
    pvs = native.list_by_class(NATIVE_CLASS)
    if not pvs:
        return Document(name="pvsystem", statements=[], profile=CIM_PROFILE)
    defaults = dss_defaults(NATIVE_CLASS)
    connections, units = [], []
    for original in pvs:
        _check(original)
        pv, defaulted = fill_defaults(FIELDS, original, defaults)
        label = f"PVSystem {pv.name}"
        terminal = device_terminal(label, pv.bus1, int(pv.phases), is_delta(pv.conn), buses)
        kva = float(pv.kVA)
        power = pv_power(label, pmpp=float(pv.Pmpp), irradiance=float(pv.irradiance), pct_pmpp=float(pv.pct_Pmpp),
                         kva=kva, pct_cutout=float(pv.pct_Cutout), pf=float(pv.pf),
                         kvar=pv.kvar if native.last_of(original, "pf", "kvar") == "kvar" else None)
        notes = ["off: below %Cutout of kVA" if power.off else None, defaulted, untranscribed_values(FIELDS, pv)]
        connections.append(connection_row(PREFIX, pv, terminal, kva=kva, p=-power.kw, q=-power.kvar,
                                          comment="\n".join(note for note in notes if note) or None))
        units.append(Row([unit_id(PREFIX, pv), cell(float(pv.Pmpp)), cell(0.0), connections[-1].cells[0]]))
    statements = [
        Table(CONNECTION, connection_columns(container), connections,
              comment="derived: p = -(Pmpp x irradiance x %Pmpp, cut to fit kVA), 0 below %Cutout (pv_power); "
                      "q = -kvar"),
        Table(_UNIT, [Column("mRID"), Column("maxP", "kW"), Column("minP", "kW"),
                      Column("PowerElectronicsConnection"), Column("EquipmentContainer", default=container)], units),
    ]
    return Document(name="pvsystem", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(pvs)))
