"""The deck's ``Options`` record: circuit name, base frequency, voltage bases (``EXPORT_MAPPING.md#options``, E10)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_core.getters import describe
from cimhub_core.getters.earth import get_earth_resistivity, get_network_earth
from cimhub_opendss.exporter.linegeometry import is_spacing_line
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.schema import opendss_schema as schema


def options_record(network, names: Names, open_terminals: list[str]) -> schema.Options:
    """``circuit`` = ``circuit_name``, ``defaultbasefreq`` = the network's base frequency (Hz), ``voltagebases``
    = the distinct BaseVoltage nominal voltages (kV), ascending, ``earthmodel`` the WireConfigurations' earth
    model (``earth_model``), and the switches' ``open_terminals`` (``Class.name terminal``)."""
    bases = {get_qty(base, "nominalVoltage", "kV") for base in network.graph.get(cim.BaseVoltage, {}).values()}
    if None in bases:
        raise ValueError("a BaseVoltage has no nominalVoltage")
    return schema.Options(name="options", circuit=circuit_name(network, names),
                          defaultbasefreq=network.base_frequency.to("Hz"), voltagebases=sorted(bases),
                          earthmodel=earth_model(network),
                          open_terminals=open_terminals or None)


def circuit_name(network, names: Names) -> str:
    """The one Feeder's name. Several Feeders are one circuit (one deck per substation) when they share one
    NormalEnergizingSubstation, named by it. No Feeder, or several without one Substation, raises. Among several,
    a Feeder that contains no equipment is not counted (H2): a frame model declares the Feeders of its whole area,
    and a deck holds only those whose equipment it has. A Feeder alone names the circuit even when empty (a deck of
    only its source)."""
    feeders = list(network.graph.get(cim.Feeder, {}).values())
    if len(feeders) > 1:
        feeders = [feeder for feeder in feeders if feeder.Equipments]
    if len(feeders) == 1:
        return names.name(feeders[0], "Circuit")
    substations = {feeder.NormalEnergizingSubstation for feeder in feeders}
    if len(substations) != 1 or None in substations:
        shown = sorted(describe(feeder) for feeder in feeders)
        raise ValueError(f"the model has {len(feeders)} Feeders with equipment {shown}; a DSS deck is one circuit: one "
                         f"Feeder, or Feeders of one NormalEnergizingSubstation")
    [substation] = substations
    return names.name(substation, "Circuit")


#: EarthModelKind -> the DSS earthmodel
EARTH_MODELS = {cim.EarthModelKind.carson: "Carson", cim.EarthModelKind.deri: "Deri"}


def earth_model(network) -> str | None:
    """The one earth model of every geometry WireConfiguration (one with a WireSpacing; ``get_earth_resistivity``)
    and, when there are spacing lines, of the network's one EarthResistivity (``get_network_earth``); DSS's
    earthmodel is the deck's. With no geometry at all, the network's one EarthResistivity, which no line names (the
    importer keeps a deck's ``Set earthmodel`` that way). None when none names one (the engine's Deri). Models that
    differ raise, and so does a configuration without an EarthResistivity beside one with: it would take the other's
    model."""
    found = {}
    for configuration in network.graph.get(cim.WireConfiguration, {}).values():
        if configuration.WireSpacing is None:
            continue  # a template LineCode: no earth
        earth = get_earth_resistivity(configuration)
        found.setdefault(earth.model if earth is not None else None, describe(configuration))
    if any(is_spacing_line(line) for line in network.graph.get(cim.ACLineSegment, {}).values()):
        found.setdefault(get_network_earth(network).model, "the spacing lines' EarthResistivity")
    if not found and network.graph.get(cim.EarthResistivity):
        found[get_network_earth(network).model] = "the network's EarthResistivity"
    if len(found) > 1:
        shown = {model.value if model is not None else None: owner for model, owner in found.items()}
        raise ValueError(f"WireConfigurations over earth models {shown}; a DSS deck has one earthmodel")
    if not found:
        return None
    [model] = found
    if model is None:
        return None
    if model not in EARTH_MODELS:
        raise ValueError(f"EarthModelKind {model.value!r} is not mapped ({sorted(m.value for m in EARTH_MODELS)} are)")
    return EARTH_MODELS[model]
