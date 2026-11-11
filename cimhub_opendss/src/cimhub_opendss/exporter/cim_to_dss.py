"""cim18v17 network -> ``DssModel`` (``DSS_REWRITE_PLAN.md`` section 8, spec ``docs/EXPORT_MAPPING.md``).

Each module in ``EXPORT_ORDER`` exports its CIM classes through the core getters. The result has the shape
``DssReader.read_all()`` returns, so ``DssWriter`` writes a deck the reader and the importer read back.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.base import FormatExporter
from cimhub_core.names import export_name
from cimhub_opendss.dss_reader import DssModel
from cimhub_opendss.dss_writer import DssWriter
from cimhub_opendss.exporter import (buscoords, capacitor, capcontrol, generator, line, linecode, linegeometry, load,
                                     pvsystem, reactor, regcontrol, storage, switch, transformer, vsource, wire,
                                     xfmrcode)
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.exporter.options import options_record

#: Modules in export order. Each has ``CIM_CLASSES`` (what it exports), ``SLOTS`` (``{DSS class: {slot: Slot}}``)
#: and ``export(context) -> list[record]`` over the whole network: a LineGeometry is one per (WireConfiguration,
#: offset) over the lines, so a module cannot work object by object.
EXPORT_ORDER = (vsource, wire, linecode, linegeometry, line, switch, xfmrcode, transformer, regcontrol, load, capacitor,
                capcontrol, pvsystem, storage, generator, reactor, buscoords)

__all__ = ["DssExporter", "EXPORT_ORDER", "cim_to_dss"]


class ExportContext(NamedTuple):
    network: object
    names: Names
    circuit_source: cim.EnergySource

    def objects(self, *cim_classes: type) -> list:
        """The network's objects of ``cim_classes``, class by class in the order given."""
        return [obj for cim_class in cim_classes for obj in self.network.graph.get(cim_class, {}).values()]


class DssExporter(FormatExporter):
    """``to_model(network, *, name_source=None, circuit_source="source") -> DssModel``.

    ``name_source`` is the shared naming switch (``cimhub_core.names``: ``'name'``, ``'mrid'``, ``'uri'``; else
    ``$CIMHUB_NAME_SOURCE``, else ``'mrid'``). ``circuit_source`` names the EnergySource written as ``New Circuit``
    when there are several (E2). Conducting equipment of a class no module exports raises.
    """

    def to_model(self, network, *, name_source: str | None = None, circuit_source: str = "source") -> DssModel:
        _check_exported(network)
        names = Names(name_source)
        context = ExportContext(network, names, _circuit_source(network, names.source, circuit_source))
        model = DssModel()
        for module in EXPORT_ORDER:
            for record in module.export(context):
                model.add_to_graph(record)
        model.add_to_graph(options_record(network, names, switch.open_terminals(context)))
        return model


def cim_to_dss(network, destination, *, per_class: bool = False, **opts) -> None:
    """Export ``network`` and write the deck ``destination`` (a ``.dss`` path), one file per DSS class beside it
    when ``per_class`` (``DssWriter.write``); ``opts`` go to ``to_model``."""
    DssWriter().write(DssExporter().to_model(network, **opts), destination, per_class=per_class)


def _circuit_source(network, name_source: str, circuit_source: str) -> cim.EnergySource:
    """The only EnergySource, or the one exported under ``circuit_source`` (E2)."""
    sources = list(network.graph.get(cim.EnergySource, {}).values())
    if len(sources) == 1:
        return sources[0]
    named = [source for source in sources if export_name(source, name_source).lower() == circuit_source.lower()]
    if len(named) != 1:
        raise ValueError(f"{len(sources)} EnergySources and {len(named)} exported as {circuit_source!r} "
                         f"(name source {name_source!r}); pass circuit_source= to name the circuit's")
    return named[0]


def _check_exported(network) -> None:
    """Raise on conducting equipment no module exports, so nothing is dropped silently."""
    exported = {cim_class for module in EXPORT_ORDER for cim_class in module.CIM_CLASSES}
    missing = {cls.__name__: len(objects) for cls, objects in network.graph.items()
               if objects and issubclass(cls, cim.ConductingEquipment) and cls not in exported}
    if missing:
        raise ValueError(f"no DSS export yet for {dict(sorted(missing.items()))}")
