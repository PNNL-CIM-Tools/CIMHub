"""cim18v17 network -> GDM ``DistributionSystem`` (``EXPORT_PLAN.md``, spec ``EXPORT_MAPPING.md``).

Each module in ``EXPORT_ORDER`` exports its CIM classes through the core getters, in GDM reference order: a
component exists before anything that names it. ``write_gdm`` writes the result as GDM JSON, which ``read_gdm`` and
the importer read back.
"""

from __future__ import annotations

from collections import Counter

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.base import FormatExporter
from cimhub_core.names import export_name
from gdm.systems.distribution import DistributionSystem

from cimhub_gdm.exporter import (
    bus,
    capacitor,
    der,
    fills,
    line,
    load,
    reactor,
    regulator,
    shell,
    source,
    switch,
    time_series,
    transformer,
)
from cimhub_gdm.exporter.naming import Names
from cimhub_gdm.exporter.shared import ExportContext
from cimhub_gdm.gdm_writer import write_gdm

#: Modules in export order; each has ``CIM_CLASSES``, ``SLOTS`` and ``export(obj, context)`` -> one GDM component,
#: or a tuple of them (a connection's DER, one per unit).
EXPORT_ORDER = (shell, bus, source, switch, line, reactor, transformer, regulator, load, capacitor, der)

__all__ = ["EXPORT_ORDER", "GdmExporter", "cim_to_gdm"]


class GdmExporter(FormatExporter):
    """``to_model(network, *, name_source=None, system_name=None) -> DistributionSystem``.

    ``name_source`` is the shared naming switch (``cimhub_core.names``: ``'name'``, ``'mrid'``, ``'uri'``; else
    ``$CIMHUB_NAME_SOURCE``, else ``'mrid'``). ``system_name`` names the system; without it, the one Feeder's
    exported name does, and several Feeders raise (X1). Conducting equipment of a class no module exports raises.
    Required GDM fields CIM cannot hold get the neutral values of ``fills.py``, with one WARNING (X4).

    ``time_points``: the TimePoint tables of the network's schedules (``read_time_points``, or the dict the importer
    filled); each EnergyConnectionSchedule becomes its load's series, and each load group's schedule one series
    shared by its loads (``time_series.py``). Without them, schedules are exported with no series and one WARNING.
    """

    def __init__(self, time_points: dict | None = None):
        self.time_points = time_points

    def to_model(self, network, *, name_source: str | None = None,
                 system_name: str | None = None) -> DistributionSystem:
        _check_exported(network)
        context = ExportContext(network, Names(name_source), {}, {}, Counter())
        system = DistributionSystem(name=system_name or _system_name(network, context.names.source),
                                    auto_add_composed_components=True)
        for module in EXPORT_ORDER:
            for cim_class in module.CIM_CLASSES:
                for obj in network.graph.get(cim_class, {}).values():
                    made = module.export(obj, context)
                    context.made[obj.uri()] = made
                    for component in made if isinstance(made, tuple) else (made,):
                        system.add_component(component)
        time_series.add_time_series(system, context, self.time_points)
        consumers = [obj for cls in load.CIM_CLASSES for obj in network.graph.get(cls, {}).values()]
        time_series.add_group_series(system, context, consumers, self.time_points)
        fills.warn(context.filled)
        return system


def cim_to_gdm(network, destination, *, time_points: dict | None = None, **opts) -> None:
    """Export ``network`` and write the GDM JSON file ``destination``; ``time_points`` as ``GdmExporter``, ``opts``
    go to ``to_model``."""
    write_gdm(GdmExporter(time_points).to_model(network, **opts), destination)


def _system_name(network, name_source: str) -> str:
    """The one Feeder's exported name (X1)."""
    feeders = list(network.graph.get(cim.Feeder, {}).values())
    if len(feeders) != 1:
        raise ValueError(f"{len(feeders)} Feeders {sorted(feeder.mRID for feeder in feeders)}; pass system_name= "
                         "to name the GDM system")
    return export_name(feeders[0], name_source)


def _check_exported(network) -> None:
    """Raise on conducting equipment no module exports, so nothing is dropped silently."""
    exported = {cim_class for module in EXPORT_ORDER for cim_class in module.CIM_CLASSES}
    missing = {cls.__name__: len(objects) for cls, objects in network.graph.items()
               if objects and issubclass(cls, cim.ConductingEquipment) and cls not in exported}
    if missing:
        raise ValueError(f"no GDM export yet for {dict(sorted(missing.items()))}")
