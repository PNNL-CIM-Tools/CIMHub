"""PhotoVoltaicUnit behind a PowerElectronicsConnection -> OpenDSS ``PVSystem`` (``EXPORT_MAPPING.md#pvsystem``).

One PVSystem per PV unit (``inverter.inverter_pieces``). ``Pmpp`` is the unit's maxP and ``irradiance`` its output
over it, so the engine gives CIM's p; ``kvar`` is q. Below the engine's default cut-out (20 % of kVA) a running PV
would be switched off, so ``%Cutout=0`` is written for it.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
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
    "irradiance": Slot("written", "the unit's output / Pmpp (get_inverter_units p, generation sign)"),
    "Pmpp": Slot("written", "the unit's maxP (kW), x 1/n for one of n phases; unset raises, a minP other than 0 "
                            "raises"),
    "pct_Cutout": Slot("rule", "0 when the output is above 0 and below the engine's 20 % of kVA, else not written"),
    "kvar": Slot("written", "the unit's share of q (generation sign: -q)"),
    "pf": Slot("not mapped", "kvar carries q"),
    "conn": Slot("written", "phaseConnection Y/Yn -> wye, D -> delta; others raise"),
    "kVA": Slot("written", f"ratedS, {_INVERTER}"),
    "kvarMax": Slot("written", f"maxQ, {_INVERTER}; unset -> not written"),
    "kvarMaxAbs": Slot("written", f"-minQ, {_INVERTER}; unset -> not written"),
    "Vminpu": Slot("written", "1 / maxIFault (the importer's rule inverted); unset -> not written"),
    "model": Slot("not mapped", "model 1, the engine's default; others raise on import"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", "untranscribed or raising on import; not in CIM"))}


def export(context) -> list[schema.Pvsystem]:
    """One PVSystem per PhotoVoltaicUnit."""
    return [_pvsystem(piece) for connection in context.objects(*CIM_CLASSES)
            for piece in inverter_pieces(connection, cim.PhotoVoltaicUnit, NAMESPACE, context.names)]


def _pvsystem(piece) -> schema.Pvsystem:
    limits = get_photovoltaic_unit(piece.unit, "kW", sign="generation")
    if limits.max_p is None or limits.max_p <= 0:
        raise ValueError(f"{describe(piece.unit)}: maxP {limits.max_p}; a PVSystem's Pmpp must be above 0")
    pmpp = limits.max_p * piece.unit_share
    if limits.min_p not in (None, 0):
        raise ValueError(f"{describe(piece.unit)}: minP {limits.min_p}; a PVSystem absorbs no power")
    if piece.p < 0:
        raise ValueError(f"{describe(piece.unit)}: p {-piece.p} kW into the PV; a PVSystem only generates")
    cutout = 0.0 if 0 < piece.p < ENGINE_CUTOUT_PERCENT / 100 * piece.slots["kVA"] else None
    return NATIVE_CLASS(name=piece.name, Pmpp=pmpp, irradiance=piece.p / pmpp, kvar=piece.q, pct_Cutout=cutout,
                        **piece.slots)
