"""TransformerTankConfiguration -> OpenDSS ``XfmrCode`` (``EXPORT_MAPPING.md#xfmrcode-t5``).

A configuration's values are read through the units that use it, since a template alone does not say its phases
(T5): every unit gives the same code. An unused configuration has no XfmrCode (a feeder package carries its
utility's whole catalogue, so most templates are its siblings'), and the skipped ones are logged. The tap range
stays on each instance.
"""

from __future__ import annotations

import logging

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_opendss.exporter import windings
from cimhub_opendss.exporter.naming import Names
from cimhub_core.export_slots import Slot, with_default
from cimhub_opendss.exporter.transformer import xfmrcode_name
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = (cim.TransformerTankConfiguration,)
NATIVE_CLASS = schema.Xfmrcode
#: the Transformer slot -> its XfmrCode spelling
RENAMED = {"XHL": "Xhl", "XHT": "Xht", "XLT": "Xlt"}
LOGGER = logging.getLogger(__name__)

_ACTIVE = "the active-winding form; the arrays carry every winding"
_NOT_IN_CIM = "untranscribed on import; not in CIM"
_TRANSFORMER = "as the Transformer's (windings.py), read through the first unit; every unit must give the same"
SLOTS = {NATIVE_CLASS: with_default(NATIVE_CLASS, {
    "name": Slot("written", "Names, the XfmrCode namespace"),
    **{slot: Slot("written", _TRANSFORMER) for slot in (
        "phases", "windings", "conns", "kVs", "kVAs", "Xhl", "Xht", "Xlt", "pct_noloadloss", "pct_imag", "wdg",
        "Rneut", "Xneut")},
    "pct_Rs": Slot("rule", f"{_TRANSFORMER}; unset r -> 0"),
    "conn": Slot("not mapped", _ACTIVE), "kV": Slot("not mapped", _ACTIVE), "kVA": Slot("not mapped", _ACTIVE),
    "tap": Slot("not mapped", _ACTIVE), "pct_R": Slot("not mapped", _ACTIVE),
    "taps": Slot("not mapped", "a tap is the instance's"), "MaxTap": Slot("not mapped", "a tap is the instance's"),
    "MinTap": Slot("not mapped", "a tap is the instance's"), "NumTaps": Slot("not mapped", "a tap is the instance's"),
    "Xscarray": Slot("not mapped", "more than 3 windings raise"),
    "pct_loadloss": Slot("not mapped", "%Rs carries the winding r"),
    "normhkVA": Slot("unset", "untranscribed on import (D9)"), "emerghkVA": Slot("unset", "untranscribed (D9)"),
    "like": Slot("not mapped", "the writer never writes like="),
}, Slot("unset", _NOT_IN_CIM))}


def export(context) -> list[schema.Xfmrcode]:
    """One XfmrCode per configuration a unit uses; an unused one is skipped and logged (T5)."""
    codes = {}
    for transformer in context.objects(*windings.TRANSFORMER_CLASSES):
        for unit in windings.units(transformer):
            if not isinstance(unit, cim.TransformerTank) or unit.TankConfiguration is None:
                continue
            configuration = unit.TankConfiguration
            code = _code(configuration, windings.read_unit(unit), context.names)
            first = codes.setdefault(configuration, code)
            if code != first:
                raise ValueError(f"{describe(configuration)}: {describe(unit)} gives other code values than an "
                                 f"earlier unit; the template must be the one source")
    unused = [configuration.mRID for configuration in context.objects(*CIM_CLASSES) if configuration not in codes]
    if unused:
        LOGGER.warning("TransformerTankConfigurations %s: no unit uses them, so no XfmrCode is written (a template "
                       "alone does not say its phases, T5)", unused)
    return list(codes.values())


def _code(configuration, unit_model: windings.UnitModel, names: Names) -> schema.Xfmrcode:
    values = windings.winding_values(unit_model)
    slots = {RENAMED.get(slot, slot): value for slot, value in values.items()}
    return NATIVE_CLASS(name=xfmrcode_name(configuration, names), **slots)
