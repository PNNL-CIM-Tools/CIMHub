"""OpenDSS ``Load`` -> ``load.cimtbl``: one ``EnergyConsumer`` per load (DSS-7).

p and q are the deck's kW and kvar (q from ``pf`` when kvar is unset). The voltage response is a shared
``LoadResponseCharacteristic``: ``zip_constant_pq`` / ``_z`` / ``_i`` from the fixed core ``zip_fractions.cimtbl``
for models 1, 2 and 5, and one exponential row ``exp_<CVRwatts>_<CVRvars>`` in this file per pair model 4 uses.
CIM gives a load no rated voltage (p is at the BaseVoltage), so ``kV`` must agree with its bus.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#load``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, untranscribed_values
from cimhub_core.load_response import ZIP_CONSTANT_I, ZIP_CONSTANT_PQ, ZIP_CONSTANT_Z
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl.injection import device_terminal, is_delta, rated_phase_kv
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Load
PREFIX = "ld_"

_CONSUMER = "EnergyConsumer"
_RESPONSE = "LoadResponseCharacteristic"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_SHAPE = "a LoadShape reference; LoadShape is not mapped (DSS-11)"
_SOLVER = "DSS solution control; no home in the network profile parts"
_HARMONIC = "harmonics model; no home in the network profile parts"
_ORDER = ("raises with kW: the engine takes whichever of kW, kVA and xfkVA comes last, and the record keeps no "
          "order")

FIELDS = {
    "name": Field("copied", ((_CONSUMER, "name", None),), "mRID = ld_ + name, lowercased"),
    "bus1": Field("structural", note="node; the nodes give the phases: 1/2/3 are A/B/C, and s1/s2 on a "
                                     "split-phase island (DSS-5); an omitted node is the DSS default (conductor k "
                                     "on node k)"),
    "phases": Field("structural", note="the conductor count; default 3. On a split-phase island 2 wye phases on "
                                       "1.2 are two legs to neutral (s1s2, kV is LL by the sqrt 3 rule)"),
    "kV": Field("structural", note="checked, not written: the phase voltage it gives (LL for delta and 2-3 "
                                   "phases, LN for 1-phase wye) must be within 1 % of the bus's, else it raises; "
                                   "CIM p is at the BaseVoltage"),
    "kW": Field("copied", ((_CONSUMER, "p", "kW"),), "consumption is positive p"),
    "pf": Field("derived", note="q (kVAr) = kW x tan(acos abs(pf)) with the sign of pf, when kvar is unset "
                                "(kvar wins in either order, engine-checked); default 0.88"),
    "model": Field("mapped", ((_CONSUMER, "LoadResponse", None),),
                   "1 zip_constant_pq, 2 zip_constant_z, 5 zip_constant_i, 4 exp_<CVRwatts>_<CVRvars>; 3, 6, 7, "
                   "8 raise; default 1"),
    "yearly": Field("untranscribed", note=_SHAPE),
    "daily": Field("untranscribed", note=_SHAPE),
    "duty": Field("untranscribed", note=_SHAPE),
    "growth": Field("untranscribed", note="a GrowthShape reference; not mapped (DSS-11)"),
    "conn": Field("mapped", ((_CONSUMER, "phaseConnection", None), (_CONSUMER, "grounded", None)),
                  "wye -> Y, grounded; delta -> D, not grounded; default wye"),
    "kvar": Field("copied", ((_CONSUMER, "q", "kVAr"),)),
    "Rneut": Field("structural", note=_NOT_MAPPED + " (>= 0: a wye neutral impedance)"),
    "Xneut": Field("structural", note=_NOT_MAPPED),
    "status": Field("untranscribed", note="Fixed/Exempt: whether load multipliers scale it; " + _SOLVER),
    "load_class": Field("untranscribed", note="a DSS report grouping"),
    "Vminpu": Field("untranscribed", note="below it the engine models the load as constant Z; " + _SOLVER),
    "Vmaxpu": Field("untranscribed", note="above it the engine models the load as constant Z; " + _SOLVER),
    "Vminnorm": Field("untranscribed", note="an EnergyMeter UE threshold; " + _SOLVER),
    "Vminemerg": Field("untranscribed", note="an EnergyMeter EEN threshold; " + _SOLVER),
    "xfkVA": Field("structural", note="raises: not mapped, and with kW the engine takes whichever comes last "
                                      "(K1 only, behind DSS-10)"),
    "allocationfactor": Field("structural", note="raises: it scales xfkVA"),
    "kVA": Field("derived", note="with kW unset: p = kVA x abs(pf), q = kVA x sin(acos abs(pf)) with the sign of pf "
                                 "(ACEP_PSIL); " + _ORDER),
    "pct_mean": Field("untranscribed", note="a Monte Carlo setting; " + _SOLVER),
    "pct_stddev": Field("untranscribed", note="a Monte Carlo setting; " + _SOLVER),
    "CVRwatts": Field("copied", ((_RESPONSE, "pVoltageExponent", None),),
                      "model 4 only (the exp_ row); default 1; unused by other models"),
    "CVRvars": Field("copied", ((_RESPONSE, "qVoltageExponent", None),),
                     "model 4 only (the exp_ row); default 2; unused by other models"),
    "kwh": Field("untranscribed", note="sizes the load only in the AllocateLoads command"),
    "kwhdays": Field("untranscribed", note="sizes the load only in the AllocateLoads command"),
    "Cfactor": Field("untranscribed", note="sizes the load only in the AllocateLoads command"),
    "CVRcurve": Field("untranscribed", note=_SHAPE),
    "NumCust": Field("copied", ((_CONSUMER, "customerCount", None),), "default 1"),
    "ZIPV": Field("untranscribed", note="used only by model 8, which raises"),
    "pct_SeriesRL": Field("untranscribed", note=_HARMONIC),
    "RelWeight": Field("untranscribed", note="a reliability weighting"),
    "Vlowpu": Field("untranscribed", note="below it the engine models the load as open; " + _SOLVER),
    "puXharm": Field("untranscribed", note=_HARMONIC),
    "XRharm": Field("untranscribed", note=_HARMONIC),
    "spectrum": Field("untranscribed", note=_HARMONIC),
    "basefreq": Field("untranscribed", note="no home on a load"),
    "enabled": Field("copied", ((_CONSUMER, "normallyInService", None),), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

#: How far a load's kV may sit from its bus's phase voltage (rounding: 2.4 against 4.16 / sqrt 3 is 0.07 %).
KV_TOLERANCE = 0.01
_ZIP_OF_MODEL = {"ConstantPQ": ZIP_CONSTANT_PQ, "ConstantZ": ZIP_CONSTANT_Z, "ConstantI": ZIP_CONSTANT_I}
_EXPONENTIAL = "CVR"
_UNMAPPED = tuple(slot for slot, field in FIELDS.items() if field.note.startswith(_NOT_MAPPED))

_PROVENANCE = """OpenDSS Load -> EnergyConsumer on its bus (DSS-7); p, q as given (q from pf when kvar is unset).
Models 1, 2, 5 name the shared zip_fractions rows; model 4 an exp_<CVRwatts>_<CVRvars> row here.
Source table: Load (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#load"""


def reactive_power(kw: float, pf: float) -> float:
    """kvar of a load given kW and pf: kW x tan(acos abs(pf)), with the sign of pf (negative is leading)."""
    return math.copysign(kw * math.tan(math.acos(abs(pf))), pf)


def power_from_kva(kva: float, pf: float) -> tuple[float, float]:
    """(kW, kvar) of a load given kVA and pf, as the engine computes them when kW is unset."""
    kw = kva * abs(pf)
    return kw, reactive_power(kw, pf)


def exponential_mrid(p_exponent: float, q_exponent: float) -> str:
    """The mRID of an exponential load model: ``exp_0.8_3``."""
    return f"exp_{p_exponent:g}_{q_exponent:g}"


def _check(load) -> None:
    """Raise on what the mapping does not cover (on the record as written, before defaults)."""
    unmapped = [slot for slot in _UNMAPPED if getattr(load, slot) is not None and not (
        slot == "Rneut" and float(load.Rneut) < 0)]
    if unmapped:
        raise ValueError(f"Load {load.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets them)")
    if load.kW is not None and load.kVA is not None:
        raise ValueError(f"Load {load.name}: kW with kVA; the engine takes whichever comes last, and the record "
                         "keeps no order")
    if load.xfkVA is not None or load.allocationfactor is not None:
        raise ValueError(f"Load {load.name}: xfkVA/allocationfactor not mapped (with kW the engine takes "
                         "whichever comes last, and the record keeps no order)")


def _used_defaults(load, defaults: dict) -> dict:
    """The defaults this load reads: not the slots that raise when set, not kW when kVA sizes it, not pf when kvar
    is given, not the CVR exponents unless it is model 4, so the row comment names only defaults that reach a
    value."""
    model = load.model if load.model is not None else defaults["model"]
    unused = {*_UNMAPPED, "xfkVA", "allocationfactor"}  # set, they raise; unset, they reach no value
    if load.kVA is not None:
        unused.add("kW")
    if load.kvar is not None:
        unused.add("pf")
    if str(getattr(model, "text", model)) != _EXPONENTIAL:
        unused |= {"CVRwatts", "CVRvars"}
    return {slot: value for slot, value in defaults.items() if slot not in unused}


def _power(original, load) -> tuple[float, float]:
    """(kW, kvar) of a load with defaults filled; ``original`` says which slots the deck set."""
    if original.kVA is not None:
        return power_from_kva(float(load.kVA), float(load.pf))
    kw = float(load.kW)
    return kw, float(load.kvar) if load.kvar is not None else reactive_power(kw, float(load.pf))


def _response(load) -> str:
    model = str(getattr(load.model, "text", load.model))
    if model in _ZIP_OF_MODEL:
        return _ZIP_OF_MODEL[model]
    if model == _EXPONENTIAL:
        return exponential_mrid(float(load.CVRwatts), float(load.CVRvars))
    raise ValueError(f"Load {load.name}: model {model} is not mapped (models 1, 2, 4 and 5 are)")


def map_load(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Load`` of a DSS model as one ``load`` document; ``container`` is the Feeder mRID."""
    loads = native.list_by_class(NATIVE_CLASS)
    defaults = dss_defaults(NATIVE_CLASS)
    rows, exponents = [], {}
    for original in loads:
        _check(original)
        load, defaulted = fill_defaults(FIELDS, original, _used_defaults(original, defaults))
        label = f"Load {load.name}"
        terminal = device_terminal(label, load.bus1, int(load.phases), is_delta(load.conn), buses)
        expected = rated_phase_kv(terminal)
        if abs(float(load.kV) / expected - 1) > KV_TOLERANCE:
            raise ValueError(f"{label}: kV={load.kV} on bus {terminal.bus}, whose {terminal.phases} "
                             f"{terminal.connection} phase voltage is {expected:.6g} kV; CIM has no load rating, "
                             "so p would be at the wrong voltage")
        response = _response(load)
        if response.startswith("exp_"):
            exponents[response] = (float(load.CVRwatts), float(load.CVRvars))
        kw, kvar = _power(original, load)
        rows.append(Row([
            mrid(PREFIX, load.name, lowercase=True), str(load.name), terminal.bus, terminal.phases,
            terminal.connection, cell(terminal.grounded), cell(kw), cell(kvar), cell(int(load.NumCust)), response,
            cell(load.enabled), terminal.system.base_voltage,
        ], comment="\n".join(part for part in (defaulted, untranscribed_values(FIELDS, load)) if part) or None))
    if not rows:
        return Document(name="load", statements=[], profile=CIM_PROFILE)
    statements = []
    if exponents:
        statements.append(Table(_RESPONSE, [Column("mRID"), Column("exponentModel"), Column("pVoltageExponent"),
                                            Column("qVoltageExponent")],
                                [Row([key, "true", cell(p), cell(q)]) for key, (p, q) in sorted(exponents.items())],
                                comment="model 4 (CVR): p = p0 (V/V0)^CVRwatts, q = q0 (V/V0)^CVRvars"))
    columns = [Column("mRID"), Column("name"), Column("node"), Column("phases"), Column("phaseConnection"),
               Column("grounded"), Column("p", "kW"), Column("q", "kVAr"), Column("customerCount"),
               Column("LoadResponse"), Column("normallyInService"), Column("BaseVoltage"),
               Column("EquipmentContainer", default=container)]
    statements.append(Table(_CONSUMER, columns, rows))
    return Document(name="load", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(loads)))
