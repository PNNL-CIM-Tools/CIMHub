"""cim18v17 network -> RAW v34 records (``RAW_REWRITE_PLAN.md`` §9, spec ``docs/EXPORT_MAPPING.md``).

Each module of ``EXPORT_ORDER`` exports its CIM classes through the core getters, over the whole network (IDs are
allocated per bus and a bus's AREA is a trace). The result has the shape ``Raw34Reader.read_all()`` returns, so
``Raw34Writer`` writes a case the reader and the importer read back.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core import GraphModel
from cimhub_core.base import FormatExporter
from cimhub_raw.exporter import (area_interchange, branch, bus, case_identification, fixed_shunt, generator, load,
                                 multi_section_line, switch, switched_shunt, zone)
from cimhub_raw.exporter.area_trace import trace_areas
from cimhub_raw.exporter.identity import bus_numbers, keyed_numbers
from cimhub_raw.exporter.ratings import ratings_in_current
from cimhub_raw.raw34_writer import Raw34Writer
from cimhub_raw.schema.raw_v34 import composite_id

#: Modules in export order. Each has ``NATIVE_CLASS``, ``CIM_CLASSES`` (the conducting equipment it exports, if
#: any), ``SLOTS`` (``{native class: {slot: Slot}}``) and ``export(context) -> list[record]``.
EXPORT_ORDER = (case_identification, zone, area_interchange, bus, branch, switch, multi_section_line, load,
                fixed_shunt, switched_shunt, generator)

__all__ = ["EXPORT_ORDER", "ExportContext", "RawExporter", "cim_to_raw", "export_context", "export_tables"]

_log = logging.getLogger(__name__)


class ExportContext(NamedTuple):
    network: object
    bus_numbers: dict  # TopologicalNode -> I (internal nodes left out)
    zone_numbers: dict  # SubGeographicalRegion -> zone I
    area_numbers: dict  # ControlArea -> area I
    bus_areas: dict  # TopologicalNode -> ControlArea or None (the R5 trace)
    branch_ratings_in_current: bool  # NXFRAT: the branch and switch ratings are CurrentLimits

    def objects(self, *cim_classes: type) -> list:
        """The network's objects of ``cim_classes``, class by class in the order given."""
        return _objects(self.network, *cim_classes)


def export_context(network) -> ExportContext:
    """The numbers, the AREA trace and the units flags every module shares."""
    nodes = list(network.graph.get(cim.TopologicalNode, {}).values())
    numbers = bus_numbers(nodes)
    internal = len(nodes) - len(numbers)
    if internal:
        _log.info("%d TopologicalNode(s) without a busNumber (internal to a device) are not buses", internal)
    return ExportContext(network, numbers,
                         keyed_numbers(network.graph.get(cim.SubGeographicalRegion, {}).values(), "srgn_"),
                         keyed_numbers(network.graph.get(cim.ControlArea, {}).values(), "ca_"),
                         trace_areas(network),
                         ratings_in_current(_objects(network, *branch.CIM_CLASSES, *switch.CIM_CLASSES)))


def export_tables(network, modules) -> GraphModel:
    """The records of ``modules`` over ``network``, each with the reader's composite ID."""
    context = export_context(network)
    model = GraphModel()
    for module in modules:
        for record in module.export(context):
            composite_id.assign_composite_id(record)
            model.add_to_graph(record)
    return model


class RawExporter(FormatExporter):
    """``to_model(network) -> GraphModel`` of RAW v34 records. Conducting equipment of a class no module exports
    raises."""

    def to_model(self, network) -> GraphModel:
        _check_exported(network)
        return export_tables(network, EXPORT_ORDER)


def cim_to_raw(network, destination) -> None:
    """Export ``network`` and write the case ``destination`` (a ``.raw`` path)."""
    Raw34Writer().write(RawExporter().to_model(network), destination)


def _objects(network, *cim_classes: type) -> list:
    return [obj for cim_class in cim_classes for obj in network.graph.get(cim_class, {}).values()]


def _check_exported(network) -> None:
    """Raise on conducting equipment no module exports, so nothing is dropped silently."""
    exported = {cim_class for module in EXPORT_ORDER for cim_class in module.CIM_CLASSES}
    missing = {cls.__name__: len(objects) for cls, objects in network.graph.items()
               if objects and issubclass(cls, cim.ConductingEquipment) and cls not in exported}
    if missing:
        raise ValueError(f"no RAW export yet for {dict(sorted(missing.items()))}")
