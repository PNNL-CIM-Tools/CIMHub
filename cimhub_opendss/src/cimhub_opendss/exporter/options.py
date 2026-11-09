"""The deck's ``Options`` record: circuit name, base frequency, voltage bases (``EXPORT_MAPPING.md#options``, E10)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.schema import opendss_schema as schema


def options_record(network, names: Names) -> schema.Options:
    """``circuit`` = the one Feeder's name, ``defaultbasefreq`` = the network's base frequency (Hz), ``voltagebases``
    = the distinct BaseVoltage nominal voltages (kV), ascending. ``earthmodel`` is not in CIM (engine default)."""
    feeders = list(network.graph.get(cim.Feeder, {}).values())
    if len(feeders) != 1:
        raise ValueError(f"the model has {len(feeders)} Feeders; a DSS deck is one circuit, so one is exported")
    bases = {get_qty(base, "nominalVoltage", "kV") for base in network.graph.get(cim.BaseVoltage, {}).values()}
    if None in bases:
        raise ValueError("a BaseVoltage has no nominalVoltage")
    return schema.Options(name="options", circuit=names.name(feeders[0], "Circuit"),
                          defaultbasefreq=network.base_frequency.to("Hz"), voltagebases=sorted(bases))
