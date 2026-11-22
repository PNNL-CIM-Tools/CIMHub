"""cim18v17 network -> ``GlmModel`` (``GLM_REWRITE_PLAN.md`` section 8, spec ``docs/EXPORT_MAPPING.md``).

Each module in ``EXPORT_ORDER`` exports its CIM classes through the core getters. The result has the shape
``GlmReader.read_all()`` returns, so ``GlmWriter`` writes a deck the reader, the importer and GridLAB-D read back.
The deck is one power flow: a ``clock`` that starts and stops at one instant, ``module powerflow`` on the NR
solver at the network's base frequency with ``line_capacitance`` on (CIM's line b is part of the model; GridLAB-D
ignores every ``c`` without it), and ``module generators`` when it holds DER. With players (X29, the caller's
``time_points``) the instant is the earliest player start, so each scheduled load is its base times the first point;
a later ``stoptime`` plays the schedule.
"""

from __future__ import annotations

from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.base import FormatExporter
from cimhub_core.getters.switch_state import STATE_ATTRIBUTE
from cimhub_gridlabd.exporter import (buses, capacitor, inverter, line, load, player, regulator, schedule,
                                      series_reactor, switch, transformer)
from cimhub_gridlabd.exporter.buses import Bus, bus_table
from cimhub_gridlabd.exporter.naming import Names
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_writer import GlmWriter, format_float
from cimhub_gridlabd.schema import gridlabd as schema

#: Modules in export order. Each has ``CIM_CLASSES`` (what it exports), ``SLOTS`` (``{GLM class: {slot: Slot}}``)
#: and ``export(context) -> list[record]`` over the whole network: a configuration is one per way lines use a
#: template, and a transformer may add a star bus, so a module cannot work object by object.
EXPORT_ORDER = (buses, line, switch, series_reactor, transformer, regulator, player, schedule, load, capacitor,
                inverter)
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
    model: GlmModel  # what the records go into: a module adds its expressions and tapes here (player, load)
    points: dict  # schedule uri -> its RegularTimePoint rows (the caller's time_points)

    def objects(self, *cim_classes: type) -> list:
        """The network's objects of ``cim_classes``, class by class in the order given."""
        return [obj for cim_class in cim_classes for obj in self.network.graph.get(cim_class, {}).values()]


class GlmExporter(FormatExporter):
    """``to_model(network, *, name_source=None, switch_state="actual") -> GlmModel``.

    ``name_source`` is the shared naming switch (``cimhub_core.names``: ``'name'``, ``'mrid'``, ``'uri'``; else
    ``$CIMHUB_NAME_SOURCE``, else ``'mrid'``). ``switch_state`` is the CIM state each switch's ``status`` reads:
    ``'actual'`` (``Switch.open``) or ``'normal'`` (``Switch.normalOpen``). Conducting equipment of a class no
    module exports raises. ``time_points`` is the caller's dict of time point tables (``cimhub_core.time_points``):
    its ``RegularTimePoint`` table gives the players their rows (X29).
    """

    def __init__(self, time_points: dict | None = None):
        self.time_points = time_points

    def to_model(self, network, *, name_source: str | None = None, switch_state: str = "actual") -> GlmModel:
        if switch_state not in STATE_ATTRIBUTE:
            raise ValueError(f"switch_state must be one of {sorted(STATE_ATTRIBUTE)}, not {switch_state!r}")
        _check_exported(network)
        names = Names(name_source)
        frequency = network.base_frequency.to("Hz")
        model = GlmModel()
        context = ExportContext(network, names, switch_state, bus_table(network, names), frequency, model,
                                _points(self.time_points))
        for module in EXPORT_ORDER:
            for record in module.export(context):
                model.add_to_graph(record)
        _set_header(model, frequency, _instant(context))
        return model


def cim_to_glm(network, destination, *, time_points: dict | None = None, **opts) -> None:
    """Export ``network`` and write the deck ``destination`` (a ``.glm`` path, its players' files beside it);
    ``opts`` go to ``to_model``."""
    GlmWriter().write(GlmExporter(time_points).to_model(network, **opts), destination)


def _points(time_points: dict | None) -> dict:
    """Schedule uri -> its ``RegularTimePoint`` rows; empty without the table."""
    if not time_points:
        return {}
    from cimhub_core.time_points import REGULAR_TIME_POINT_CLASS, rows_by_schedule  # the time-points extra

    table = time_points.get(REGULAR_TIME_POINT_CLASS)
    return {} if table is None else rows_by_schedule(table)


def _instant(context: ExportContext) -> str:
    """The clock's one instant: the earliest player start (UTC), else ``INSTANT``."""
    starts = [player.start(schedule) for schedule in context.objects(cim.ConformLoadSchedule)
              if schedule.uri() in context.points and not player.is_day(schedule)]
    if not starts:
        return INSTANT
    return f"'{min(starts):%Y-%m-%d %H:%M:%S}'"


def _set_header(model: GlmModel, frequency: float, instant: str) -> None:
    model.clock.update(timezone="UTC0", starttime=instant, stoptime=instant)
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
