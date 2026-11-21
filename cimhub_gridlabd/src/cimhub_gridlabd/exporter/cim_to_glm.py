"""cim18v17 network -> ``GlmModel`` (``GLM_REWRITE_PLAN.md`` section 8, spec ``docs/EXPORT_MAPPING.md``).

Each module in ``EXPORT_ORDER`` exports its CIM classes through the core getters. The result has the shape
``GlmReader.read_all()`` returns, so ``GlmWriter`` writes a deck the reader, the importer and GridLAB-D read back.
The deck is one power flow: a ``clock`` that starts and stops at one instant, ``module powerflow`` on the NR
solver at the network's base frequency with ``line_capacitance`` on (CIM's line b is part of the model; GridLAB-D
ignores every ``c`` without it), and ``module generators`` when it holds DER.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.base import FormatExporter
from cimhub_core.getters.switch_state import STATE_ATTRIBUTE
from cimhub_gridlabd.exporter import buses, capacitor, inverter, line, load, regulator, switch, transformer
from cimhub_gridlabd.exporter.buses import Bus, bus_table
from cimhub_gridlabd.exporter.naming import Names
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_writer import GlmWriter, format_float
from cimhub_gridlabd.schema import gridlabd as schema

#: Modules in export order. Each has ``CIM_CLASSES`` (what it exports), ``SLOTS`` (``{GLM class: {slot: Slot}}``)
#: and ``export(context) -> list[record]`` over the whole network: a configuration is one per way lines use a
#: template, and a transformer may add a star bus, so a module cannot work object by object.
EXPORT_ORDER = (buses, line, switch, transformer, regulator, load, capacitor, inverter)
#: equipment no GLM object stands for: a busbar is its node's bus
NOT_EXPORTED = (cim.BusbarSection,)
#: one instant: the deck is a single power flow, not a time series
INSTANT = "'2000-01-01 00:00:00'"
DER_CLASSES = (schema.Inverter, schema.Solar, schema.Battery)

__all__ = ["EXPORT_ORDER", "GlmExporter", "cim_to_glm"]


class ExportContext(NamedTuple):
    network: object
    names: Names
    switch_state: str
    buses: dict[cim.ConnectivityNode, Bus]
    frequency: float  # Hz

    def objects(self, *cim_classes: type) -> list:
        """The network's objects of ``cim_classes``, class by class in the order given."""
        return [obj for cim_class in cim_classes for obj in self.network.graph.get(cim_class, {}).values()]


class GlmExporter(FormatExporter):
    """``to_model(network, *, name_source=None, switch_state="actual") -> GlmModel``.

    ``name_source`` is the shared naming switch (``cimhub_core.names``: ``'name'``, ``'mrid'``, ``'uri'``; else
    ``$CIMHUB_NAME_SOURCE``, else ``'mrid'``). ``switch_state`` is the CIM state each switch's ``status`` reads:
    ``'actual'`` (``Switch.open``) or ``'normal'`` (``Switch.normalOpen``). Conducting equipment of a class no
    module exports raises.
    """

    def to_model(self, network, *, name_source: str | None = None, switch_state: str = "actual") -> GlmModel:
        if switch_state not in STATE_ATTRIBUTE:
            raise ValueError(f"switch_state must be one of {sorted(STATE_ATTRIBUTE)}, not {switch_state!r}")
        _check_exported(network)
        names = Names(name_source)
        frequency = network.base_frequency.to("Hz")
        context = ExportContext(network, names, switch_state, bus_table(network, names), frequency)
        model = GlmModel()
        for module in EXPORT_ORDER:
            for record in module.export(context):
                model.add_to_graph(record)
        _set_header(model, frequency)
        return model


def cim_to_glm(network, destination, **opts) -> None:
    """Export ``network`` and write the deck ``destination`` (a ``.glm`` path); ``opts`` go to ``to_model``."""
    GlmWriter().write(GlmExporter().to_model(network, **opts), destination)


def _set_header(model: GlmModel, frequency: float) -> None:
    model.clock.update(timezone="UTC0", starttime=INSTANT, stoptime=INSTANT)
    model.globals["relax_naming_rules"] = "1"
    model.modules["powerflow"] = {"solver_method": "NR", "nominal_frequency": format_float(frequency),
                                  "line_capacitance": "TRUE"}
    if any(model.count(cls) for cls in DER_CLASSES):
        model.modules["generators"] = {}


def _check_exported(network) -> None:
    """Raise on conducting equipment no module exports, so nothing is dropped silently."""
    exported = {cim_class for module in EXPORT_ORDER for cim_class in module.CIM_CLASSES} | set(NOT_EXPORTED)
    missing = {cls.__name__: len(objects) for cls, objects in network.graph.items()
               if objects and issubclass(cls, cim.ConductingEquipment) and cls not in exported}
    if missing:
        raise ValueError(f"no GLM export yet for {dict(sorted(missing.items()))}")
