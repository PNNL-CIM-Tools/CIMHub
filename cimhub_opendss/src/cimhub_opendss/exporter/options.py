"""The deck's ``Options`` record: circuit name, base frequency, voltage bases (``EXPORT_MAPPING.md#options``, E10)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.earth import get_earth_resistivity
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.schema import opendss_schema as schema


def options_record(network, names: Names, open_terminals: list[str]) -> schema.Options:
    """``circuit`` = the one Feeder's name, ``defaultbasefreq`` = the network's base frequency (Hz), ``voltagebases``
    = the distinct BaseVoltage nominal voltages (kV), ascending, ``earthmodel`` the WireConfigurations' earth
    model (``earth_model``), and the switches' ``open_terminals`` (``Class.name terminal``)."""
    feeders = list(network.graph.get(cim.Feeder, {}).values())
    if len(feeders) != 1:
        raise ValueError(f"the model has {len(feeders)} Feeders; a DSS deck is one circuit, so one is exported")
    bases = {get_qty(base, "nominalVoltage", "kV") for base in network.graph.get(cim.BaseVoltage, {}).values()}
    if None in bases:
        raise ValueError("a BaseVoltage has no nominalVoltage")
    return schema.Options(name="options", circuit=names.name(feeders[0], "Circuit"),
                          defaultbasefreq=network.base_frequency.to("Hz"), voltagebases=sorted(bases),
                          earthmodel=earth_model(network),
                          open_terminals=open_terminals or None)


#: EarthModelKind -> the DSS earthmodel
EARTH_MODELS = {cim.EarthModelKind.carson: "Carson", cim.EarthModelKind.deri: "Deri"}


def earth_model(network) -> str | None:
    """The one earth model of every WireConfiguration (``get_earth_resistivity``); DSS's earthmodel is the deck's.
    None when no configuration names one (the engine's Deri). Configurations that differ raise, and so does one
    without an EarthResistivity beside one with: it would take the other's model."""
    found = {}
    for configuration in network.graph.get(cim.WireConfiguration, {}).values():
        earth = get_earth_resistivity(configuration)
        found.setdefault(earth.model if earth is not None else None, configuration)
    if len(found) > 1:
        shown = {model.value if model is not None else None: describe(obj) for model, obj in found.items()}
        raise ValueError(f"WireConfigurations over earth models {shown}; a DSS deck has one earthmodel")
    if not found:
        return None
    [model] = found
    return EARTH_MODELS[model] if model is not None else None
