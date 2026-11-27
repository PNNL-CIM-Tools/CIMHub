"""PhotoVoltaicUnit behind a PowerElectronicsConnection -> OpenDSS ``PVSystem`` (``EXPORT_MAPPING.md#pvsystem``).

One PVSystem per PV unit (``inverter.inverter_pieces``). ``Pmpp`` is the unit's maxP and ``kvar`` is q.
``irradiance`` is the unit's (the gridappsd extension), else its output over Pmpp. The engine's output is the
panel's Pmpp x irradiance capped at Pmpp x %Pmpp, so ``%Pmpp`` is written when CIM's p is below the panel's power
(a PV cut to fit kVA or held back), and the engine gives CIM's p. The engine switches a PV off when the panel's
power is below its default cut-out (20 % of kVA), so ``%Cutout=0`` is written for a running one.

A connection's own ``EnergyConnectionSchedule`` with points (S9) is its ``yearly`` LoadShape, which scales the
irradiance: mult = p / (Pmpp x irradiance) at each point, and ``%Cutin=0 %Cutout=0`` so that the engine gives each
point's p, low ones too. q is ``kvar`` when every point's q is the written kvar, else ``pf`` when q is in proportion
to p; another q raises, as does a p above the %Pmpp cap.
"""

from __future__ import annotations

import math

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_opendss.exporter import loadshape
from cimhub_core.getters.der import get_photovoltaic_unit
from cimhub_opendss.exporter.inverter import inverter_pieces
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.PowerElectronicsConnection,)
NATIVE_CLASS = schema.Pvsystem
NAMESPACE = "PVSystem"
#: the engine's default %Cutout: an available power below it of kVA switches the PV off (S4b engine rules)
ENGINE_CUTOUT_PERCENT = 20.0

_INVERTER = "the connection's, by the unit's share (inverter_pieces)"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names: the connection's for one unit, the unit's for several, <name>_<phase> per phase"),
    "phases": Slot("written", "the phase conductors; a delta across two is 1"),
    "bus1": Slot("written", "bus_ref of the phase conductors; a wye inverter's neutral is node 0"),
    "kv": Slot("written", "ratedU (kV, LL), / sqrt 3 for 1-phase wye (S4b-4 inverted)"),
    "irradiance": Slot("written", "the unit's irradiance (kW/m2); unset -> the unit's output / Pmpp "
                                  "(get_inverter_units p, generation sign)"),
    "Pmpp": Slot("written", "the unit's maxP (kW), x 1/n for one of n phases; unset raises, a minP other than 0 "
                            "raises"),
    "pct_Pmpp": Slot("rule", "100 x output / Pmpp when the output is below Pmpp x irradiance, else not written; an "
                             "output above it raises"),
    "pct_Cutout": Slot("rule", "0 when the output is above 0 and Pmpp x irradiance below the engine's 20 % of kVA, "
                               "or with a yearly shape; else not written"),
    "kvar": Slot("written", "the unit's share of q (generation sign: -q)"),
    "pf": Slot("rule", "with a yearly shape whose q is in proportion to p: p / hypot(p, q) with the sign of q; "
                       "else kvar carries q"),
    "conn": Slot("written", "phaseConnection Y/Yn -> wye, D -> delta; others raise"),
    "kVA": Slot("written", f"ratedS, {_INVERTER}"),
    "kvarMax": Slot("written", f"maxQ, {_INVERTER}; unset -> not written"),
    "kvarMaxAbs": Slot("written", f"-minQ, {_INVERTER}; unset -> not written"),
    "Vminpu": Slot("written", "1 / maxIFault (the importer's rule inverted); unset -> not written"),
    "model": Slot("not mapped", "model 1, the engine's default; others raise on import"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "yearly": Slot("written", "the connection's EnergyConnectionSchedule as a LoadShape, mult = p / (Pmpp x "
                              "irradiance) (S9); %Cutin, %Cutout 0 and q by kvar or pf with it"),
    "pct_Cutin": Slot("rule", "0 with a yearly shape, else not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "untranscribed or raising on import; not in CIM"))}


#: how far a point may stray from the rule it is checked against (relative, and absolute in kW)
POINT_TOL = 1e-6


def export(context) -> list:
    """One PVSystem per PhotoVoltaicUnit, its yearly LoadShape first when new."""
    records = []
    for connection in context.objects(*CIM_CLASSES):
        pieces = inverter_pieces(connection, cim.PhotoVoltaicUnit, NAMESPACE, context.names)
        # a schedule is the connection's: it maps when the connection is one PVSystem of one unit
        found = loadshape.device_schedule(context, connection, len(pieces) * len(connection.PowerElectronicsUnit)) \
            if pieces else None
        for piece in pieces:
            pv = _pvsystem(piece)
            if found is not None:
                records += _yearly(context, pv, piece, found)
            records.append(pv)
    return records


def _yearly(context, pv: schema.Pvsystem, piece, found) -> list[schema.Loadshape]:
    """Give ``pv`` its yearly shape (mult = p / panel), %Cutin, %Cutout and q rule; the new LoadShape records."""
    label = describe(found.schedule)
    if found.p is None:
        raise ValueError(f"{label}: no p; a PVSystem's shape scales its irradiance")
    panel = pv.Pmpp * pv.irradiance
    if panel <= 0:
        raise ValueError(f"{label}: Pmpp x irradiance is {panel} kW; a PVSystem's shape scales a panel above 0")
    below = [number for number, p in enumerate(found.p, start=1) if p < -POINT_TOL]
    if below:
        raise ValueError(f"{label}: points {below[:5]} are below 0 kW; a PVSystem only generates (the engine reads a "
                         "negative multiplier as 0)")
    cap = pv.Pmpp * pv.pct_Pmpp / 100 if pv.pct_Pmpp is not None else math.inf
    over = [number for number, p in enumerate(found.p, start=1) if p > cap + POINT_TOL]
    if over:
        raise ValueError(f"{label}: points {over[:5]} are above the {cap:g} kW the written %Pmpp caps the PV at")
    if found.q is not None and not _close(found.q, [piece.q] * len(found.q)):
        if piece.p == 0 or not _close(found.q, [p * piece.q / piece.p for p in found.p]):
            raise ValueError(f"{label}: its q is neither the PV's {piece.q:g} kvar nor in proportion to p; a PVSystem "
                             "gives one or the other")
        pv.kvar, pv.pf = None, math.copysign(piece.p / math.hypot(piece.p, piece.q), piece.q)
    pv.pct_Cutin, pv.pct_Cutout = 0.0, 0.0
    pv.yearly, shapes = loadshape.device_yearly(context, found, [p / panel for p in found.p])
    return shapes


def _close(values: list[float], expected: list[float]) -> bool:
    return all(math.isclose(value, other, rel_tol=POINT_TOL, abs_tol=POINT_TOL)
               for value, other in zip(values, expected))


def _pvsystem(piece) -> schema.Pvsystem:
    limits = get_photovoltaic_unit(piece.unit, "kW", "kW/m2", sign="generation")
    if limits.max_p is None or limits.max_p <= 0:
        raise ValueError(f"{describe(piece.unit)}: maxP {limits.max_p}; a PVSystem's Pmpp must be above 0")
    pmpp = limits.max_p * piece.unit_share
    if limits.min_p not in (None, 0):
        raise ValueError(f"{describe(piece.unit)}: minP {limits.min_p}; a PVSystem absorbs no power")
    if piece.p < 0:
        raise ValueError(f"{describe(piece.unit)}: p {-piece.p} kW into the PV; a PVSystem only generates")
    # fallback, when CIM has no irradiance: the output over Pmpp, so the panel gives exactly the output
    irradiance = limits.irradiance if limits.irradiance is not None else piece.p / pmpp
    panel = pmpp * irradiance
    if math.isclose(piece.p, panel, rel_tol=1e-9, abs_tol=1e-9):
        pct_pmpp = None
    elif piece.p < panel:
        pct_pmpp = 100 * piece.p / pmpp
    else:
        raise ValueError(f"{describe(piece.unit)}: p {piece.p} kW is above the panel's {panel} kW (maxP x "
                         f"irradiance {irradiance} kW/m2)")
    cutout = 0.0 if piece.p > 0 and panel < ENGINE_CUTOUT_PERCENT / 100 * piece.slots["kVA"] else None
    return NATIVE_CLASS(name=piece.name, Pmpp=pmpp, irradiance=irradiance, pct_Pmpp=pct_pmpp, kvar=piece.q,
                        pct_Cutout=cutout, **piece.slots)
