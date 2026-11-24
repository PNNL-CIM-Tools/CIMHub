"""PowerTransformer / AutoTransformer (VoltageRegulator) -> OpenDSS ``Transformer``
(``EXPORT_MAPPING.md#s6c-transformers-xfmrcode-regulators-regcontrol``).

One DSS Transformer per unit (T4). A unit on a TankConfiguration names its XfmrCode and writes only its buses
(and taps); every other form is inline (T1). The values are ``windings.py``'s.
"""

from __future__ import annotations

import re

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.limits_by_type import get_limits_by_type
from cimhub_opendss.exporter import windings
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = windings.TRANSFORMER_CLASSES
NATIVE_CLASS = schema.Transformer
XFMRCODE_NAMESPACE = "XfmrCode"

_ACTIVE = "the active-winding form; the arrays carry every winding"
_INLINE = "inline units only; a unit on a TankConfiguration takes it from its XfmrCode"
_NOT_IN_CIM = "untranscribed on import; not in CIM"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names; a one-unit transformer by itself, each tank of several by the tank (T4)"),
    "phases": Slot("written", f"3 when every winding has A, B, C, else 1 (a coil); {_INLINE}"),
    "windings": Slot("written", f"the model's windings, 2 or 3; {_INLINE}"),
    "wdg": Slot("written", "the one winding grounded through rground/xground (T6)"),
    "bus": Slot("not mapped", _ACTIVE), "conn": Slot("not mapped", _ACTIVE), "kV": Slot("not mapped", _ACTIVE),
    "kVA": Slot("not mapped", _ACTIVE), "tap": Slot("not mapped", _ACTIVE), "pct_R": Slot("not mapped", _ACTIVE),
    "Rneut": Slot("written", "rground (ohm) of winding wdg; its neutral on .4 (T6)"),
    "Xneut": Slot("written", "xground (ohm) of winding wdg"),
    "buses": Slot("written", "bus_ref of each winding's phases: a coil's N on .0; a 3-phase wye solid .1.2.3, "
                             "else .1.2.3.4 (E7, T6)"),
    "conns": Slot("written", f"connectionKind D -> delta, Y/Yn/I -> wye; AUTO: wye with a neutral; {_INLINE}"),
    "kVs": Slot("written", f"a coil's or an AutoTransformerEnd's baseU, a 3-phase winding's ratedU (kV); {_INLINE}"),
    "kVAs": Slot("written", f"a coil's baseS (AUTO: ratedS), a 3-phase winding's ratedS (kVA); {_INLINE}"),
    "taps": Slot("written", "1, and get_tap_ratio(actual) on the RatioTapChanger's winding"),
    "XHL": Slot("written", f"mesh (1,2) x, percent on winding 1's kVA; {_INLINE}"),
    "XHT": Slot("written", f"mesh (1,3) x; {_INLINE}"), "XLT": Slot("written", f"mesh (2,3) x; {_INLINE}"),
    "Xscarray": Slot("not mapped", "more than 3 windings raise"),
    "pct_loadloss": Slot("not mapped", "%Rs carries the winding r (AUTO: the mesh r halved, T7)"),
    "pct_noloadloss": Slot("written", f"the core g (percent on winding 1's kVA); unset -> not written; {_INLINE}"),
    "pct_imag": Slot("written", f"the core b (percent); unset -> not written; {_INLINE}"),
    "pct_Rs": Slot("rule", f"winding r x kVA_n / kVA_1 (AUTO: [r/2 r/2], T7); unset -> 0; {_INLINE}"),
    "MaxTap": Slot("written", "get_tap_ratio(high)"), "MinTap": Slot("written", "get_tap_ratio(low)"),
    "NumTaps": Slot("written", "highStep - lowStep"),
    "XfmrCode": Slot("written", "the unit's TankConfiguration (BY_TANK_ENDS, BY_LUGS)"),
    "normhkVA": Slot("unset", "untranscribed on import"), "emerghkVA": Slot("unset", "untranscribed"),
    "RdcOhms": Slot("rule", f"each winding's rDC (ohm), written per winding; an end has none -> not written; {_INLINE}"),
    "Seasons": Slot("rule", "the number of season ratings (season_ratings); none -> not written"),
    "Ratings": Slot("rule", "the PowerTransformer's ApparentPowerLimits of type olt_season<n> (kVA), in season "
                            "order; other types are not written; none -> not written"),
    "bank": Slot("unset", "each DSS Transformer is its own PowerTransformer (DSS-2)"),
    "enabled": Slot("written", "get_in_service(which='normal'); unset -> not written"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", _NOT_IN_CIM))}


def xfmrcode_name(configuration, names: Names) -> str:
    """The DSS name of a TransformerTankConfiguration, as its XfmrCode and every instance write it."""
    return names.name(configuration, XFMRCODE_NAMESPACE)


#: the importer's season rating types, olt_season<n> (transformer.season_limit_type)
SEASON_TYPE = re.compile(r"olt_season(\d+)")


def season_ratings(limits: dict, owner) -> dict:
    """``Seasons`` and ``Ratings`` (kVA) from ``limits`` by type (``get_limits_by_type``): the ``olt_season<n>``
    ones, in season order; empty when there are none. Seasons that are not 1..n raise, since DSS numbers them."""
    by_season = {}
    for limit_type, value in limits.items():
        match = SEASON_TYPE.fullmatch(limit_type.mRID)
        if match is not None:
            by_season[int(match.group(1))] = value
    if not by_season:
        return {}
    if sorted(by_season) != list(range(1, len(by_season) + 1)):
        raise ValueError(f"{describe(owner)}: season ratings for seasons {sorted(by_season)}; DSS's Ratings are "
                         "seasons 1..n")
    return dict(Seasons=len(by_season), Ratings=[by_season[number] for number in sorted(by_season)])


def export(context) -> list[schema.Transformer]:
    """One Transformer per unit of each transformer."""
    records = []
    for transformer in context.objects(*CIM_CLASSES):
        units = windings.units(transformer)
        for unit in units:
            records.append(_transformer(transformer, unit, len(units) > 1, context.names))
    return records


def _transformer(transformer, unit, shared: bool, names: Names) -> schema.Transformer:
    unit_model = windings.read_unit(unit)
    slots = dict(name=windings.unit_name(transformer, unit, names), buses=windings.winding_buses(unit_model, names),
                 **windings.tap_values(unit_model, shared=shared),
                 enabled=get_in_service(transformer, which="normal"),
                 **season_ratings(get_limits_by_type(transformer, cim.ApparentPowerLimit, "kVA"), transformer))
    if shared and slots.get("Ratings"):
        raise ValueError(f"{describe(transformer)}: seasonal ratings on a transformer of several units; DSS rates "
                         "each unit's Transformer")
    if unit_model.model.form in windings.TEMPLATE_FORMS:
        slots["XfmrCode"] = xfmrcode_name(unit.TankConfiguration, names)
    else:
        slots.update(windings.winding_values(unit_model))
    return NATIVE_CLASS(**slots)
